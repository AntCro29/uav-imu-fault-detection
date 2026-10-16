import os
import sys
import matplotlib.pyplot as plt
from pymavlink import mavutil

fichier = sys.argv[1]
sortie = sys.argv[2]

PARAMS_BIAIS = ("SIM_ACC1_BIAS_X", "SIM_ACC2_BIAS_X", "SIM_ACC3_BIAS_X")
MODE_CIRCLE = 7

mlog = mavutil.mavlink_connection(fichier)

biais = {"t": [], "ax": []}
magneto = {"t": [], "sm": []}
changements = []
dernieres_valeurs = {}
t_circle = None

while True:
    msg = mlog.recv_match(type=["XKF2", "XKF4", "MODE", "PARM"])
    if msg is None:
        break
    t = msg.TimeUS / 1e6
    genre = msg.get_type()
    if genre == "XKF2" and msg.C == 0:
        biais["t"].append(t)
        biais["ax"].append(msg.AX)
    elif genre == "XKF4" and msg.C == 0:
        magneto["t"].append(t)
        magneto["sm"].append(msg.SM)
    elif genre == "MODE":
        if msg.Mode == MODE_CIRCLE and t_circle is None:
            t_circle = t
    elif genre == "PARM" and msg.Name in PARAMS_BIAIS:
        # La première valeur lue (relevé initial) sert de référence ; on ne garde
        # ensuite que les vrais changements, ce qui élimine aussi les PARM écrits en double
        if msg.Name in dernieres_valeurs and msg.Value != dernieres_valeurs[msg.Name]:
            changements.append((t, msg.Name, msg.Value))
        dernieres_valeurs[msg.Name] = msg.Value

# Référence de temps : entrée en mode CIRCLE (début du log si absente)
t0 = t_circle if t_circle is not None else 0.0

print(f"--- {fichier} (t = 0 à l'entrée en CIRCLE, {t0:.1f} s depuis le début du log)")
for t, nom, valeur in changements:
    print(f"{t - t0:7.1f} s  {nom} = {valeur}")

fig, (ax_biais, ax_mag) = plt.subplots(2, 1, figsize=(11, 7), sharex=True)

ax_biais.plot([t - t0 for t in biais["t"]], biais["ax"])
ax_biais.set_ylabel("Biais X estimé (m/s²)\nXKF2.AX, cœur 0")

ax_mag.plot([t - t0 for t in magneto["t"]], magneto["sm"])
ax_mag.set_ylabel("Innov. magnéto\nXKF4.SM, cœur 0")
ax_mag.set_xlabel("Temps depuis l'entrée en CIRCLE (s)")

for t, nom, valeur in changements:
    couleur = "red" if valeur != 0 else "green"
    for ax in (ax_biais, ax_mag):
        ax.axvline(t - t0, color=couleur, linestyle="--", linewidth=0.8)

fig.suptitle(f"Biais estimé et innovation magnétomètre : {os.path.basename(fichier)}")
plt.tight_layout()
plt.savefig(sortie)
print(f"Figure enregistrée : {sortie}")
