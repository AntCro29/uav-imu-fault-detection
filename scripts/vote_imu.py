"""Réponse « R-IMU » à une panne d'IMU : vote entre trois IMU, bascule forcée du cœur EKF.

Utilisé par vol_auto.py --reponse rimu (conception validée par Antoine le 2026-11-02), avec
--imus 3. Les mesures arrivent par SCALED_IMU, SCALED_IMU2 et SCALED_IMU3 (IMU 0, 1, 2),
demandés à 25 Hz comme les messages IMU du log, en mG et mrad/s (GCS_Common.cpp:2375-2380).
Vote, séparément pour l'accéléromètre et le gyroscope :
  - moyenne de chaque IMU sur les FENETRE_S dernières secondes ;
  - écart entre deux IMU = norme de la différence de leurs moyennes ;
  - l'IMU i est suspecte si ses deux écarts dépassent le seuil et si l'écart entre les deux
    autres reste sous le seuil ;
  - elle est déclarée en panne si elle reste suspecte pendant PERSISTANCE_S.
La décision est mémorisée jusqu'à la fin du vol (le cœur 0 reste faux 90 s après le retrait
d'un biais de 1,0 m/s², vols pilotes 391 et 397). Le module décide seulement ; vol_auto.py
force le cœur sain (EK3_PRIMARY, puis EK3_OPTIONS bit 1 : AP_NavEKF3.cpp:965-972).
Seuils = MARGE × écart maximal mesuré sur 12 nominaux à 3 IMU (logs 403, 409, 415 à 424 ;
cercle, de 10 s au RTL ; sans et avec vibration, vent de 0 à 9 m/s), réglages figés le
2026-11-02 avant le test.
"""
import math
from collections import deque

FENETRE_S = 2.0
PERSISTANCE_S = 0.5
MARGE = 1.25                     # choix d'Antoine du 2026-11-02
MAX_NOMINAL = {"acc": 0.206,     # m/s², log 424 (9 m/s, vibration)
               "gyr": 0.0078}    # rad/s, log 424
SEUILS = {c: MARGE * v for c, v in MAX_NOMINAL.items()}
G = 9.80665                      # GRAVITY_MSS d'ArduPilot
IMUS = (0, 1, 2)
COEUR_DE_IMU = {0: 0, 1: 1}      # EK3_IMU_MASK = 3 : cœur 0 sur l'IMU 0, cœur 1 sur l'IMU 1 ; IMU 2 témoin


class Vote:
    def __init__(self):
        self.mesures = {i: deque() for i in IMUS}   # (t, (ax, ay, az), (gx, gy, gz)) par IMU
        self.ecarts = {}           # derniers écarts, par capteur puis par paire
        self.suspecte = None       # (imu, capteur) suspecte en ce moment
        self.t_suspecte = None     # depuis quand
        self.fautive = None        # (imu, capteur, instant) une fois déclarée

    def ajouter(self, imu, t, msg):
        """Un message SCALED_IMU* (t en s, horloge de l'autopilote) ; renvoie l'IMU déclarée en panne ou None."""
        acc = tuple(v * G / 1000 for v in (msg.xacc, msg.yacc, msg.zacc))
        gyr = tuple(v / 1000 for v in (msg.xgyro, msg.ygyro, msg.zgyro))
        file = self.mesures[imu]
        file.append((t, acc, gyr))
        while t - file[0][0] > FENETRE_S:
            file.popleft()
        return self.evaluer(t)

    def moyenne(self, imu, k):
        file = self.mesures[imu]
        return [sum(m[k][a] for m in file) / len(file) for a in range(3)]

    def evaluer(self, t):
        # fenêtre pleine pour les trois IMU (même règle que la calibration : moyenne sur 2 s)
        if any(not f or f[-1][0] - f[0][0] < FENETRE_S - 0.1 for f in self.mesures.values()):
            return None
        # Vote seulement quand les trois IMU ont leur mesure du même instant : SCALED_IMU, 2 et 3 partent
        # l'un après l'autre avec le même horodatage, et voter entre deux revient à comparer des fenêtres
        # décalées d'un échantillon (écart gyro jusqu'à 0,013 rad/s en manœuvre, IMU 0 seule, log 425)
        if len({f[-1][0] for f in self.mesures.values()}) != 1:
            return None
        suspecte = None
        for k, capteur in ((1, "acc"), (2, "gyr")):
            moy = {i: self.moyenne(i, k) for i in IMUS}
            d = {(a, b): math.dist(moy[a], moy[b]) for a in IMUS for b in IMUS if a < b}
            self.ecarts[capteur] = d
            s = SEUILS[capteur]
            for i in IMUS:
                j, l = (x for x in IMUS if x != i)
                if d[min(i, j), max(i, j)] > s and d[min(i, l), max(i, l)] > s and d[j, l] <= s:
                    suspecte = suspecte or (i, capteur)
        # écarts toujours mis à jour (trace), décision une seule fois
        if self.fautive is not None:
            return None
        if suspecte != self.suspecte:
            self.suspecte, self.t_suspecte = suspecte, t
        if suspecte is not None and t - self.t_suspecte >= PERSISTANCE_S:
            self.fautive = (*suspecte, t)
            return suspecte[0]
        return None
