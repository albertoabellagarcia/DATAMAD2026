"""Resume las respuestas de la encuesta (CSV exportado de Google Forms) en encuesta/resultados_<fecha>.md.

El CSV no se sube: aunque es anónimo, tiene textos libres. Solo se publican los recuentos.
Uso, desde la raíz de datos-transporte:
  python encuesta/resumen_encuesta.py <respuestas.csv> --fecha AAAA-MM-DD
"""
import argparse
import pandas as pd

PREGUNTAS = {  # índice de columna -> nombre corto
    2: "Días a la semana", 3: "Mira la app", 4: "Llegó tarde en el último mes",
    5: "La app dijo una hora y llegó mucho más tarde", 6: "Se fue y pasó justo después",
    7: "Confianza en la app (1 a 5)", 8: "Sale antes por si acaso", 9: "Dejó de coger un transporte",
    11: "«Entre 19 y 26» frente a «21»", 12: "Avisaría a otros viajeros", 13: "Edad",
}


def tabla(serie, n=None):
    n = n or serie.notna().sum()
    c = serie.value_counts()
    return "\n".join(["| Respuesta | n | % |", "|---|---|---|"] +
                     [f"| {k} | {v} | {100 * v / n:.0f}% |" for k, v in c.items()])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("--fecha", required=True)
    a = ap.parse_args()
    df = pd.read_csv(a.csv)
    c = df.columns
    n = len(df)
    pct = lambda m: f"{100 * m.sum() / n:.0f}%"
    s = [f"# Resultados de la encuesta ({a.fecha})", "",
         f"{n} respuestas. Muestra de conveniencia (enlace compartido y encuestas en la calle), no representativa: "
         f"{pct(df[c[13]] == 'Menos de 25')} son menores de 25 años. Generado con `encuesta/resumen_encuesta.py`.", "",
         "## Lo principal", "",
         f"- Llegaron tarde por el transporte en el último mes: {pct(df[c[4]] != 'Ninguna vez')} (3 veces o más: {pct(df[c[4]] == '3 veces o más')}).",
         f"- La app dijo una hora y llegó mucho más tarde: {pct(df[c[5]] != 'Nunca')} alguna vez (a menudo: {pct(df[c[5]] == 'A menudo')}).",
         f"- Se fueron de la parada y pasó justo después: {pct(df[c[6]] == 'Sí')}.",
         f"- Confianza en la app: media {df[c[7]].mean():.2f} de 5.",
         f"- Salen antes por si acaso: {pct(df[c[8]] != 'No')}; 10 min o más: {pct(df[c[8]].isin(['Unos 10 minutos', '15 minutos o más']))}.",
         f"- Dejaron de coger un transporte por no fiarse: {pct(df[c[9]] == 'Sí')}.",
         f"- Ventana frente a minuto exacto: más útil {pct(df[c[11]] == 'Más útil')}, igual {pct(df[c[11]] == 'Igual de útil')}, menos {pct(df[c[11]] == 'Menos útil')}.",
         f"- Avisarían a otros viajeros: {pct(df[c[12]] == 'Sí')} sí, {pct(df[c[12]] == 'Depende')} depende.", "",
         f"Ojo: la pregunta de «mucho más tarde» empuja hacia el sí; el {pct(df[c[5]] != 'Nunca')} no debe defenderse como medida.", "",
         "## Transporte que usan (respuesta múltiple; % sobre personas)", "",
         tabla(df[c[1]].str.split(";").explode().str.strip(), n), ""]
    for i, nombre in PREGUNTAS.items():
        s += [f"## {nombre}", "", tabla(df[c[i]]), ""]
    x = pd.crosstab(df[c[3]], df[c[11]])
    s += ["## Ventana según si miran la app", "",
          "| Mira la app | " + " | ".join(x.columns) + " |", "|---" * (len(x.columns) + 1) + "|"] + \
         [f"| {k} | " + " | ".join(str(v) for v in fila) + " |" for k, fila in x.iterrows()] + ["",
          "Entre quienes miran siempre la app el reparto es casi igual: conviene enseñar la cifra de la app junto a la ventana, no sustituirla.", ""]
    with open(f"encuesta/resultados_{a.fecha}.md", "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(s))


if __name__ == "__main__":
    main()
