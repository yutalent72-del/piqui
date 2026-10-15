from datetime import datetime, timezone, timedelta
import itertools
import math
import re
import unicodedata
import requests
import streamlit as st

# ========= CONFIGURACIÓN DE LA PÁGINA =========
st.set_page_config(
    page_title="Piquis AI · Elite Sports Analytics",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Estilos CSS Neón Dark Premium
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .main { background-color: #070a13; color: #f8fafc; }
    .piqui-header {
        background: linear-gradient(135deg, #1e1b4b 0%, #0f172a 100%);
        padding: 28px; border-radius: 20px; border: 1px solid #3730a3;
        box-shadow: 0 10px 30px -10px rgba(99, 102, 241, 0.3); margin-bottom: 25px;
    }
    .calendar-container {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        border: 2px solid #3b82f6; border-radius: 18px; padding: 22px; margin-bottom: 25px;
        box-shadow: 0 4px 20px rgba(59, 130, 246, 0.2);
    }
    .card-match {
        background: linear-gradient(145deg, #1e293b 0%, #0f172a 100%);
        padding: 24px; border-radius: 20px; margin-bottom: 22px; border: 1px solid #334155;
        box-shadow: 0 12px 28px -5px rgba(0, 0, 0, 0.4); transition: all 0.3s ease;
    }
    .card-match:hover { border-color: #6366f1; transform: translateY(-2px); }
    .piqui-speech-box {
        background: linear-gradient(135deg, #111827 0%, #1e1b4b 100%);
        border-left: 5px solid #6366f1; padding: 18px 20px; border-radius: 0 14px 14px 0;
        margin-top: 16px; font-size: 15px; color: #e0e7ff; line-height: 1.6;
        box-shadow: inset 0 2px 4px rgba(0,0,0,0.2);
    }
    .badge-ml { background: linear-gradient(90deg, #2563eb, #3b82f6); color: white; padding: 6px 12px; border-radius: 8px; font-size: 12px; font-weight: 800; }
    .badge-spread { background: linear-gradient(90deg, #7c3aed, #8b5cf6); color: white; padding: 6px 12px; border-radius: 8px; font-size: 12px; font-weight: 800; }
    .badge-total { background: linear-gradient(90deg, #d97706, #f59e0b); color: white; padding: 6px 12px; border-radius: 8px; font-size: 12px; font-weight: 800; }
    .metric-card { background-color: #0f172a; padding: 16px; border-radius: 12px; border: 1px solid #1e293b; text-align: center; }
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
                <p style="margin: 5px 0 0 0; color: #94a3b8; font-size: 15px;">Modelo Cuantitativo Avanzado: Pitágoras, Log5 y Poisson con Análisis de Piqui.</p>
            </div>
            <div>
                <span style="background-color: #22c55e20; color: #4ade80; padding: 8px 16px; border-radius: 30px; font-size: 13px; font-weight: bold; border: 1px solid #22c55e40;">🟢 API Conectada</span>
            </div>
        </div>
    </div>
""",
    unsafe_allow_html=True,
)

# CLAVE DE THE ODDS API CONFIGURADA
DEFAULT_ODDS_KEY = "5833e2cadae2fa0026f1a9090481dfa5"

# ========= DICCIONARIO DE LIGAS =========
LIGAS = {
    "ligamx": (
        "Liga MX",
        "soccer_mexico_ligamx",
        "soccer/mex.1",
        "us",
        "soccer",
        1.35,
        0.30,
        0,
        1.7,
        1.6,
    ),
    "mls": (
        "MLS",
        "soccer_usa_mls",
        "soccer/usa.1",
        "us",
        "soccer",
        1.35,
        0.30,
        0,
        1.7,
        1.6,
    ),
    "epl": (
        "Premier League",
        "soccer_epl",
        "soccer/eng.1",
        "eu",
        "soccer",
        1.35,
        0.25,
        0,
        1.7,
        1.6,
    ),
    "laliga": (
        "LaLiga",
        "soccer_spain_la_liga",
        "soccer/esp.1",
        "eu",
        "soccer",
        1.35,
        0.25,
        0,
        1.7,
        1.6,
    ),
    "seriea": (
        "Serie A",
        "soccer_italy_serie_a",
        "soccer/ita.1",
        "eu",
        "soccer",
        1.35,
        0.25,
        0,
        1.7,
        1.6,
    ),
    "bundesliga": (
        "Bundesliga",
        "soccer_germany_bundesliga",
        "soccer/ger.1",
        "eu",
        "soccer",
        1.35,
        0.25,
        0,
        1.7,
        1.6,
    ),
    "ucl": (
        "Champions",
        "soccer_uefa_champs_league",
        "soccer/uefa.champions",
        "eu",
        "soccer",
        1.35,
        0.25,
        0,
        1.7,
        1.6,
    ),
    "mlb": (
        "MLB",
        "baseball_mlb",
        "baseball/mlb",
        "us",
        "points",
        1.83,
        0.15,
        0.08,
        4.2,
        4.4,
    ),
    "kbo": ("KBO", "baseball_kbo", None, "us", "points", 1.83, 0.15, 0.08, 4.2, 4.4),
    "nba": (
        "NBA",
        "basketball_nba",
        "basketball/nba",
        "us",
        "points",
        13.91,
        2.5,
        0.30,
        12,
        18,
    ),
    "ncaab": (
        "NCAAB",
        "basketball_ncaab",
        "basketball/mens-college-basketball",
        "us",
        "points",
        11.5,
        3.5,
        0.40,
        11,
        16,
    ),
    "nfl": (
        "NFL",
        "americanfootball_nfl",
        "football/nfl",
        "us",
        "points",
        2.37,
        1.8,
        0.15,
        13.5,
        13,
    ),
    "ncaaf": (
        "NCAAF",
        "americanfootball_ncaaf",
        "football/college-football",
        "us",
        "points",
        2.37,
        3.0,
        0.30,
        16,
        16,
    ),
    "nhl": (
        "NHL",
        "icehockey_nhl",
        "hockey/nhl",
        "us",
        "points",
        2.15,
        0.15,
        0.10,
        2.3,
        2.2,
    ),
}

# --- CALENDARIO PROMINENTE EN EL CUERPO ---
st.markdown('<div class="calendar-container">', unsafe_allow_html=True)
col_cal1, col_cal2 = st.columns([2, 2])

with col_cal1:
  st.markdown(
      "### 📅 Selecciona la Fecha de Análisis\n*Elige el día para el que"
      " deseas que Piqui analice la cartelera:*"
  )
  fecha_seleccionada = st.date_input(
      "Fecha activa", datetime.now().date(), label_visibility="collapsed"
  )

with col_cal2:
  st.markdown("### ⚽ Filtrar por Liga / Deporte")
  nombres_ligas = ["Todas las Ligas"] + [cfg[0] for cfg in LIGAS.values()]
  liga_filtro = st.selectbox(
      "Liga activa", nombres_ligas, label_visibility="collapsed"
  )

st.markdown("</div>", unsafe_allow_html=True)

# Sidebar Financiera
st.sidebar.markdown("### ⚙️ Configuración del Motor")
odds_api_key_input = st.sidebar.text_input(
    "The Odds API Key:", type="password", value=DEFAULT_ODDS_KEY
)
casa_apuestas = st.sidebar.selectbox("Casa Objetivo:", ["Playdoit", "Draftea"])
banco = st.sidebar.number_input("Bankroll Inicial ($)", value=1000.0, step=100.0)
mezcla_modelo = st.sidebar.slider("Peso Modelo vs Mercado", 0.1, 0.9, 0.5, 0.1)
ev_minimo = st.sidebar.slider("EV Mínimo (%)", 0.0, 5.0, 0.5, 0.5) / 100.0


# ========= FUNCIONES MATEMÁTICAS =========
def pitagoras(pf, pa, exp):
  if pf <= 0 and pa <= 0:
    return 0.5
  return pf**exp / (pf**exp + pa**exp)


def log5(a, b):
  d = a + b - 2 * a * b
  return 0.5 if d == 0 else (a - a * b) / d


def clamp(p, lo=0.02, hi=0.98):
  return max(lo, min(hi, p))


def logit(p):
  return math.log(p / (1 - p))


def sigmoid(x):
  return 1 / (1 + math.exp(-x))


def norm_cdf(z):
  return 0.5 * (1 + math.erf(z / math.sqrt(2)))


def poisson(k, l):
  return math.exp(-l) * l**k / math.factorial(k)


def a_americano(dec):
  if not dec or dec <= 1:
    return "+100"
  return (
      f"+{round((dec-1)*100)}" if dec >= 2 else f"{round(-100/(dec-1))}"
  )


def futbol_probs(lh, la):
  m = [
      [poisson(i, lh) * poisson(j, la) for j in range(11)] for i in range(11)
  ]
  home = sum(m[i][j] for i in range(11) for j in range(11) if i > j)
  draw = sum(m[i][i] for i in range(11))
  away = 1 - home - draw

  def over(line):
    return sum(
        m[i][j] for i in range(11) for j in range(11) if i + j > line
    )

  def handicap(line_local):
    win = push = 0
    for i in range(11):
      for j in range(11):
        d = i + line_local - j
        if d > 0:
          win += m[i][j]
        elif d == 0:
          push += m[i][j]
    return win + push / 2

  return home, draw, away, over, handicap


# ========= ESPN STANDINGS =========
def normalizar(s):
  s = (
      unicodedata.normalize("NFD", s or "")
      .encode("ascii", "ignore")
      .decode()
      .lower()
  )
  s = re.sub(r"[^a-z0-9 ]", " ", s)
  s = re.sub(
      r"\b(fc|cf|sc|club|de|ac|afc|cd|ud|ss|as|the|calcio)\b", " ", s
  )
  return re.sub(r"\s+", " ", s).strip()


@st.cache_data(ttl=600)
def obtener_standings(path):
  try:
    d = requests.get(
        f"https://site.api.espn.com/apis/v2/sports/{path}/standings",
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=15,
    ).json()
  except Exception:
    return []
  entries = []

  def recorrer(n):
    entries.extend(n.get("standings", {}).get("entries", []))
    for c in n.get("children", []):
      recorrer(c)

  recorrer(d)
  equipos = []
  for e in entries:
    s = {
        st["name"]: st["value"]
        for st in e.get("stats", [])
        if isinstance(st.get("value"), (int, float))
    }
    w, l, t = s.get("wins", 0), s.get("losses", 0), s.get("ties", 0)
    gp = s.get("gamesPlayed") or (w + l + t + s.get("overtimeLosses", 0))
    tm = e.get("team", {})
    nombres = [
        tm.get("displayName"),
        tm.get("shortDisplayName"),
        tm.get("name"),
        tm.get("location"),
        f'{tm.get("location","")} {tm.get("name","")}',
    ]
    equipos.append({
        "name": tm.get("displayName"),
        "names": [normalizar(n) for n in nombres if n],
        "gp": gp,
        "pf": s.get("pointsFor", 0),
        "pa": s.get("pointsAgainst", 0),
    })
  return equipos


def buscar_equipo(equipos, nombre):
  n = normalizar(nombre)
  nt = set(n.split())
  mejor, score_mejor = None, 0
  for t in equipos:
    for c in t["names"]:
      if c == n:
        return t
      score = 0.8 if (c in n or n in c) else 0
      ct = set(c.split())
      score = max(score, len(nt & ct) / max(1, len(nt | ct)))
      if score > score_mejor:
        mejor, score_mejor = t, score
  return mejor if score_mejor >= 0.5 else None


# ========= THE ODDS API =========
@st.cache_data(ttl=300)
def traer_momios(sport_key, region, markets, api_key):
  if not api_key:
    return []
  try:
    r = requests.get(
        f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds",
        params={
            "apiKey": api_key,
            "regions": region,
            "markets": markets,
            "oddsFormat": "decimal",
        },
        timeout=20,
    )
    if r.status_code in (404, 422):
      return []
    r.raise_for_status()
    return r.json()
  except Exception:
    return []


def resumir_mercado(ev, mkey):
  libros = [
      (b["title"], m)
      for b in ev.get("bookmakers", [])
      for m in b.get("markets", [])
      if m["key"] == mkey
  ]
  if not libros:
    return []

  def firma(outs):
    if mkey == "h2h":
      return ""
    ref = next(
        (
            o
            for o in outs
            if o["name"] == (ev["home_team"] if mkey == "spreads" else "Over")
        ),
        {},
    )
    return str(ref.get("point", ""))

  conteo = {}
  for _, m in libros:
    conteo[firma(m["outcomes"])] = conteo.get(firma(m["outcomes"]), 0) + 1
  if not conteo:
    return []
  moda = max(conteo, key=conteo.get)
  filas = {}
  for libro, m in libros:
    if firma(m["outcomes"]) != moda:
      continue
    imp = sum(1 / o["price"] for o in m["outcomes"])
    if imp <= 0:
      continue
    for o in m["outcomes"]:
      k = (o["name"], o.get("point"))
      f = filas.setdefault(
          k,
          {
              "name": o["name"],
              "point": o.get("point"),
              "odds": 0,
              "book": "",
              "fair": 0,
              "n": 0,
          },
      )
      if o["price"] > f["odds"]:
        f["odds"], f["book"] = o["price"], libro
      f["fair"] += (1 / o["price"]) / imp
      f["n"] += 1
  return [{**f, "fair": f["fair"] / f["n"]} for f in filas.values()]


# ========= PROYECCIÓN Y MODELO =========
def proyectar(cfg, hs, as_):
  _, _, _, _, tipo, exp, adv_pts, adv_logit, _, _ = cfg
  if not hs or not as_ or hs["gp"] < 2 or as_["gp"] < 2:
    return None
  if hs["pf"] + hs["pa"] <= 0 or as_["pf"] + as_["pa"] <= 0:
    return None
  p_h, p_a = pitagoras(hs["pf"], hs["pa"], exp), pitagoras(
      as_["pf"], as_["pa"], exp
  )
  l5 = log5(clamp(p_h), clamp(p_a))
  pts_h = (hs["pf"] / hs["gp"] + as_["pa"] / as_["gp"]) / 2 + adv_pts / 2
  pts_a = (as_["pf"] / as_["gp"] + hs["pa"] / hs["gp"]) / 2 - adv_pts / 2
  pr = {
      "home": pts_h,
      "away": pts_a,
      "total": pts_h + pts_a,
      "spread": pts_h - pts_a,
      "pyth_h": p_h,
      "pyth_a": p_a,
      "log5": l5,
      "home_win": sigmoid(logit(clamp(l5)) + adv_logit),
      "fut": None,
  }
  if tipo == "soccer":
    fp = futbol_probs(max(0.2, pts_h), max(0.2, pts_a))
    pr["home_win"], pr["draw"], pr["fut"] = fp[0], fp[1], fp
  return pr


# ========= EJECUCIÓN PRINCIPAL =========
with st.spinner(
    "🦜 Piqui está consultando The Odds API y calculando las proyecciones..."
):
  todos_picks = []

  for clave, cfg in LIGAS.items():
    nombre_liga, odds_key, espn, region, tipo = cfg[:5]
    if liga_filtro != "Todas las Ligas" and nombre_liga != liga_filtro:
      continue

    markets = "h2h" if tipo == "individual" else "h2h,spreads,totals"
    eventos = traer_momios(odds_key, region, markets, odds_api_key_input)
    equipos = obtener_standings(espn) if espn else []

    for ev in eventos:
      # Filtrar por fecha si aplica
      try:
        dt_com = datetime.fromisoformat(
            ev["commence_time"].replace("Z", "+00:00")
        )
        if dt_com.date() != fecha_seleccionada:
          continue
      except Exception:
        pass

      hs = buscar_equipo(equipos, ev["home_team"])
      as_ = buscar_equipo(equipos, ev["away_team"])
      pr = proyectar(cfg, hs, as_)

      _, _, _, _, _, _, _, _, sd_m, sd_t = cfg

      for mkey, etiqueta in (
          ("h2h", "Ganador"),
          ("spreads", "Spread"),
          ("totals", "Total"),
      ):
        for r in resumir_mercado(ev, mkey):
          pt, mp = r["point"] or 0, None
          if pr:
            fut = pr["fut"]
            if mkey == "h2h":
              if r["name"] == ev["home_team"]:
                mp = pr["home_win"]
              elif r["name"] == ev["away_team"]:
                mp = fut[2] if fut else 1 - pr["home_win"]
              else:
                mp = pr.get("draw")
            elif mkey == "spreads":
              if r["name"] == ev["home_team"]:
                mp = (
                    fut[4](pt)
                    if fut
                    else 1 - norm_cdf((-pt - pr["spread"]) / sd_m)
                )
              else:
                mp = (
                    1 - fut[4](-pt)
                    if fut
                    else norm_cdf((pt - pr["spread"]) / sd_m)
                )
            else:
              over = (
                  fut[3](pt)
                  if fut
                  else 1 - norm_cdf((pt - pr["total"]) / sd_t)
              )
              mp = over if r["name"] == "Over" else 1 - over

          prob = (
              r["fair"]
              if mp is None
              else mezcla_modelo * clamp(mp) + (1 - mezcla_modelo) * r["fair"]
          )
          ev_val = prob * r["odds"] - 1

          if ev_val >= ev_minimo or prob >= 0.50:
            if mkey == "h2h":
              sel = "Empate" if r["name"] == "Draw" else r["name"]
            elif mkey == "spreads":
              sel = f'{r["name"]} {"+" if pt > 0 else ""}{pt}'
            else:
              sel = f'{"Más" if r["name"] == "Over" else "Menos"} de {pt}'

            todos_picks.append({
                "liga": nombre_liga,
                "evento": f"{ev['away_team']} vs {ev['home_team']}",
                "mercado": etiqueta,
                "pick": sel,
                "odds": r["odds"],
                "casa": r["book"],
                "prob": prob,
                "ev": ev_val,
                "proy": pr,
            })

  # Ordenar resultados
  todos_picks.sort(key=lambda p: p["ev"] * p["prob"], reverse=True)

  # ========= PESTAÑAS DE VISUALIZACIÓN =========
  tab1, tab2 = st.tabs([
      "🎯 Picks Recomendados por Piqui",
      "🧠 Auditoría de Proyecciones",
  ])

  with tab1:
    st.markdown(
        f"### 🎯 Mejores Oportunidades Encontradas ({fecha_seleccionada})"
    )
    if todos_picks:
      for p in todos_picks[:15]:
        badge_class = "badge-ml"
        if p["mercado"] == "Spread":
          badge_class = "badge-spread"
        elif p["mercado"] == "Total":
          badge_class = "badge-total"

        stake_calculado = max(10.0, min(banco * 0.05, banco * max(p["ev"], 0.02)))

        explicacion_piqui = (
            f"🦜 **Piqui dice:** Analicé las líneas de mercado para"
            f" **{p['evento']}** y detecté valor matemático en"
            f" **{p['pick']}**. La efectividad/probabilidad estimada es del"
            f" **{p['prob']*100:.1f}%** con un Momio de **{a_americano(p['odds'])}"
            f"** en *{p['casa']}*. El valor esperado (**EV**) es de"
            f" **+{p['ev']*100:.1f}%**, lo que nos deja una recomendación"
            f" sólida para jugar en {casa_apuestas}."
        )

        st.markdown(
            f"""
              <div class="card-match">
                  <div style="display: flex; align-items: center; justify-content: space-between;">
                      <div>
                          <span style="background-color: #3b82f620; color: #60a5fa; padding: 4px 12px; border-radius: 6px; font-size: 11px; font-weight: 700; border: 1px solid #3b82f640;">{p['liga']}</span>
                          <h4 style="margin: 12px 0 4px 0; font-size: 20px;">{p['evento']}</h4>
                      </div>
                      <div style="text-align: right;">
                          <span style="color: #4ade80; font-weight: 800; font-size: 22px;">{p['prob']*100:.1f}% Efectividad</span><br>
                          <span style="color: #94a3b8; font-size: 13px;">Cuota: <b>{a_americano(p['odds'])}</b> ({p['odds']:.2f} | {p['casa']}) | EV: <b style="color: #22c55e;">+{p['ev']*100:.1f}%</b></span>
                      </div>
                  </div>
                  <hr style="border-color: #334155; margin: 14px 0;">
                  <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px;">
                      <div>
                          <span class="{badge_class}">{p['mercado']}</span> &nbsp;
                          <b style="font-size: 16px;">{p['pick']}</b>
                      </div>
                      <div>
                          <span style="color: #94a3b8; font-size: 13px;">Inversión Sugerida:</span> <b style="color: #f1f5f9; font-size: 15px;">${stake_calculado:.2f}</b>
                      </div>
                  </div>
                  <div class="piqui-speech-box">
                      {explicacion_piqui}
                  </div>
              </div>
          """,
            unsafe_allow_html=True,
        )
    else:
      st.info(
          "🦜 **Piqui dice:** No encontré partidos programados para esta fecha"
          " o los encuentros están fuera del rango de la API. Prueba seleccionando"
          " el día de hoy o mañana en el calendario."
      )

  with tab2:
    st.markdown("### 🧠 Centro de Auditoría Cuantitativa")
    if todos_picks:
      seleccion = st.selectbox(
          "Selecciona un evento:", [p["evento"] for p in todos_picks]
      )
      match_sel = next(p for p in todos_picks if p["evento"] == seleccion)
      pr = match_sel["proy"]

      if pr:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
          st.markdown(
              f"""<div class="metric-card"><span style="color: #94a3b8; font-size: 12px;">Pitágoras Local</span><br><b style="font-size: 18px; color: #60a5fa;">{pr['pyth_h']*100:.1f}%</b></div>""",
              unsafe_allow_html=True,
          )
        with col2:
          st.markdown(
              f"""<div class="metric-card"><span style="color: #94a3b8; font-size: 12px;">Pitágoras Visita</span><br><b style="font-size: 18px; color: #f43f5e;">{pr['pyth_a']*100:.1f}%</b></div>""",
              unsafe_allow_html=True,
          )
        with col3:
          st.markdown(
              f"""<div class="metric-card"><span style="color: #94a3b8; font-size: 12px;">Log5 H2H</span><br><b style="font-size: 18px; color: #a855f7;">{pr['log5']*100:.1f}%</b></div>""",
              unsafe_allow_html=True,
          )
        with col4:
          st.markdown(
              f"""<div class="metric-card"><span style="color: #94a3b8; font-size: 12px;">Total Proyectado</span><br><b style="font-size: 18px; color: #22c55e;">{pr['total']:.1f} pts</b></div>""",
              unsafe_allow_html=True,
          )
      else:
        st.warning(
            "Este evento utiliza cuotas de consenso de mercado (sin estadísticas"
            " de tabla en ESPN)."
        )
    else:
      st.info("No hay datos de auditoría disponibles.")

st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: #64748b; font-size: 13px;'>Piquis"
    " AI Engine · Conectado en tiempo real a The Odds API. Apuesta con"
    " responsabilidad.</div>",
    unsafe_allow_html=True,
)
