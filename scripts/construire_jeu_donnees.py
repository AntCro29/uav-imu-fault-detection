"""Construit le jeu de données étiqueté : un CSV par log, une ligne par message XKF4 du cœur 0.

Usage : python scripts/construire_jeu_donnees.py <dossier_sortie> <log1.BIN> [<log2.BIN> ...]

Colonnes :
  log, t_cercle_s (t = 0 à l'entrée en CIRCLE), phase (avant_cercle, cercle, rtl),
  SV, SP, SH, SM (innovations XKF4, cœur 0), gps_fix, gps_nsats (dernière valeur connue),
  type_panne (aucune, acc, derive, gyr, bruit_gyr, bloque, gps, mag, jam, leurre, leurre_rampe),
  amplitude, etiquette
  (nominal, panne, apres_panne),
  t_depuis_injection_s, t_depuis_retrait_s.

Étiquetage tiré des messages PARM : la dernière valeur lue de chaque paramètre SIM avant l'entrée
en CIRCLE sert de référence (un réglage fait avant le décollage, comme vol_auto.py --bruit, fait
partie du vol, ce n'est pas une panne), seuls les vrais changements comptent. La panne va de la première injection au
dernier retrait ; tout ce qui suit le retrait est « apres_panne » (la durée à exclure du
décompte des fausses alarmes se choisit à l'évaluation, grâce à t_depuis_retrait_s).
type_panne et amplitude ne sont renseignés que sur les lignes panne et apres_panne (« aucune »
et vide sur les lignes nominal). Amplitude : biais en m/s² pour acc ; valeur finale de la rampe
en m/s² pour derive (biais d'accéléromètre qui change plusieurs fois) ; rad/s pour gyr ; valeur
de SIM_GYR*_RND (°/s, multipliée par les gaz) pour bruit_gyr ; valeur forcée en m/s² pour
bloque ; décalage de SIM_MAG_OFS_X pour mag (+150 : le compas voit −150 mG sur son axe X) ;
vide pour gps (coupure) et jam (brouillage, SIM_GPS1_JAM) ; décalage vers le nord en m pour leurre
(SIM_GPS1_GLTCH_X, en degrés dans le log, converti avec LATLON_TO_M comme dans vol_auto.py) et
leurre_rampe (même paramètre qui prend plusieurs valeurs : valeur finale de la rampe).
"""
import csv
import os
import sys
from pymavlink import mavutil

TYPES = {"SIM_ACC1_BIAS_X": "acc", "SIM_ACC2_BIAS_X": "acc", "SIM_ACC3_BIAS_X": "acc",
         "SIM_MAG1_OFS_X": "mag", "SIM_MAG2_OFS_X": "mag", "SIM_MAG3_OFS_X": "mag",
         "SIM_GPS1_ENABLE": "gps",
         "SIM_GYR1_BIAS_X": "gyr", "SIM_GYR2_BIAS_X": "gyr", "SIM_GYR3_BIAS_X": "gyr",
         "SIM_GYR1_RND": "bruit_gyr", "SIM_GYR2_RND": "bruit_gyr", "SIM_GYR3_RND": "bruit_gyr",
         "SIM_ACCEL1_FAIL": "bloque", "SIM_ACCEL2_FAIL": "bloque", "SIM_ACCEL3_FAIL": "bloque",
         "SIM_GPS1_JAM": "jam", "SIM_GPS1_GLTCH_X": "leurre"}
M_PAR_DEGRE = 0.011131884502145034 * 1e7   # LATLON_TO_M d'ArduPilot, comme vol_auto.py
MODE_CIRCLE, MODE_RTL = 7, 6
COLONNES = ["log", "t_cercle_s", "phase", "SV", "SP", "SH", "SM", "gps_fix", "gps_nsats",
            "type_panne", "amplitude", "etiquette", "t_depuis_injection_s", "t_depuis_retrait_s"]


def lire_log(chemin):
    mlog = mavutil.mavlink_connection(chemin)
    innovations = []
    gps = []
    changements = []
    valeurs_depart = {}
    dernieres_valeurs = {}
    t_circle = t_rtl = None
    while True:
        msg = mlog.recv_match(type=["MODE", "XKF4", "GPS", "PARM"])
        if msg is None:
            break
        t = msg.TimeUS / 1e6
        genre = msg.get_type()
        if genre == "MODE":
            if msg.Mode == MODE_CIRCLE and t_circle is None:
                t_circle = t
            elif msg.Mode == MODE_RTL and t_circle is not None and t_rtl is None:
                t_rtl = t
        elif genre == "XKF4" and msg.C == 0:
            innovations.append((t, msg.SV, msg.SP, msg.SH, msg.SM))
        elif genre == "GPS" and getattr(msg, "I", 0) == 0:
            gps.append((t, msg.Status, msg.NSats))
        elif genre == "PARM" and msg.Name in TYPES:
            if msg.Name not in dernieres_valeurs or t_circle is None:
                valeurs_depart[msg.Name] = msg.Value
            elif msg.Value != dernieres_valeurs[msg.Name]:
                saine = 1.0 if TYPES[msg.Name] == "gps" else valeurs_depart[msg.Name]
                changements.append((t, msg.Name, msg.Value, msg.Value == saine))
            dernieres_valeurs[msg.Name] = msg.Value
    return innovations, gps, changements, valeurs_depart, t_circle, t_rtl


def decrire_panne(changements, valeurs_depart):
    injections = [c for c in changements if not c[3]]
    retraits = [c for c in changements if c[3]]
    if not injections:
        return "aucune", "", None, None
    types = {TYPES[nom] for _, nom, _, _ in injections}
    if len(types) > 1:
        sys.exit(f"Plusieurs types de panne dans le même log : {types}")
    type_panne = types.pop()
    _, nom, valeur, _ = injections[0]
    # Dérive : le même paramètre prend plusieurs valeurs successives (rampe) ; l'amplitude est
    # alors la valeur la plus éloignée de la valeur saine, pas le premier pas
    valeurs_nom = [v for _, n, v, _ in injections if n == nom]
    if type_panne in ("acc", "leurre") and len(set(valeurs_nom)) > 1:
        type_panne = "derive" if type_panne == "acc" else "leurre_rampe"
        valeur = max(valeurs_nom, key=lambda v: abs(v - valeurs_depart[nom]))
    if type_panne == "mag":
        amplitude = f"{valeur - valeurs_depart[nom]:+g}"
    elif type_panne in ("gps", "jam"):
        amplitude = ""
    elif type_panne in ("leurre", "leurre_rampe"):
        amplitude = f"{(valeur - valeurs_depart[nom]) * M_PAR_DEGRE:.1f}"
    else:
        amplitude = f"{valeur:g}"
    t_injection = injections[0][0]
    t_retrait = retraits[-1][0] if retraits else None
    return type_panne, amplitude, t_injection, t_retrait


def construire(chemin, dossier_sortie):
    innovations, gps, changements, valeurs_depart, t_circle, t_rtl = lire_log(chemin)
    if t_circle is None:
        sys.exit(f"{chemin} : pas d'entrée en CIRCLE")
    type_panne, amplitude, t_inj, t_ret = decrire_panne(changements, valeurs_depart)
    numero = int(os.path.splitext(os.path.basename(chemin))[0])
    sortie = os.path.join(dossier_sortie, f"log_{numero:08d}.csv")

    compte = {}
    i_gps = 0
    gps_fix = gps_nsats = ""
    with open(sortie, "w", newline="") as f:
        ecrivain = csv.writer(f)
        ecrivain.writerow(COLONNES)
        for t, sv, sp, sh, sm in innovations:
            # Statut GPS : dernière valeur connue à l'instant t
            while i_gps < len(gps) and gps[i_gps][0] <= t:
                _, gps_fix, gps_nsats = gps[i_gps]
                i_gps += 1
            if t < t_circle:
                phase = "avant_cercle"
            elif t_rtl is None or t < t_rtl:
                phase = "cercle"
            else:
                phase = "rtl"
            if t_inj is None or t < t_inj:
                etiquette = "nominal"
            elif t_ret is None or t < t_ret:
                etiquette = "panne"
            else:
                etiquette = "apres_panne"
            depuis_inj = f"{t - t_inj:.2f}" if t_inj is not None and t >= t_inj else ""
            depuis_ret = f"{t - t_ret:.2f}" if t_ret is not None and t >= t_ret else ""
            # Le type et l'amplitude ne sont renseignés que pendant et après la panne
            type_ligne, amplitude_ligne = ("aucune", "") if etiquette == "nominal" else (type_panne, amplitude)
            ecrivain.writerow([numero, f"{t - t_circle:.2f}", phase, sv, sp, sh, sm, gps_fix, gps_nsats,
                               type_ligne, amplitude_ligne, etiquette, depuis_inj, depuis_ret])
            compte[(phase, etiquette)] = compte.get((phase, etiquette), 0) + 1

    resume = ", ".join(f"{p}/{e} {n}" for (p, e), n in sorted(compte.items()))
    panne = f"{type_panne} {amplitude}".strip()
    bornes = "" if t_inj is None else f", panne de {t_inj - t_circle:.1f} à {t_ret - t_circle:.1f} s"
    print(f"{os.path.basename(sortie)} : {panne}{bornes} ; lignes : {resume}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    dossier = sys.argv[1]
    os.makedirs(dossier, exist_ok=True)
    for chemin in sys.argv[2:]:
        construire(chemin, dossier)
