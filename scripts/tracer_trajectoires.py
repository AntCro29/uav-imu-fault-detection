"""Trajectoires pendant le cercle, vues de dessus, pour plusieurs logs côte à côte.

Usage : python scripts/tracer_trajectoires.py <image.png> <log1.BIN> [<log2.BIN> ...]
Positions POS entre l'entrée en CIRCLE et le passage en RTL, en mètres par rapport au point de
décollage (première position du log). Le titre de chaque vue rappelle le vent réglé
(SIM_WIND_SPD, SIM_WIND_DIR, SIM_WIND_TURB) et une flèche indique le sens du vent.
"""
import math
import os
import sys
import matplotlib.pyplot as plt
from pymavlink import mavutil

MODE_CIRCLE, MODE_RTL = 7, 6
BLEU, ORANGE = "#2a78d6", "#eb6834"

sortie = sys.argv[1]
logs = sys.argv[2:]

fig, axes = plt.subplots(1, len(logs), figsize=(4.7 * len(logs), 4.8), squeeze=False)
for ax, chemin in zip(axes[0], logs):
    mlog = mavutil.mavlink_connection(chemin)
    t_circle = t_rtl = origine = None
    vent = {}
    est, nord = [], []
    while True:
        msg = mlog.recv_match(type=["MODE", "POS", "PARM"])
        if msg is None:
            break
        t = msg.TimeUS / 1e6
        genre = msg.get_type()
        if genre == "PARM" and msg.Name in ("SIM_WIND_SPD", "SIM_WIND_DIR", "SIM_WIND_TURB"):
            vent[msg.Name] = msg.Value
        elif genre == "MODE":
            if msg.Mode == MODE_CIRCLE and t_circle is None:
                t_circle = t
            elif msg.Mode == MODE_RTL and t_circle is not None and t_rtl is None:
                t_rtl = t
        elif genre == "POS":
            if origine is None:
                origine = (msg.Lat, msg.Lng)
            elif t_circle is not None and t_rtl is None:
                est.append((msg.Lng - origine[1]) * 111320 * math.cos(math.radians(origine[0])))
                nord.append((msg.Lat - origine[0]) * 111320)

    ax.plot(est, nord, color=BLEU, linewidth=1)
    ax.plot(0, 0, "k+", markersize=10)
    vitesse = vent.get("SIM_WIND_SPD", 0)
    titre = f"{os.path.basename(chemin)} : "
    if vitesse > 0:
        direction = math.radians(vent.get("SIM_WIND_DIR", 0))
        titre += f"{vitesse:g} m/s de {vent.get('SIM_WIND_DIR', 0):g}°, turb. {vent.get('SIM_WIND_TURB', 0):g}"
        # le vent vient de SIM_WIND_DIR : la flèche pointe dans le sens où il souffle
        dx, dy = -math.sin(direction) * 25, -math.cos(direction) * 25
        ax.annotate("vent", xy=(dx, -45 + dy), xytext=(0, -45), color=ORANGE, ha="center",
                    arrowprops=dict(arrowstyle="->", color=ORANGE))
    else:
        titre += "sans vent"
    ax.set_title(titre, fontsize=10, loc="left")
    ax.set_aspect("equal")
    ax.set_xlim(-70, 70)
    ax.set_ylim(-80, 60)
    ax.set_xlabel("Est (m)")
    ax.grid(color="#e6e6e1", linewidth=0.6)
axes[0][0].set_ylabel("Nord (m)")
fig.suptitle("Trajectoire pendant le cercle, vue de dessus (+ = point de décollage)", x=0.01, ha="left")
plt.tight_layout(rect=(0, 0, 1, 0.95))
plt.savefig(sortie, dpi=105)
print(f"Figure enregistrée : {sortie}")
