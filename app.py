import pandas as pd
import numpy as np
import streamlit as st

# Configuración de la página
st.set_page_config(
    page_title="AI Sports Betting & Analytics", page_icon="📈", layout="wide"
)

st.title("🤖 AI Sports Betting Model & Value Finder")
st.markdown(
    "Modelo analítico especializado para cálculo de **Pitágoras, Log5, Ventaja Local y Proyecciones de Spread/Totales** orientado a Draftea y Playdoit."
)

# Sidebar para navegación y filtros
st.sidebar.header("⚙️ Configuración del Modelo")
deporte_seleccionado = st.sidebar.selectbox(
    "Selecciona el Deporte:",
    [
        "Fútbol (Liga MX / USA / EUR)",
        "MLB / KBO",
        "NBA / NCAAB",
        "NFL / NCAAF",
        "UFC",
        "Tenis",
        "NHL",
    ],
)

casa_apuestas = st.sidebar.selectbox(
    "Casa de Apuestas Objetivo:", ["Playdoit", "Draftea"]
)

st.sidebar.markdown("---")
st.sidebar.info(
    "💡 *Consejo:* El modelo compara la línea proyectada de la IA contra la línea de la casa para detectar valor (+EV)."
)

# Simulación de Base de Datos / Carga de Partidos del Día
@st.cache_data
def cargar_partidos_ejemplo():
    data = {
        "Deporte": [
            "Fútbol (Liga MX / USA / EUR)",
            "MLB / KBO",
            "NBA / NCAAB",
            "NFL / NCAAF",
            "UFC",
        ],
        "Partido": [
            "América vs. Rayados",
            "Yankees vs. Dodgers",
            "Celtics vs. Lakers",
            "Chiefs vs. 49ers",
            "Islam Makhachev vs. Charles Oliveira",
        ],
        "Cuota Casa (Playdoit/Draftea)": [1.95, 1.85, 2.10, 1.90, 2.05],
        "Probabilidad IA (%)": [58.5, 52.0, 54.0, 51.5, 62.0],
        "Pick Sugerido": [
            "América ML / Over 2.5",
            "Yankees -1.5",
            "Celtics -4.5",
            "Over 48.5",
            "Makhachev por Sumisión",
        ],
        "Valor Esperado (+EV)": [
            "+8.3%",
            "+4.2%",
            "+6.1%",
            "+2.2%",
            "+12.1%",
        ],
    }
    return pd.DataFrame(data)


df_partidos = cargar_partidos_ejemplo()

# Filtrar por deporte seleccionado
df_filtrado = df_partidos[df_partidos["Deporte"] == deporte_seleccionado]

# Visualización en la WebApp
st.subheader(f"📊 Análisis y Picks de IA para: {deporte_seleccionado}")

if not df_filtrado.empty:
    st.dataframe(
        df_filtrado[["Partido", "Pick Sugerido", "Cuota Casa (Playdoit/Draftea)", "Probabilidad IA (%)", "Valor Esperado (+EV)"]],
        use_container_width=True,
    )

    st.markdown("---")
    st.subheader("🔬 Desglose de Métricas del Partido Seleccionado")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(label="Expectativa Pitagórica", value="0.642 vs 0.510")
    with col2:
        st.metric(label="Log5 (Prob. H2H)", value="58.5%")
    with col3:
        st.metric(label="Ventaja Local (HFA)", value="+3.2 pts / %")
    with col4:
        st.metric(label="Spread Proyectado IA", value="-4.5 pts")

    st.success(
        f"✅ **Pick Recomendado con mayor eficiencia para {casa_apuestas}:** "
        f"{df_filtrado.iloc[0]['Pick Sugerido']} (Edge detectado: {df_filtrado.iloc[0]['Valor Esperado (+EV)']})"
    )
else:
    st.warning(
        "No hay partidos cargados en este momento para esta categoría o se está esperando la actualización de los rosters y H2H."
    )
