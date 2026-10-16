"""Cap du drone, intensité du champ mesuré par le compas 1 et innovation magnétomètre.

Usage : python scripts/tracer_cap_magneto.py <log.BIN> <image.png>
Trace sur un axe de temps commun (t = 0 à l'entrée en CIRCLE) : le cap ATT.Yaw,
l'intensité |B| du champ mesuré par le compas 1 (MAG, instance 0, en mG) et SM
(XKF4, cœur 0). Lignes rouges aux injections et vertes aux retraits de panne
(vrais changements de SIM_MAG*_OFS_X, SIM_ACC*_BIAS_X ou SIM_GPS1_ENABLE).
Affiche aussi la durée mesurée d'un tour de cercle (passages du cap par 0°).
"""
import math
import os
import sys
import matplotlib.pyplot as plt
from pymavlink import mavutil

fichier = sys.argv[1]
sortie = sys.argv[2]

PARAMS_PANNE = ("SIM_MAG1_OFS_X", "SIM_MAG2_OFS_X", "SIM_MAG3_OFS_X",
                "SIM_ACC1_BIAS_X", "SIM_ACC2_BIAS_X", "SIM_ACC3_BIAS_X", "SIM_GPS1_ENABLE")
VALEURS_SAINES = {"SIM_GPS1_ENABLE": 1.0}  # pour les autres paramètres, valeur saine = valeur de départ
MODE_CIRCLE = 7
BLEU, ORANGE, ENCRE = "#2a78d6", "#eb6834", "#1f1f1e"

mlog = mavutil.mavlink_connection(fichier)

cap = {"t": [], "v": []}
champ = {"t": [], "v": []}
sm = {"t": [], "v": []}
changements = []
valeurs_depart = {}
dernieres_valeurs = {}
t_circle = None

while True:
    msg = mlog.recv_match(type=["MODE", "ATT", "MAG", "XKF4", "PARM"])
    if msg is None:
        break
    t = msg.TimeUS / 1e6
    genre = msg.get_type()
    if genre == "MODE":
        if msg.Mode == MODE_CIRCLE and t_circle is None:
            t_circle = t
    elif genre == "ATT":
        cap["t"].append(t)
        cap["v"].append(msg.Yaw)
    elif genre == "MAG" and msg.I == 0:
        champ["t"].append(t)
        champ["v"].append(math.sqrt(msg.MagX ** 2 + msg.MagY ** 2 + msg.MagZ ** 2))
    elif genre == "XKF4" and msg.C == 0:
        sm["t"].append(t)
        sm["v"].append(msg.SM)
    elif genre == "PARM" and msg.Name in PARAMS_PANNE:
        # La première valeur lue (relevé initial) sert de référence ; on ne garde
        # ensuite que les vrais changements, ce qui élimine aussi les PARM écrits en double
        if msg.Name not in dernieres_valeurs:
            valeurs_depart[msg.Name] = msg.Value
        elif msg.Value != dernieres_valeurs[msg.Name]:
            saine = VALEURS_SAINES.get(msg.Name, valeurs_depart[msg.Name])
            changements.append((t, msg.Name, msg.Value, msg.Value == saine))
        dernieres_valeurs[msg.Name] = msg.Value

# Référence de temps : entrée en mode CIRCLE (début du log si absente)
t0 = t_circle if t_circle is not None else 0.0

print(f"--- {fichier} (t = 0 à l'entrée en CIRCLE, {t0:.1f} s depuis le début du log)")
for t, nom, valeur, retrait in changements:
    print(f"{t - t0:7.1f} s  {nom} = {valeur:g}  ({'retrait' if retrait else 'injection'})")

# Durée d'un tour : passages du cap de ~360° à ~0° pendant le cercle
passages = [cap["t"][i] - t0 for i in range(1, len(cap["t"]))
            if cap["v"][i - 1] > 300 and cap["v"][i] < 60 and cap["t"][i] > t0]
tours = [b - a for a, b in zip(passages, passages[1:])]
if tours:
    print(f"Durée mesurée d'un tour : {min(tours):.1f} à {max(tours):.1f} s ({len(tours)} tours)")

fig, axes = plt.subplots(3, 1, figsize=(11, 8), sharex=True)
for ax, donnees, nom, couleur in zip(
        axes, (cap, champ, sm),
        ("Cap ATT.Yaw (deg)", "|B| mesuré, compas 1 (mG)", "Innov. magnéto SM\nXKF4, cœur 0"),
        (BLEU, ORANGE, ENCRE)):
    ax.plot([t - t0 for t in donnees["t"]], donnees["v"], color=couleur, linewidth=1.2)
    ax.set_ylabel(nom)
    ax.grid(axis="y", color="#e6e6e1", linewidth=0.6)
    for t, nom_param, valeur, retrait in changements:
        ax.axvline(t - t0, color="green" if retrait else "red", linestyle="--", linewidth=0.8)
    for cote in ("top", "right"):
        ax.spines[cote].set_visible(False)
axes[-1].set_xlabel("Temps depuis l'entrée en CIRCLE (s)")
axes[0].set_xlim(left=-10)

fig.suptitle(f"Cap, champ mesuré et innovation magnétomètre : {os.path.basename(fichier)}",
             x=0.01, ha="left")
plt.tight_layout()
plt.savefig(sortie, dpi=110)
print(f"Figure enregistrée : {sortie}")
