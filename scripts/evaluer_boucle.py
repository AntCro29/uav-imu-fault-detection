"""Résultats d'une campagne de la boucle complète : décisions, conformité, erreurs vraies.

Usage : python scripts/evaluer_boucle.py [--depuis AAAAMMJJ-HHMMSS] <logs> <journal> [<journal> ...]
<logs> : numéros des logs dans l'ordre des vols, en plages séparées par des virgules (la numérotation
d'ArduPilot repart à 1 après 500, LOG_MAX_FILES, AP_Logger.cpp:198-205). Les journaux (ceux de
l'horodatage --depuis ou plus récents) sont triés par horodatage et associés un à un à ces logs ; la
configuration est lue dans le nom du journal.
Exemple (campagne de test du 2026-11-03, vols 445 à 492) :
  python scripts/evaluer_boucle.py --depuis 20261103-182500 459-500,1-6 data/journal_*_2026110[34]-*.txt
Par vol, t = 0 à l'entrée en CIRCLE :
  - décision de la boucle (première ligne « BOUCLE : famille ... »), IMU déclarée par le vote et son
    délai, exclusions du GPS par R3 (délai, cause), retours au GPS, dernier recours ;
  - conformité au résultat attendu, fixé avant tout calcul : biais sur l'IMU 1 → vote IMU 0 acc,
    GPS gardé ; gyro sur l'IMU 2 → vote IMU 1 gyr, GPS gardé ; dérive commune → aucune IMU, GPS
    gardé ; leurres et brouillage → GPS écarté pendant la panne, aucune IMU ; magnétomètre et
    nominal → aucune action ;
  - erreur d'attitude et de position vraies du cœur principal (evaluer_rimu.lire), au maximum
    pendant la panne et 90 s après (nominal : cercle de 10 à 180 s) ;
  - part du temps dans la zone surveillée (< 60 m du centre vrai du cercle avant la panne), de
    l'injection à +150 s.
"""
import os
import re
import sys
import numpy as np
import pandas as pd
from evaluer_rimu import lire

ZONE_M = 60.0
SCENARIOS = ("nominal", "biais", "derive", "gyro", "leurre_rampe", "leurre", "jam", "magneto")
GPS = ("leurre", "leurre_rampe", "jam")
IMU_ATTENDUE = {"biais": "IMU 0 acc", "gyro": "IMU 1 gyr"}


def plages(texte):
    """« 459-500,1-6 » → [459, ..., 500, 1, ..., 6]"""
    logs = []
    for p in texte.split(","):
        a, _, b = p.partition("-")
        logs += list(range(int(a), int(b or a) + 1))
    return logs


def configuration(chemin):
    """Configuration d'un vol lue dans le nom de son journal (journal_<arguments>_<date>.txt)."""
    nom = os.path.basename(chemin)[len("journal_"):-len("_AAAAMMJJ-HHMMSS.txt")]
    scenario = next(s for s in SCENARIOS if nom.startswith(s))
    a = [x for x in nom[len(scenario):].split("_") if x]
    opt = lambda nom_, defaut=None: a[a.index(nom_) + 1] if nom_ in a else defaut
    return {"scenario": scenario, "vent": tuple(float(v) for v in a[:3]), "inj": float(opt("injection", "nan")),
            "imu": int(opt("imu", 0)), "amp": opt("amplitude", ""), "reponse": opt("reponse", "rien")}


def associer(logs, journaux, depuis=None):
    """(log, configuration, journal) pour chaque journal, dans l'ordre chronologique."""
    journaux = sorted((j for j in journaux if depuis is None or j[-19:-4] >= depuis), key=lambda p: p[-19:])
    if len(journaux) != len(logs):
        sys.exit(f"{len(journaux)} journaux pour {len(logs)} logs")
    return [(n, configuration(j), j) for n, j in zip(logs, journaux)]


def lire_journal(chemin):
    r = {"famille": None, "decision": None, "imu": None, "t_imu": None, "exclusions": [], "retours": [], "recours": None}
    for ligne in open(chemin):
        m = re.search(r"cercle=\s*([\d.]+) s", ligne)
        if not m:
            continue
        t = float(m.group(1))
        if "BOUCLE : famille" in ligne and r["famille"] is None:
            r["famille"] = re.search(r"famille (\S+)", ligne).group(1).rstrip(",")
            r["decision"] = ligne.split("BOUCLE : ", 1)[1].strip()
        d = re.search(r"R-IMU : IMU (\d) \((\w+)\) déclarée", ligne)
        if d and r["imu"] is None:
            r["imu"], r["t_imu"] = f"IMU {d.group(1)} {d.group(2)}", t
        e = re.search(r"R3 : GPS écarté \(([^)]*)\)", ligne)
        if e:
            r["exclusions"].append((t, e.group(1)))
        if "R3 : retour au GPS" in ligne:
            r["retours"].append(t)
        if "dernier recours" in ligne and r["recours"] is None:
            r["recours"] = (t, ligne.split("dernier recours", 1)[1].strip())
    return r


def evaluer(n, c, j):
    jr = lire_journal(j)
    att, pos, princ = lire(n)
    nominal = c["scenario"] == "nominal"
    t0 = 10.0 if nominal else c["inj"]
    t1 = 180.0 if nominal else c["inj"] + 60
    fin = 180.0 if nominal else c["inj"] + 150
    avant = pos[(pos.tc >= 10) & (pos.tc < (180 if nominal else t0))]
    centre = (avant.n.mean(), avant.e.mean())
    fen = pos[(pos.tc >= t0) & (pos.tc < fin)]
    zone = np.mean(np.hypot(fen.n - centre[0], fen.e - centre[1]) < ZONE_M) * 100
    excl = jr["exclusions"]
    pb = []
    if c["scenario"] in GPS:
        if not [x for x in excl if t0 <= x[0] < t1]:
            pb.append("GPS non écarté pendant la panne")
        if jr["imu"]:
            pb.append(f"{jr['imu']} déclarée à tort")
    else:
        if excl:
            pb.append("GPS écarté à tort")
        attendue = IMU_ATTENDUE.get(c["scenario"])
        if c["reponse"] in ("boucle", "rimu") and jr["imu"] != attendue:
            pb.append(f"vote : {jr['imu'] or 'aucune'} (attendu {attendue or 'aucune'})")
    r = {"log": n, "scenario": c["scenario"], "vent": int(c["vent"][1]), "reponse": c["reponse"],
         "famille": jr["famille"] or "—",
         "imu": (f"{jr['imu']} +{jr['t_imu'] - t0:.1f}" if jr["imu"] else "—"),
         "gps_ecarte": "; ".join(f"+{t - t0:.1f} ({cause.split(';')[0][:22]})" for t, cause in excl) or "—",
         "retour": ", ".join(f"+{t - t0:.1f}" for t in jr["retours"]) or "—",
         "recours": f"+{jr['recours'][0] - t0:.1f} {jr['recours'][1][:20]}" if jr["recours"] else "—"}
    phases = {"cercle": (10, 180)} if nominal else {"pendant": (t0, t1), "apres": (t1, t1 + 90)}
    for ph, (a, b) in phases.items():
        r[f"att_{ph}"] = round(att[(att.tc >= a) & (att.tc < b)].err.max(), 2)
        r[f"pos_{ph}"] = round(pos[(pos.tc >= a) & (pos.tc < b)].err.max(), 1)
    r["zone_%"] = round(zone)
    r["conforme"] = "oui" if not pb else "NON : " + " ; ".join(pb)
    r["decision"] = jr["decision"] or "—"
    return r


def arguments():
    a = sys.argv[1:]
    depuis = None
    if "--depuis" in a:
        i = a.index("--depuis")
        depuis = a[i + 1]
        del a[i:i + 2]
    if len(a) < 2:
        sys.exit(__doc__)
    return associer(plages(a[0]), a[1:], depuis)


if __name__ == "__main__":
    rangs = []
    for n, c, j in arguments():
        rangs.append(evaluer(n, c, j))
        print(rangs[-1], flush=True)
    t = pd.DataFrame(rangs)
    pd.set_option("display.width", 320)
    pd.set_option("display.max_columns", 40)
    pd.set_option("display.max_colwidth", 60)
    print()
    for titre, masque in (("Pannes", t.scenario != "nominal"), ("Nominaux", t.scenario == "nominal")):
        print(titre)
        print(t[masque].drop(columns="decision").dropna(axis=1, how="all").to_string(index=False))
        print()
    print("Décisions de la boucle")
    print(t[t.reponse == "boucle"][["log", "scenario", "vent", "decision"]].to_string(index=False))
