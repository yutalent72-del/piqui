from datetime import date
import math
import pandas as pd
import requests
import streamlit as st

# Configuración de la página web
st.set_page_config(
    page_title="Piquis AI · Elite Sports Betting", page_icon="⚡", layout="wide"
)

# Estilos CSS avanzados para una UI/UX ultra limpia, moderna y de nivel comercial
st.markdown("""
    <style>
    .main { background-color: #090d16; color: #f1f5f9; }
    .card-match {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        padding: 24px;
        border-radius: 16px;
        margin-bottom: 20px;
        border: 1px solid #334155;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3);
    }
    .card-match:hover { border-color: #3b82f6; }
    .ai-box {
        background-color: #111827;
        border-left: 4px solid #3b82f6;
        padding: 16px;
        border-radius: 0 12px 12px 0;
        margin-top: 12px;
        font-size: 14px;
        color: #e2e8f0;
        line-height: 1.5;
    }
    .badge-ml { background-color: #3b82f6; color: white; padding: 4px 10px; border-radius: 6px; font-size: 11px; font-weight: 700; text-transform: uppercase; }
    .badge-spread { background-color: #8b5cf6; color: white; padding: 4px 10px; border-radius: 6px; font-size: 11px; font-weight: 700; text-transform: uppercase; }
    .badge-total { background-color: #f59e0b; color: white; padding: 4px 10px; border-radius: 6px; font-size: 11px; font-weight: 700; text-transform: uppercase; }
    .metric-container {
        background-color: #1e293b;
        padding: 12px;
        border-radius: 10px;
        border: 1px solid #334155;
        text-align: center;
    }
    </style>
""", unsafe_allow_html=True)

# Encabezado principal
col_h1, col_h2 = st.columns([4, 1])
with col_h1:
  st.markdown(
      "# ⚡ Piquis AI <span style='color: #3b82f6; font-size: 20px;'>Quantitative"
      " Betting Engine</span>",
      unsafe_allow_html=True,
  )
  st.markdown(
      "Modelo predictivo especializado en **Pitágoras, Log5, Ventaja Local,"
      " Proyecciones y Kelly** optimizado para encontrar valor (+EV) en"
      " **Draftea y Playdoit**."
  )
with col_h2:
  st.markdown(
      "<div style='text-align: right; padding-top: 10px;'><span"
      " style='background-color: #22c55e20; color: #22c55e; padding: 6px 12px;"
      " border-radius: 20px; font-size: 12px; font-weight: bold;'>🟢 Sistema"
      " En Línea</span></div>",
      unsafe_allow_html=True,
  )

# --- 1. CONFIGURACIÓN DE LIGAS Y MERCADOS ---
SITE_API = "https://site.api.espn.com/apis/site/v2/sports"
STANDINGS_API = "https://site.api.espn.com/apis/v2/sports"

LEAGUES = [
    {
        "key": "uefa.champions",
        "path": "soccer/uefa.champions",
        "name": "Champions League",
        "exp": 1.7,
        "hfa": 0.32,
        "model": "poisson",
    },
    {
        "key": "uefa.europa",
        "path": "soccer/uefa.europa",
        "name": "Europa League",
        "exp": 1.7,
        "hfa": 0.32,
        "model": "poisson",
    },
    {
        "key": "mex.1",
        "path": "soccer/mex.1",
        "name": "Liga MX",
        "exp": 1.7,
        "hfa": 0.38,
        "model": "poisson",
    },
    {
        "key": "usa.1",
        "path": "soccer/usa.1",
        "name": "MLS",
        "exp": 1.7,
        "hfa": 0.35,
        "model": "poisson",
    },
    {
        "key": "mlb",
        "path": "baseball/mlb",
        "name": "MLB",
        "exp": 1.83,
        "hfa": 0.24,
        "model": "points",
        "sigma": 1.4,
        "sigma_total": 1.6,
    },
    {
        "key": "kbo",
        "path": "baseball/kbo",
        "name": "KBO",
        "exp": 1.83,
        "hfa": 0.24,
        "model": "points",
        "sigma": 1.5,
        "sigma_total": 1.7,
    },
    {
        "key": "nba",
        "path": "basketball/nba",
        "name": "NBA",
        "exp": 13.91,
        "hfa": 2.6,
        "model": "points",
        "sigma": 11.5,
        "sigma_total": 18.0,
    },
    {
        "key": "mens-college-basketball",
        "path": "basketball/mens-college-basketball",
        "name": "NCAAB",
        "exp": 11.5,
        "hfa": 3.1,
        "model": "points",
        "sigma": 10.5,
        "sigma_total": 15.0,
    },
    {
        "key": "nfl",
        "path": "football/nfl",
        "name": "NFL",
        "exp": 2.37,
        "hfa": 1.9,
        "model": "points",
        "sigma": 13.8,
        "sigma_total": 13.5,
    },
    {
        "key": "college-football",
        "path": "football/college-football",
        "name": "NCAAF",
        "exp": 2.6,
        "hfa": 2.5,
        "model": "points",
        "sigma": 14.5,
        "sigma_total": 16.0,
    },
    {
        "key": "nhl",
        "path": "hockey/nhl",
        "name": "NHL",
        "exp": 1.9,
        "hfa": 0.16,
        "model": "poisson",
    },
    {
        "key": "ufc",
        "path": "mma/ufc",
        "name": "UFC",
        "exp": 1.5,
        "hfa": 0.0,
        "model": "points",
        "sigma": 1.0,
        "sigma_total": 1.0,
    },
    {
        "key": "tennis",
        "path": "tennis/atp",
        "name": "Tenis ATP",
        "exp": 1.5,
        "hfa": 0.0,
        "model": "points",
        "sigma": 1.0,
        "sigma_total": 1.0,
    },
]

# Sidebar Interactiva
st.sidebar.markdown("### 🎛️ Panel de Control")
fecha_seleccionada = st.sidebar.date_input(
    "📅 Calendario de Partidos", date.today()
)
fecha_str = fecha_seleccionada.strftime("%Y%m%d")

deportes_disponibles = ["Todas las Ligas"] + [l["name"] for l in LEAGUES]
deporte_filtro = st.sidebar.selectbox(
    "⚽ Filtrar Deporte / Liga", deportes_disponibles
)

st.sidebar.markdown("---")
st.sidebar.markdown("### 💰 Parámetros Financieros")
casa_apuestas = st.sidebar.selectbox(
    "Casa Objetivo:", ["Playdoit", "Draftea"]
)
banco = st.sidebar.number_input(
    "Bankroll Disponible ($)", value=1000.0, step=100.0, format="%.2f"
)
umbral_edge = (
    st.sidebar.slider("Edge Mínimo Requerido (%)", 0.5, 10.0, 1.0, 0.5) / 100.0
)


# --- 2. FUNCIONES Y MATEMÁTICA ---
def _num(value):
  if isinstance(value, (int, float)):
    return float(value)
  if isinstance(value, str):
    cleaned = "".join(ch for ch in value if ch.isdigit() or ch in ".+-")
    try:
      return float(cleaned)
    except ValueError:
      return None
  return None


@st.cache_data(ttl=300)
def descargar_datos_fecha(f_str):
  partidos_totales = []
  tablas_totales = {}
  for league in LEAGUES:
    try:
      url = f"{SITE_API}/{league['path']}/scoreboard"
      response = requests.get(
          url, params={"dates": f_str, "limit": 100}, timeout=10
      )
      if response.ok:
        payload = response.json()
        for event in payload.get("events", []):
          for competition in event.get("competitions", []):
            competitors = competition.get("competitors", [])
            if len(competitors) < 2:
              continue
            home = next(
                (c for c in competitors if c.get("homeAway") == "home"),
                competitors[0],
            )
            away = next(
                (c for c in competitors if c.get("homeAway") == "away"),
                competitors[1],
            )

            team_h = home.get("team") or {}
            team_a = away.get("team") or {}

            odds = (competition.get("odds") or [{}])[0]
            moneyline = odds.get("moneyline", {})
            point_spread = odds.get("pointSpread", {})
            total = odds.get("total", {})

            partidos_totales.append({
                "id": competition.get("id"),
                "liga": league["name"],
                "league_key": league["key"],
                "inicio": competition.get("date"),
                "local": team_h.get("displayName"),
                "visitante": team_a.get("displayName"),
                "local_corto": team_h.get("shortDisplayName"),
                "visitante_corto": team_a.get("shortDisplayName"),
                "logo_local": team_h.get("logo"),
                "logo_visitante": team_a.get("logo"),
                "sede_neutral": bool(competition.get("neutralSite")),
                "ml_local": _num(
                    (
                        (moneyline.get("home") or {}).get("close") or {}
                    ).get("odds")
                ),
                "ml_visitante": _num(
                    (
                        (moneyline.get("away") or {}).get("close") or {}
                    ).get("odds")
                ),
                "ml_empate": _num(
                    (
                        (moneyline.get("draw") or {}).get("close") or {}
                    ).get("odds")
                ),
                "spread_local": _num(
                    (
                        (point_spread.get("home") or {}).get("close") or {}
                    ).get("line")
                ),
                "spread_local_cuota": _num(
                    (
                        (point_spread.get("home") or {}).get("close") or {}
                    ).get("
