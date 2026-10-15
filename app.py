from datetime import date
import itertools
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

# Estilos CSS Limpios y Profesionales
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    .main { background-color: #0b0f19; color: #f1f5f9; }
    
    .header-box {
        background: linear-gradient(135deg, #1e1b4b 0%, #0f172a 100%);
        border: 1px solid #312e81;
        padding: 24px;
        border-radius: 16px;
        margin-bottom: 20px;
    }
    
    .calendar-box {
        background-color: #111827;
        border: 1px solid #374151;
        padding: 20px;
        border-radius: 14px;
        margin-bottom: 20px;
    }
    
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
    
    .parlay-card {
        background: linear-gradient(135deg, #1e1b4b 0%, #111827 100%);
        border: 2px solid #6366f1;
        padding: 22px;
        border-radius: 16px;
        margin-bottom: 20px;
        box-shadow: 0 4px 20px rgba(99, 102, 241, 0.15);
    }
    
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
        <p style="margin: 5px 0 0 0; color: #94a3b8; font-size: 14px;">Picks directos y razonamiento matemático con cuotas oficiales sincronizadas.</p>
    </div>
""",
    unsafe_allow_html=True,
)

# Ligas Oficiales ESPN
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


def decimal_a_americano(dec):
  if not dec or dec <= 1.01:
    return "+100"
  return (
      f"+{round((dec - 1) * 100)}" if dec >= 2.0 else f"{round(-100 / (dec - 1))}"
  )


# Descarga de cartelera y cálculo de probabilidades sin vig
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

          odd_h = (ml.get("home") or {}).get("close", {}).get("odds")
          odd_a = (ml.get("away") or {}).get("close", {}).get("odds")

          dec_h = (
              (1 + odd_h / 100 if odd_h > 0 else 1 + 100 / abs(odd_h))
              if odd_h
              else None
          )
          dec_a = (
              (1 + odd_a / 100 if odd_a > 0 else 1 + 100 / abs(odd_a))
              if odd_a
              else None
          )

          prob_h, prob_a = None, None
          if dec_h and dec_a:
            iv_h, iv_a = 1 / dec_h, 1 / dec_a
            suma_vig = iv_h + iv_a
            prob_h = (iv_h / suma_vig) * 100
            prob_a = (iv_a / suma_vig) * 100

          eventos.append({
              "liga": league["name"],
              "local": (home.get("team") or {}).get("displayName"),
              "visitante": (away.get("team") or {}).get("displayName"),
              "logo_local": (home.get("team") or {}).get("logo"),
              "logo_visitante": (away.get("team") or {}).get("logo"),
              "odd_local": odd_h,
              "odd_visitante": odd_a,
              "dec_local": dec_h,
              "dec_visitante": dec_a,
              "prob_local": prob_h,
              "prob_visitante": prob_a,
          })
    except Exception:
      pass
  return eventos


with st.spinner("Sincronizando cartelera y calculando probabilidades..."):
  partidos = cargar_cartelera(fecha_str)

if filtro_liga != "Todas las Ligas":
  partidos = [p for p in partidos if p["liga"] == filtro_liga]

tab1, tab2 = st.tabs([
    "🎯 Cartelera y Picks con Razonamiento",
    "🧩 Parlays Generados por Piqui",
])

with tab1:
  st.markdown(
      f"### 🎯 Análisis y Picks Recomendados ({fecha_seleccionada})"
  )

  if partidos:
    for p in partidos:
      local = p["local"] or "Local"
      visitante = p["visitante"] or "Visitante"
      logo_l = p["logo_local"] or "https://via.placeholder.com/30"
      logo_v = p["logo_visitante"] or "https://via.placeholder.com/30"

      ph = p["prob_local"]
      pa = p["prob_visitante"]

      if ph and pa:
        if ph > pa:
          pick_recomendado = f"Gana {local} (Moneyline)"
          prob_pick = ph
          momio_pick = decimal_a_americano(p["dec_local"])
          razonamiento = (
              f"Piqui proyecta una ventaja estadística para el equipo local."
              f" El mercado le otorga una probabilidad implícita sin comisión"
              f" (*fair odds*) del **{ph:.1f}%** frente al **{pa:.1f}%** del"
              f" visitante. La cuota de mercado en **{momio_pick}** ofrece"
              " solidez matemática para respaldar al local."
          )
        else:
          pick_recomendado = f"Gana {visitante} (Moneyline)"
          prob_pick = pa
          momio_pick = decimal_a_americano(p["dec_visitante"])
          razonamiento = (
              f"Piqui identifica mejores tendencias en el cuadro visitante."
              f" Su probabilidad ajustada de victoria sin vig es del"
              f" **{pa:.1f}%**, superando el **{ph:.1f}%** del anfitrión."
              f" Respaldar al visitante a cuota **{momio_pick}** presenta una"
              " expectativa favorable."
          )
      else:
        pick_recomendado = "Sin línea definitiva configurada"
        prob_pick = 50.0
        momio_pick = "N/D"
        razonamiento = (
            "Las
