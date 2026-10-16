"""Comparaison des vols automatiques à échelles communes (innovations XKF4, cœur 0).

Usage : python scripts/comparer_vols.py <image.png>
Écrit pour la série automatique : logs 19 à 25 dans ~/drone/ardupilot/logs/ (voir README).
Colonnes : biais accéléromètre (25, 20), coupure GPS (24, 21), panne magnétomètre (19) ;
lignes : SV, SP, SH, SM, avec la même échelle verticale sur chaque ligne ;
référence nominale en gris (log 22) ; t = 0 à l'entrée en CIRCLE.
"""
import os
import sys
import matplotlib.pyplot as plt
from pymavlink import mavutil

sortie = sys.argv[1]

BLEU, ORANGE, GRIS = "#2a78d6", "#eb6834", "#9a9a94"
ENCRE, ENCRE_2 = "#1f1f1e", "#6b6b66"
CANAUX = [("SV", "Innov. vitesse (SV)"), ("SP", "Innov. position (SP)"),
          ("SH", "Innov. hauteur (SH)"), ("SM", "Innov. magnéto (SM)")]
COLONNES = [
    ("Biais accéléromètre X", [(25, "biais 1,0 m/s²", BLEU, 180), (20, "biais 0,5 m/s²", ORANGE, 180)]),
    ("Coupure GPS", [(24, "coupure 60 s", BLEU, 180), (21, "coupure 30 s", ORANGE, 150)]),
    ("Panne magnétomètre", [(19, "décalage +150 sur X", BLEU, 180)]),
]
NOMINAL = 22


def lire(n):
    m = mavutil.mavlink_connection(os.path.expanduser(f"~/drone/ardupilot/logs/{n:08d}.BIN"))
    t_circle = None
    donnees = {"t": [], **{c: [] for c, _ in CANAUX}}
    while True:
        msg = m.recv_match(type=["MODE", "XKF4"])
        if msg is None:
            break
        t = msg.TimeUS / 1e6
        if msg.get_type() == "MODE" and msg.Mode == 7 and t_circle is None:
            t_circle = t
        elif msg.get_type() == "XKF4" and msg.C == 0 and t_circle is not None:
            donnees["t"].append(t - t_circle)
            for c, _ in CANAUX:
                donnees[c].append(getattr(msg, c))
    return donnees


vols = {n: lire(n) for n in {NOMINAL} | {n for _, liste in COLONNES for n, *_ in liste}}

plt.rcParams.update({"font.size": 9, "axes.edgecolor": "#c9c9c4", "axes.labelcolor": ENCRE_2,
                     "xtick.color": ENCRE_2, "ytick.color": ENCRE_2, "text.color": ENCRE})
fig, axes = plt.subplots(len(CANAUX), len(COLONNES), figsize=(14, 10), sharex=True, sharey="row")

for j, (titre, liste) in enumerate(COLONNES):
    for i, (canal, nom_canal) in enumerate(CANAUX):
        ax = axes[i][j]
        nominal = vols[NOMINAL]
        ax.plot(nominal["t"], nominal[canal], color=GRIS, linewidth=1.0, label="nominal (log 22)")
        for n, nom, couleur, t_retrait in liste:
            d = vols[n]
            ax.plot(d["t"], d[canal], color=couleur, linewidth=1.4, label=f"{nom} (log {n})")
            ax.axvline(t_retrait, color=couleur, linestyle="--", linewidth=0.9)
        ax.axvline(120, color=ENCRE_2, linestyle="--", linewidth=0.9)
        if canal == "SM":
            ax.axhline(1.0, color=ENCRE_2, linestyle=":", linewidth=0.9)
        ax.grid(axis="y", color="#e6e6e1", linewidth=0.6)
        ax.set_axisbelow(True)
        for cote in ("top", "right"):
            ax.spines[cote].set_visible(False)
        if j == 0:
            ax.set_ylabel(nom_canal)
        if i == 0:
            ax.set_title(titre, fontsize=11, color=ENCRE, loc="left")
            ax.legend(loc="upper left", frameon=False, fontsize=8)
        if i == len(CANAUX) - 1:
            ax.set_xlabel("Temps depuis l'entrée en CIRCLE (s)")

axes[3][0].annotate("seuil de rejet (1)", xy=(-5, 1.0), xytext=(-5, 1.03), fontsize=7.5, color=ENCRE_2)
axes[0][0].set_xlim(-10, 280)
fig.suptitle("Innovations EKF (cœur 0) à échelles communes par ligne — injection à 120 s "
             "(tiret gris), retrait (tiret de la couleur du vol)", fontsize=11, x=0.01, ha="left")
plt.tight_layout(rect=(0, 0, 1, 0.97))
plt.savefig(sortie, dpi=120)
print(f"Figure enregistrée : {sortie}")
