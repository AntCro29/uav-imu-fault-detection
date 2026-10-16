"""Vol SITL automatique selon la procédure du projet, piloté en pymavlink au lieu de MAVProxy.

Usage : python vol_auto.py <scenario> [vent_vitesse vent_direction vent_turbulence]
                           [--injection T] [--amplitude A]
        (le SITL doit écouter sur tcp:127.0.0.1:5760)
Scénarios : nominal, gps60, gps30, biais10, biais05, biais (amplitude obligatoire), magneto
Vent optionnel : vitesse (m/s), direction d'où il vient (degrés vrais), turbulence (m/s).
--injection : instant d'injection en s après l'entrée en CIRCLE (120 par défaut). Le cercle
est très régulier (un tour ≈ 30,8 s) : changer l'instant change le cap à l'injection.
--amplitude : biais en m/s² (biais*), ou décalage ajouté à la valeur de départ de
SIM_MAG*_OFS_X (magneto, défaut +150) ; sans objet pour les coupures GPS.
Réglé avant le décollage avec SIM_WIND_T = 1 (vent uniforme en altitude : le drone à 15 m
subit le vent réglé ; par défaut le simulateur le réduirait de √(altitude / 60)).
Le plus simple est de passer par scripts/lancer_vol.sh, qui démarre et arrête le SITL.

Déroulé : attente que les deux cœurs EKF utilisent le GPS, FS_EKF_ACTION 0,
CIRCLE_RADIUS_M 30, CIRCLE_RATE 15, mode guided, armement, takeoff 15,
stabilisation 10 s, rc 3 1500 (renvoyé toutes les 0,5 s), mode circle.
Vol nominal : 180 s de cercle. Vol avec panne : cercle jusqu'à l'instant d'injection (120 s
par défaut), injection (tous les paramètres envoyés d'affilée), durée de la panne, retrait,
90 s de cercle.
Puis mode rtl et attente du désarmement.
"""
import argparse
import sys
import time
from pymavlink import mavutil

IMU = ["SIM_ACC1_BIAS_X", "SIM_ACC2_BIAS_X", "SIM_ACC3_BIAS_X"]
SCENARIOS = {
    "nominal": None,
    "gps60": {"params": ["SIM_GPS1_ENABLE"], "attendu": 1.0, "injection": 0.0, "retrait": 1.0, "duree": 60},
    "gps30": {"params": ["SIM_GPS1_ENABLE"], "attendu": 1.0, "injection": 0.0, "retrait": 1.0, "duree": 30},
    "biais10": {"params": IMU, "attendu": 0.0, "injection": 1.0, "retrait": 0.0, "duree": 60},
    "biais05": {"params": IMU, "attendu": 0.0, "injection": 0.5, "retrait": 0.0, "duree": 60},
    "biais": {"params": IMU, "attendu": 0.0, "injection": None, "retrait": 0.0, "duree": 60},
    "magneto": {"params": ["SIM_MAG1_OFS_X", "SIM_MAG2_OFS_X", "SIM_MAG3_OFS_X"],
                "attendu": 5.0, "injection": 155.0, "retrait": 5.0, "duree": 60},
}
CERCLE_NOMINAL = 180
CERCLE_APRES = 90
ALT_DECOLLAGE = 15.0
ALT_SECURITE = 8.0
GUIDED, RTL, CIRCLE = 4, 6, 7

arguments = argparse.ArgumentParser(description="Vol SITL automatique")
arguments.add_argument("scenario", choices=list(SCENARIOS))
arguments.add_argument("vent", nargs="*", type=float, help="vitesse (m/s) direction (deg) turbulence (m/s)")
arguments.add_argument("--injection", type=float, default=120.0, help="instant d'injection après l'entrée en CIRCLE (s)")
arguments.add_argument("--amplitude", type=float, help="biais (m/s²) ou décalage magnétomètre à injecter")
args = arguments.parse_args()
if len(args.vent) not in (0, 3):
    arguments.error("le vent demande trois valeurs : vitesse direction turbulence")
vent = args.vent or None
CERCLE_AVANT = args.injection

panne = SCENARIOS[args.scenario]
if panne is not None:
    panne = dict(panne)
    if args.amplitude is not None:
        if panne["params"] == ["SIM_GPS1_ENABLE"]:
            arguments.error("--amplitude est sans objet pour une coupure GPS")
        # biais : valeur injectée = amplitude ; magnétomètre : décalage ajouté à la valeur de départ
        panne["injection"] = panne["attendu"] + args.amplitude
    elif panne["injection"] is None:
        arguments.error(f"le scénario {args.scenario} demande --amplitude")
elif args.amplitude is not None or args.injection != 120.0:
    arguments.error("--injection et --amplitude sont sans objet pour un vol nominal")

etat = {"alt": None, "arme": False, "mode": None, "crash": False, "fix": None, "sats": None,
        "ekf_gps": set(), "ack_takeoff": None}
params = {}
t_debut = time.monotonic()
t_cercle = None
override = False
panne_active = False
dernier_envoi = 0.0


def journal(texte):
    t = time.monotonic() - t_debut
    tc = f"{time.monotonic() - t_cercle:6.1f}" if t_cercle is not None else "     -"
    alt = f"{etat['alt']:5.1f}" if etat["alt"] is not None else "    -"
    print(f"[t={t:6.1f} s | cercle={tc} s | alt={alt} m] {texte}", flush=True)


def connecter():
    fin = time.monotonic() + 180
    while time.monotonic() < fin:
        try:
            m = mavutil.mavlink_connection("tcp:127.0.0.1:5760", source_system=255)
            if m.wait_heartbeat(timeout=10):
                return m
        except OSError:
            time.sleep(2)
    sys.exit("Pas de connexion au SITL")


m = connecter()
journal(f"Connecté au SITL, scénario {args.scenario}, vent {vent}, injection à {CERCLE_AVANT:g} s"
        + ("" if panne is None else f", valeur injectée {panne['injection']:g}"))
m.mav.request_data_stream_send(1, 1, mavutil.mavlink.MAV_DATA_STREAM_ALL, 4, 1)


def traiter(msg):
    genre = msg.get_type()
    if genre == "GLOBAL_POSITION_INT":
        etat["alt"] = msg.relative_alt / 1000
    elif genre == "HEARTBEAT" and msg.get_srcSystem() == 1 and msg.get_srcComponent() == 1:
        etat["arme"] = bool(msg.base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED)
        etat["mode"] = msg.custom_mode
    elif genre == "PARAM_VALUE":
        params[msg.param_id] = msg.param_value
    elif genre == "STATUSTEXT":
        journal(f"AP: {msg.text}")
        # En RTL, « Hit ground » est le contact normal à l'atterrissage
        if "Hit ground" in msg.text and etat["mode"] != RTL:
            etat["crash"] = True
        if "is using GPS" in msg.text:
            etat["ekf_gps"].add(msg.text.split()[1])
    elif genre == "COMMAND_ACK" and msg.command == mavutil.mavlink.MAV_CMD_NAV_TAKEOFF:
        etat["ack_takeoff"] = msg.result
    elif genre == "GPS_RAW_INT":
        if (msg.fix_type, msg.satellites_visible) != (etat["fix"], etat["sats"]):
            etat["fix"], etat["sats"] = msg.fix_type, msg.satellites_visible
            journal(f"GPS : fix={msg.fix_type}, satellites={msg.satellites_visible}")


def pomper(duree, jusqua=None):
    """Lit les messages pendant `duree` s, renvoie l'override RC et applique la sécurité."""
    global dernier_envoi
    fin = time.monotonic() + duree
    while time.monotonic() < fin:
        if time.monotonic() - dernier_envoi > 0.5:
            m.mav.heartbeat_send(mavutil.mavlink.MAV_TYPE_GCS, mavutil.mavlink.MAV_AUTOPILOT_INVALID, 0, 0, 0)
            if override:
                m.mav.rc_channels_override_send(1, 1, 0, 0, 1500, 0, 0, 0, 0, 0)
            dernier_envoi = time.monotonic()
        msg = m.recv_match(blocking=True, timeout=0.2)
        if msg is not None:
            traiter(msg)
        if panne_active and etat["alt"] is not None and etat["alt"] < ALT_SECURITE:
            journal(f"SÉCURITÉ : altitude < {ALT_SECURITE} m, retrait immédiat de la panne")
            retirer()
        if etat["crash"]:
            sys.exit("Crash simulé (SIM Hit ground)")
        if jusqua is not None and jusqua():
            return True
    return False


def lire(nom):
    params.pop(nom, None)
    m.mav.param_request_read_send(1, 1, nom.encode(), -1)
    if not pomper(5, lambda: nom in params):
        sys.exit(f"Paramètre introuvable : {nom}")
    return params[nom]


def regler(valeurs):
    """Envoie tous les paramètres d'affilée, puis vérifie qu'ils sont acceptés."""
    for nom in valeurs:
        params.pop(nom, None)
    for nom, valeur in valeurs.items():
        m.mav.param_set_send(1, 1, nom.encode(), float(valeur), mavutil.mavlink.MAV_PARAM_TYPE_REAL32)
    ok = pomper(5, lambda: all(nom in params and abs(params[nom] - v) < 1e-3 for nom, v in valeurs.items()))
    if not ok:
        sys.exit(f"Réglage non confirmé : {valeurs} -> {params}")
    journal("param set " + ", ".join(f"{n} {v}" for n, v in valeurs.items()) + " (confirmé)")


def changer_mode(numero, nom):
    m.mav.set_mode_send(1, mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED, numero)
    if not pomper(5, lambda: etat["mode"] == numero):
        sys.exit(f"Mode {nom} refusé")
    journal(f"mode {nom}")


def retirer():
    global panne_active
    panne_active = False
    regler({nom: panne["retrait"] for nom in panne["params"]})
    journal("Panne retirée")


# Vérification des valeurs de départ avant tout vol
if panne is not None:
    for nom in panne["params"]:
        valeur = lire(nom)
        journal(f"Valeur de départ {nom} = {valeur}")
        if abs(valeur - panne["attendu"]) > 1e-3:
            sys.exit(f"{nom} vaut {valeur}, attendu {panne['attendu']} : arrêt sans injection")

# Fin du démarrage : un mode réglé avant est écrasé par l'initialisation (mode STABILIZE)
if not pomper(180, lambda: {"IMU0", "IMU1"} <= etat["ekf_gps"]):
    sys.exit("L'EKF n'utilise pas le GPS")
journal("Les deux cœurs EKF utilisent le GPS")

# Vent (avant le décollage, pour qu'il soit établi pendant tout le cercle)
if vent is not None:
    regler({"SIM_WIND_T": 1})
    regler({"SIM_WIND_SPD": vent[0], "SIM_WIND_DIR": vent[1], "SIM_WIND_TURB": vent[2]})

# Paramètres
regler({"FS_EKF_ACTION": 0})
regler({"CIRCLE_RADIUS_M": 30})
regler({"CIRCLE_RATE": 15})
changer_mode(GUIDED, "guided")
pomper(5)

# Armement et décollage immédiat (mode GUIDED revérifié à chaque essai)
for essai in range(3):
    if etat["mode"] != GUIDED:
        journal(f"Mode {etat['mode']} au lieu de GUIDED, on le remet")
        changer_mode(GUIDED, "guided")
    fin = time.monotonic() + 60
    while not etat["arme"]:
        if time.monotonic() > fin:
            sys.exit("Armement impossible")
        m.mav.command_long_send(1, 1, mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM, 0, 1, 0, 0, 0, 0, 0, 0)
        pomper(5, lambda: etat["arme"])
    journal("arm throttle (armé)")
    etat["ack_takeoff"] = None
    m.mav.command_long_send(1, 1, mavutil.mavlink.MAV_CMD_NAV_TAKEOFF, 0, 0, 0, 0, 0, 0, 0, ALT_DECOLLAGE)
    pomper(3, lambda: etat["ack_takeoff"] is not None)
    journal(f"takeoff {ALT_DECOLLAGE:.0f} (accusé de réception : {etat['ack_takeoff']}, 0 = accepté)")
    if etat["ack_takeoff"] == mavutil.mavlink.MAV_RESULT_ACCEPTED:
        break
    pomper(5)
else:
    sys.exit("Décollage refusé 3 fois")
if not pomper(90, lambda: etat["alt"] is not None and etat["alt"] >= ALT_DECOLLAGE - 1):
    sys.exit("Altitude de décollage non atteinte")
journal("Altitude atteinte, stabilisation 10 s")
pomper(10)

override = True
pomper(1)
journal("rc 3 1500 (renvoyé toutes les 0,5 s)")
changer_mode(CIRCLE, "circle")
t_cercle = time.monotonic()
journal("t = 0 du cercle")

# Cercle nominal, ou cercle avec panne
if panne is None:
    pomper(CERCLE_NOMINAL)
else:
    pomper(CERCLE_AVANT)
    journal(f"Injection : {panne['params']} = {panne['injection']}")
    regler({nom: panne["injection"] for nom in panne["params"]})
    panne_active = True
    pomper(panne["duree"], lambda: not panne_active)
    if panne_active:
        retirer()
    pomper(CERCLE_APRES)

# Atterrissage
changer_mode(RTL, "rtl")
if not pomper(240, lambda: not etat["arme"] or (etat["alt"] is not None and etat["alt"] < 0.3)):
    sys.exit("Pas d'atterrissage après RTL")
# Avec du vent, le drone posé peut rester armé : le régulateur demande encore de l'inclinaison
# pour tenir la position, et le détecteur d'atterrissage d'ArduPilot ne conclut jamais
# (drapeau ANGLE de LDET, vu au log 26). On désarme alors comme le ferait un pilote.
if not pomper(15, lambda: not etat["arme"]):
    journal("Toujours armé 15 s après le contact avec le sol : désarmement demandé")
    m.mav.command_long_send(1, 1, mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM, 0, 0, 0, 0, 0, 0, 0, 0)
    if not pomper(5, lambda: not etat["arme"]):
        journal("Désarmement refusé : désarmement forcé (drone au sol)")
        m.mav.command_long_send(1, 1, mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM, 0, 0, 21196, 0, 0, 0, 0, 0)
        if not pomper(5, lambda: not etat["arme"]):
            sys.exit("Désarmement impossible")
journal("DISARMED")
pomper(5)
journal("Vol terminé")
