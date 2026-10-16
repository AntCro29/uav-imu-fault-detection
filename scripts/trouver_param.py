import sys
from pymavlink import mavutil

mlog = mavutil.mavlink_connection(sys.argv[1])

while True:
    msg = mlog.recv_match(type="PARM")
    if msg is None:
        break
    if msg.Name == "SIM_GPS1_ENABLE":
        print(f"t = {msg.TimeUS / 1e6:.1f} s -> valeur mise à {msg.Value}")