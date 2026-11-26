import streamlit as st
import pandas as pd
import os

# =====================================
# CONFIGURACIÓN
# =====================================

st.set_page_config(
    page_title="HabitaMadrid",
    page_icon="🏠",
    layout="wide"
)

# =====================================
# CARGAR DATOS
# =====================================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

csv_path = os.path.join(
    BASE_DIR,
    "data",
    "habitamadrid_dataset_final.csv"
)

df = pd.read_csv(
    csv_path,
    encoding="utf-8"
)

# =====================================
# CONVERTIR COLUMNAS NUMÉRICAS
# =====================================

columnas_numericas = [
    "score_transporte",
    "score_aire",
    "score_vivienda",
    "score_final"
]

for col in columnas_numericas:

    df[col] = (
        df[col]
        .astype(str)
        .str.replace(",", ".", regex=False)
    )

    df[col] = pd.to_numeric(
        df[col],
        errors="coerce"
    )

# =====================================
# CABECERA
# =====================================

st.title("🏠 HabitaMadrid")

st.markdown("""
Encuentra el municipio más adecuado para vivir
en la Comunidad de Madrid según tus preferencias.
""")

# =====================================
# SIDEBAR
# =====================================

st.sidebar.header("Preferencias")

perfil = st.sidebar.selectbox(
    "Selecciona un perfil",
    [
        "Personalizado",
        "🎓 Estudiante",
        "👨‍👩‍👧 Familia",
        "💼 Trabajador"
    ]
)

if perfil == "🎓 Estudiante":

    peso_vivienda = 60
    peso_transporte = 30
    peso_aire = 10

elif perfil == "👨‍👩‍👧 Familia":

    peso_vivienda = 35
    peso_transporte = 25
    peso_aire = 40

elif perfil == "💼 Trabajador":

    peso_vivienda = 25
    peso_transporte = 60
    peso_aire = 15

else:

    peso_vivienda = st.sidebar.slider(
        "🏠 Vivienda",
        0,
        100,
        40
    )

    peso_transporte = st.sidebar.slider(
        "🚇 Transporte",
        0,
        100,
        35
    )

    peso_aire = st.sidebar.slider(
        "🌿 Calidad del aire",
        0,
        100,
        25
    )

# =====================================
# CONFIGURACIÓN ACTUAL
# =====================================
st.sidebar.write(
    f"Total seleccionado: "
    f"{peso_vivienda + peso_transporte + peso_aire}%"
)

st.sidebar.info(
    "La aplicación ajusta automáticamente los pesos para el cálculo."
)

st.sidebar.markdown("---")

st.sidebar.subheader("Configuración actual")

st.sidebar.write(f"🏠 Vivienda: {peso_vivienda}%")
st.sidebar.write(f"🚇 Transporte: {peso_transporte}%")
st.sidebar.write(f"🌿 Calidad del aire: {peso_aire}%")

# =====================================
# NORMALIZAR PESOS
# =====================================

suma = (
    peso_vivienda +
    peso_transporte +
    peso_aire
)

peso_vivienda /= suma
peso_transporte /= suma
peso_aire /= suma

# =====================================
# SCORE PERSONALIZADO
# =====================================

df["score_personalizado"] = (
    peso_vivienda * df["score_vivienda"]
    + peso_transporte * df["score_transporte"]
    + peso_aire * df["score_aire"]
)

df["score_personalizado"] = (
    df["score_personalizado"]
    .round(2)
)

# =====================================
# RANKING
# =====================================

ranking = df.sort_values(
    by="score_personalizado",
    ascending=False
)

# =====================================
# GANADOR
# =====================================

mejor = ranking.iloc[0]

st.success(
    f"🏆 Municipio recomendado: {mejor['municipio']} "
    f"(Score: {mejor['score_personalizado']})"
)

st.info(
    f"""
    📌 **¿Por qué se recomienda {mejor['municipio']}?**

    Este municipio obtiene la mejor puntuación según las preferencias seleccionadas.
    La recomendación se basa en la combinación de los indicadores de vivienda,
    transporte público y calidad del aire definidos por el usuario.
    """
)

# =====================================
# TABLA
# =====================================

st.subheader("🏆 Top 10 municipios recomendados")

tabla = ranking[
    [
        "municipio",
        "score_personalizado",
        "score_vivienda",
        "score_transporte",
        "score_aire"
    ]
].copy()

tabla = tabla.round(2)

tabla.columns = [
    "Municipio",
    "Score final",
    "Vivienda",
    "Transporte",
    "Calidad aire"
]

st.dataframe(
    tabla
    .head(10)
    .reset_index(drop=True)
)

# =====================================
# GRÁFICO
# =====================================

st.subheader("📊 Comparativa de puntuaciones")

grafico = ranking.head(10).copy()

grafico = grafico.set_index("municipio")

st.bar_chart(
    grafico["score_personalizado"]
)

# =====================================
# TOP 3
# =====================================

st.subheader("🥇 Tus 3 mejores opciones")

top3 = ranking.head(3).reset_index(drop=True)

col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        label="🥇 Primera opción",
        value=top3.loc[0, "municipio"],
        delta=f"Score {top3.loc[0, 'score_personalizado']:.2f}"
    )

with col2:
    st.metric(
        label="🥈 Segunda opción",
        value=top3.loc[1, "municipio"],
        delta=f"Score {top3.loc[1, 'score_personalizado']}"
    )

with col3:
    st.metric(
        label="🥉 Tercera opción",
        value=top3.loc[2, "municipio"],
        delta=f"Score {top3.loc[2, 'score_personalizado']}"
    )
