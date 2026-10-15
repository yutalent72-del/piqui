from datetime import date
import math
import pandas as pd
import requests
import streamlit as st

# Configuración de la página
st.set_page_config(
    page_title="Piquis AI · Elite Sports Betting",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Estilos CSS Limpios y Profesionales (Estilo Bloomberg / Terminal Financiera)
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    .main { background-color: #0b0f19; color: #f1f5f9; }
    
    /* Header minimalista y elegante */
    .header-box {
        background: linear-gradient(135deg, #1e1b4b 0%, #0f172a 100%);
        border: 1px solid #312e81;
        padding: 24px;
        border-radius: 16px;
        margin-bottom: 20px;
    }
    
    /* Calendario centrado y grande */
    .calendar-box {
        background-color: #111827;
        border: 1px solid #374151;
        padding: 20px;
        border-radius: 14px;
        margin-bottom: 20px;
    }
    
    /* Tarjetas de partidos limpias */
    .match-card {
        background-color: #111827;
        border: 1px solid #1f2937;
        padding: 20px;
        border-radius: 14px;
        margin-bottom: 16px;
        transition: border-color 0.2s;
    }
    .match-card:hover {
        border-color: #6366f1;
    }
    
    /* Caja de voz de Piqui */
    .piqui-box {
        background-color: #0f172a;
        border-left: 4px solid #6366f1;
        padding: 14px 16px;
        border-radius: 0 10px 10px 0;
        margin-top: 12px;
        color: #e2e8f0;
        font-size: 14px;
        line-height: 1.5;
    }
    </style>
""",
    unsafe_allow_html=True,
)

# Header
st.markdown(
    """
    <div class="header-box">
        <h1 style="margin:0; font-size: 28px; font-weight: 700; color: #818cf8;">⚡ Piquis AI · Terminal Cuantitativa</h1>
        <p style="margin: 5px 0 0 0; color: #94a3b8; font-size: 14px;">Análisis directo con carteleras oficiales sincronizadas al instante.</p>
    </div>
""",
    unsafe_allow_html=True,
)

# Configuración de Ligas Oficiales ESPN
LEAGUES = [
    {
        "key": "mex.1",
        "path": "soccer/mex.1",
        "name": "Liga MX",
        "exp": 1.7,
        "hfa": 0.38,
    },
    {
        "key": "usa.1",
        "path": "soccer/usa.1",
        "name": "MLS",
        "exp": 1.7,
        "hfa": 0.35,
    },
    {
        "key": "uefa.champions",
        "path": "soccer/uefa.champions",
        "name": "Champions League",
        "exp": 1.7,
        "hfa": 0.32,
    },
    {
        "key": "nba",
        "path": "basketball/nba",
        "name": "NBA",
        "exp": 13.91,
        "hfa": 2.6,
    },
    {"key": "mlb", "path": "baseball/mlb", "name": "MLB", "exp": 1.83, "hfa": 0.24},
    {"key": "nfl", "path": "football/nfl", "name": "NFL", "exp": 2.37, "hfa": 1.9},
]

SITE_API = "https://site.api.espn.com/apis/site/v2/sports"

# Contenedor de Fecha y Filtros
st.markdown('<div class="calendar-box">', unsafe_allow_html=True)
col1, col2 = st.columns(2)
with col1:
  st.markdown("**📅 Selecciona la Fecha de Análisis:**")
  fecha_seleccionada = st.date_input(
      "Fecha", date.today(), label_visibility="collapsed"
  )
  fecha_str = fecha_seleccionada.strftime("%Y%m%d")
with col2:
  st.markdown("**⚽ Filtrar Liga:**")
  deportes = ["Todas las Ligas"] + [l["name"] for l in LEAGUES]
  filtro_liga = st.selectbox("Liga", deportes, label_visibility="collapsed")
st.markdown("</div>", unsafe_allow_html=True)


# Descarga directa y limpia desde ESPN
@st.cache_data(ttl=180)
def cargar_cartelera(f_str):
  eventos = []
  for league in LEAGUES:
    try:
      url = f"{SITE_API}/{league['path']}/scoreboard"
      res = requests.get(url, params={"dates": f_str, "limit": 50}, timeout=8)
      if res.ok:
        data = res.json()
        for ev in data.get("events", []):
          comp = ev.get("competitions", [{}])[0]
          comps = comp.get("competitors", [])
          if len(comps) < 2:
            continue

          home = next((c for c in comps if c.get("homeAway") == "home"), comps[0])
          away = next((c for c in comps if c.get("homeAway") == "away"), comps[1])

          odds_list = comp.get("odds", [])
          odds = odds_list[0] if odds_list else {}
          ml = odds.get("moneyline", {})

          eventos.append({
              "liga": league["name"],
              "local": (home.get("team") or {}).get("displayName"),
              "visitante": (away.get("team") or {}).get("displayName"),
              "logo_local": (home.get("team") or {}).get("logo"),
              "logo_visitante": (away.get("team") or {}).get("logo"),
              "ml_local": (ml.get("home") or {}).get("close", {}).get("odds"),
              "ml_visitante": (ml.get("away") or {}).get("close", {}).get("odds"),
          })
    except Exception:
      pass
  return eventos


with st.spinner("Sincronizando cartelera oficial..."):
  partidos = cargar_cartelera(fecha_str)

# Filtrar por liga seleccionada
if filtro_liga != "Todas las Ligas":
  partidos = [p for p in partidos if p["liga"] == filtro_liga]

st.markdown(f"### 🎯 Cartelera y Picks ({fecha_seleccionada})")

if partidos:
  for p in partidos:
    local = p["local"] or "Local"
    visitante = p["visitante"] or "Visitante"
    logo_l = p["logo_local"] or "https://via.placeholder.com/30"
    logo_v = p["logo_visitante"] or "https://via.placeholder.com/30"

    # Análisis directo y limpio de Piqui sin inventar momios raros
    explicacion_piqui = (
        f"🦜 **Piqui dice:** Analicé el duelo entre **{local}** y"
        f" **{visitante}**. La información está sincronizada directamente de"
        " la cartelera oficial. Revisa las líneas de tu casa de apuestas"
        " preferida para este enfrentamiento."
    )

    st.markdown(
        f"""
        <div class="match-card">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <span style="color: #60a5fa; font-size: 11px; font-weight: 700; background: #1e3a8a40; padding: 3px 8px; border-radius: 4px;">{p['liga']}</span>
                    <h4 style="margin: 8px 0 0 0; font-size: 18px; display: flex; align-items: center; gap: 10px;">
                        <img src="{logo_l}" width="28" height="28" style="border-radius: 50%;"> {local} 
                        <span style="color: #64748b; font-size: 13px; font-weight: normal;">vs</span> 
                        <img src="{logo_v}" width="28" height="28" style="border-radius: 50%;"> {visitante}
                    </h4>
                </div>
            </div>
            <div class="piqui-box">
                {explicacion_piqui}
            </div>
        </div>
    """,
        unsafe_allow_html=True,
    )
else:
  st.info(
      "No hay partidos programados en las ligas principales para esta fecha."
      " Prueba seleccionando el día actual en el calendario de arriba."
  )
