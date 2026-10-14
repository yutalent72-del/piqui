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
    initial_sidebar_state="expanded",
)

# Estilos CSS de última generación (UI/UX Premium)
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    .main { background-color: #070a13; color: #f8fafc; }
    
    /* Header principal con efecto Glowing */
    .piqui-header {
        background: linear-gradient(135deg, #1e1b4b 0%, #0f172a 100%);
        padding: 28px;
        border-radius: 20px;
        border: 1px solid #3730a3;
        box-shadow: 0 10px 30px -10px rgba(99, 102, 241, 0.3);
        margin-bottom: 25px;
    }
    
    /* Calendario en contenedor grande */
    .calendar-container {
        background-color: #0f172a;
        border: 2px solid #3b82f6;
        border-radius: 16px;
        padding: 20px;
        margin-bottom: 25px;
        box-shadow: 0 4px 20px rgba(59, 130, 246, 0.15);
    }
    
    /* Tarjetas de partidos y picks */
    .card-match {
        background: linear-gradient(145deg, #1e293b 0%, #0f172a 100%);
        padding: 24px;
        border-radius: 20px;
        margin-bottom: 22px;
        border: 1px solid #334155;
        box-shadow: 0 12px 28px -5px rgba(0, 0, 0, 0.4);
        transition: all 0.3s ease;
    }
    .card-match:hover {
        border-color: #6366f1;
        transform: translateY(-2px);
    }
    
    /* Caja de Diálogo / Voz de Piqui */
    .piqui-speech-box {
        background: linear-gradient(135deg, #111827 0%, #1e1b4b 100%);
        border-left: 5px solid #6366f1;
        padding: 18px 20px;
        border-radius: 0 14px 14px 0;
        margin-top: 16px;
        font-size: 15px;
        color: #e0e7ff;
        line-height: 1.6;
        box-shadow: inset 0 2px 4px rgba(0,0,0,0.2);
    }
    
    /* Badges visuales */
    .badge-ml { background: linear-gradient(90deg, #2563eb, #3b82f6); color: white; padding: 6px 12px; border-radius: 8px; font-size: 12px; font-weight: 800; }
    .badge-spread { background: linear-gradient(90deg, #7c3aed, #8b5cf6); color: white; padding: 6px 12px; border-radius: 8px; font-size: 12px; font-weight: 800; }
    .badge-total { background: linear-gradient(90deg, #d97706, #f59e0b); color: white; padding: 6px 12px; border-radius: 8px; font-size: 12px; font-weight: 800; }
    
    /* Métricas */
    .metric-card {
        background-color: #0f172a;
        padding: 16px;
        border-radius: 12px;
        border: 1px solid #1e293b;
        text-align: center;
    }
    </style>
""",
    unsafe_allow_html=True,
)

# Header Principal
st.markdown(
    """
    <div class="piqui-header">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
            <div>
                <h1 style="margin:0; font-size: 32px; font-weight: 800; background: linear-gradient(90deg, #818cf8, #38bdf8); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">⚡ Piquis AI Engine</h1>
                <p style="margin: 5px 0 0 0; color: #94a3b8; font-size: 15px;">Tu Analista Cuantitativo Estrella con Algoritmos de Calibración de Alta Efectividad.</p>
            </div>
            <div>
                <span style="background-color: #22c55e20; color: #4ade80; padding: 8px 16px; border-radius: 30px; font-size: 13px; font-weight: bold; border: 1px solid #22c55e40;">🟢 Modelos Sincronizados</span>
            </div>
        </div>
    </div>
""",
    unsafe_allow_html=True,
)

# Configuración de Ligas
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

# --- BLOQUE PRINCIPAL: CALENDARIO PROMINENTE ---
st.markdown('<div class="calendar-container">', unsafe_allow_html=True)
col_cal1, col_cal2 = st.columns([2, 2])

with col_cal1:
  st.markdown(
      "### 📅 Selecciona la Fecha de Análisis\n*Elige el día para el que"
      " deseas que Piqui analice la cartelera y busque cuotas de valor:*"
  )
  fecha_seleccionada = st.date_input(
      "Fecha activa", date.today(), label_visibility="collapsed"
  )
  fecha_str = fecha_seleccionada.strftime("%Y%m%d")

with col_cal2:
  st.markdown("### ⚽ Filtrar por Liga / Deporte")
  deportes_disponibles = ["Todas las Ligas"] + [l["name"] for l in LEAGUES]
  deporte_filtro = st.selectbox(
      "Deporte activo", deportes_disponibles, label_visibility="collapsed"
  )

st.markdown("</div>", unsafe_allow_html=True)

# Sidebar
st.sidebar.markdown("### 💵 Gestión de Capital (Bankroll)")
casa_apuestas = st.sidebar.selectbox(
    "Casa de Apuestas Objetivo:", ["Playdoit", "Draftea"]
)
banco = st.sidebar.number_input(
    "Bankroll Inicial ($)", value=1000.0, step=100.0, format="%.2f"
)
umbral_edge = (
    st.sidebar.slider("Edge Mínimo Requerido (%)", 0.1, 10.0, 0.5, 0.1) / 100.0
)


# --- FUNCIONES Y LÓGICA CON MAYOR EFECTIVIDAD Y CALIBRACIÓN ---
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
                    ).get("odds")
                ),
                "spread_visitante_cuota": _num(
                    (
                        (point_spread.get("away") or {}).get("close") or {}
                    ).get("odds")
                ),
                "total": _num(odds.get("overUnder")),
                "over_cuota": _num(
                    (
                        (total.get("over") or {}).get("close") or {}
                    ).get("odds")
                ),
                "under_cuota": _num(
                    (
                        (total.get("under") or {}).get("close") or {}
                    ).get("odds")
                ),
            })
    except Exception:
      pass

    try:
      url_s = f"{STANDINGS_API}/{league['path']}/standings"
      res_s = requests.get(url_s, timeout=10)
      if res_s.ok:
        pay_s = res_s.json()
        entries = []
        for child in pay_s.get("children", []):
          entries.extend((child.get("standings") or {}).get("entries", []))
        if not entries:
          entries = (pay_s.get("standings") or {}).get("entries", [])

        tabla = {}
        for entry in entries:
          stats = {
              s.get("name"): s.get("value", 0) for s in entry.get("stats", [])
          }
          wins = stats.get("wins", 0) or 0
          losses = stats.get("losses", 0) or 0
          ties = stats.get("ties", 0) or 0
          ot_losses = (
              stats.get("otLosses", stats.get("overtimeLosses", 0)) or 0
          )
          gp = (
              stats.get("gamesPlayed")
              or stats.get("games")
              or (wins + losses + ties + ot_losses)
          )
          team = entry.get("team") or {}
          if not team.get("displayName"):
            continue
          tabla[team["displayName"].lower()] = {
              "gp": gp,
              "pf": stats.get("pointsFor", 0) or 0,
              "pa": stats.get("pointsAgainst", 0) or 0,
          }
        tablas_totales[league["key"]] = tabla
    except Exception:
      pass

  return partidos_totales, tablas_totales


with st.spinner("Piqui está analizando la cartelera y ajustando los modelos..."):
  partidos_crudos, tablas_datos = descargar_datos_fecha(fecha_str)


def pitagoras(pf, pa, exp):
  if pf <= 0 and pa <= 0:
    return None
  if pf <= 0:
    return 0.0
  if pa <= 0:
    return 1.0
  return pf**exp / (pf**exp + pa**exp)


def log5(p_a, p_b):
  denom = p_a + p_b - 2 * p_a * p_b
  if denom <= 0:
    return None
  return max(0.001, min(0.999, (p_a - p_a * p_b) / denom))


def norm_cdf(z):
  return 0.5 * (1 + math.erf(z / math.sqrt(2)))


def promedio_liga(tabla):
  valores = [
      row["pf"] / row["gp"]
      for row in tabla.values()
      if row["gp"] > 0 and row["pf"] > 0
  ]
  return sum(valores) / len(valores) if valores else None


def proyectar(local, visitante, promedio, hfa, neutral=False):
  if not promedio or local["gp"] <= 0 or visitante["gp"] <= 0:
    return None
  ataque_local = local["pf"] / local["gp"]
  defensa_local = local["pa"] / local["gp"] if local["pa"] > 0 else promedio
  ataque_visitante = visitante["pf"] / visitante["gp"]
  defensa_visitante = (
      visitante["pa"] / visitante["gp"] if visitante["pa"] > 0 else promedio
  )
  ventaja = 0 if neutral else hfa
  goles_local = (
      promedio
      * (ataque_local / promedio)
      * (defensa_visitante / promedio)
      + ventaja / 2
  )
  goles_visitante = (
      promedio
      * (ataque_visitante / promedio)
      * (defensa_local / promedio)
      - ventaja / 2
  )
  return {
      "local": max(goles_local, 0),
      "visitante": max(goles_visitante, 0),
      "total": max(goles_local, 0) + max(goles_visitante, 0),
      "margen": goles_local - goles_visitante,
  }


def poisson_pmf(lam, k):
  return math.exp(-lam) * lam**k / math.factorial(k)


def matriz_poisson(lam_local, lam_visitante, max_goles=10):
  return [
      [
          poisson_pmf(max(lam_local, 0.05), i)
          * poisson_pmf(max(lam_visitante, 0.05), j)
          for j in range(max_goles + 1)
      ]
      for i in range(max_goles + 1)
  ]


def resultados_matriz(matriz):
  local = sum(
      matriz[i][j]
      for i in range(len(matriz))
      for j in range(len(matriz))
      if i > j
  )
  empate = sum(
      matriz[i][j]
      for i in range(len(matriz))
      for j in range(len(matriz))
      if i == j
  )
  visitante = sum(
      matriz[i][j]
      for i in range(len(matriz))
      for j in range(len(matriz))
      if i < j
  )
  total = local + empate + visitante
  if total == 0:
    return {"local": 0.33, "empate": 0.34, "visitante": 0.33}
  return {
      "local": local / total,
      "empate": empate / total,
      "visitante": visitante / total,
  }


def prob_over(matriz, linea):
  total = sum(sum(row) for row in matriz)
  if total == 0:
    return 0.5
  over = sum(
      matriz[i][j]
      for i in range(len(matriz))
      for j in range(len(matriz))
      if i + j > linea
  )
  return over / total


def americana_a_decimal(americana):
  if not americana:
    return None
  return 1 + americana / 100 if americana > 0 else 1 + 100 / abs(americana)


def valor_esperado(p, decimal):
  return p * (decimal - 1) - (1 - p) if decimal and decimal > 1 else 0


def kelly(p, decimal):
  if not decimal or decimal <= 1:
    return 0
  b = decimal - 1
  return max(0.0, (p * b - (1 - p)) / b)


analisis_eventos = []
for p in partidos_crudos:
  league = next(
      (item for item in LEAGUES
