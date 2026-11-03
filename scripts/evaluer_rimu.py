"""Résultats d'une campagne R-IMU : vote, cœur principal, erreurs d'attitude et de position vraies.

Usage : python scripts/evaluer_rimu.py <premier_log> <journal> [<journal> ...]
Les journaux de vol_auto.py (data/journal_*.txt) sont triés par leur horodatage et associés aux
logs consécutifs à partir de <premier_log>. La configuration du vol (scénario, vent, IMU en
panne, instant d'injection, amplitude, vibration, réponse) est lue dans le nom du journal.
Exemple (campagne de test du 2026-11-02, logs 427 à 454) :
  python scripts/evaluer_rimu.py 427 data/journal_*20261102-1[4-9]*.txt
Par vol, t = 0 à l'entrée en CIRCLE :
  - IMU déclarée par le vote et délai depuis l'injection (journal, horloge du cercle) ;
  - changements de cœur principal (messages « EKF3 primary changed ») ;
  - erreur d'attitude vraie (roulis et tangage, XKF1 du cœur principal contre SIM) et erreur de
    position horizontale (XKF1.PN/PE du cœur principal contre SIM.Lat/Lng, origine ORGN), au
    maximum avant (10 s → injection), pendant la panne (60 s) et 90 s après le retrait ; pour un
    nominal, sur le cercle de 10 à 180 s.
--imu N du lanceur = IMU N − 1 du vote (SIM_ACCn_*, SIM_GYRn_* = IMU n − 1).
"""
import os
import re
import sys
import numpy as np
import pandas as pd
from pymavlink import mavutil
from erreur_navigation import coeur_principal, position_principale, dernier, en_metres

LOGS = os.path.expanduser("~/drone/ardupilot/logs/{:08d}.BIN")
SCENARIOS = ("nominal", "biais", "derive", "gyro", "bruit_gyro", "bloque")


def configuration(chemin):
    """Configuration d'un vol lue dans le nom de son journal (journal_<arguments>_<date>.txt)."""
    nom = os.path.basename(chemin)[len("journal_"):-len("_AAAAMMJJ-HHMMSS.txt")]
    scenario = next(s for s in sorted(SCENARIOS, key=len, reverse=True) if nom.startswith(s))
    a = nom[len(scenario):].strip("_").split("_")
    opt = lambda nom_, defaut=None: a[a.index(nom_) + 1] if nom_ in a else defaut
    vent = a[:3] if a and re.fullmatch(r"[\d.]+", a[0]) else None
    return {"scenario": scenario, "vent": "/".join(vent[:2]) if vent else "0",
            "vent_reglage": tuple(float(v) for v in vent) if vent else (0.0, 180.0, 0.0),
            "imu": int(opt("imu", 0)), "inj": float(opt("injection", 120)), "amp": opt("amplitude", ""),
            "vib": "vibration" in a, "flux": "optique" in a, "reponse": opt("reponse", "rien")}


def associer(premier, journaux):
    """(log, configuration, journal) pour chaque journal, dans l'ordre chronologique."""
    journaux = sorted(journaux, key=lambda p: p[-19:])
    return [(premier + i, configuration(j), j) for i, j in enumerate(journaux)]


def declaration(chemin):
    """(IMU, capteur, instant du cercle) de la première IMU déclarée en panne, ou None."""
    for ligne in open(chemin):
        m = re.search(r"cercle=\s*([\d.]+) s.*R-IMU : IMU (\d) \((\w+)\) déclarée", ligne)
        if m:
            return int(m.group(2)), m.group(3), float(m.group(1))
    return None


def lire(n):
    m = mavutil.mavlink_connection(LOGS.format(n))
    sim, xkf, textes = [], [], []
    coeurs = {0: [], 1: []}
    origine = tc = None
    while True:
        x = m.recv_match(type=["ORGN", "SIM", "XKF1", "MSG", "MODE"])
        if x is None:
            break
        t = x.TimeUS / 1e6
        g = x.get_type()
        if g == "ORGN" and origine is None:
            origine = (x.Lat, x.Lng)
        elif g == "SIM":
            sim.append((t, x.Roll, x.Pitch, x.Lat, x.Lng))
        elif g == "XKF1" and x.C in coeurs:
            xkf.append((t, x.C, x.Roll, x.Pitch))
            coeurs[x.C].append((t, x.PN, x.PE))
        elif g == "MSG":
            textes.append((t, x.Message))
        elif g == "MODE" and x.Mode == 7 and tc is None:
            tc = t
    princ, _ = coeur_principal(textes)
    s = pd.DataFrame(sim, columns=["t", "r", "p", "lat", "lng"]).sort_values("t")
    s["n"], s["e"] = en_metres(s.lat, s.lng, origine)
    k = pd.DataFrame(xkf, columns=["t", "C", "r", "p"])
    k = k[[dernier(princ, t, 0) == c for t, c in zip(k.t, k.C)]].sort_values("t")
    att = pd.merge_asof(k, s[["t", "r", "p"]], on="t", direction="nearest", suffixes=("", "_v"))
    att["err"] = np.hypot(att.r - att.r_v, att.p - att.p_v)
    pos = pd.DataFrame(position_principale(coeurs, textes), columns=["t", "pn", "pe"]).sort_values("t")
    pos = pd.merge_asof(pos, s[["t", "n", "e"]], on="t", direction="nearest")
    pos["err"] = np.hypot(pos.pn - pos.n, pos.pe - pos.e)
    att["tc"], pos["tc"] = att.t - tc, pos.t - tc
    return att, pos, [(t - tc, c) for t, c in princ if t > tc]


def evaluer(n, c, journal):
    decl = declaration(journal)
    att, pos, princ = lire(n)
    nominal = c["scenario"] == "nominal"
    if nominal:
        t0, phases = 10.0, {"cercle": (10, 180)}
    else:
        t0, t1 = c["inj"], c["inj"] + 60
        phases = {"avant": (10, t0), "pendant": (t0, t1), "après": (t1, t1 + 90)}
    r = {"log": n, "panne": c["scenario"] + (f" {c['amp']}" if c["amp"] else ""),
         "imu": c["imu"] - 1 if c["imu"] else None, "vent": c["vent"], "vib": "oui" if c["vib"] else "non",
         "reponse": c["reponse"]}
    if decl:
        r["declaree"] = f"IMU {decl[0]} {decl[1]}"
        r["delai_s"] = round(decl[2] - t0, 1) if not nominal else round(decl[2], 1)
    else:
        r["declaree"], r["delai_s"] = "aucune", None
    r["coeur"] = ", ".join(f"{cc} à {t:.1f}" for t, cc in princ) or "—"
    for ph, (a, b) in phases.items():
        r[f"att_{ph}"] = round(att[(att.tc >= a) & (att.tc < b)].err.max(), 2)
        r[f"pos_{ph}"] = round(pos[(pos.tc >= a) & (pos.tc < b)].err.max(), 1)
    return r


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    rangs = []
    for n, c, j in associer(int(sys.argv[1]), sys.argv[2:]):
        rangs.append(evaluer(n, c, j))
        print(rangs[-1], flush=True)
    t = pd.DataFrame(rangs)
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 30)
    print()
    for titre, masque in (("Pannes", t.panne != "nominal"), ("Nominaux", t.panne == "nominal")):
        print(titre)
        print(t[masque].dropna(axis=1, how="all").to_string(index=False))
        print()
