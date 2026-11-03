"""Déroulé d'une campagne à trois IMU comparé à la configuration demandée, sans lire aucun résultat.

Usage : python scripts/verifier_rimu.py <premier_log> <journal> [<journal> ...]
(mêmes arguments qu'evaluer_rimu.py). Par vol : SIM_IMU_COUNT et EK3_IMU_MASK à 3, vent,
vibration et flux optique ; panne sur le seul paramètre attendu (SIM_ACCn_BIAS_X ou
SIM_GYRn_BIAS_X), injection à l'instant demandé, retrait 60 s après, amplitude, nombre de pas
d'une dérive ; RTL à injection + 150 s (180 s pour un nominal) ; désarmement et altitude vraie à
ce moment ; altitude vraie minimale en cercle ; plus grand intervalle entre deux messages XKF4
(cœur 0), IMU (IMU 0) et SIM, pour repérer un trou dans le log. Ni innovations, ni attitude, ni
bascule de cœur.
"""
import sys
from pymavlink import mavutil
from evaluer_rimu import LOGS, associer

REGLAGES = ("SIM_IMU_COUNT", "SIM_WIND_SPD", "SIM_WIND_DIR", "SIM_WIND_TURB", "SIM_WIND_T",
            "SIM_VIB_MOT_MAX", "SIM_FLOW_ENABLE", "EK3_IMU_MASK")
PANNES = [f"SIM_{c}{n}_BIAS_X" for c in ("ACC", "GYR") for n in (1, 2, 3)]


def lire(n):
    m = mavutil.mavlink_connection(LOGS.format(n))
    reg, derniere, chg = {}, {}, []
    tc = trtl = alt0 = None
    arm, sim = [], []
    t_prec = {"XKF4": None, "IMU": None, "SIM": None}
    trou = {k: 0 for k in t_prec}
    while True:
        x = m.recv_match(type=["PARM", "MODE", "ARM", "SIM", "XKF4", "IMU"])
        if x is None:
            break
        t = x.TimeUS / 1e6
        g = x.get_type()
        if g in t_prec and (g != "XKF4" or x.C == 0) and (g != "IMU" or x.I == 0):
            if t_prec[g] is not None:
                trou[g] = max(trou[g], t - t_prec[g])
            t_prec[g] = t
        if g == "PARM":
            if x.Name in REGLAGES:
                reg[x.Name] = x.Value
            if x.Name in PANNES:
                if x.Name in derniere and x.Value != derniere[x.Name]:
                    chg.append((t, x.Name, x.Value))
                derniere[x.Name] = x.Value
        elif g == "MODE":
            if x.Mode == 7 and tc is None:
                tc = t
            elif x.Mode == 6 and tc is not None and trtl is None:
                trtl = t
        elif g == "ARM":
            arm.append((t, x.ArmState))
        elif g == "SIM":
            if alt0 is None:
                alt0 = x.Alt
            sim.append((t, x.Alt - alt0))
    return reg, chg, tc, trtl, arm, sim, trou


def verifier(n, c):
    reg, chg, tc, trtl, arm, sim, trou = lire(n)
    pb = []
    if reg.get("SIM_IMU_COUNT") != 3 or reg.get("EK3_IMU_MASK") != 3:
        pb.append(f"IMU_COUNT {reg.get('SIM_IMU_COUNT')} MASK {reg.get('EK3_IMU_MASK')}")
    vent = (reg.get("SIM_WIND_SPD"), reg.get("SIM_WIND_DIR"), reg.get("SIM_WIND_TURB"))
    if any(abs(a - b) > 1e-3 for a, b in zip(vent, c["vent_reglage"])) or reg.get("SIM_WIND_T") != 1:
        pb.append(f"vent {vent} T {reg.get('SIM_WIND_T')}")
    if (reg.get("SIM_VIB_MOT_MAX", 0) > 0) != c["vib"] or (reg.get("SIM_FLOW_ENABLE", 0) == 1) != c["flux"]:
        pb.append(f"vib {reg.get('SIM_VIB_MOT_MAX')} flux {reg.get('SIM_FLOW_ENABLE')}")
    enc = [(t - tc, nom, v) for t, nom, v in chg if t > tc]
    if len(enc) != len(chg):
        pb.append(f"{len(chg) - len(enc)} changement(s) de panne avant le cercle")
    noms = sorted({nom for _, nom, _ in enc})
    if c["scenario"] == "nominal":
        if enc:
            pb.append(f"panne dans un nominal : {noms}")
        rtl_attendu, panne = 180.0, "—"
    else:
        attendu = f"SIM_{'GYR' if c['scenario'] == 'gyro' else 'ACC'}{c['imu']}_BIAS_X"
        if noms != [attendu]:
            pb.append(f"paramètres touchés {noms}, attendu {attendu}")
        t_inj = enc[0][0] if enc else float("nan")
        retraits = [t for t, _, v in enc if v == 0]
        t_ret = retraits[-1] if retraits else float("nan")
        vmax = max((abs(v) for _, _, v in enc), default=0)
        pas = len({round(t, 1) for t, _, v in enc if v != 0})
        if abs(t_inj - c["inj"]) > 0.5:
            pb.append(f"injection à {t_inj:.1f} s")
        if abs(t_ret - (c["inj"] + 60)) > 1.0:
            pb.append(f"retrait à {t_ret:.1f} s")
        if abs(vmax - float(c["amp"])) > 1e-3:
            pb.append(f"amplitude max {vmax:g}")
        if c["scenario"] == "derive" and pas < 55:
            pb.append(f"rampe : {pas} pas")
        rtl_attendu = c["inj"] + 150
        panne = (f"{attendu} {t_inj:.1f} → {t_ret:.1f} s, max {vmax:g}"
                 + (f", {pas} pas" if c["scenario"] == "derive" else ""))
    if trtl is None or abs(trtl - tc - rtl_attendu) > 1.0:
        pb.append(f"RTL à {None if trtl is None else round(trtl - tc, 1)} s")
    alt_min = min(a for t, a in sim if tc + 10 <= t < (trtl or 1e9))
    desarme = [t for t, s in arm if s == 0]
    if desarme:
        alt_d = min(sim, key=lambda p: abs(p[0] - desarme[-1]))[1]
        fin = f"désarmé à {desarme[-1] - tc:.0f} s, alt vraie {alt_d:+.1f} m"
    else:
        fin = f"non désarmé, fin du log à {sim[-1][0] - tc:.0f} s, alt vraie {sim[-1][1]:+.1f} m"
    trous = ", ".join(f"{k} {d * 1000:.0f} ms" for k, d in trou.items())
    return (f"log {n} | {c['scenario']} {c['reponse']} vent {c['vent']} {'vib+flux' if c['vib'] else 'calme'} | "
            f"{panne} | RTL {trtl - tc:.1f} s | alt min cercle {alt_min:.1f} m | {fin} | trou max {trous} | "
            + ("OK" if not pb else "PROBLÈME : " + " ; ".join(pb)))


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    for n, c, _ in associer(int(sys.argv[1]), sys.argv[2:]):
        print(verifier(n, c), flush=True)
