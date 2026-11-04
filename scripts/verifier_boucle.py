"""Déroulé d'une campagne de la boucle complète comparé à la commande, sans lire aucun résultat.

Usage : python scripts/verifier_boucle.py [--depuis AAAAMMJJ-HHMMSS] <logs> <journal> [<journal> ...]
(mêmes arguments qu'evaluer_boucle.py). Par vol : SIM_IMU_COUNT et EK3_IMU_MASK à 3, vent, ni
vibration ni flux optique ; paramètres de panne attendus et eux seuls (SIM_ACCn_BIAS_X,
SIM_GYRn_BIAS_X, SIM_ACC1/2/3_BIAS_X pour la dérive, SIM_GPS1_GLTCH_X, SIM_GPS1_JAM,
SIM_MAG1/2/3_OFS_X) ; injection à l'instant demandé, retrait 60 s après, nombre de pas d'une rampe ;
RTL à injection + 150 s (180 s pour un nominal ; un RTL plus tôt est celui du dernier recours de R3,
à lire dans le journal) ; altitude vraie minimale en cercle ; distance horizontale vraie maximale au
départ ; désarmement et position vraie à ce moment ; plus grand intervalle entre deux messages XKF4
(cœur 0) et SIM.
"""
import math
from pymavlink import mavutil
from evaluer_boucle import arguments
from evaluer_rimu import LOGS

REGLAGES = ("SIM_IMU_COUNT", "EK3_IMU_MASK", "SIM_WIND_SPD", "SIM_WIND_DIR", "SIM_WIND_TURB", "SIM_WIND_T",
            "SIM_VIB_MOT_MAX", "SIM_FLOW_ENABLE")
PANNES = sorted({f"SIM_{c}{n}_BIAS_X" for c in ("ACC", "GYR") for n in (1, 2, 3)}
                | {f"SIM_MAG{n}_OFS_X" for n in (1, 2, 3)} | {"SIM_GPS1_GLTCH_X", "SIM_GPS1_JAM", "SIM_GPS1_ENABLE"})


def attendus(c):
    return {"biais": [f"SIM_ACC{c['imu']}_BIAS_X"], "gyro": [f"SIM_GYR{c['imu']}_BIAS_X"],
            "derive": ["SIM_ACC1_BIAS_X", "SIM_ACC2_BIAS_X", "SIM_ACC3_BIAS_X"],
            "leurre": ["SIM_GPS1_GLTCH_X"], "leurre_rampe": ["SIM_GPS1_GLTCH_X"], "jam": ["SIM_GPS1_JAM"],
            "magneto": ["SIM_MAG1_OFS_X", "SIM_MAG2_OFS_X", "SIM_MAG3_OFS_X"], "nominal": []}[c["scenario"]]


def verifier(n, c):
    m = mavutil.mavlink_connection(LOGS.format(n))
    reg, derniere, chg, arm, sim = {}, {}, [], [], []
    tc = trtl = None
    prec = {"XKF4": None, "SIM": None}
    trou = {k: 0.0 for k in prec}
    while True:
        x = m.recv_match(type=["PARM", "MODE", "ARM", "SIM", "XKF4"])
        if x is None:
            break
        t, g = x.TimeUS / 1e6, x.get_type()
        if g in prec and (g != "XKF4" or x.C == 0):
            if prec[g] is not None:
                trou[g] = max(trou[g], t - prec[g])
            prec[g] = t
        if g == "PARM":
            if x.Name in REGLAGES:
                reg[x.Name] = x.Value
            if x.Name in PANNES:
                if x.Name in derniere and x.Value != derniere[x.Name]:
                    chg.append((t, x.Name, x.Value, derniere[x.Name]))
                derniere[x.Name] = x.Value
        elif g == "MODE":
            if x.Mode == 7 and tc is None:
                tc = t
            elif x.Mode == 6 and tc is not None and trtl is None:
                trtl = t
        elif g == "ARM":
            arm.append((t, x.ArmState))
        elif g == "SIM":
            sim.append((t, x.Lat, x.Lng, x.Alt))
    pb = []
    if reg.get("SIM_IMU_COUNT") != 3 or reg.get("EK3_IMU_MASK") != 3:
        pb.append(f"IMU {reg.get('SIM_IMU_COUNT')} masque {reg.get('EK3_IMU_MASK')}")
    vent = (reg.get("SIM_WIND_SPD"), reg.get("SIM_WIND_DIR"), reg.get("SIM_WIND_TURB"))
    if any(v is None or abs(v - w) > 1e-3 for v, w in zip(vent, c["vent"])) or reg.get("SIM_WIND_T") != 1:
        pb.append(f"vent {vent}")
    if reg.get("SIM_VIB_MOT_MAX", 0) > 0 or reg.get("SIM_FLOW_ENABLE", 0) == 1:
        pb.append("vibration ou flux")
    enc = [(t - tc, nom, v, v0) for t, nom, v, v0 in chg if t > tc]
    if len(enc) != len(chg):
        pb.append(f"{len(chg) - len(enc)} changement(s) avant le cercle")
    noms = sorted({e[1] for e in enc})
    if noms != sorted(attendus(c)):
        pb.append(f"paramètres {noms}")
    if c["scenario"] == "nominal":
        rtl_attendu, panne = 180.0, "—"
    else:
        t_inj = enc[0][0] if enc else float("nan")
        t_ret = enc[-1][0] if enc else float("nan")
        pas = len({round(e[0], 1) for e in enc}) - 1
        if abs(t_inj - c["inj"]) > 0.5:
            pb.append(f"injection à {t_inj:.1f} s")
        if abs(t_ret - (c["inj"] + 60)) > 1.0:
            pb.append(f"retrait à {t_ret:.1f} s")
        if c["scenario"] in ("derive", "leurre_rampe") and pas < 55:
            pb.append(f"rampe : {pas} pas")
        vmax = max((abs(e[2] - e[3]) for e in enc), default=0)
        rtl_attendu = c["inj"] + 150
        panne = f"{t_inj:.1f} → {t_ret:.1f} s, {pas} pas, écart max {vmax:.6g}"
    if trtl is None or abs(trtl - tc - rtl_attendu) > 1.0:
        pb.append(f"RTL à {None if trtl is None else round(trtl - tc, 1)} s")
    lat0, lng0, alt0 = sim[0][1], sim[0][2], sim[0][3]
    def dist(p):
        return math.hypot((p[1] - lat0) * 111319.5, (p[2] - lng0) * 111319.5 * math.cos(math.radians(lat0)))
    cercle = [p for p in sim if tc + 10 <= p[0] < (trtl or 1e9)]
    alt_min = min(p[3] - alt0 for p in cercle)
    dmax = max(dist(p) for p in sim)
    desarme = [t for t, s in arm if s == 0]
    if desarme:
        p = min(sim, key=lambda q: abs(q[0] - desarme[-1]))
        fin = f"désarmé à {desarme[-1] - tc:.0f} s, alt vraie {p[3] - alt0:+.1f} m, à {dist(p):.0f} m du départ"
    else:
        p = sim[-1]
        fin = f"NON DÉSARMÉ, fin du log à {p[0] - tc:.0f} s, alt vraie {p[3] - alt0:+.1f} m, à {dist(p):.0f} m"
    return (f"log {n:>3} | {c['scenario']:<12} {c['reponse']:<6} vent {c['vent'][1]:g}° | {panne} | "
            f"alt min cercle {alt_min:.1f} m | dist max {dmax:.0f} m | {fin} | trou XKF4 {trou['XKF4'] * 1000:.0f} ms "
            f"SIM {trou['SIM'] * 1000:.0f} ms | " + ("OK" if not pb else "PROBLÈME : " + " ; ".join(pb)))


if __name__ == "__main__":
    for n, c, _ in arguments():
        print(verifier(n, c), flush=True)
