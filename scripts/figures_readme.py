"""Figures simplifiées du README, lues dans l'archive des logs (vols/vol_NNNN.BIN, docs/index_vols.csv).

Usage : python scripts/figures_readme.py [dossier_sortie]   (défaut : docs/figures)
  - readme_brouillage.png : brouillage GPS de 60 s, trajectoire vraie vue de dessus selon la
    réaction (vols 133 à 136 : aucune, atterrissage d'ArduPilot, ArduPilot avec traînée, R3) ;
  - readme_vibration.png : innovations SV, SP, SM (cœur 0) d'un vol normal avec et sans vibration
    (vols 233 et 242), seuils fixes calibrés sans vibration ;
  - readme_leurre_boucle.png : leurre GPS de 100 m sous vibration avec la boucle complète
    (vol 502) : chronogramme (innovations, score de l'autoencodeur, décisions de la boucle, erreur
    de position) et vue de dessus. Le chronogramme lit la trace écrite en vol par vol_auto.py
    (data/en_ligne_20261104-194216.csv, non versionnée).
Archive : ~/drone/archive_logs (ou la variable ARCHIVE_LOGS).
"""
import contextlib
import io
import os
import sys
import joblib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
from pymavlink import mavutil

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import erreur_navigation as en

DEPOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRACE_502 = os.path.join(DEPOT, "data", "en_ligne_20261104-194216.csv")   # trace en vol du vol 502
DETECTEUR_V = os.path.join(DEPOT, "data", "detecteur_vibration.joblib")   # seuil de l'autoencodeur
ARCHIVE = os.environ.get("ARCHIVE_LOGS", os.path.expanduser("~/drone/archive_logs"))
VRAIE, ESTIMEE, GPS, PANNE = "#222222", "#1f6fd1", "#e07b00", "#f4cccc"
SEUILS_FIXES = {"SV": 0.24, "SP": 0.04, "SM": 0.08}   # calibrés sans vibration (docs/resultats.md, test final)


def log(vol):
    return os.path.join(ARCHIVE, "vols", f"vol_{vol:04d}.BIN")


def analyser(vol):
    with contextlib.redirect_stdout(io.StringIO()):   # analyser() imprime son rapport
        return en.analyser(log(vol))


def brouillage(sortie):
    titres = ["Aucune réaction", "ArduPilot : atterrissage", "ArduPilot + traînée :\natterrissage",
              "Ce projet : GPS écarté,\nmission continuée"]
    fig, axes = plt.subplots(1, 4, figsize=(14, 4.2))
    for ax, vol, titre in zip(axes, (133, 134, 135, 136), titres):
        df, centre, t_pert = analyser(vol)
        ax.add_patch(Circle((centre[1], centre[0]), en.ZONE_M, fill=False, ls=":", color="grey"))
        ax.plot(df.e, df.n, color=VRAIE, lw=1.2)
        ax.plot(df.e.iloc[-1], df.n.iloc[-1], "x", color=VRAIE, ms=8, mew=2)
        ax.set_title(titre, fontsize=11)
        ax.set_aspect("equal", adjustable="datalim")
        ax.set_xlabel("est (m)")
        ax.grid(alpha=0.3)
    axes[0].set_ylabel("nord (m)")
    fig.legend(handles=[plt.Line2D([], [], color=VRAIE, label="trajectoire vraie"),
                        plt.Line2D([], [], color=VRAIE, marker="x", ls="", mew=2, label="position à la fin"),
                        plt.Line2D([], [], color="grey", ls=":", label="zone surveillée (60 m)")],
               loc="lower center", ncol=3, frameon=False)
    fig.suptitle("Brouillage GPS de 60 s, vent de 6 m/s : où va le drone ?", fontsize=13)
    fig.tight_layout(rect=(0, 0.07, 1, 0.95))
    fig.savefig(sortie, dpi=120)


def innovations(vol):
    m = mavutil.mavlink_connection(log(vol))
    tc, lignes = None, []
    while True:
        x = m.recv_match(type=["MODE", "XKF4"])
        if x is None:
            break
        if x.get_type() == "MODE":
            if x.Mode == en.MODE_CIRCLE and tc is None:
                tc = x.TimeUS / 1e6
            elif x.Mode == en.MODE_RTL and tc is not None:
                break
        elif x.C == 0 and tc is not None:
            lignes.append((x.TimeUS / 1e6 - tc, x.SV, x.SP, x.SM))
    return pd.DataFrame(lignes, columns=["t", "SV", "SP", "SM"])


def vibration(sortie):
    avec, sans = innovations(233), innovations(242)
    noms = {"SV": "vitesse GPS (SV)", "SP": "position GPS (SP)", "SM": "magnétomètre (SM)"}
    fig, axes = plt.subplots(3, 1, figsize=(10, 6.5), sharex=True)
    for ax, c in zip(axes, noms):
        ax.plot(avec.t, avec[c], color="#c0392b", lw=0.9, label="avec vibration")
        ax.plot(sans.t, sans[c], color=ESTIMEE, lw=0.9, label="sans vibration")
        ax.axhline(SEUILS_FIXES[c], color="black", ls="--", lw=0.9, label="seuil réglé sans vibration")
        ax.set_ylabel(noms[c])
        ax.grid(alpha=0.3)
    axes[0].legend(loc="upper right", ncol=3, fontsize=9)
    axes[-1].set_xlabel("temps de vol en cercle (s)")
    fig.suptitle("Innovations d'un vol normal, avec et sans vibration des moteurs", fontsize=13)
    fig.tight_layout()
    fig.savefig(sortie, dpi=120)


def leurre_boucle(sortie):
    vol = 502
    df, centre, t_pert = analyser(vol)
    trace = pd.read_csv(TRACE_502)
    seuil_ae = joblib.load(DETECTEUR_V)["seuil_ae"]
    ecarte = trace.t_cercle_s[trace.r3 == "ecarte"]
    t_ecarte, t_repris = ecarte.min(), ecarte.max()
    alarme = trace[(trace["AE + ML"] == 1) & (trace.r3 == "normal") & (trace.t_cercle_s < t_ecarte)]
    t_alarme = alarme.t_cercle_s.min()
    a, b = t_pert[0] - 20, t_pert[1] + 50
    tr = trace[(trace.t_cercle_s >= a) & (trace.t_cercle_s <= b)].copy()
    tr.loc[tr.r3 == "ecarte", ["SV", "SP", "score_ae"]] = np.nan   # GPS écarté : innovations figées, non utilisées
    f = df[(df.tc >= a) & (df.tc <= b)]

    fig = plt.figure(figsize=(14, 8.5))
    gs = fig.add_gridspec(4, 2, width_ratios=[2.2, 1], height_ratios=[1, 1, 0.6, 1], hspace=0.5, wspace=0.18)
    axes = [fig.add_subplot(gs[0, 0])]
    axes += [fig.add_subplot(gs[i, 0], sharex=axes[0]) for i in (1, 2, 3)]
    ax_inn, ax_ae, ax_dec, ax_err = axes
    for ax in axes:
        ax.axvspan(*t_pert, color=PANNE, zorder=0)
        ax.grid(alpha=0.3)
    for ax in axes[:-1]:
        ax.tick_params(labelbottom=False)

    ax_inn.semilogy(tr.t_cercle_s, tr.SP.clip(lower=0.01), color=GPS, lw=1, label="position GPS (SP)")
    ax_inn.semilogy(tr.t_cercle_s, tr.SV.clip(lower=0.01), color=ESTIMEE, lw=1, label="vitesse GPS (SV)")
    ax_inn.set_ylabel("innovation")
    ax_inn.legend(loc="upper right", fontsize=8, ncol=2)
    ax_inn.text(t_ecarte + 2, 1, "GPS écarté : innovations\nnon calculées", fontsize=8, color="grey", va="center")
    ax_inn.set_title("① Les innovations GPS explosent quand le leurre commence (zone rose)", fontsize=10, loc="left")

    ax_ae.semilogy(tr.t_cercle_s, tr.score_ae, color="#6a3d9a", lw=1)
    ax_ae.axhline(seuil_ae, color="black", ls="--", lw=0.9, label="seuil d'alarme")
    ax_ae.set_ylabel("score")
    ax_ae.legend(loc="upper right", fontsize=8)
    ax_ae.set_title(f"② L'autoencodeur donne l'alarme {virgule(t_alarme - t_pert[0])} s après le début du leurre",
                    fontsize=10, loc="left")

    ax_dec.broken_barh([(t_alarme, t_ecarte - t_alarme)], (1.1, 0.8), color="#c0392b")
    ax_dec.broken_barh([(t_ecarte, t_repris - t_ecarte)], (0.1, 0.8), color="green")
    ax_dec.set_ylim(0, 2)
    ax_dec.set_yticks([0.5, 1.5], ["GPS écarté", "alarme"])
    ax_dec.text(t_ecarte + 1, 1.5, "classifieur : famille « GPS »", fontsize=8, va="center")
    ax_dec.text(t_repris - 1, 0.5, "GPS repris", fontsize=8, va="center", ha="right", color="white")
    ax_dec.set_title(f"③ {virgule(t_ecarte - t_alarme)} s plus tard, le classifieur reconnaît une panne GPS : "
                     "le GPS est écarté, puis repris quand il redevient cohérent", fontsize=10, loc="left")

    ax_err.plot(f.tc, f.erreur, color=ESTIMEE, lw=1.2)
    ax_err.set_ylabel("erreur (m)")
    ax_err.set_xlabel("temps de vol en cercle (s)")
    ax_err.set_title(f"④ Le drone reste précis : erreur de position ≤ {f.erreur.max():.0f} m, "
                     "alors que le GPS est faux de 100 m", fontsize=10, loc="left")

    ax = fig.add_subplot(gs[:3, 1])
    ax.add_patch(Circle((centre[1], centre[0]), en.ZONE_M, fill=False, ls=":", color="grey"))
    g = gps_vol(vol)
    g = g[(g.tc >= t_pert[0]) & (g.tc <= t_pert[1])]
    vrai = pd.merge_asof(g.sort_values("t"), df[["t", "n", "e"]].sort_values("t"), on="t", direction="nearest")
    g = g[np.hypot(vrai.n_g - vrai.n, vrai.e_g - vrai.e).to_numpy() > 50]   # GPS effectivement décalé
    ax.plot(g.e_g, g.n_g, ".", color=GPS, ms=1.5)
    ax.plot(f.e, f.n, color=VRAIE, lw=1.2)
    ax.plot(f.e_e, f.n_e, color=ESTIMEE, lw=1, ls="--")
    ax.set_aspect("equal", adjustable="datalim")
    ax.set_xlabel("est (m)")
    ax.set_ylabel("nord (m)")
    ax.set_title("Vue de dessus", fontsize=11)
    ax.grid(alpha=0.3)
    ax_leg = fig.add_subplot(gs[3, 1])
    ax_leg.axis("off")
    ax_leg.legend(handles=[plt.Line2D([], [], color=GPS, marker=".", ls="", ms=8, label="position du GPS leurré"),
                       plt.Line2D([], [], color=VRAIE, label="position vraie"),
                       plt.Line2D([], [], color=ESTIMEE, ls="--", label="position estimée par le drone"),
                       plt.Line2D([], [], color="grey", ls=":", label="zone surveillée (60 m)")],
              loc="center", fontsize=9, frameon=False)
    fig.suptitle("La boucle en action : détecter, classer, réagir (leurre GPS de 100 m, sous vibration)", fontsize=13)
    fig.subplots_adjust(left=0.09, right=0.98, top=0.91, bottom=0.07)
    fig.savefig(sortie, dpi=120)


def virgule(x):
    return f"{x:.1f}".replace(".", ",")


def gps_vol(vol):
    """Positions du GPS 1 (en mètres depuis l'origine du log), temps du log et temps de cercle."""
    origine, *_, t_cercle, t_rtl, reglages = en.lire(log(vol))
    m = mavutil.mavlink_connection(log(vol))
    gps = []
    while True:
        x = m.recv_match(type="GPS")
        if x is None:
            break
        if getattr(x, "I", 0) == 0:
            gps.append((x.TimeUS / 1e6, x.Lat, x.Lng))
    g = pd.DataFrame(gps, columns=["t", "lat", "lng"])
    g["n_g"], g["e_g"] = en.en_metres(g.lat, g.lng, origine)
    g["tc"] = g.t - t_cercle
    return g


if __name__ == "__main__":
    dossier = sys.argv[1] if len(sys.argv) > 1 else os.path.join(en.__file__.rsplit("/scripts/", 1)[0], "docs", "figures")
    for nom, f in (("readme_brouillage.png", brouillage), ("readme_vibration.png", vibration),
                   ("readme_leurre_boucle.png", leurre_boucle)):
        f(os.path.join(dossier, nom))
        print(os.path.join(dossier, nom))
