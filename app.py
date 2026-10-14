from datetime import date, datetime, timezone
import math
import pandas as pd
import requests
import streamlit as st

# Configuración de la página web
st.set_page_config(
    page_title="Piquis · AI Sports Analytics", page_icon="⚡", layout="wide"
)

# Estilos CSS personalizados para una UX moderna y limpia
st.markdown("""
    <style>
    .main { background-color: #0f172a; color: #f8fafc; }
    .stMetric { background-color: #1e293b; padding: 15px; border-radius: 10px; border: 1px solid #334155; }
    .card-partido { background-color: #1e293b; padding: 20px; border-radius: 12px; margin-bottom: 15px; border: 1px solid #334155; }
    </style>
""", unsafe_allow_html=True)

st.title("⚡ Piquis · Analista Deportivo & Modelos AI")
st.markdown(
    "Plataforma cuantitativa avanzada: **Pitágoras, Log5, Ventaja Local, Proyecciones, Spreads, Totales y Criterio de Kelly** optimizada para **Draftea y Playdoit**."
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

# Sidebar Interactiva (Calendario y Filtros UX)
st.sidebar.header("📅 Calendario & Filtros")
fecha_seleccionada = st.sidebar.date_input(
    "Selecciona Fecha de Análisis", date.today()
)
fecha_str = fecha_seleccionada.strftime("%Y%m%d")

deportes_disponibles = ["Todos"] + [l["name"] for l in LEAGUES]
deporte_filtro = st.sidebar.selectbox("Filtrar por Liga / Deporte", deportes_disponibles)

st.sidebar.markdown("---")
st.sidebar.header("⚙️ Gestión de Bankroll")
casa_apuestas = st.sidebar.selectbox(
    "Casa de Apuestas Objetivo:", ["Playdoit", "Draftea"]
)
banco = st.sidebar.number_input(
    "Bankroll Inicial ($)", value=1000.0, step=100.0, format="%.2f"
)
umbral_edge = (
    st.sidebar.slider("Edge Mínimo Requerido (%)", 0.5, 10.0, 1.5, 0.5) / 100.0
)


# --- 2. FUNCIONES DE DESCARGA Y MATEMÁTICA ---
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
      # Scoreboard con fecha específica
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

    # Descargar Standings para modelos Pitagóricos
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


with st.spinner(f"Analizando agenda y cuotas para el {fecha_seleccionada}..."):
  partidos_crudos, tablas_datos = descargar_datos_fecha(fecha_str)


# Fórmulas
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


# Procesamiento del motor de análisis
analisis_eventos = []
for p in partidos_crudos:
  league = next(
      (item for item in LEAGUES if item["key"] == p["league_key"]), None
  )
  if not league:
    continue
  if deporte_filtro != "Todos" and league["name"] != deporte_filtro:
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
  promedio = promedio_liga(tabla) or 1.2

  neutral_log5 = log5(p_pit_l, p_pit_v) if p_pit_l and p_pit_v else 0.5
  proyeccion = proyectar(
      local, visitante, promedio, league["hfa"], p["sede_neutral"]
  )

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

  candidatos.sort(key=lambda c: c["ev"], reverse=True)

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
      "pick": candidatos[0] if candidatos else None,
      "candidatos": candidatos,
  })

# --- 3. PESTAÑAS DE NAVEGACIÓN UX ---
tab1, tab2, tab3 = st.tabs(
    ["🎯 Picks +EV & Calendario", "📊 Auditoría & Explicación AI", "🧩 Parlays"]
)

with tab1:
  st.subheader(f"📅 Picks Automatizados para la fecha: {fecha_seleccionada}")
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

      st.markdown(f"""
                <div class="card-partido">
                    <div style="display: flex; align-items: center; justify-content: space-between;">
                        <div>
                            <span style="background-color: #3b82f6; color: white; padding: 3px 8px; border-radius: 4px; font-size: 12px; font-weight: bold;">{ev['liga']}</span>
                            <h4 style="margin: 10px 0 5px 0; display: flex; align-items: center; gap: 10px;">
                                <img src="{logo_l}" width="28" height="28"> {ev['local_nombre']} vs <img src="{logo_v}" width="28" height="28"> {ev['visitante_nombre']}
                            </h4>
                        </div>
                        <div style="text-align: right;">
                            <span style="color: #22c55e; font-weight: bold; font-size: 18px;">EV: +{p['ev']*100:.1f}%</span><br>
                            <span style="color: #94a3b8; font-size: 13px;">Cuota: {p['cuota_americana']}</span>
                        </div>
                    </div>
                    <hr style="border-color: #334155; margin: 10px 0;">
                    <p style="margin: 0; font-size: 15px;">
                        🔥 <b>Pick Sugerido para {casa_apuestas}:</b> <span style="color: #60a5fa;">{p['etiqueta']}</span> 
                        | Probabilidad IA: <b>{p['prob_modelo']*100:.1f}%</b> 
                        | Stake Sugerido (Kelly): <b>${p['kelly']*banco:.2f}</b>
                    </p>
                </div>
            """, unsafe_allow_html=True)
  else:
    st.info(
        "No se detectaron apuestas con valor positivo superior al umbral en la"
        " fecha seleccionada. Cambia de fecha en el calendario lateral o ajusta"
        " el edge mínimo."
    )

with tab2:
  st.subheader("🔬 Auditoría de Modelos y Explicación Algorítmica")
  if analisis_eventos:
    seleccion_partido = st.selectbox(
        "Elige un partido para auditar:", [e["partido"] for e in analisis_eventos]
    )
    match_sel = next(
        e for e in analisis_eventos if e["partido"] == seleccion_partido
    )

    col1, col2, col3 = st.columns(3)
    with col1:
      st.metric(
          "Expectativa Pitagórica",
          f"{match_sel['pitagoras_local']*100:.1f}% vs"
          f" {match_sel['pitagoras_visitante']*100:.1f}%",
      )
    with col2:
      st.metric("Log5 H2H Ajustado", f"{match_sel['log5_local']*100:.1f}%")
    with col3:
      if match_sel["proyeccion"]:
        st.metric(
            "Marcador Proyectado",
            f"{match_sel['proyeccion']['local']:.1f} -"
            f" {match_sel['proyeccion']['total'] - match_sel['proyeccion']['local']:.1f}",
        )
      else:
        st.metric("Marcador Proyectado", "N/D")

    st.markdown("### 🤖 Reporte de Análisis Técnico de IA")
    if match_sel["pick"]:
      p_sel = match_sel["pick"]
      st.success(
          f"**Conclusión del Modelo:** El pick **{p_sel['etiqueta']}** presenta un"
          f" rendimiento esperado (*EV*) de **+{p_sel['ev']*100:.1f}%**. Esto"
          " se debe a que la probabilidad calculada por nuestros algoritmos"
          f" (**{p_sel['prob_modelo']*100:.1f}%**) supera la cuota implícita de"
          f" la casa de apuestas ({p_sel['cuota_americana']})."
      )
    else:
      st.warning(
          "Este evento no cuenta con un margen de valor (*Edge*) suficiente"
          " frente a las líneas actuales de las casas de apuestas."
      )
  else:
    st.warning("No hay partidos disponibles para desglosar.")

with tab3:
  st.subheader("🧩 Constructor de Parlays Científicos (+EV)")
  picks_planos = []
  for e in analisis_eventos:
    for c in e["candidatos"]:
      picks_planos.append(
          {**c, "partido": e["partido"], "liga": e["liga"]}
      )

  if len(picks_planos) >= 3:
    picks_planos.sort(key=lambda x: x["ev"], reverse=True)
    patas = picks_planos[:3]

    prob_comb = 1.0
    cuota_comb = 1.0
    nombres_patas = []
    for pata in patas:
      prob_comb *= pata["prob_modelo"]
      cuota_comb *= pata["cuota_decimal"]
      nombres_patas.append(f"{pata['etiqueta']} ({pata['partido']})")

    ev_parlay = valor_esperado(prob_comb, cuota_comb)
    stake_parlay = min(kelly(prob_comb, cuota_comb) * 0.25, 0.05) * banco

    st.markdown(f"""
            <div class="card-partido" style="border: 2px solid #3b82f6;">
                <h3>🎯 Parlay Destacado de 3 Patas</h3>
                <ul>
                    <li><b>Patas:</b> { ' + '.join(nombres_patas) }</li>
                </ul>
                <hr style="border-color: #334155;">
                <p><b>Probabilidad Combinada:</b> {prob_comb*100:.2f}% | <b>Cuota Total Decimal:</b> {cuota_comb:.2f}</p>
                <p><b>Valor Esperado (EV):</b> <span style="color: #22c55e;">+{ev_parlay*100:.2f}%</span> | <b>Stake Sugerido:</b> ${stake_parlay:.2f}</p>
            </div>
        """, unsafe_allow_html=True)
  else:
    st.info(
        "Se necesitan al menos 3 picks con valor positivo en la fecha elegida"
        " para armar los parlays automáticos."
    )

st.markdown("---")
st.caption(
    "Piquis AI Engine · Arquitectura orientada a Draftea y Playdoit con"
    " estadísticas de ESPN en tiempo real."
)
