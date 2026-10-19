"""Erreur de navigation réelle et tenue du cercle d'un vol : vérité du simulateur contre estimation.

Usage : python scripts/erreur_navigation.py <log.BIN> [image.png [titre]]
Position vraie : SIM.Lat/Lng (simulateur, 10 Hz), ramenée en mètres nord/est depuis l'origine de
l'EKF (ORGN) avec LATLON_TO_M d'ArduPilot. Position estimée : XKF1.PN/PE du cœur 0 (même origine,
10 Hz, le cœur que lisent les détecteurs ; identique à POS à 1 cm près au log 37 quand les deux
existent). POS n'est pas utilisé : il n'est presque plus enregistré quand l'EKF perd la position
(1,2 message/s pendant la coupure GPS du log 37). t = 0 à l'entrée en CIRCLE.
Perturbation : du premier au dernier vrai changement de SIM_GPS1_ENABLE, SIM_GPS1_JAM ou
SIM_GPS1_GLTCH_X (PARM), ou de la bascule sur le jeu de sources 2 au retour au jeu 1 (EV 86 / 85).
Mesures par phase (avant, pendant, après, jusqu'au RTL) :
  - erreur de navigation |vraie − estimée| (max et à la fin de la phase) ;
  - distance vraie au centre du cercle (centre = moyenne de la position vraie sur le cercle avant
    la perturbation, après 10 s) : max, et part du temps dans la zone surveillée (< ZONE_M) ;
  - vent estimé par l'EKF (XKF2.VWN/VWE, cœur 0) contre le vent réglé (SIM_WIND_SPD/DIR).
"""
import math
import sys
import numpy as np
import pandas as pd
from pymavlink import mavutil

M_PAR_DEGRE = 0.011131884502145034 * 1e7   # LATLON_TO_M d'ArduPilot (AP_Math/definitions.h:52)
ZONE_M = 60.0                               # zone surveillée : 2 × le rayon du cercle (choix d'Antoine)
PARAMS_GPS = ("SIM_GPS1_ENABLE", "SIM_GPS1_JAM", "SIM_GPS1_GLTCH_X")
SOURCES_SECONDAIRES, SOURCES_PRIMAIRES = 86, 85
MODE_CIRCLE, MODE_RTL = 7, 6
DEBUT_CENTRE = 10.0


def lire(chemin):
    mlog = mavutil.mavlink_connection(chemin)
    sim, pos, vent, textes, debut_fin = [], [], [], [], []
    origine = t_cercle = t_rtl = None
    depart, derniere, reglages = {}, {}, {}
    while True:
        msg = mlog.recv_match(type=["ORGN", "SIM", "XKF1", "XKF2", "MODE", "PARM", "EV", "MSG"])
        if msg is None:
            break
        t = msg.TimeUS / 1e6
        genre = msg.get_type()
        if genre == "ORGN" and origine is None:
            origine = (msg.Lat, msg.Lng)
        elif genre == "SIM":
            sim.append((t, msg.Lat, msg.Lng, msg.Alt))
        elif genre == "XKF1" and msg.C == 0:
            pos.append((t, msg.PN, msg.PE))
        elif genre == "XKF2" and msg.C == 0:
            vent.append((t, msg.VWN, msg.VWE))
        elif genre == "MODE":
            if msg.Mode == MODE_CIRCLE and t_cercle is None:
                t_cercle = t
            elif msg.Mode == MODE_RTL and t_cercle is not None and t_rtl is None:
                t_rtl = t
        elif genre == "PARM":
            if msg.Name in PARAMS_GPS:
                if msg.Name not in derniere:
                    depart[msg.Name] = msg.Value
                elif msg.Value != derniere[msg.Name]:
                    debut_fin.append((t, msg.Value != depart[msg.Name]))
                derniere[msg.Name] = msg.Value
            elif msg.Name in ("SIM_WIND_SPD", "SIM_WIND_DIR"):
                reglages[msg.Name] = msg.Value
        elif genre == "EV" and msg.Id in (SOURCES_SECONDAIRES, SOURCES_PRIMAIRES):
            debut_fin.append((t, msg.Id == SOURCES_SECONDAIRES))
        elif genre == "MSG":
            textes.append((t, msg.Message))
    return origine, sim, pos, vent, textes, debut_fin, t_cercle, t_rtl, reglages


def en_metres(lat, lng, origine):
    n = (np.asarray(lat) - origine[0]) * M_PAR_DEGRE
    e = (np.asarray(lng) - origine[1]) * M_PAR_DEGRE * math.cos(math.radians(origine[0]))
    return n, e


def analyser(chemin):
    origine, sim, pos, vent, textes, debut_fin, t_cercle, t_rtl, reglages = lire(chemin)
    if origine is None or t_cercle is None:
        sys.exit("Log sans origine EKF ou sans entrée en CIRCLE")
    vrai = pd.DataFrame(sim, columns=["t", "lat", "lng", "alt"])
    est = pd.DataFrame(pos, columns=["t", "n_e", "e_e"])
    df = pd.merge_asof(vrai.sort_values("t"), est.sort_values("t"), on="t", direction="nearest")
    df["n"], df["e"] = en_metres(df.lat, df.lng, origine)
    df["erreur"] = np.hypot(df.n - df.n_e, df.e - df.e_e)
    df["tc"] = df.t - t_cercle
    fin = (t_rtl if t_rtl is not None else df.t.iloc[-1]) - t_cercle
    df = df[(df.tc >= 0) & (df.tc <= fin)].reset_index(drop=True)

    debuts = [t - t_cercle for t, debut in debut_fin if debut]
    fins = [t - t_cercle for t, debut in debut_fin if not debut]
    t_pert = (debuts[0], fins[-1] if fins else fin) if debuts else None

    avant = df[(df.tc >= DEBUT_CENTRE) & (df.tc < (t_pert[0] if t_pert else fin))]
    centre = (avant.n.mean(), avant.e.mean())
    df["dist_centre"] = np.hypot(df.n - centre[0], df.e - centre[1])

    print(f"{chemin}")
    if reglages:
        print(f"Vent réglé : {reglages.get('SIM_WIND_SPD', 0):g} m/s venant de {reglages.get('SIM_WIND_DIR', 0):g}°")
    v = pd.DataFrame(vent, columns=["t", "VWN", "VWE"])
    v["tc"] = v.t - t_cercle
    v_avant = v[(v.tc >= DEBUT_CENTRE) & (v.tc < (t_pert[0] if t_pert else fin))]
    if len(v_avant):
        vn, ve = v_avant.VWN.mean(), v_avant.VWE.mean()
        # le vent « vient de » la direction réglée : il souffle vers la direction opposée
        print(f"Vent estimé par l'EKF (cœur 0, cercle avant perturbation) : {math.hypot(vn, ve):.2f} m/s "
              f"venant de {(math.degrees(math.atan2(-ve, -vn))) % 360:.0f}° (VWN {vn:+.2f}, VWE {ve:+.2f})")
    print("Perturbation : " + (f"{t_pert[0]:.1f} → {t_pert[1]:.1f} s de cercle" if t_pert else "aucune"))
    print(f"Centre du cercle (vrai, avant perturbation) : N {centre[0]:+.1f} m, E {centre[1]:+.1f} m ; "
          f"zone surveillée < {ZONE_M:g} m")

    phases = [("avant", DEBUT_CENTRE, t_pert[0] if t_pert else fin)]
    if t_pert:
        phases += [("pendant", t_pert[0], t_pert[1]), ("après", t_pert[1], fin)]
    print(f"\n{'phase':<8} {'durée':>7} {'erreur nav. max':>16} {'à la fin':>9} {'dist. centre max':>17} {'dans la zone':>13}")
    for nom, a, b in phases:
        p = df[(df.tc >= a) & (df.tc < b)]
        if p.empty:
            continue
        print(f"{nom:<8} {b - a:>6.0f}s {p.erreur.max():>15.1f}m {p.erreur.iloc[-1]:>8.1f}m "
              f"{p.dist_centre.max():>16.1f}m {np.mean(p.dist_centre < ZONE_M) * 100:>12.0f}%")
    print("Messages pendant le cercle :")
    for t, texte in textes:
        if 0 <= t - t_cercle <= fin and any(k in texte for k in ("EKF", "lane", "aiding", "Failsafe", "GPS")):
            print(f"  {t - t_cercle:7.1f} s  {texte}")
    return df, centre, t_pert


def tracer(df, centre, t_pert, sortie, titre):
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(1, 2, figsize=(13, 5.5), gridspec_kw={"width_ratios": [1, 1.4]})
    pert = (df.tc >= t_pert[0]) & (df.tc < t_pert[1]) if t_pert else np.zeros(len(df), bool)
    ax[0].plot(df.e, df.n, color="#333333", lw=1, label="vraie")
    ax[0].plot(df.e_e, df.n_e, color="#2a78d6", lw=1, ls="--", label="estimée (EKF)")
    if pert.any():
        ax[0].plot(df.e[pert], df.n[pert], color="#d6452a", lw=1.5, label="vraie, pendant la perturbation")
    ax[0].add_patch(plt.Circle((centre[1], centre[0]), ZONE_M, fill=False, color="#999999", ls=":"))
    ax[0].set_aspect("equal")
    ax[0].set_xlabel("est (m)")
    ax[0].set_ylabel("nord (m)")
    ax[0].legend(fontsize=8, frameon=False)
    ax[1].plot(df.tc, df.erreur, color="#2a78d6", lw=1.2, label="erreur de navigation |vraie − estimée|")
    ax[1].plot(df.tc, df.dist_centre, color="#333333", lw=1.2, label="distance vraie au centre")
    ax[1].axhline(ZONE_M, color="#999999", ls=":", lw=1, label=f"zone surveillée ({ZONE_M:g} m)")
    if t_pert:
        ax[1].axvspan(*t_pert, color="#f3d6d6", lw=0, zorder=0)
    ax[1].set_xlabel("temps depuis l'entrée en cercle (s)  —  zone rose : perturbation")
    ax[1].set_ylabel("m")
    ax[1].legend(fontsize=8, frameon=False)
    for a in ax:
        a.grid(True, color="#e6e6e6", lw=0.6)
        a.set_axisbelow(True)
    fig.suptitle(titre, fontsize=12, x=0.01, ha="left")
    fig.tight_layout()
    fig.savefig(sortie, dpi=110)
    plt.close(fig)


if __name__ == "__main__":
    if len(sys.argv) not in (2, 3, 4):
        sys.exit(__doc__)
    df, centre, t_pert = analyser(sys.argv[1])
    if len(sys.argv) >= 3:
        tracer(df, centre, t_pert, sys.argv[2], sys.argv[3] if len(sys.argv) == 4 else sys.argv[1].split("/")[-1])
