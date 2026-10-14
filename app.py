import math
import pandas as pd
import requests
import streamlit as st

# Configuración de la página web
st.set_page_config(
    page_title="Piquis · Analista Deportivo & Modelos AI", page_icon="⚡", layout="wide"
)

st.title("🤖 Piquis · Analista Deportivo con Modelos Estadísticos")
st.markdown(
    "WebApp conectada a modelos cuantitativos: **Pitágoras, Log5, Ventaja Local, Proyecciones de Goles/Puntos, Spread, Totales y Parlays con Criterio de Kelly** orientada a **Draftea y Playdoit**."
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
        "unit": "goles",
    },
    {
        "key": "uefa.europa",
        "path": "soccer/uefa.europa",
        "name": "Europa League",
        "exp": 1.7,
        "hfa": 0.32,
        "model": "poisson",
        "unit": "goles",
    },
    {
        "key": "mex.1",
        "path": "soccer/mex.1",
        "name": "Liga MX",
        "exp": 1.7,
        "hfa": 0.38,
        "model": "poisson",
        "unit": "goles",
    },
    {
        "key": "usa.1",
        "path": "soccer/usa.1",
        "name": "MLS",
        "exp": 1.7,
        "hfa": 0.35,
        "model": "poisson",
        "unit": "goles",
    },
    {
        "key": "mlb",
        "path": "baseball/mlb",
        "name": "MLB",
        "exp": 1.83,
        "hfa": 0.24,
        "model": "points",
        "unit": "carreras",
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
        "unit": "carreras",
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
        "unit": "pts",
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
        "unit": "pts",
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
        "unit": "pts",
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
        "unit": "pts",
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
        "unit": "goles",
    },
    {
        "key": "ufc",
        "path": "mma/ufc",
        "name": "UFC",
        "exp": 1.5,
        "hfa": 0.0,
        "model": "points",
        "unit": "pts",
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
        "unit": "sets",
        "sigma": 1.0,
        "sigma_total": 1.0,
    },
]

# Sidebar de configuración
st.sidebar.header("⚙️ Opciones de Apuesta")
casa_apuestas = st.sidebar.selectbox(
    "Casa de Apuestas Objetivo:", ["Playdoit", "Draftea"]
)
banco = st.sidebar.number_input("Bankroll Inicial ($)", value=1000.0, step=100.0)
umbral_edge = (
    st.sidebar.slider("Edge Mínimo Requerido (%)", 1.0, 10.0, 2.0, 0.5) / 100.0
)

st.sidebar.markdown("---")
st.sidebar.info(
    "💡 *Nota:* Si alguna liga no tiene partidos programados para hoy en la API pública de ESPN, se mostrará limpia para evitar errores."
)


# --- 2. FUNCIONES DE DESCARGA Y MODELADO MATEMÁTICO ---
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


@st.cache_data(ttl=600)
def descargar_partidos_liga(league):
  try:
    url = f"{SITE_API}/{league['path']}/scoreboard"
    response = requests.get(url, params={"limit": 100}, timeout=10)
    if not response.ok:
      return []
    payload = response.json()
    partidos = []
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
        odds = (competition.get("odds") or [{}])[0]
        moneyline = odds.get("moneyline", {})
        point_spread = odds.get("pointSpread", {})
        total = odds.get("total", {})

        partidos.append({
            "id": competition.get("id"),
            "liga": league["name"],
            "league_key": league["key"],
            "inicio": competition.get("date"),
            "local": (home.get("team") or {}).get("displayName"),
            "visitante": (away.get("team") or {}).get("displayName"),
            "local_corto": (home.get("team") or {}).get("shortDisplayName"),
            "visitante_corto": (away.get("team") or {}).get("shortDisplayName"),
            "sede_neutral": bool(competition.get("neutralSite")),
            "ml_local": _num(
                (((moneyline.get("home") or {}).get("close") or {}).get("odds"))
            ),
            "ml_visitante": _num(
                (((moneyline.get("away") or {}).get("close") or {}).get("odds"))
            ),
            "ml_empate": _num(
                (((moneyline.get("draw") or {}).get("close") or {}).get("odds"))
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
                (((total.get("over") or {}).get("close") or {}).get("odds"))
            ),
            "under_cuota": _num(
                (((total.get("under") or {}).get("close") or {}).get("odds"))
            ),
        })
    return partidos
  except Exception:
    return []


@st.cache_data(ttl=600)
def descargar_posiciones_liga(league):
  try:
    url = f"{STANDINGS_API}/{league['path']}/standings"
    response = requests.get(url, timeout=10)
    if not response.ok:
      return {}
    payload = response.json()
    entries = []
    for child in payload.get("children", []):
      entries.extend((child.get("standings") or {}).get("entries", []))
    if not entries:
      entries = (payload.get("standings") or {}).get("entries", [])

    tabla = {}
    for entry in entries:
      stats = {s.get("name"): s.get("value", 0) for s in entry.get("stats", [])}
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
          "wins": wins,
          "losses": losses,
      }
    return tabla
  except Exception:
    return {}


# Fórmulas de modelado
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


def implicita(cuota_americana):
  decimal = americana_a_decimal(cuota_americana)
  return 1 / decimal if decimal else None


def quitar_vig(probabilidades):
  total = sum(probabilidades)
  return [p / total for p in probabilities] if total else probabilidades


def valor_esperado(p, decimal):
  return p * (decimal - 1) - (1 - p) if decimal and decimal > 1 else 0


def kelly(p, decimal):
  if not decimal or decimal <= 1:
    return 0
  b = decimal - 1
  return max(0.0, (p * b - (1 - p)) / b)


# --- 3. CARGA Y PROCESAMIENTO DE DATOS EN VIVO ---
with st.spinner(
    "Descargando estadísticas en vivo, rosters y calculando algoritmos de IA..."
):
  partidos_totales = []
  tablas_totales = {}
  for league in LEAGUES:
    p_liga = descargar_partidos_liga(league)
    t_liga = descargar_posiciones_liga(league)
    if p_liga:
      partidos_totales.extend(p_liga)
    if t_liga:
      tablas_totales[league["key"]] = t_liga


def analizar_partido(partido):
  league = next(
      (item for item in LEAGUES if item["key"] == partido["league_key"]), None
  )
  tabla = tablas_totales.get(partido["league_key"], {})
  if not league:
    return None

  local = tabla.get((partido["local"] or "").lower(), {"gp": 1, "pf": 1, "pa": 1})
  visitante = tabla.get(
      (partido["visitante"] or "").lower(), {"gp": 1, "pf": 1, "pa": 1}
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
  promedio = promedio_liga(tabla) or 1.2

  neutral_log5 = log5(p_pit_l, p_pit_v) if p_pit_l and p_pit_v else 0.5
  proyeccion = proyectar(
      local, visitante, promedio, league["hfa"], partido["sede_neutral"]
  )

  # Modelo final de probabilidades
  if league["model"] == "points" and proyeccion:
    sigma = league.get("sigma", 10.0)
    desde_proyeccion = norm_cdf(proyeccion["margen"] / sigma)
    p_modelo_local = (
        (neutral_log5 + desde_proyeccion) / 2
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
    mezcla = 0.35 * (neutral_log5 or 0.5) + 0.65 * split_m
    p_modelo_local = (1 - p_modelo_empate) * mezcla
    p_modelo_visitante = (1 - p_modelo_empate) * (1 - mezcla)
  else:
    p_modelo_local, p_modelo_empate, p_modelo_visitante = 0.45, 0.20, 0.35

  candidatos = []

  def agregar(mercado, seleccion, etiqueta, prob, cuota_americana):
    decimal = americana_a_decimal(cuota_americana)
    if not decimal:
      return
    ev_val = valor_esperado(prob, decimal)
    kelly_val = kelly(prob, decimal)
    edge = prob - (1 / decimal)
    if edge >= umbral_edge:
      candidatos.append({
          "mercado": mercado,
          "seleccion": seleccion,
          "etiqueta": etiqueta,
          "prob_modelo": prob,
          "cuota_decimal": decimal,
          "cuota_americana": cuota_americana,
          "edge": edge,
          "ev": ev_val,
          "kelly": kelly_val,
      })

  agregar(
      "ML",
      "local",
      f"Gana {partido['local_corto'] or partido['local']}",
      p_modelo_local,
      partido.get("ml_local"),
  )
  agregar(
      "ML",
      "visitante",
      f"Gana {partido['visitante_corto'] or partido['visitante']}",
      p_modelo_visitante,
      partido.get("ml_visitante"),
  )
  if p_modelo_empate and partido.get("ml_empate"):
    agregar(
        "1X2", "empate", "Empate", p_modelo_empate, partido.get("ml_empate")
    )

  if (
      league["model"] == "points"
      and proyeccion
      and partido.get("spread_local") is not None
  ):
    linea = partido["spread_local"]
    sigma = league.get("sigma", 10.0)
    cubre = norm_cdf((proyeccion["margen"] + linea) / sigma)
    agregar(
        "Spread",
        "local",
        f"{partido['local_corto']} {linea:+}",
        cubre,
        partido.get("spread_local_cuota"),
    )
    agregar(
        "Spread",
        "visitante",
        f"{partido['visitante_corto']} {-linea:+}",
        1 - cubre,
        partido.get("spread_visitante_cuota"),
    )

  if partido.get("total") and proyeccion:
    if league["model"] == "points":
      sigma_t = league.get("sigma_total", 12.0)
      over = 1 - norm_cdf(
          (partido["total"] - proyeccion["total"]) / sigma_t
      )
    else:
      over = prob_over(
          matriz_poisson(proyeccion["local"], proyeccion["visitante"]),
          partido["total"],
      )
    agregar(
        "Total",
        "over",
        f"Más de {partido['total']}",
        over,
        partido.get("over_cuota"),
    )
    agregar(
        "Total",
        "under",
        f"Menos de {partido['total']}",
        1 - over,
        partido.get("under_cuota"),
    )

  candidatos.sort(key=lambda c: c["ev"], reverse=True)

  return {
      "partido": f"{partido['local']} vs {partido['visitante']}",
      "liga": league["name"],
      "pitagoras_local": p_pit_l,
      "pitagoras_visitante": p_pit_v,
      "log5_local": neutral_log5,
      "proyeccion": proyeccion,
      "pick": candidatos[0] if candidatos else None,
      "candidatos": candidatos,
  }


analisis = [
    a for a in (analizar_partido(p) for p in partidos_totales) if a and a["pick"]
]

# --- 4. INTERFAZ GRÁFICA EN STREAMLIT ---
st.subheader("🎯 Panel de Picks Inteligentes (+EV)")

if analisis:
  filas = []
  for a in analisis:
    pick = a["pick"]
    filas.append({
        "Liga": a["liga"],
        "Partido": a["partido"],
        "Mercado": pick["mercado"],
        "Pick Sugerido": pick["etiqueta"],
        "Cuota": pick["cuota_americana"],
        "Prob. IA %": round(pick["prob_modelo"] * 100, 1),
        "Edge %": round(pick["edge"] * 100, 1),
        "EV %": round(pick["ev"] * 100, 1),
        "Stake Kelly ($)": round(pick["kelly"] * banco, 2),
    })

  df_picks = pd.DataFrame(filas).sort_values(by="EV %", ascending=False)
  st.dataframe(df_picks, use_container_width=True)

  st.markdown("---")
  st.subheader("📊 Desglose Analítico Detallado por Partido")

  partido_sel = st.selectbox(
      "Selecciona un evento para auditar sus métricas de IA:",
      [a["partido"] for a in analisis],
  )
  match_obj = next(a for a in analisis if a["partido"] == partido_sel)

  c1, c2, c3, c4 = st.columns(4)
  with c1:
    st.metric(
        "Pitágoras Local / Visitante",
        f"{match_obj['pitagoras_local']*100:.1f}% / {match_obj['pitagoras_visitante']*100:.1f}%",
    )
  with c2:
    st.metric("Log5 Neutral", f"{match_obj['log5_local']*100:.1f}%")
  with c3:
    if match_obj["proyeccion"]:
      st.metric(
          "Proyección Marcador",
          f"{match_obj['proyeccion']['local']:.1f} - {match_obj['proyeccion']['visitante']:.1f}",
      )
    else:
      st.metric("Proyección Marcador", "N/D")
  with c4:
    if match_obj["pick"]:
      st.metric(
          f"Mejor Apuesta para {casa_apuestas}",
          match_obj["pick"]["etiqueta"],
          delta=f"+{match_obj['pick']['ev']*100:.1f}% EV",
      )

else:
  st.warning(
      "No se encontraron picks con valor positivo superior al umbral actual"
      " contra las líneas de las casas de apuestas en este momento."
  )

st.markdown("---")
st.caption(
    "Desarrollado para Eloy Zambrano · Piquis AI Engine operando con cuotas de"
    " referencia en tiempo real."
)
