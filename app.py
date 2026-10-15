# picks.py — Modelo de picks: Pitágoras, Log5, ventaja local, proyección, total y spread
from datetime import datetime, timezone, timedelta
import itertools
import math
import re
import sys
import unicodedata
import requests

# ========= CONFIGURACIÓN =========
ODDS_API_KEY = "PEGA_AQUI_TU_CLAVE"  # https://the-odds-api.com
HORAS = 36  # partidos de las próximas X horas
MEZCLA_MODELO = 0.5  # 0.5 = 50% modelo + 50% mercado
EV_MINIMO = 0.015  # valor esperado mínimo (1.5%)
PROB_MINIMA = 0.38
MOMIO_MAXIMO = 4.5

# clave: (nombre, odds_key, espn_path, region, tipo, exp_pitagoras, ventaja_pts, ventaja_logit, sd_margen, sd_total)
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
    "ufc": ("UFC", "mma_mixed_martial_arts", None, "us", "individual", 0, 0, 0, 0, 0),
    "tenis": ("Tenis", "tennis", None, "eu", "individual", 0, 0, 0, 0, 0),
}


# ========= MATEMÁTICAS =========
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


# ========= ESPN =========
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


def standings(path):
  try:
    d = requests.get(
        f"https://site.api.espn.com/apis/v2/sports/{path}/standings",
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=20,
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


# ========= MOMIOS =========
def traer_momios(sport_key, region, markets):
  r = requests.get(
      f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds",
      params={
          "apiKey": ODDS_API_KEY,
          "regions": region,
          "markets": markets,
          "oddsFormat": "decimal",
      },
      timeout=30,
  )
  if r.status_code in (404, 422):
    return []
  r.raise_for_status()
  print(f"   (consultas restantes: {r.headers.get('x-requests-remaining')})")
  return r.json()


def llaves_tenis():
  r = requests.get(
      "https://api.the-odds-api.com/v4/sports",
      params={"apiKey": ODDS_API_KEY},
      timeout=30,
  )
  return [
      s["key"] for s in r.json() if s["group"] == "Tennis" and s["active"]
  ][:3]


def resumir_mercado(ev, mkey):
  """Mejor momio por resultado + probabilidad justa (sin vig) promedio entre casas."""
  libros = [
      (b["title"], m)
      for b in ev["bookmakers"]
      for m in b["markets"]
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
  moda = max(conteo, key=conteo.get)
  filas = {}
  for libro, m in libros:
    if firma(m["outcomes"]) != moda:
      continue
    imp = sum(1 / o["price"] for o in m["outcomes"])
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


# ========= MODELO =========
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


def picks_evento(ev, cfg, equipos):
  nombre_liga, _, _, _, tipo, _, _, _, sd_m, sd_t = cfg
  pr = (
      None
      if tipo == "individual"
      else proyectar(
          cfg,
          buscar_equipo(equipos, ev["home_team"]),
          buscar_equipo(equipos, ev["away_team"]),
      )
  )
  salida = []
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
                fut[4](pt) if fut else 1 - norm_cdf((-pt - pr["spread"]) / sd_m)
            )
          else:
            mp = (
                1 - fut[4](-pt)
                if fut
                else norm_cdf((pt - pr["spread"]) / sd_m)
            )
        else:
          over = fut[3](pt) if fut else 1 - norm_cdf((pt - pr["total"]) / sd_t)
          mp = over if r["name"] == "Over" else 1 - over
      prob = (
          r["fair"]
          if mp is None
          else MEZCLA_MODELO * clamp(mp) + (1 - MEZCLA_MODELO) * r["fair"]
      )
      ev_ = prob * r["odds"] - 1
      if mkey == "h2h":
        sel = "Empate" if r["name"] == "Draw" else r["name"]
      elif mkey == "spreads":
        sel = f'{r["name"]} {"+" if pt > 0 else ""}{pt}'
      else:
        sel = f'{"Más" if r["name"] == "Over" else "Menos"} de {pt}'
      salida.append({
          "liga": nombre_liga,
          "evento": f'{ev["away_team"]} @ {ev["home_team"]}',
          "event_id": ev["id"],
          "hora": ev["commence_time"],
          "mercado": etiqueta,
          "pick": sel,
          "odds": r["odds"],
          "casa": r["book"],
          "prob": prob,
          "mercado_prob": r["fair"],
          "modelo_prob": mp,
          "ev": ev_,
          "momio_min": 1 / prob,
          "proy": pr,
      })
  buenos = [
      p
      for p in salida
      if p["ev"] > EV_MINIMO
      and p["prob"] >= PROB_MINIMA
      and p["odds"] <= MOMIO_MAXIMO
  ]
  return sorted(buenos, key=lambda p: p["ev"] * p["prob"], reverse=True)[:2]


def picks_liga(clave):
  cfg = LIGAS[clave]
  nombre, odds_key, espn, region, tipo = cfg[:5]
  print(f"\n>> {nombre}")
  markets = "h2h" if tipo == "individual" else "h2h,spreads,totals"
  llaves = llaves_tenis() if odds_key == "tennis" else [odds_key]
  eventos = [e for k in llaves for e in traer_momios(k, region, markets)]
  ahora = datetime.now(timezone.utc)
  eventos = [
      e
      for e in eventos
      if ahora
      < datetime.fromisoformat(e["commence_time"].replace("Z", "+00:00"))
      < ahora + timedelta(hours=HORAS)
  ]
  if not eventos:
    print("   Sin partidos en las próximas horas.")
    return []
  equipos = standings(espn) if espn else []
  if tipo != "individual" and not equipos:
    print("   Sin estadísticas de ESPN: se usa consenso de mercado.")
  return [p for e in eventos for p in picks_evento(e, cfg, equipos)]


# ========= PARLAYS =========
def parlays(picks):
  por_evento = {}
  for p in picks:
    if (
        p["event_id"] not in por_evento
        or p["prob"] > por_evento[p["event_id"]]["prob"]
    ):
      por_evento[p["event_id"]] = p
  pool = sorted(
      [p for p in por_evento.values() if p["prob"] >= 0.52],
      key=lambda p: -p["prob"],
  )[:9]
  combos = []
  for n in (2, 3):
    for legs in itertools.combinations(pool, n):
      odds = math.prod(l["odds"] for l in legs)
      prob = math.prod(l["prob"] for l in legs)
      if prob >= 0.2:
        combos.append({
            "legs": legs,
            "odds": odds,
            "prob": prob,
            "ev": prob * odds - 1,
        })
  mejores = []
  for n in (2, 3):
    mejores += sorted(
        [c for c in combos if len(c["legs"]) == n], key=lambda c: -c["ev"] * c["prob"]
    )[:2]
  return mejores


# ========= SALIDA =========
def hora_mx(iso):
  t = datetime.fromisoformat(iso.replace("Z", "+00:00")) - timedelta(hours=6)
  return t.strftime("%a %H:%M")


def main():
  claves = sys.argv[1:] or ["ligamx", "mlb", "nba", "nfl", "nhl"]
  todos = []
  for c in claves:
    if c not in LIGAS:
      print(f"Liga desconocida: {c}. Opciones: {', '.join(LIGAS)}")
      continue
    try:
      todos += picks_liga(c)
    except Exception as e:
      print(f"   Error: {e}")
  todos.sort(key=lambda p: p["ev"] * p["prob"], reverse=True)

  print("\n" + "=" * 70 + "\n TOP PICKS DEL DÍA\n" + "=" * 70)
  for i, p in enumerate(todos[:16], 1):
    print(f"\n#{i} [{p['liga']}] {p['evento']}  ({hora_mx(p['hora'])} MTY)")
    print(
        f"   {p['mercado']}: {p['pick']}  @ {a_americano(p['odds'])}"
        f" ({p['odds']:.2f}, {p['casa']})"
    )
    print(
        f"   Prob {p['prob']*100:.1f}% | Mercado {p['mercado_prob']*100:.1f}% |"
        f" EV +{p['ev']*100:.1f}% | Momio mínimo en Draftea/Play Doit:"
        f" {a_americano(p['momio_min'])}"
    )
    pr = p["proy"]
    if pr:
      print(
          f"   Proyección: local {pr['home']:.1f} - visita {pr['away']:.1f} |"
          f" Total {pr['total']:.1f} | Spread {pr['spread']:+.1f} | Pitágoras"
          f" {pr['pyth_h']*100:.0f}%/{pr['pyth_a']*100:.0f}% | Log5"
          f" {pr['log5']*100:.0f}% | Con local {pr['home_win']*100:.0f}%"
      )
  if not todos:
    print("\nSin picks con valor por ahora.")

  ps = parlays(todos)
  if ps:
    print("\n" + "=" * 70 + "\n PARLAYS\n" + "=" * 70)
    for c in ps:
      print(
          f"\nParlay {len(c['legs'])} patas @ {a_americano(c['odds'])} | Prob"
          f" {c['prob']*100:.1f}% | EV {c['ev']*100:+.1f}%"
      )
      for l in c["legs"]:
        print(
            f"   - [{l['liga']}] {l['evento']}: {l['mercado']} {l['pick']} @"
            f" {a_americano(l['odds'])} ({l['prob']*100:.0f}%)"
        )
  print("\nApuesta con responsabilidad. Ningún pick es seguro.")


if __name__ == "__main__":
  main()
