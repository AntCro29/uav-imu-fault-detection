import sys
import matplotlib.pyplot as plt
from pymavlink import mavutil

fichier = sys.argv[1]
sortie = sys.argv[2]

noms_modes = {0: "STABILIZE", 2: "ALT_HOLD", 4: "GUIDED", 5: "LOITER",
              6: "RTL", 7: "CIRCLE", 9: "LAND"}

mlog = mavutil.mavlink_connection(fichier)

evenements = []
xkf4 = {"t": [], "sv": [], "sp": [], "sh": [], "sm": []}
gps = {"t": [], "status": [], "nsats": []}

while True:
    msg = mlog.recv_match(type=["XKF4", "GPS", "ARM", "MODE", "PARM"])
    if msg is None:
        break
    t = msg.TimeUS / 1e6
    genre = msg.get_type()
    if genre == "XKF4" and msg.C == 0:
        xkf4["t"].append(t)
        xkf4["sv"].append(msg.SV)
        xkf4["sp"].append(msg.SP)
        xkf4["sh"].append(msg.SH)
        xkf4["sm"].append(msg.SM)
    elif genre == "GPS":
        gps["t"].append(t)
        gps["status"].append(msg.Status)
        gps["nsats"].append(msg.NSats)
    elif genre == "ARM":
        evenements.append((t, "arm", f"ARM état={msg.ArmState}"))
    elif genre == "MODE":
        numero = msg.Mode
        evenements.append((t, "mode", f"MODE {noms_modes.get(numero, numero)}"))
    elif genre == "PARM" and msg.Name in ("SIM_GPS1_ENABLE", "SIM_ACC1_BIAS_X"):
        evenements.append((t, "gps", f"{msg.Name} = {msg.Value}"))

# Référence de temps : premier armement
t_arm = next((t for t, genre, texte in evenements
              if genre == "arm" and texte.endswith("1")), 0.0)

# On ignore les PARM écrits avant l'armement (dump initial des paramètres)
evenements = [e for e in evenements if e[1] != "gps" or e[0] > t_arm]

print(f"--- Chronologie (secondes après l'armement) : {fichier}")
for t, genre, texte in sorted(evenements):
    if t >= t_arm - 1:
        print(f"{t - t_arm:7.1f} s  {texte}")

fig, axes = plt.subplots(5, 1, figsize=(11, 11), sharex=True)
tx = [t - t_arm for t in xkf4["t"]]
for ax, cle, nom in zip(axes[:4], ["sv", "sp", "sh", "sm"],
                        ["Innov. vitesse", "Innov. position",
                         "Innov. hauteur", "Innov. magneto"]):
    ax.plot(tx, xkf4[cle])
    ax.set_ylabel(nom)

tg = [t - t_arm for t in gps["t"]]
axes[4].plot(tg, gps["nsats"], label="Satellites")
axes[4].plot(tg, gps["status"], label="Status fix")
axes[4].set_ylabel("GPS")
axes[4].legend()
axes[4].set_xlabel("Temps depuis l'armement (s)")

for t, genre, texte in evenements:
    if t < t_arm:
        continue
    couleur = "red" if genre == "gps" else "grey"
    for ax in axes:
        ax.axvline(t - t_arm, color=couleur, linestyle="--", linewidth=0.8)

axes[0].set_xlim(left=-5)
plt.tight_layout()
plt.savefig(sortie)
plt.show()