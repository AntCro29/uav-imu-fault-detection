"""Précision du stationnaire en SITL, avec les statistiques de la campagne d'essais réels du DJI Lito X1.

Usage : python scripts/comparer_stationnaire.py <log.BIN> [...]
Vols faits par vol_auto.py --stationnaire H : LOITER pendant STATIONNAIRE_S (200 s). Trois paliers de
60 s commencent 10, 75 et 140 s après l'entrée en LOITER.
Pour chaque palier, centile 95 de l'écart à la position moyenne du palier :
  - position vraie (SIM), l'équivalent de la vidéo dans les essais réels ;
  - position estimée (XKF1 du cœur principal, comme dans erreur_navigation.py), l'équivalent du
    journal DJI ;
  - écart vraie − estimée, chaque série centrée sur sa moyenne du palier ;
en horizontal et en vertical. Inclinaison moyenne (ATT) : direction vers laquelle le drone penche
(d'où vient le vent) et écart-type, à comparer à l'inclinaison relevée sur le DJI.
"""
import math
import sys

import numpy as np
import pandas as pd
from pymavlink import mavutil

from erreur_navigation import en_metres, position_principale

MODE_LOITER = 5
PALIERS_S = (10, 75, 140)
DUREE_PALIER_S = 60


def lire(chemin):
    mlog = mavutil.mavlink_connection(chemin)
    sim, att, textes = [], [], []
    horiz, vert = {0: [], 1: []}, {0: [], 1: []}
    origine = t_loiter = None
    while True:
        msg = mlog.recv_match(type=["ORGN", "SIM", "XKF1", "ATT", "MODE", "MSG"])
        if msg is None:
            break
        t = msg.TimeUS / 1e6
        genre = msg.get_type()
        if genre == "ORGN" and origine is None:
            origine = (msg.Lat, msg.Lng)
        elif genre == "SIM":
            sim.append((t, msg.Lat, msg.Lng, msg.Alt))
        elif genre == "XKF1" and msg.C in horiz:
            horiz[msg.C].append((t, msg.PN, msg.PE))
            vert[msg.C].append((t, -msg.PD, 0.0))
        elif genre == "ATT":
            att.append((t, msg.Roll, msg.Pitch, msg.Yaw))
        elif genre == "MODE" and msg.Mode == MODE_LOITER and t_loiter is None:
            t_loiter = t
        elif genre == "MSG":
            textes.append((t, msg.Message))
    if origine is None or t_loiter is None:
        sys.exit(f"{chemin} : log sans origine EKF ou sans entrée en LOITER")
    vrai = pd.DataFrame(sim, columns=["t", "lat", "lng", "alt"])
    vrai["n"], vrai["e"] = en_metres(vrai.lat, vrai.lng, origine)
    est = pd.DataFrame(position_principale(horiz, textes), columns=["t", "n", "e"])
    est_v = pd.DataFrame(position_principale(vert, textes), columns=["t", "h", "_"])
    return vrai, est, est_v, pd.DataFrame(att, columns=["t", "roll", "pitch", "yaw"]), t_loiter


def p95(x):
    return round(float(np.quantile(x, 0.95)), 2)


def analyser(chemin):
    vrai, est, est_v, att, t0 = lire(chemin)
    lignes = []
    for i, debut in enumerate(PALIERS_S, 1):
        a, b = t0 + debut, t0 + debut + DUREE_PALIER_S
        v = vrai[(vrai.t >= a) & (vrai.t < b)]
        n_est = np.interp(v.t, est.t, est.n)
        e_est = np.interp(v.t, est.t, est.e)
        h_est = np.interp(v.t, est_v.t, est_v.h)
        nv, ev, hv = v.n - v.n.mean(), v.e - v.e.mean(), v.alt - v.alt.mean()
        ne, ee, he = n_est - n_est.mean(), e_est - e_est.mean(), h_est - h_est.mean()
        w = att[(att.t >= a) & (att.t < b)]
        roulis, tangage = w.roll.mean(), w.pitch.mean()
        incl = math.degrees(math.acos(math.cos(math.radians(roulis)) * math.cos(math.radians(tangage))))
        # tangage ArduPilot positif nez haut : le drone penche vers l'avant quand tangage < 0
        direction = (w.yaw.mean() + math.degrees(math.atan2(roulis, -tangage))) % 360
        lignes.append({
            "palier": i, "p95_h_vrai_m": p95(np.hypot(nv, ev)), "p95_h_estimé_m": p95(np.hypot(ne, ee)),
            "p95_écart_h_m": p95(np.hypot(nv - ne, ev - ee)),
            "p95_v_vrai_m": p95(np.abs(hv)), "p95_v_estimé_m": p95(np.abs(he)),
            "incl_moy_deg": round(incl, 1), "penche_vers_deg": round(direction),
            "écart_type_tangage_roulis_deg": f"{w.pitch.std():.1f} / {w.roll.std():.1f}",
        })
    return pd.DataFrame(lignes)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__.splitlines()[2])
    pd.set_option("display.width", 220)
    pd.set_option("display.max_columns", 20)
    for chemin in sys.argv[1:]:
        print(f"== {chemin}")
        print(analyser(chemin).to_string(index=False))
