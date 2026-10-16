import sys
import pandas as pd
from pymavlink import mavutil

nom_fichier = sys.argv[1]
nom_sortie = sys.argv[2]

mlog = mavutil.mavlink_connection(nom_fichier)

lignes = []
while True:
    msg = mlog.recv_match(type="XKF4")
    if msg is None:
        break
    lignes.append({
        "temps_us": msg.TimeUS,
        "innov_vitesse": msg.SV,
        "innov_position": msg.SP,
        "innov_hauteur": msg.SH,
        "innov_magneto": msg.SM,
    })

df = pd.DataFrame(lignes)
df.to_csv(nom_sortie, index=False)
print(f"{len(df)} messages extraits vers {nom_sortie}")