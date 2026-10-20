"""Vol SITL automatique selon la procédure du projet, piloté en pymavlink au lieu de MAVProxy.

Usage : python vol_auto.py <scenario> [vent_vitesse vent_direction vent_turbulence]
                           [--injection T] [--amplitude A] [--detecteur] [--trainee] [--bascule T]
                           [--reponse rien|natif|natif_trainee|r3]
        (le SITL doit écouter sur tcp:127.0.0.1:5760)
Scénarios : nominal, gps60, gps30, biais10, biais05, biais, magneto, jam, et (amplitude obligatoire)
derive, gyro, bruit_gyro, bloque, leurre, leurre_rampe.
jam : brouillage GPS simulé pendant 60 s (SIM_GPS1_JAM = 1 : perte de signal, puis fix, nombre
de satellites, vitesse et position erratiques, SIM_GPS.cpp:288-347).
Vent optionnel : vitesse (m/s), direction d'où il vient (degrés vrais), turbulence (m/s).
--injection : instant d'injection en s après l'entrée en CIRCLE (120 par défaut). Le cercle
est très régulier (un tour ≈ 30,8 s) : changer l'instant change le cap à l'injection.
--amplitude : selon le scénario (vérifié dans le code SITL, commit 14c871f) :
  biais : biais d'accéléromètre X des trois IMU, m/s² (SIM_ACC*_BIAS_X) ;
  derive : valeur finale d'une rampe du même biais, atteinte à la fin des 60 s de panne
           (un pas par seconde), m/s² ;
  gyro : biais de gyroscope X des trois IMU, rad/s (SIM_GYR*_BIAS_X) ;
  bruit_gyro : bruit aléatoire de gyroscope des trois IMU, ajouté sur les trois axes avec une
               amplitude radians(valeur) × gaz (SIM_GYR*_RND, en °/s) ;
  bloque : accéléromètre de l'IMU 1 seule forcé à cette valeur sur ses trois axes, m/s²
           (SIM_ACCEL1_FAIL ; 0 désactive) ;
  magneto : décalage ajouté à la valeur de départ de SIM_MAG*_OFS_X (défaut +150) ;
  leurre : décalage vers le nord de la position GPS, en m (SIM_GPS1_GLTCH_X, en degrés de
           latitude dans le simulateur ; fix et vitesse GPS inchangés, SIM_GPS.cpp:574-583) ;
  leurre_rampe : même décalage en rampe, valeur finale atteinte à la fin des 60 s ;
  sans objet pour les coupures et le brouillage GPS.
Réglé avant le décollage avec SIM_WIND_T = 1 (vent uniforme en altitude : le drone à 15 m
subit le vent réglé ; par défaut le simulateur le réduirait de √(altitude / 60)).
--detecteur : fait tourner pendant le cercle les quatre détecteurs (detecteur_en_ligne.py), à
partir de data/detecteur_en_ligne.joblib (créé par `detecteur_en_ligne.py preparer`). Les
innovations arrivent par EKF_STATUS_REPORT, demandé à 10 Hz, tronquées au centième comme XKF4.
Chaque échantillon est écrit dans data/en_ligne_<date>.csv, chaque début et fin d'alarme dans le
journal. Aucune action sur le drone : le vol se déroule comme sans l'option.
--trainee : avant le décollage, active l'estimation du vent par la traînée (EK3_DRAG_BCOEF_X/Y
9,5, EK3_DRAG_MCOEF 0,082, valeurs du test DeadReckoningInWind d'ArduPilot pour ce simulateur)
et désactive le failsafe de navigation à l'estime (FS_DR_ENABLE 0, sinon RTL dès que l'EKF
navigue sans GPS), pour observer l'EKF sans changement de mode.
--bascule T (vol nominal) : à T s de cercle, passe l'EKF sur le jeu de sources 2 (position et
vitesse horizontales : aucune, hauteur : baromètre, cap : compas), réglé avant le décollage, par
MAV_CMD_SET_EKF_SOURCE_SET, pendant 60 s, puis revient au jeu 1 (GPS).
--reponse : réponse à la panne (partie B de la récupération) :
  rien (défaut) : FS_EKF_ACTION 0, ArduPilot ne change pas de mode ;
  natif : FS_EKF_ACTION 1, réglage par défaut d'ArduPilot (LAND sur failsafe EKF) ;
  natif_trainee : idem, plus la traînée (--trainee) et FS_DR_ENABLE 2 (RTL dès que l'EKF navigue
                  à l'estime, défaut d'ArduPilot) ;
  r3 : notre réponse (recuperation.py) : détecteur et traînée actifs, FS_EKF_ACTION 0,
       FS_DR_ENABLE 0, FS_DR_TIMEOUT 120 ; sur décision de R3, bascule sur le jeu de sources sans
       GPS (comme --bascule), retour au jeu 1, ou RTL en dernier recours (LAND si ArduPilot le
       refuse). Chaque décision est écrite dans le journal, et l'état de R3 dans la trace du
       détecteur.
Le plus simple est de passer par scripts/lancer_vol.sh, qui démarre et arrête le SITL.

Déroulé : attente que les deux cœurs EKF utilisent le GPS, FS_EKF_ACTION 0,
CIRCLE_RADIUS_M 30, CIRCLE_RATE 15, mode guided, armement, takeoff 15,
stabilisation 10 s, rc 3 1500 (renvoyé toutes les 0,5 s), mode circle.
Vol nominal : 180 s de cercle. Vol avec panne : cercle jusqu'à l'instant d'injection (120 s
par défaut), injection (tous les paramètres envoyés d'affilée), durée de la panne, retrait,
90 s de cercle.
Puis mode rtl (land si ArduPilot refuse le rtl) et attente du désarmement.
"""
import argparse
import csv
import os
import sys
import time
from pymavlink import mavutil

DEPOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FICHIER_DETECTEUR = os.path.join(DEPOT, "data", "detecteur_en_ligne.joblib")

# 1° de latitude en m : LATLON_TO_M d'ArduPilot (AP_Math/definitions.h:52, m pour 1e-7 degré)
M_PAR_DEGRE = 0.011131884502145034 * 1e7
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
    "derive": {"params": IMU, "attendu": 0.0, "injection": None, "retrait": 0.0, "duree": 60, "rampe": True},
    "gyro": {"params": ["SIM_GYR1_BIAS_X", "SIM_GYR2_BIAS_X", "SIM_GYR3_BIAS_X"],
             "attendu": 0.0, "injection": None, "retrait": 0.0, "duree": 60},
    "bruit_gyro": {"params": ["SIM_GYR1_RND", "SIM_GYR2_RND", "SIM_GYR3_RND"],
                   "attendu": 0.0, "injection": None, "retrait": 0.0, "duree": 60},
    "bloque": {"params": ["SIM_ACCEL1_FAIL"], "attendu": 0.0, "injection": None, "retrait": 0.0, "duree": 60},
    "jam": {"params": ["SIM_GPS1_JAM"], "attendu": 0.0, "injection": 1.0, "retrait": 0.0, "duree": 60},
    "leurre": {"params": ["SIM_GPS1_GLTCH_X"], "attendu": 0.0, "injection": None, "retrait": 0.0,
               "duree": 60, "echelle": 1 / M_PAR_DEGRE},
    "leurre_rampe": {"params": ["SIM_GPS1_GLTCH_X"], "attendu": 0.0, "injection": None, "retrait": 0.0,
                     "duree": 60, "echelle": 1 / M_PAR_DEGRE, "rampe": True},
}
TRAINEE = {"EK3_DRAG_BCOEF_X": 9.5, "EK3_DRAG_BCOEF_Y": 9.5, "EK3_DRAG_MCOEF": 0.082}
SOURCES_SANS_GPS = {"EK3_SRC2_POSXY": 0, "EK3_SRC2_VELXY": 0, "EK3_SRC2_POSZ": 1, "EK3_SRC2_VELZ": 0,
                    "EK3_SRC2_YAW": 1}
DUREE_BASCULE = 60
CERCLE_NOMINAL = 180
CERCLE_APRES = 90
ALT_DECOLLAGE = 15.0
ALT_SECURITE = 8.0
# R3 v3 : durée pendant laquelle Copter accepte la position estimée à l'estime (défaut 30 s, plage
# documentée 0 à 120 s). Avec 30 s, Copter perdait la position avant le dernier recours de R3 et
# refusait le RTL (vols 151, 155, 157, 159, 167, 169, 171). La navigation à l'estime commence
# environ 10 s après l'exclusion du GPS : le délai tombe donc après le recours (120 s).
DUREE_ESTIME_S = 120
GUIDED, RTL, CIRCLE, LAND = 4, 6, 7, 9

arguments = argparse.ArgumentParser(description="Vol SITL automatique")
arguments.add_argument("scenario", choices=list(SCENARIOS))
arguments.add_argument("vent", nargs="*", type=float, help="vitesse (m/s) direction (deg) turbulence (m/s)")
arguments.add_argument("--injection", type=float, default=120.0, help="instant d'injection après l'entrée en CIRCLE (s)")
arguments.add_argument("--amplitude", type=float, help="biais (m/s²) ou décalage magnétomètre à injecter")
arguments.add_argument("--detecteur", action="store_true", help="fait tourner les détecteurs pendant le cercle")
arguments.add_argument("--trainee", action="store_true", help="estimation du vent par la traînée (EK3_DRAG_*)")
arguments.add_argument("--bascule", type=float, help="instant (s de cercle) de la bascule sur le jeu de sources sans GPS")
arguments.add_argument("--reponse", choices=["rien", "natif", "natif_trainee", "r3"], default="rien",
                       help="réponse à la panne")
args = arguments.parse_args()
if args.reponse == "r3":
    args.detecteur = args.trainee = True
if len(args.vent) not in (0, 3):
    arguments.error("le vent demande trois valeurs : vitesse direction turbulence")
vent = args.vent or None
CERCLE_AVANT = args.injection

panne = SCENARIOS[args.scenario]
if panne is not None:
    panne = dict(panne)
    if args.amplitude is not None:
        if panne["params"] in (["SIM_GPS1_ENABLE"], ["SIM_GPS1_JAM"]):
            arguments.error("--amplitude est sans objet pour une coupure ou un brouillage GPS")
        # biais : valeur injectée = amplitude ; magnétomètre : décalage ajouté à la valeur de départ ;
        # leurre : mètres convertis en degrés
        panne["injection"] = panne["attendu"] + args.amplitude * panne.get("echelle", 1)
    elif panne["injection"] is None:
        arguments.error(f"le scénario {args.scenario} demande --amplitude")
elif args.amplitude is not None or args.injection != 120.0:
    arguments.error("--injection et --amplitude sont sans objet pour un vol nominal")
if args.bascule is not None and args.reponse == "r3":
    arguments.error("--bascule et --reponse r3 s'excluent")
if args.bascule is not None and (panne is not None or args.bascule + DUREE_BASCULE > CERCLE_NOMINAL):
    arguments.error(f"--bascule : vol nominal seulement, et T + {DUREE_BASCULE} s ≤ {CERCLE_NOMINAL} s")

etat = {"alt": None, "arme": False, "mode": None, "crash": False, "fix": None, "sats": None,
        "ekf_gps": set(), "ack_takeoff": None, "ack_source": None,
        "lat_gps": None, "lon_gps": None, "lat_est": None, "lon_est": None}
params = {}
t_debut = time.monotonic()
t_cercle = None
override = False
panne_active = False
en_cercle = False
dernier_envoi = 0.0
detecteur = trace = None
alarmes = {}
recup = None
action = None       # décision de R3, exécutée par pomper() après le message qui l'a produite
execution = False   # vrai pendant l'exécution d'une décision (pomper() y est appelé de nouveau)


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

if args.detecteur:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import detecteur_en_ligne as enligne
    detecteur = enligne.charger(FICHIER_DETECTEUR)
    alarmes = {nom: False for nom in enligne.NOMS}
    # 10 Hz, comme XKF4 (intervalle en µs)
    m.mav.command_long_send(1, 1, mavutil.mavlink.MAV_CMD_SET_MESSAGE_INTERVAL, 0,
                            mavutil.mavlink.MAVLINK_MSG_ID_EKF_STATUS_REPORT, 100000, 0, 0, 0, 0, 0)
    chemin_trace = os.path.join(DEPOT, "data", f"en_ligne_{time.strftime('%Y%m%d-%H%M%S')}.csv")
    fichier_trace = open(chemin_trace, "w", newline="")
    trace = csv.writer(fichier_trace)
    trace.writerow(["t_cercle_s", "SV", "SP", "SM", "gps_fix", "score_ml"] + enligne.NOMS + ["r3"])
    journal(f"Détecteur en ligne chargé ({FICHIER_DETECTEUR}), trace : {chemin_trace}")
if args.reponse == "r3":
    import recuperation
    recup = recuperation.Recuperateur()


def traiter(msg):
    global action
    genre = msg.get_type()
    if genre == "GLOBAL_POSITION_INT":
        etat["alt"] = msg.relative_alt / 1000
        etat["lat_est"], etat["lon_est"] = msg.lat / 1e7, msg.lon / 1e7
    elif genre == "HEARTBEAT" and msg.get_srcSystem() == 1 and msg.get_srcComponent() == 1:
        etat["arme"] = bool(msg.base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED)
        etat["mode"] = msg.custom_mode
    elif genre == "PARAM_VALUE":
        params[msg.param_id] = msg.param_value
    elif genre == "STATUSTEXT":
        journal(f"AP: {msg.text}")
        # En RTL ou LAND, « Hit ground » est le contact normal à l'atterrissage
        if "Hit ground" in msg.text and etat["mode"] not in (RTL, LAND):
            etat["crash"] = True
        if "is using GPS" in msg.text:
            etat["ekf_gps"].add(msg.text.split()[1])
    elif genre == "COMMAND_ACK" and msg.command == mavutil.mavlink.MAV_CMD_NAV_TAKEOFF:
        etat["ack_takeoff"] = msg.result
    elif genre == "COMMAND_ACK" and msg.command == mavutil.mavlink.MAV_CMD_SET_EKF_SOURCE_SET:
        etat["ack_source"] = msg.result
    elif genre == "EKF_STATUS_REPORT" and detecteur is not None and en_cercle:
        v = {c: enligne.quantifier(getattr(msg, champ)) for c, champ in
             (("SV", "velocity_variance"), ("SP", "pos_horiz_variance"), ("SM", "compass_variance"))}
        if recup is not None and recup.etat != "normal":
            # GPS écarté : innovations figées par l'EKF, le détecteur n'est pas alimenté (R3 v2)
            trace.writerow([f"{time.monotonic() - t_cercle:.2f}", v["SV"], v["SP"], v["SM"], etat["fix"], ""]
                           + [""] * len(enligne.NOMS) + [recup.etat])
            return
        etats = detecteur.ajouter(v["SV"], v["SP"], v["SM"], etat["fix"])
        if recup is not None:
            action = action or recup.detecteur(time.monotonic(), detecteur.n - 1, detecteur.canaux,
                                               detecteur.alarme_gps, etat["fix"])
        trace.writerow([f"{time.monotonic() - t_cercle:.2f}", v["SV"], v["SP"], v["SM"], etat["fix"],
                        f"{detecteur.score:.4f}"] + [int(etats[n]) for n in enligne.NOMS]
                       + [recup.etat if recup is not None else ""])
        for nom, actif in etats.items():
            if actif != alarmes[nom]:
                texte = "ALARME" if actif else "fin d'alarme"
                journal(f"DÉTECTEUR {nom} : {texte}")
                alarmes[nom] = actif
    elif genre == "GPS_RAW_INT":
        if (msg.fix_type, msg.satellites_visible) != (etat["fix"], etat["sats"]):
            etat["fix"], etat["sats"] = msg.fix_type, msg.satellites_visible
            journal(f"GPS : fix={msg.fix_type}, satellites={msg.satellites_visible}")
        if recup is not None and en_cercle and etat["lat_est"] is not None:
            action = action or recup.gps(time.monotonic(), msg.fix_type, msg.lat / 1e7, msg.lon / 1e7,
                                         etat["lat_est"], etat["lon_est"])


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
        if action is not None and not execution:
            executer()
        # Seulement en CIRCLE : un LAND ou un RTL décidé par ArduPilot descend normalement
        if panne_active and etat["mode"] == CIRCLE and etat["alt"] is not None and etat["alt"] < ALT_SECURITE:
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
    # tolérance relative : un leurre de quelques 1e-4 degré passerait une tolérance absolue de 1e-3
    ok = pomper(5, lambda: all(nom in params and abs(params[nom] - v) <= 1e-6 + 1e-5 * abs(v)
                               for nom, v in valeurs.items()))
    if not ok:
        sys.exit(f"Réglage non confirmé : {valeurs} -> {params}")
    journal("param set " + ", ".join(f"{n} {v}" for n, v in valeurs.items()) + " (confirmé)")


def changer_mode(numero, nom, obligatoire=True):
    m.mav.set_mode_send(1, mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED, numero)
    if not pomper(5, lambda: etat["mode"] == numero):
        if obligatoire:
            sys.exit(f"Mode {nom} refusé")
        journal(f"Mode {nom} refusé")
        return False
    journal(f"mode {nom}")
    return True


def rentrer():
    """RTL, ou LAND si ArduPilot le refuse (le RTL exige une position, LAND non)."""
    if not changer_mode(RTL, "rtl", obligatoire=False):
        changer_mode(LAND, "land")


def basculer(jeu):
    etat["ack_source"] = None
    m.mav.command_long_send(1, 1, mavutil.mavlink.MAV_CMD_SET_EKF_SOURCE_SET, 0, jeu, 0, 0, 0, 0, 0, 0)
    if not pomper(3, lambda: etat["ack_source"] is not None):
        sys.exit(f"Pas d'accusé de réception pour le jeu de sources {jeu}")
    if etat["ack_source"] != mavutil.mavlink.MAV_RESULT_ACCEPTED:
        sys.exit(f"Jeu de sources {jeu} refusé (résultat {etat['ack_source']})")
    journal(f"Jeu de sources EKF {jeu} (accepté)")


def executer():
    """Exécute la décision de R3, une seule à la fois (les commandes rappellent pomper())."""
    global action, execution
    decision, action, execution = action, None, True
    if decision == "ecarter":
        journal(f"R3 : GPS écarté ({recup.cause}) ; détecteur suspendu, "
                f"{detecteur.n - recup.indice_episode} échantillon(s) de l'épisode retirés")
        detecteur.suspendre(recup.indice_episode)
        alarmes.update({nom: False for nom in alarmes})
        basculer(2)
    elif decision == "revenir":
        journal(f"R3 : retour au GPS (écart {recup.ecart:.1f} m < tolérance {recup.tolerance:.1f} m, "
                f"sous la tolérance pendant {recuperation.DUREE_RETOUR_S:g} s)")
        basculer(1)
    elif decision == "recours":
        journal(f"R3 : GPS écarté depuis plus de {recuperation.DUREE_MAX_S:g} s, dernier recours RTL")
        rentrer()
    execution = False


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
regler({"FS_EKF_ACTION": 1 if args.reponse in ("natif", "natif_trainee") else 0})
if args.reponse == "natif_trainee":
    regler(TRAINEE)
    regler({"FS_DR_ENABLE": 2})
elif args.trainee:
    regler(TRAINEE)
    regler({"FS_DR_ENABLE": 0})
if args.reponse == "r3":
    regler({"FS_DR_TIMEOUT": DUREE_ESTIME_S})
if args.bascule is not None or args.reponse == "r3":
    regler(SOURCES_SANS_GPS)
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
en_cercle = True
journal("t = 0 du cercle")

# Cercle nominal, ou cercle avec panne
if panne is None and args.bascule is not None:
    pomper(args.bascule)
    basculer(2)
    pomper(DUREE_BASCULE)
    basculer(1)
    pomper(CERCLE_NOMINAL - args.bascule - DUREE_BASCULE)
elif panne is None:
    pomper(CERCLE_NOMINAL)
else:
    pomper(CERCLE_AVANT)
    if panne.get("rampe"):
        # Dérive : la valeur monte d'un pas par seconde jusqu'à l'amplitude, atteinte à la fin
        journal(f"Injection en rampe : {panne['params']} de 0 à {panne['injection']} en {panne['duree']} s")
        debut = time.monotonic()
        panne_active = True
        for pas in range(1, panne["duree"] + 1):
            if not panne_active:      # garde-fou d'altitude déclenché : ne pas réinjecter
                break
            regler({nom: panne["injection"] * pas / panne["duree"] for nom in panne["params"]})
            if pomper(debut + pas - time.monotonic(), lambda: not panne_active):
                break
    else:
        journal(f"Injection : {panne['params']} = {panne['injection']}")
        regler({nom: panne["injection"] for nom in panne["params"]})
        panne_active = True
        pomper(panne["duree"], lambda: not panne_active)
    if panne_active:
        retirer()
    pomper(CERCLE_APRES)

# Atterrissage
en_cercle = False
if trace is not None:
    fichier_trace.flush()
if not etat["arme"]:
    # LAND ou RTL décidé par ArduPilot pendant la mission : le drone est déjà posé
    journal(f"Drone déjà posé et désarmé (mode {etat['mode']}) : pas de RTL")
elif etat["mode"] not in (RTL, LAND):
    rentrer()
# 900 s : sous 9 m/s, après une coupure GPS, le drone peut revenir de loin à ≈ 1 m/s (log 72)
if not pomper(900, lambda: not etat["arme"] or (etat["alt"] is not None and etat["alt"] < 0.3)):
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
