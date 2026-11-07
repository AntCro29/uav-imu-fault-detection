"""Données du tableau de bord (docs/dashboard/) : les 48 vols de test de la boucle sous vibration.

Usage : python scripts/exporter_dashboard.py [sortie]   (défaut : docs/dashboard/donnees.js)

Vols 496 à 543 (campagne du 2026-11-04/05, journaux à partir de 20261104-185000), lus dans l'archive
(~/drone/archive_logs ou ARCHIVE_LOGS) sous leur numéro de vol, grâce à docs/index_vols.csv.
Par vol :
  - résultats d'evaluer_boucle.evaluer (décision, conformité, erreurs vraies, zone), inchangés ;
  - innovations et score de l'autoencodeur tels que la boucle les a vus en vol (trace
    data/en_ligne_*.csv, écrite quelques secondes après le journal) ; les vols de la réponse R-IMU
    seule n'ont pas de trace (le détecteur ne tourne pas) : innovations XKF4 du cœur 0 lues dans le log ;
  - erreur de position et d'attitude vraies du cœur principal, positions vraie, estimée et GPS ;
  - instants clés lus dans le journal : alarme, décision, GPS écarté / repris, IMU désignée.
Fausses alarmes : alarmes des détecteurs (lignes « DÉTECTEUR » des journaux de la boucle) commencées
après 10 s de cercle et avant l'injection, ou avant le RTL pour un vol normal.
Écrit un fichier JavaScript (window.DONNEES = {...}) pour que la page s'ouvre aussi hors ligne.
"""
import csv
import datetime as dt
import glob
import json
import os
import re
import sys
import joblib
import numpy as np
import pandas as pd
from pymavlink import mavutil

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import evaluer_boucle as eb
import evaluer_rimu as er
import figures_readme as fr

DEPOT = fr.DEPOT
DEPUIS, LOGS_CAMPAGNE = "20261104-185000", "10-57"
DETECTEURS = ("autoencodeur", "isolation forest", "AE + ML")
PAS_TRACE, PAS_NAV = 0.2, 0.5          # secondes entre deux points exportés
er.LOGS = os.path.join(fr.ARCHIVE, "vols", "vol_{:04d}.BIN")   # lire(n) lit le vol n de l'archive

_cache = {}
_lire = er.lire


def lire(vol):
    if vol not in _cache:
        _cache[vol] = _lire(vol)
    return _cache[vol]


eb.lire = lire   # evaluer() et l'export lisent chaque log une seule fois


def vols_par_journal():
    with open(os.path.join(DEPOT, "docs", "index_vols.csv"), newline="") as f:
        return {r["journal"]: int(r["vol"]) for r in csv.DictReader(f) if r["journal"] and r["vol"]}


def horodatage(chemin):
    return dt.datetime.strptime(chemin[-19:-4], "%Y%m%d-%H%M%S")


def trace_du_vol(journal, traces):
    t = horodatage(journal)
    c = [x for x in traces if 0 <= (horodatage(x) - t).total_seconds() <= 30]
    return c[0] if len(c) == 1 else None


def lire_log(vol):
    """Positions GPS (instance 0) en mètres, instant du RTL et innovations XKF4 du cœur 0, en temps de cercle."""
    origine = tc = t_rtl = None
    gps, xkf = [], []
    m = mavutil.mavlink_connection(er.LOGS.format(vol))
    while True:
        x = m.recv_match(type=["ORGN", "MODE", "GPS", "XKF4"])
        if x is None:
            break
        g, t = x.get_type(), x.TimeUS / 1e6
        if g == "ORGN" and origine is None:
            origine = (x.Lat, x.Lng)
        elif g == "MODE":
            if x.Mode == 7 and tc is None:
                tc = t
            elif x.Mode == 6 and tc is not None and t_rtl is None:
                t_rtl = t
        elif g == "GPS" and getattr(x, "I", 0) == 0:
            gps.append((t, x.Lat, x.Lng))
        elif g == "XKF4" and x.C == 0:
            xkf.append((t, x.SV, x.SP, x.SH, x.SM))
    g = pd.DataFrame(gps, columns=["t", "lat", "lng"])
    g["n"], g["e"] = er.en_metres(g.lat, g.lng, origine)
    g["tc"] = g.t - tc
    k = pd.DataFrame(xkf, columns=["t", "SV", "SP", "SH", "SM"])
    k["tc"] = k.t - tc
    return g, t_rtl - tc, k


def alarmes_journal(journal):
    """Débuts d'alarme de chaque détecteur (temps de cercle)."""
    debuts = []
    for ligne in open(journal, newline="").read().split("\n"):
        m = re.search(r"cercle=\s*([\d.]+) s.*DÉTECTEUR (.+) : ALARME", ligne)
        if m and m.group(2) in DETECTEURS:
            debuts.append((float(m.group(1)), m.group(2)))
    return debuts


def instant_decision(journal):
    for ligne in open(journal, newline="").read().split("\n"):
        m = re.search(r"cercle=\s*([\d.]+) s.*BOUCLE : famille", ligne)
        if m:
            return float(m.group(1))
    return None


def reechantillonner(df, t, a, b, pas, colonnes):
    """Valeur la plus proche tous les `pas` secondes entre a et b (NaN → None pour le JSON)."""
    grille = pd.DataFrame({t: np.round(np.arange(a, b + pas / 2, pas), 2)})
    d = pd.merge_asof(grille, df.sort_values(t)[[t] + colonnes], on=t, direction="nearest", tolerance=pas)
    return {c: [None if pd.isna(v) else round(float(v), 4) for v in d[c]] for c in [t] + colonnes}


def nettoyer(v):
    if isinstance(v, (np.floating, float)):
        return None if np.isnan(v) else round(float(v), 2)
    if isinstance(v, np.integer):
        return int(v)
    return v


def exporter(sortie):
    journaux = glob.glob(os.path.join(DEPOT, "data", "journal_*_2026110[45]-*.txt"))
    traces = sorted(glob.glob(os.path.join(DEPOT, "data", "en_ligne_2026110[45]-*.csv")))
    index = vols_par_journal()
    seuil_ae = float(joblib.load(fr.DETECTEUR_V)["seuil_ae"])
    vols, expo, fausses = [], 0.0, []
    for log, c, j in eb.associer(eb.plages(LOGS_CAMPAGNE), journaux, DEPUIS):
        vol = index[os.path.basename(j)]
        r = {k: nettoyer(v) for k, v in eb.evaluer(vol, c, j).items()}
        r["vol"], r["log"] = vol, log
        att, pos, _ = lire(vol)
        gps, t_rtl, xkf = lire_log(vol)
        nominal = c["scenario"] == "nominal"
        inj = None if nominal else c["inj"]
        a, b = (10.0, t_rtl) if nominal else (inj - 30, inj + 150)
        jr = eb.lire_journal(j)
        r.update(scenario=c["scenario"], amplitude=c["amp"], injection=inj, fin_panne=None if nominal else inj + 60,
                 rtl=round(t_rtl, 1), vent_vitesse=c["vent"][0])
        r["instants"] = {"exclusions": [round(t, 1) for t, _ in jr["exclusions"]],
                         "retours": [round(t, 1) for t in jr["retours"]],
                         "imu": jr["t_imu"], "decision": instant_decision(j)}
        if c["reponse"] == "boucle":
            fin_normal = t_rtl if nominal else inj
            expo += fin_normal - 10
            fausses += [(vol, t, d) for t, d in alarmes_journal(j) if 10 <= t < fin_normal]
        chemin = trace_du_vol(j, traces)
        if chemin:
            tr = pd.read_csv(chemin)
            # vols de la réaction choisie à la main : pas de colonne d'alarme de la boucle
            tr["alarme"] = tr["AE + ML"] if "AE + ML" in tr else np.nan
            tr.loc[tr.r3 == "ecarte", ["SV", "SP", "SH", "SM", "score_ae", "alarme"]] = np.nan
            r["source"] = "trace"
            r["trace"] = reechantillonner(tr.rename(columns={"t_cercle_s": "tc"}), "tc", a, b, PAS_TRACE,
                                          ["SV", "SP", "SH", "SM", "score_ae", "alarme"])
            alarme = tr[(tr.alarme == 1) & (tr.t_cercle_s >= (10 if nominal else inj))]
            r["instants"]["alarme"] = None if alarme.empty else round(float(alarme.t_cercle_s.iloc[0]), 2)
        else:
            r["source"] = "log"
            r["trace"] = reechantillonner(xkf, "tc", a, b, PAS_TRACE, ["SV", "SP", "SH", "SM"])
            r["instants"]["alarme"] = None
        p = pos.rename(columns={"err": "err_pos"})
        nav = pd.merge_asof(p.sort_values("tc"), att[["tc", "err"]].rename(columns={"err": "err_att"}).sort_values("tc"),
                            on="tc", direction="nearest")
        r["nav"] = reechantillonner(nav, "tc", a, b, PAS_NAV, ["err_pos", "err_att", "n", "e", "pn", "pe"])
        r["gps"] = reechantillonner(gps, "tc", a, b, PAS_NAV, ["n", "e"])
        avant = pos[(pos.tc >= 10) & (pos.tc < (t_rtl if nominal else inj))]
        r["centre"] = [round(float(avant.n.mean()), 2), round(float(avant.e.mean()), 2)]
        vols.append(r)
        print(f"vol {vol} (log {log}) {c['scenario']:<12} {c['reponse']:<6} {r['source']:<5} {r['conforme']}", flush=True)
    boucle = [v for v in vols if v["reponse"] == "boucle"]
    resume = {"vols": len(vols), "vols_boucle": len(boucle),
              "conformes_boucle": sum(v["conforme"] == "oui" for v in boucle),
              "fausses_alarmes": len(fausses), "duree_normale_s": round(expo),
              "zone_100": sum(v["zone_%"] == 100 for v in boucle),
              "recours": sum(v["recours"] != "—" for v in boucle),
              "seuil_ae": round(seuil_ae, 3), "zone_m": eb.ZONE_M,
              "genere": dt.date.today().isoformat()}
    print(resume)
    os.makedirs(os.path.dirname(sortie), exist_ok=True)
    with open(sortie, "w") as f:
        f.write("// Généré par scripts/exporter_dashboard.py, ne pas modifier à la main.\n")
        f.write("window.DONNEES = ")
        json.dump({"resume": resume, "vols": vols}, f, ensure_ascii=False, separators=(",", ":"))
        f.write(";\n")
    print(f"{sortie} : {os.path.getsize(sortie) / 1e6:.1f} Mo")


if __name__ == "__main__":
    exporter(sys.argv[1] if len(sys.argv) > 1 else os.path.join(DEPOT, "docs", "dashboard", "donnees.js"))
