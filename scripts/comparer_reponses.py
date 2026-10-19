"""Compare les réponses à une même panne : une ligne par vol, positions et erreurs en fonction du temps.

Usage : python scripts/comparer_reponses.py <image.png> <titre> <log:étiquette> [...]
  log : numéro du log dans ~/drone/ardupilot/logs (ou $ARDUPILOT/logs).
Colonnes : trajectoire vue de dessus, positions nord et est en fonction du temps (vraie et estimée,
cadrées sur la vraie), erreur de navigation et distance au centre (échelle log au-delà de 50 m).
Marques : panne, bascules de R3 (EV 86 / 85), LAND et RTL décidés en cours de mission.
Mesures : celles de erreur_navigation.py.
Exemple (leurre en échelon, partie B) :
    python scripts/comparer_reponses.py docs/figures/leurre_echelon_4_reponses.png "Leurre" \
        "151:R0 rien" "152:R1 natif" "153:R2 natif + traînée" "154:R3"
"""
import contextlib
import io
import os
import sys
import numpy as np
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import erreur_navigation as en

LOGS = os.path.join(os.environ.get("ARDUPILOT", os.path.expanduser("~/drone/ardupilot")), "logs")

VRAIE, ESTIMEE, PANNE, GRILLE = "#333333", "#2a78d6", "#f3d6d6", "#e6e6e6"
MODE_COUL = {9: ("LAND", "#d6452a"), 6: ("RTL", "#eda100")}


def charger(n):
    chemin = os.path.join(LOGS, f"{n:08d}.BIN")
    with contextlib.redirect_stdout(io.StringIO()):
        df, centre, t_pert = en.analyser(chemin)
        _, _, _, _, _, _, bascules, modes, t_cercle, _, _ = en.lire(chemin)
    bascules = [(t - t_cercle, b) for t, b in bascules if t > t_cercle]
    modes = [(t - t_cercle, md) for t, md in modes if 0 < t - t_cercle <= df.tc.iloc[-1]]
    return df, centre, t_pert, bascules, modes


def cadre(v, marge=0.15):
    a, b = np.nanmin(v), np.nanmax(v)
    d = max(b - a, 20) * marge
    return a - d, b + d


def ligne(ax, df, centre, t_pert, bascules, modes, etiquette, t_max):
    t = df.tc
    for a in ax[1:]:
        if t_pert:
            a.axvspan(*t_pert, color=PANNE, lw=0, zorder=0)
        for tb, sans_gps in bascules:
            a.axvline(tb, color="#1baf7a", lw=1.2, ls="--" if sans_gps else ":")
        for tm, md in modes:
            if md in MODE_COUL:
                a.axvline(tm, color=MODE_COUL[md][1], lw=1.5)
    # vue de dessus, cadrée sur la position vraie
    ax[0].plot(df.e, df.n, color=VRAIE, lw=1)
    ax[0].plot(df.e_e, df.n_e, color=ESTIMEE, lw=1, ls="--")
    ax[0].add_patch(plt.Circle((centre[1], centre[0]), en.ZONE_M, fill=False, color="#999999", ls=":"))
    ax[0].set_xlim(*cadre(np.r_[df.e, centre[1] - en.ZONE_M, centre[1] + en.ZONE_M]))
    ax[0].set_ylim(*cadre(np.r_[df.n, centre[0] - en.ZONE_M, centre[0] + en.ZONE_M]))
    ax[0].set_aspect("equal", adjustable="box")
    ax[0].set_ylabel(etiquette, fontsize=10, fontweight="bold")
    # positions en fonction du temps, cadrées sur la vraie
    for a, vrai, est, nom in ((ax[1], df.n, df.n_e, "nord"), (ax[2], df.e, df.e_e, "est")):
        a.plot(t, vrai, color=VRAIE, lw=1.1)
        a.plot(t, est, color=ESTIMEE, lw=1.1, ls="--")
        lo, hi = cadre(vrai)
        a.set_ylim(lo, hi)
        hors = (est < lo) | (est > hi)
        if hors.any():
            a.text(0.01, 0.04, f"estimée hors cadre (jusqu'à {np.nanmax(np.abs(est)):.0f} m)",
                   transform=a.transAxes, fontsize=7, color=ESTIMEE)
        a.set_ylabel(f"{nom} (m)", fontsize=8)
    ax[3].plot(t, df.erreur, color=ESTIMEE, lw=1.1)
    ax[3].plot(t, df.dist_centre, color=VRAIE, lw=1.1)
    ax[3].axhline(en.ZONE_M, color="#999999", ls=":", lw=1)
    ax[3].set_yscale("symlog", linthresh=50)
    ax[3].set_ylim(bottom=0)
    for a in ax[1:]:
        a.set_xlim(0, t_max)
    ax[3].set_ylabel("m (échelle log au-delà de 50)", fontsize=8)
    for a in ax:
        a.grid(True, color=GRILLE, lw=0.6)
        a.set_axisbelow(True)
        a.tick_params(labelsize=7)


if __name__ == "__main__":
    if len(sys.argv) < 4:
        sys.exit(__doc__)
    sortie, titre, vols = sys.argv[1], sys.argv[2], [a.split(":", 1) for a in sys.argv[3:]]
    fig, axes = plt.subplots(len(vols), 4, figsize=(17, 3.4 * len(vols)),
                             gridspec_kw={"width_ratios": [1, 1.3, 1.3, 1.3]})
    axes = np.atleast_2d(axes)
    donnees = [charger(int(n)) for n, _ in vols]
    # fin de l'axe du temps : fin prévue de la mission (retrait + 90 s), la plus tardive des vols
    t_max = max(d[2][1] + 90 if d[2] else d[0].tc.iloc[-1] for d in donnees)
    for ax, d, (_, etiquette) in zip(axes, donnees, vols):
        ligne(ax, *d, etiquette, t_max)
    for a, t in zip(axes[0], ["trajectoire vue de dessus", "position nord en fonction du temps",
                              "position est en fonction du temps", "erreur de navigation et distance au centre"]):
        a.set_title(t, fontsize=9)
    axes[-1, 0].set_xlabel("est (m)", fontsize=8)
    for a in axes[-1, 1:]:
        a.set_xlabel("temps depuis l'entrée en cercle (s)", fontsize=8)
    poignees = [plt.Line2D([], [], color=VRAIE, lw=1.2, label="vraie / distance vraie au centre"),
                plt.Line2D([], [], color=ESTIMEE, lw=1.2, ls="--", label="estimée par l'EKF / erreur de navigation"),
                plt.Rectangle((0, 0), 1, 1, color=PANNE, label="panne"),
                plt.Line2D([], [], color="#1baf7a", ls="--", label="R3 : GPS écarté"),
                plt.Line2D([], [], color="#1baf7a", ls=":", label="R3 : retour au GPS"),
                plt.Line2D([], [], color="#d6452a", label="LAND décidé par ArduPilot"),
                plt.Line2D([], [], color="#eda100", label="RTL décidé par ArduPilot"),
                plt.Line2D([], [], color="#999999", ls=":", label="zone surveillée (60 m)")]
    fig.legend(handles=poignees, loc="lower center", ncol=8, fontsize=8, frameon=False)
    fig.suptitle(titre, fontsize=12, x=0.01, ha="left")
    fig.tight_layout(rect=(0, 0.03, 1, 0.97))
    fig.savefig(sortie, dpi=100)
    print(sortie)
