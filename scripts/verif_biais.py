import sys
import matplotlib.pyplot as plt
from pymavlink import mavutil

mlog = mavutil.mavlink_connection(sys.argv[1])

temps = []
biais_x = []
changements = []

while True:
    msg = mlog.recv_match(type=["XKF2", "PARM"])
    if msg is None:
        break
    if msg.get_type() == "XKF2" and msg.C == 0:
        temps.append(msg.TimeUS / 1e6)
        biais_x.append(msg.AX)
    elif msg.get_type() == "PARM" and msg.Name == "SIM_ACC1_BIAS_X":
        changements.append(msg.TimeUS / 1e6)
        print(f"t = {msg.TimeUS / 1e6:.1f} s -> SIM_ACC1_BIAS_X = {msg.Value}")

plt.plot(temps, biais_x)
for t in changements:
    plt.axvline(t, color="red", linestyle="--")
plt.xlabel("Temps depuis le début du log (s)")
plt.ylabel("Biais X estimé par l'EKF (XKF2.AX)")
plt.show()