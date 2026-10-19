"""Réponse « R3 » à une panne GPS : écarter le GPS, continuer la mission à l'estime, revenir au GPS.

Utilisé par vol_auto.py --reponse r3 (choix d'Antoine du 2026-10-18, option B). Version 2, après la
campagne des vols 132 à 149 (v1 : retour après 5 s, voir le commit 571c843). Automate :
  normal  → écarté   si la règle GPS du détecteur se déclenche (pas de fix 3D pendant 0,5 s),
                     ou si le seuil adaptatif donne l'alarme sur SP seul en premier alors que le
                     fix GPS est bon (signature supposée d'un leurre ; un biais d'accéléromètre
                     sous vent peut donner la même, d'où le vol témoin) ;
  écarté  → normal   si, pendant DUREE_RETOUR_S, le fix est 3D et la position GPS brute reste à
                     moins de ECART_RETOUR_M de la position estimée à l'estime ;
  écarté  → recours  si le GPS est écarté depuis plus de DUREE_MAX_S (RTL).
Dans l'état « écarté », l'EKF ne fusionne plus le GPS : ses innovations ne sont plus mises à jour
(ArduPilot renvoie la dernière valeur, par exemple SP figé à 26,41 après un leurre de 100 m). La
décision est donc mémorisée, et seul le critère de retour peut la lever ; vol_auto.py n'alimente
plus le détecteur pendant l'exclusion et en retire les échantillons de l'épisode d'alarme qui l'a
déclenchée (`indice_episode`), pour qu'au retour son seuil adaptatif reparte du nominal d'avant.
Après un retour, seul un épisode d'alarme qui commence après REFRACTAIRE_S peut écarter de
nouveau le GPS : un épisode commencé pendant le recalage de l'EKF ne compte pas (vol 136).
Le module décide seulement ; vol_auto.py envoie les commandes (jeu de sources, mode).
"""
import math
from detecteur_adaptatif import PERSISTANCE

ECART_RETOUR_M = 25.0      # = EK3_GLITCH_RAD par défaut, rayon de recalage de l'EKF sur le GPS
DUREE_RETOUR_S = 30.0     # v1 : 5 s, trop court pour un leurre lent (vol 144) ; 25 m / 30 s ≈ 0,8 m/s
DUREE_MAX_S = 120.0        # durée maximale sans GPS fiable (choix d'Antoine : 2 min)
REFRACTAIRE_S = 10.0       # après un retour, pas de nouvelle exclusion pendant le recalage
M_PAR_DEGRE = 0.011131884502145034 * 1e7   # LATLON_TO_M d'ArduPilot (AP_Math/definitions.h:52)
FIX_3D = 3


class Recuperateur:
    def __init__(self):
        self.etat = "normal"
        self.premiers = None     # canaux en alarme au début de l'épisode d'alarme en cours
        self.t_episode = None    # instant de début de cet épisode
        self.indice_episode = None   # numéro du premier dépassement de l'épisode (l'alarme n'est
                                     # déclarée qu'après PERSISTANCE dépassements consécutifs)
        self.t_ecart = self.t_coherent = self.t_retour = None
        self.cause = None
        self.ecart = None        # dernier écart GPS brut − position estimée (m)

    def detecteur(self, t, indice, canaux, alarme_gps, fix):
        """Un échantillon du détecteur (10 Hz, numéro `indice`) ; renvoie « ecarter » ou None."""
        actifs = {c for c, a in canaux.items() if a}
        if not actifs:
            self.premiers = None
        elif self.premiers is None:
            self.premiers, self.t_episode, self.indice_episode = actifs, t, indice - (PERSISTANCE - 1)
        if self.etat != "normal":
            return None
        if self.t_retour is not None and t - self.t_retour < REFRACTAIRE_S:
            return None
        if alarme_gps:
            self.cause = "pas de fix GPS 3D"
            if self.premiers is None:
                self.indice_episode = indice - (PERSISTANCE - 1)
        elif (self.premiers == {"SP"} and (fix or 0) >= FIX_3D
              and (self.t_retour is None or self.t_episode >= self.t_retour + REFRACTAIRE_S)):
            self.cause = "alarme sur SP en premier, fix GPS bon"
        else:
            return None
        self.etat, self.t_ecart, self.t_coherent = "ecarte", t, None
        return "ecarter"

    def gps(self, t, fix, lat, lon, lat_est, lon_est):
        """Une position GPS brute et la position estimée (degrés) ; renvoie « revenir », « recours » ou None."""
        if self.etat != "ecarte":
            return None
        if t - self.t_ecart > DUREE_MAX_S:
            self.etat = "recours"
            return "recours"
        dn = (lat - lat_est) * M_PAR_DEGRE
        de = (lon - lon_est) * M_PAR_DEGRE * math.cos(math.radians(lat_est))
        self.ecart = math.hypot(dn, de)
        if (fix or 0) >= FIX_3D and self.ecart < ECART_RETOUR_M:
            if self.t_coherent is None:
                self.t_coherent = t
            if t - self.t_coherent >= DUREE_RETOUR_S:
                self.etat, self.t_retour, self.premiers, self.t_episode = "normal", t, None, None
                return "revenir"
        else:
            self.t_coherent = None
        return None
