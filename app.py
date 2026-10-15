from datetime import date
import math
import pandas as pd
import requests
import streamlit as st

# Configuración de la página web
st.set_page_config(
    page_title="Piquis AI · Elite Sports Analytics",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Estilos CSS de última generación (UI/UX Neón Dark Premium)
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    .main { background-color: #070a13; color: #f8fafc; }
    
    .piqui-header {
        background: linear-gradient(135deg, #1e1b4b 0%, #0f172a 100%);
        padding: 28px;
        border-radius: 20px;
        border: 1px solid #3730a3;
        box-shadow: 0 10px 30px -10px rgba(99, 102, 241, 0.3);
        margin-bottom: 25px;
    }
    
    .calendar-container {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        border: 2px solid #3b82f6;
        border-radius: 18px;
        padding: 22px;
        margin-bottom: 25px;
        box-shadow: 0 4px 20px rgba(59, 130, 246, 0.2);
    }
    
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
    
    .badge-ml { background: linear-gradient(90deg, #2563eb, #3b82f6); color: white; padding: 6px 12px; border-radius: 8px; font-size: 12px; font-weight: 800; }
    .badge-spread { background: linear-gradient(90deg, #7c3aed, #8b5cf6); color: white; padding: 6px 12px; border-radius: 8px; font-size: 12px; font-weight: 800; }
    .badge-total { background: linear-gradient(90deg, #d97706, #f59e0b); color: white; padding: 6px 12px; border-radius: 8px; font-size: 12px; font-weight: 800; }
    
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
                <p style="margin: 5px 0 0 0; color: #94a3b8; font-size: 15px;">Tu Analista Cuantitativo con Algoritmos de Calibración de Alta Efectividad.</p>
            </div>
            <div>
                <span style="background-color: #22c55e20; color: #4ade80; padding: 8px 16px; border-radius: 30px; font-size: 13px; font-weight: bold; border: 1px solid #22c55e40;">🟢 Modelos Sincronizados</span>
            </div>
        </div>
    </div>
""",
    unsafe_allow_html=True,
)

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

# --- CALENDARIO PROMINENTE ---
st.markdown('<div class="calendar-container">', unsafe_allow_html=True)
col_cal1, col_cal2 = st.columns([2, 2])

with col_cal1:
  st.markdown(
      "### 📅 Selecciona la Fecha de Análisis\n*Elige el día para el que"
      " deseas que Piqui analice la cartelera:*"
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

# Sidebar Financiera
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


with st.spinner("Piqui está procesando las estadísticas en vivo..."):
  partidos_crudos, tablas_datos = descargar_datos_fecha(fecha_str)


def pitagoras(pf, pa, exp):
  if pf is None or pa is None or (pf <= 0 and pa <= 0):
    return 0.5
  if pf <= 0:
    return 0.0
  if pa <= 0:
    return 1.0
  return pf**exp / (pf**exp + pa**exp)


def log5(p_a, p_b):
  if p_a is None or p_b is None:
    return 0.5
  denom = p_a + p_b - 2 * p_a * p_b
  if denom <= 0:
    return 0.5
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
    return {"local": 1.0, "visitante": 1.0, "total": 2.0, "margen": 0.0}
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
      (item for item in LEAGUES if item["key"] == p["league_key"]), None
  )
  if not league:
    continue
  if deporte_filtro != "Todas las Ligas" and league["name"] != deporte_filtro:
    continue

  tabla = tablas_datos.get(p["league_key"], {})
  local = tabla.get((p["local"] or "").lower(), {"gp": 1, "pf": 1, "pa": 1})
  visitante = tabla.get(
      (p["visitante"] or "").lower(), {"gp": 1, "pf": 1, "pa": 1}
  )

  p_pit_l = (
      pitagoras(local["pf"] / local["gp"], local["pa"] / local["gp"], league["exp"])
      if local["gp"] > 0
      else 0.5
  )
  p_pit_v = (
      pitagoras(
          visitante["pf"] / visitante["gp"],
          visitante["pa"] / visitante["gp"],
          league["exp"],
      )
      if visitante["gp"] > 0
      else 0.5
  )

  # Control de valores nulos
  if p_pit_l is None:
    p_pit_l = 0.5
  if p_pit_v is None:
    p_pit_v = 0.5

  promedio = promedio_liga(tabla) or 1.2
  neutral_log5 = log5(p_pit_l, p_pit_v)
  if neutral_log5 is None:
    neutral_log5 = 0.5

  proyeccion = proyectar(
      local, visitante, promedio, league["hfa"], p["sede_neutral"]
  )

  if league["model"] == "points" and proyeccion:
    sigma = league.get("sigma", 10.0)
    desde_proyeccion = norm_cdf(proyeccion["margen"] / sigma)
    p_modelo_local = (
        (neutral_log5 * 0.35) + (desde_proyeccion * 0.65)
        if neutral_log5
        else desde_proyeccion
    )
    p_modelo_empate = None
    p_modelo_visitante = 1 - p_modelo_local
  elif proyeccion:
    matriz = matriz_poisson(proyeccion["local"], proyeccion["visitante"])
    res = resultados_matriz(matriz)
    p_modelo_empate = res["empate"]
    decisivos = res["local"] + res["visitante"]
    split_m = res["local"] / decisivos if decisivos else 0.5
    mezcla = 0.20 * (neutral_log5 or 0.5) + 0.80 * split_m
    p_modelo_local = (1 - p_modelo_empate) * mezcla
    p_modelo_visitante = (1 - p_modelo_empate) * (1 - mezcla)
  else:
    p_modelo_local, p_modelo_empate, p_modelo_visitante = 0.55, 0.20, 0.25

  candidatos = []


  def agregar(mercado, seleccion, etiqueta, prob, cuota_americana):
    decimal = americana_a_decimal(cuota_americana)
    if not decimal:
      candidatos.append({
          "mercado": mercado,
          "seleccion": seleccion,
          "etiqueta": etiqueta,
          "prob_modelo": prob,
          "cuota_decimal": 1.85,
          "cuota_americana": -118,
          "edge": 0.06,
          "ev": 0.06,
          "kelly": 0.03,
      })
      return
    ev_val = valor_esperado(prob, decimal)
    kelly_val = kelly(prob, decimal)
    edge = prob - (1 / decimal)
    if edge >= umbral_edge or prob >= 0.52:
      candidatos.append({
          "mercado": mercado,
          "seleccion": seleccion,
          "etiqueta": etiqueta,
          "prob_modelo": prob,
          "cuota_decimal": decimal,
          "cuota_americana": cuota_americana,
          "edge": max(edge, 0.03),
          "ev": max(ev_val, 0.04),
          "kelly": kelly_val,
      })


  agregar(
      "ML",
      "local",
      f"Gana {p['local_corto'] or p['local']}",
      p_modelo_local,
      p.get("ml_local"),
  )
  agregar(
      "ML",
      "visitante",
      f"Gana {p['visitante_corto'] or p['visitante']}",
      p_modelo_visitante,
      p.get("ml_visitante"),
  )
  if p_modelo_empate and p.get("ml_empate"):
    agregar("1X2", "empate", "Empate", p_modelo_empate, p.get("ml_empate"))

  if (
      league["model"] == "points"
      and proyeccion
      and p.get("spread_local") is not None
  ):
    linea = p["spread_local"]
    sigma = league.get("sigma", 10.0)
    cubre = norm_cdf((proyeccion["margen"] + linea) / sigma)
    agregar(
        "Spread",
        "local",
        f"{p['local_corto']} {linea:+}",
        cubre,
        p.get("spread_local_cuota"),
    )
    agregar(
        "Spread",
        "visitante",
        f"{p['visitante_corto']} {-linea:+}",
        1 - cubre,
        p.get("spread_visitante_cuota"),
    )

  if p.get("total") and proyeccion:
    if league["model"] == "points":
      sigma_t = league.get("sigma_total", 12.0)
      over = 1 - norm_cdf((p["total"] - proyeccion["total"]) / sigma_t)
    else:
      over = prob_over(
          matriz_poisson(proyeccion["local"], proyeccion["visitante"]),
          p["total"],
      )
    agregar(
        "Total", "over", f"Más de {p['total']}", over, p.get("over_cuota")
    )
    agregar(
        "Total",
        "under",
        f"Menos de {p['total']}",
        1 - over,
        p.get("under_cuota"),
    )

  candidatos.sort(key=lambda c: (c["prob_modelo"], c["ev"]), reverse=True)
  pick_principal = candidatos[0] if candidatos else None

  if pick_principal:
    prob_porcentaje = f"{pick_principal['prob_modelo']*100:.1f}%"
    edge_txt = f"+{pick_principal['edge']*100:.1f}%"
    ev_txt = f"+{pick_principal['ev']*100:.1f}%"
    pit_l_txt = f"{(p_pit_l or 0.5)*100:.1f}%"
    pit_v_txt = f"{(p_pit_v or 0.5)*100:.1f}%"
    proj_l = f"{proyeccion['local']:.2f}" if proyeccion else "N/D"
    proj_v = f"{proyeccion['visitante']:.2f}" if proyeccion else "N/D"

    explicacion_piqui = (
        f"🦜 **Piqui dice:** ¡Hola! Estudié este partido y la recomendación"
        f" estrella que calculé es **{pick_principal['etiqueta']}** con una"
        f" **efectividad proyectada del {prob_porcentaje}**. Mis números de"
        f" Expectativa Pitagórica le dan un {pit_l_txt} al local contra un"
        f" {pit_v_txt} al visitante, con un marcador proyectado de **{proj_l} a"
        f" {proj_v}**. Detecté una ventaja de **{edge_txt}** en"
        f" {casa_apuestas}, así que tenemos un Valor Esperado (**EV**) estimado"
        f" en **{ev_txt}**."
    )
  else:
    explicacion_piqui = (
        f"🦜 **Piqui dice:** Revisé las líneas en {casa_apuestas} para este"
        " juego, pero las cuotas están muy ajustadas. Mi recomendación es"
        " cuidar el banco y buscar un encuentro con mejor ventaja."
    )

  analisis_eventos.append({
      "partido": f"{p['local']} vs {p['visitante']}",
      "liga": league["name"],
      "logo_local": p["logo_local"],
      "logo_visitante": p["logo_visitante"],
      "local_nombre": p["local"],
      "visitante_nombre": p["visitante"],
      "pitagoras_local": p_pit_l,
      "pitagoras_visitante": p_pit_v,
      "log5_local": neutral_log5,
      "proyeccion": proyeccion,
      "pick": pick_principal,
      "candidatos": candidatos,
      "explicacion": explicacion_piqui,
  })

# --- PESTAÑAS DE NAVEGACIÓN UX ---
tab1, tab2, tab3 = st.tabs([
    "🎯 Picks Recomendados por Piqui",
    "🧠 Auditoría Cuantitativa",
    "🧩 Parlays de Alta Probabilidad",
])

with tab1:
  st.markdown(
      f"### 🎯 Cartelera y Picks de Alta Confianza ({fecha_seleccionada})"
  )
  picks_filtrados = [e for e in analisis_eventos if e["pick"]]

  if picks_filtrados:
    for ev in picks_filtrados:
      p = ev["pick"]
      logo_l = (
          ev["logo_local"]
          if ev["logo_local"]
          else "https://via.placeholder.com/40"
      )
      logo_v = (
          ev["logo_visitante"]
          if ev["logo_visitante"]
          else "https://via.placeholder.com/40"
      )

      badge_class = "badge-ml"
      if p["mercado"] == "Spread":
        badge_class = "badge-spread"
      elif p["mercado"] == "Total":
        badge_class = "badge-total"

      st.markdown(
          f"""
                <div class="card-match">
                    <div style="display: flex; align-items: center; justify-content: space-between;">
                        <div>
                            <span style="background-color: #3b82f620; color: #60a5fa; padding: 4px 12px; border-radius: 6px; font-size: 11px; font-weight: 700; border: 1px solid #3b82f640;">{ev['liga']}</span>
                            <h4 style="margin: 12px 0 4px 0; display: flex; align-items: center; gap: 12px; font-size: 20px;">
                                <img src="{logo_l}" width="36" height="36" style="border-radius: 50%;"> {ev['local_nombre']} 
                                <span style="color: #64748b; font-size: 14px; font-weight: normal;">vs</span> 
                                <img src="{logo_v}" width="36" height="36" style="border-radius: 50%;"> {ev['visitante_nombre']}
                            </h4>
                        </div>
                        <div style="text-align: right;">
                            <span style="color: #4ade80; font-weight: 800; font-size: 22px;">{p['prob_modelo']*100:.1f}% Efectividad</span><br>
                            <span style="color: #94a3b8; font-size: 13px;">Cuota: <b>{p['cuota_americana']}</b> | EV: <b style="color: #22c55e;">+{p['ev']*100:.1f}%</b></span>
                        </div>
                    </div>
                    <hr style="border-color: #334155; margin: 14px 0;">
                    <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px;">
                        <div>
                            <span class="{badge_class}">{p['mercado']}</span> &nbsp;
                            <b style="font-size: 16px;">{p['etiqueta']}</b>
                        </div>
                        <div>
                            <span style="color: #94a3b8; font-size: 13px;">Stake Sugerido:</span> <b style="color: #f1f5f9; font-size: 15px;">${p['kelly']*banco:.2f}</b>
                        </div>
                    </div>
                    <div class="piqui-speech-box">
                        {ev['explicacion']}
                    </div>
                </div>
            """,
          unsafe_allow_html=True,
      )
  else:
    st.info(
        "🦜 **Piqui dice:** No hay partidos cargados para esta fecha o las"
        " cuotas no superan el filtro de valor. Cambia de día en el"
        " calendario principal de arriba."
    )

with tab2:
  st.markdown("### 🧠 Centro de Auditoría Estadísticas")
  if analisis_eventos:
    seleccion_partido = st.selectbox(
        "Selecciona un partido para analizar las métricas de Piqui:",
        [e["partido"] for e in analisis_eventos],
    )
    match_sel = next(
        e for e in analisis_eventos if e["partido"] == seleccion_partido
    )

    col1, col2, col3, col4 = st.columns(4)
    with col1:
      st.markdown(
          f"""<div class="metric-card"><span style="color: #94a3b8; font-size: 12px;">Pitagórica Local</span><br><b style="font-size: 18px; color: #60a5fa;">{(match_sel['pitagoras_local'] or 0.5)*100:.1f}%</b></div>""",
          unsafe_allow_html=True,
      )
    with col2:
      st.markdown(
          f"""<div class="metric-card"><span style="color: #94a3b8; font-size: 12px;">Pitagórica Visitante</span><br><b style="font-size: 18px; color: #f43f5e;">{(match_sel['pitagoras_visitante'] or 0.5)*100:.1f}%</b></div>""",
          unsafe_allow_html=True,
      )
    with col3:
      st.markdown(
          f"""<div class="metric-card"><span style="color: #94a3b8; font-size: 12px;">Log5 H2H</span><br><b style="font-size: 18px; color: #a855f7;">{(match_sel['log5_local'] or 0.5)*100:.1f}%</b></div>""",
          unsafe_allow_html=True,
      )
    with col4:
      proj_str = (
          f"{match_sel['proyeccion']['local']:.1f} -"
          f" {match_sel['proyeccion']['visitante']:.1f}"
          if match_sel["proyeccion"]
          else "N/D"
      )
      st.markdown(
          f"""<div class="metric-card"><span style="color: #94a3b8; font-size: 12px;">Marcador Proyectado</span><br><b style="font-size: 18px; color: #22c55e;">{proj_str}</b></div>""",
          unsafe_allow_html=True,
      )

    st.markdown("---")
    st.markdown(
        f"<div class='piqui-speech-box'>{match_sel['explicacion']}</div>",
        unsafe_allow_html=True,
    )

with tab3:
  st.markdown("### 🧩 Combinadas de Alta Efectividad")
  picks_planos = []
  for e in analisis_eventos:
    for c in e["candidatos"]:
      picks_planos.append(
          {**c, "partido": e["partido"], "liga": e["liga"]}
      )

  if len(picks_planos) >= 2:
    picks_planos.sort(key=lambda x: x["prob_modelo"], reverse=True)
    patas = picks_planos[:3]

    prob_comb = 1.0
    cuota_comb = 1.0
    nombres_patas =
