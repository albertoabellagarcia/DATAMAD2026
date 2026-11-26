"""06 · Mapas y herramienta interactiva.

Geometría: Mapa/limites_secciones_censales_2019.zip (Seccionado_2019, EPSG:25830), secciones
disueltas por CDMUNI -> 179 municipios. El zip original no se modifica.

Capas:
  - Índice de desajuste 2025 (02_indice), con municipios de fiabilidad baja rayados.
  - Tipología (04_clustering), en paneles pequeños (uno por tipo).
  - Cursos de FP para el empleo presenciales/mixtos con municipio (capa complementaria: el 54 % de
    los presenciales y todos los de teleformación no tienen municipio).
Salidas: Mapa/municipios_cm.geojson, Mapa/mapa_indice_2025.png, Mapa/mapa_tipologia_2025.png,
         Mapa/ForMadrid_mapa.html (herramienta para ayuntamientos y academias).
"""
import json
import textwrap
import unicodedata

import folium
import geopandas as gpd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm
from matplotlib.patches import Patch

from utilidades import DATOS, RAIZ, RESULTADOS

MAPA = RAIZ / "Mapa"
ANIO = 2025
INK, INK2, MUTED, SURF, NEUTRO = "#0b0b0b", "#52514e", "#898781", "#fcfcfb", "#f0efec"
# Divergente azul (menos desajuste) <-> rojo (más desajuste), gris neutro en 0
CMAP = LinearSegmentedColormap.from_list("formadrid", ["#104281", "#3987e5", NEUTRO, "#e34948", "#8f1d1d"])
VMAX = 1.5


def normalizar(nombre: str) -> str:
    """MAYÚSCULAS sin tildes; 'Rozas de Madrid (Las)' y 'ROZAS DE MADRID (LAS)' quedan iguales."""
    s = unicodedata.normalize("NFKD", str(nombre)).encode("ascii", "ignore").decode()
    return " ".join(s.upper().replace("-", " ").split())


# ---------------------------------------------------------------- geometría municipal
sec = gpd.read_file("zip://" + str(MAPA / "limites_secciones_censales_2019.zip") + "!Seccionado_2019.shp")
mun_geo = sec.dissolve(by="CDMUNI", as_index=False)[["CDMUNI", "geometry"]].rename(columns={"CDMUNI": "cod_mun"})
assert len(mun_geo) == 179

# ---------------------------------------------------------------- datos
ind = pd.read_csv(RESULTADOS / "indice_municipios.csv", dtype={"cod_mun": str})
ind = ind[ind.anio == ANIO]
tip = pd.read_csv(RESULTADOS / "tipologia_municipios.csv", dtype={"cod_mun": str})[
    ["cod_mun", "cluster", "tipo", "baja_cualif", "alta_cualif", "temporal", "var_paro"]]
ten = pd.read_csv(RESULTADOS / "tendencias_municipios.csv", dtype={"cod_mun": str})[
    ["cod_mun", "cambio_rango_22_25"]]

cur = pd.read_csv(DATOS / "cursos_formacion_empleo.csv", sep=";", encoding="latin-1", dtype=str)
pres = cur[cur["modalidad"].map(normalizar).isin(["PRESENCIAL", "MIXTA"]) & cur["centro_municipio"].notna()]
pres = pres.assign(clave=pres["centro_municipio"].map(normalizar))
ind["clave"] = ind["municipio"].map(normalizar)
sin_cruce = sorted(set(pres["clave"]) - set(ind["clave"]))
if sin_cruce:
    raise SystemExit(f"Municipios de cursos sin cruce: {sin_cruce}. Revisar nombres antes de seguir.")
n_cursos = pres.groupby("clave").size().rename("cursos_presenciales")
familias = pres.groupby("clave")["familia_desc"].agg(
    lambda s: ", ".join(s.str.capitalize().value_counts().head(3).index))
resumen_cursos = {
    "total": len(cur), "teleformacion": int(cur["modalidad"].map(normalizar).eq("TELEFORMACION").sum()),
    "presenciales_con_municipio": len(pres), "municipios_con_cursos": int(pres["clave"].nunique()),
}
print("Cursos:", resumen_cursos)

d = (ind.merge(tip, on="cod_mun").merge(ten, on="cod_mun")
     .join(n_cursos, on="clave").join(familias.rename("familias_cursos"), on="clave"))
d["cursos_presenciales"] = d["cursos_presenciales"].fillna(0).astype(int)
d["cursos_por_1000_parados"] = 1000 * d["cursos_presenciales"] / d["paro"]
d.drop(columns="clave").to_csv(RESULTADOS / "municipios_2025_completo.csv", index=False, float_format="%.4f")
g = mun_geo.merge(d, on="cod_mun")
assert len(g) == 179

# ---------------------------------------------------------------- GeoJSON (WGS84, simplificado)
g_web = g.copy()
g_web["geometry"] = g_web.geometry.simplify(60)
g_web = g_web.to_crs(4326)
g_web.to_file(MAPA / "municipios_cm.geojson", driver="GeoJSON")


def estilo_ejes(ax):
    ax.set_axis_off()
    ax.set_facecolor(SURF)


# ---------------------------------------------------------------- PNG: índice 2025
fig, ax = plt.subplots(figsize=(7, 7.6), dpi=200)
fig.patch.set_facecolor(SURF)
norm = TwoSlopeNorm(vmin=-VMAX, vcenter=0, vmax=VMAX)
g.plot(column=g["indice"].clip(-VMAX, VMAX), cmap=CMAP, norm=norm, ax=ax, edgecolor=SURF, linewidth=0.4)
baja = g[g.fiabilidad.str.startswith("baja")]
baja.plot(ax=ax, facecolor="none", edgecolor=INK2, linewidth=0, hatch="////", alpha=0.35)
estilo_ejes(ax)
sm = plt.cm.ScalarMappable(cmap=CMAP, norm=norm)
cb = fig.colorbar(sm, ax=ax, orientation="horizontal", fraction=0.035, pad=0.01, aspect=40)
cb.set_ticks([-VMAX, 0, VMAX]); cb.set_ticklabels(["Menor desajuste", "Media", "Mayor desajuste"])
cb.ax.tick_params(labelsize=8, colors=INK2, length=0); cb.outline.set_visible(False)
x_centro = g.geometry.union_all().centroid.x
for _, r in g[g.fiabilidad.eq("alta")].nlargest(6, "indice").iterrows():
    p = r.geometry.representative_point()
    izq = p.x < x_centro  # etiquetas hacia fuera del mapa para evitar solapes
    ax.plot(p.x, p.y, "o", ms=2.5, color=INK)
    ax.annotate(r.municipio, (p.x, p.y), xytext=(-6 if izq else 6, 0), textcoords="offset points", fontsize=7,
                color=INK, ha="right" if izq else "left", va="center",
                bbox=dict(boxstyle="round,pad=0.15", fc=SURF, ec="none", alpha=0.85))
ax.set_title(f"Índice de desajuste del mercado laboral · {ANIO}", loc="left", fontsize=12, color=INK,
             fontweight="bold")
ax.legend(handles=[Patch(facecolor="none", edgecolor=INK2, hatch="////", label="< 1.000 afiliados residentes (fiabilidad baja)")],
          loc="lower left", frameon=False, fontsize=7, labelcolor=INK2)
fig.text(0.02, 0.01, "Etiquetas: 6 municipios con mayor índice (fiabilidad alta). Índice relativo: media de z-scores de "
         "déficit de empleo local, presión de paro y desajuste sectorial.\nFuente: Comunidad de Madrid (afiliados, paro "
         "registrado, secciones censales 2019). Elaboración: ForMadrid.", fontsize=6, color=MUTED)
fig.savefig(MAPA / "mapa_indice_2025.png", facecolor=SURF, bbox_inches="tight")
# Variante para diapositiva: sin título ni notas (la diapositiva ya los lleva)
ax.set_title("", loc="left")  # el título se puso con loc="left"
for t in list(fig.texts):
    t.remove()
fig.savefig(MAPA / "mapa_indice_2025_diapositiva.png", facecolor=SURF, bbox_inches="tight", pad_inches=0.05)
plt.close(fig)

# ---------------------------------------------------------------- PNG: tipología (paneles)
tipos = g[["cluster", "tipo"]].drop_duplicates().sort_values("cluster")
orden = list(tipos.itertuples(index=False))[1:] + list(tipos.itertuples(index=False))[:1]  # pequeños al final
fig, axs = plt.subplots(2, 3, figsize=(11, 8), dpi=200)
fig.patch.set_facecolor(SURF)
for ax, (cl, nombre) in zip(axs.flat, orden):
    g.plot(ax=ax, color="#e1e0d9", edgecolor=SURF, linewidth=0.3)
    sel = g[g.cluster == cl]
    sel.plot(ax=ax, color="#2a78d6" if cl else "#898781", edgecolor=SURF, linewidth=0.3)
    estilo_ejes(ax)
    pct = sel.paro.sum() / g.paro.sum()
    ax.set_title(f"{textwrap.fill(nombre, 40)}\n{len(sel)} municipios · {pct:.0%} del paro".replace(".", ","),
                 fontsize=8.5, color=INK, loc="left")
fig.suptitle(f"Tipología de municipios · {ANIO}", x=0.02, ha="left", fontsize=13, fontweight="bold", color=INK)
fig.text(0.02, 0.01, "k-means (k=5, silueta 0,24: tipología orientativa) sobre déficit de empleo, presión de paro, desajuste "
         "sectorial, cualificación, temporalidad y variación del paro 2021-2025.", fontsize=7, color=MUTED)
fig.tight_layout(rect=(0, 0.03, 1, 0.95))
fig.savefig(MAPA / "mapa_tipologia_2025.png", facecolor=SURF)
plt.close(fig)

# ---------------------------------------------------------------- HTML interactivo (folium)
def hex_indice(v):
    if pd.isna(v):
        return "#c3c2b7"
    return matplotlib.colors.to_hex(CMAP(norm(np.clip(v, -VMAX, VMAX))))


def pct(v):
    return "—" if pd.isna(v) else f"{v:.1%}".replace(".", ",")


def num(v, dec=0):
    return "—" if pd.isna(v) else f"{v:,.{dec}f}".replace(",", "X").replace(".", ",").replace("X", ".")


g_web["color"] = g_web["indice"].map(hex_indice)
g_web["t_indice"] = g_web["indice"].map(lambda v: num(v, 2))
g_web["t_rango"] = g_web["rango"].map(lambda v: f"{int(v)} / 179")
g_web["t_paro"] = g_web["paro"].map(num)
g_web["t_ratio"] = g_web["ratio_empleo"].map(lambda v: num(v, 2))
g_web["t_presion"] = g_web["comp_B_presion_paro"].map(pct)
g_web["t_sector"] = g_web["comp_C_desajuste_sectorial"].map(pct)
g_web["t_baja"] = g_web["baja_cualif"].map(pct)
g_web["t_varparo"] = g_web["var_paro"].map(pct)
g_web["t_cursos"] = g_web["cursos_presenciales"].astype(str)
g_web["familias_cursos"] = g_web["familias_cursos"].fillna("—")

campos = ["municipio", "tipo", "t_indice", "t_rango", "fiabilidad", "t_paro", "t_varparo", "t_ratio",
          "t_presion", "t_sector", "t_baja", "t_cursos", "familias_cursos"]
alias = ["Municipio", "Tipo", "Índice de desajuste", "Puesto (1 = mayor desajuste)", "Fiabilidad",
         "Paro registrado (mar-2025)", "Variación paro 2021-2025", "Empleos por afiliado residente (corregido)",
         "Presión de paro", "Parados que tendrían que cambiar de sector", "Afiliados residentes poco cualificados",
         "Cursos FP presenciales con municipio", "Familias más ofertadas"]

# Sin mapa base en línea: la herramienta funciona sin conexión y abierta como fichero local
# (los servidores de teselas de OpenStreetMap rechazan las peticiones desde file://).
URL_JS = "https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet.js"
URL_CSS = "https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet.css"
m = folium.Map(location=[40.45, -3.7], zoom_start=9, tiles=None, control_scale=True)
m.default_js = [("leaflet", URL_JS)]       # solo Leaflet (sin jQuery, Bootstrap ni iconos)
m.default_css = [("leaflet_css", URL_CSS)]
m.get_root().header.add_child(folium.Element(
    "<style>.leaflet-container { background: #f4f3ef !important; }</style>"))
minx, miny, maxx, maxy = g_web.total_bounds
m.fit_bounds([[miny, minx], [maxy, maxx]])  # encuadre automático a cualquier tamaño de pantalla
capa = folium.GeoJson(
    json.loads(g_web[["geometry", "color"] + campos].to_json()),
    name=f"Índice de desajuste {ANIO}",
    style_function=lambda f: {"fillColor": f["properties"]["color"], "color": "#ffffff", "weight": 0.6,
                              "fillOpacity": 0.85},
    highlight_function=lambda f: {"weight": 2.5, "color": "#0b0b0b"},
    tooltip=folium.GeoJsonTooltip(fields=campos, aliases=alias, sticky=True,
                                  style="font-family: system-ui, sans-serif; font-size: 12px;"),
)
capa.add_to(m)
leyenda = f"""
<div style="position: fixed; top: 12px; right: 12px; z-index: 450; background: #fcfcfb; padding: 10px 12px;
     border-radius: 6px; box-shadow: 0 1px 4px rgba(0,0,0,.2); font: 12px system-ui, sans-serif; color: #0b0b0b; max-width: 300px;">
  <b>ForMadrid · ¿dónde reforzar la formación?</b><br>
  Índice de desajuste del mercado laboral {ANIO} (relativo entre los 179 municipios)<br>
  <div style="height: 10px; margin: 6px 0 2px; border-radius: 3px;
       background: linear-gradient(90deg, #104281, #3987e5, #f0efec, #e34948, #8f1d1d);"></div>
  <div style="display:flex; justify-content: space-between; color:#52514e;"><span>Menor</span><span>Mayor</span></div>
  <div style="color:#898781; margin-top: 6px;">Pasa el ratón por un municipio para ver el detalle.
  Fiabilidad baja: &lt; 1.000 afiliados residentes. Cursos: solo presenciales con municipio
  ({resumen_cursos['presenciales_con_municipio']} de {resumen_cursos['total']}).<br>
  Fuente: Portal de Datos Abiertos de la Comunidad de Madrid · INE.</div>
</div>"""
m.get_root().html.add_child(folium.Element(leyenda))
m.get_root().header.add_child(folium.Element("<title>ForMadrid · mapa</title>"))
m.save(str(MAPA / "ForMadrid_mapa.html"))
# Incrustar Leaflet (Codigo/vendor/, licencia BSD-2) para que el HTML no dependa de ninguna CDN
VENDOR = RAIZ / "Codigo" / "vendor"
html = (MAPA / "ForMadrid_mapa.html").read_text(encoding="utf-8")
js = (VENDOR / "leaflet.js").read_text(encoding="utf-8")
css = (VENDOR / "leaflet.css").read_text(encoding="utf-8")
n_js, n_css = html.count(f'src="{URL_JS}"'), html.count(f'href="{URL_CSS}"')
assert n_js == 1 and n_css == 1, f"Referencias a Leaflet inesperadas: js={n_js}, css={n_css}"
html = html.replace(f'<script src="{URL_JS}"></script>', f"<script>{js}</script>")
html = html.replace(f'<link rel="stylesheet" href="{URL_CSS}"/>', f"<style>{css}</style>")
# (folium añade un @font-face de iconos que no se usa: no se descarga si no hay iconos)
assert '<script src="http' not in html and 'rel="stylesheet" href="http' not in html, \
    "Quedan scripts u hojas de estilo externas en el HTML"
(MAPA / "ForMadrid_mapa.html").write_text(html, encoding="utf-8")
print("Mapas guardados en", MAPA)

# Contraste oferta / necesidad (para cifras clave)
alta = d[d.fiabilidad == "alta"]
q4 = alta[alta.indice >= alta.indice.quantile(0.75)]
print(f"Cuartil superior (fiabilidad alta): {len(q4)} municipios, {int((q4.cursos_presenciales > 0).sum())} con algún "
      f"curso presencial; cursos por 1.000 parados: Q4 {1000 * q4.cursos_presenciales.sum() / q4.paro.sum():.1f} "
      f"vs resto {1000 * alta.drop(q4.index).cursos_presenciales.sum() / alta.drop(q4.index).paro.sum():.1f}")
