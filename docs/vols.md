# Vols réalisés

Correction du 2026-10-28 : le simulateur n'a que deux IMU (`SIM_IMU_COUNT` = 2, valeur par
défaut). Les pannes étaient aussi réglées sur une troisième IMU (`SIM_ACC3_*`, `SIM_GYR3_*`), qui
n'existe pas : elles ont donc toujours touché les deux IMU, et c'est ce qu'indique maintenant
cette documentation.

Numérotation : les vols manuels 1 à 4 sont les logs ArduPilot 13 à 16 ; à partir du vol 5,
numéro du log = numéro du vol + 14 (vol 5 = `00000019.BIN`). Détail de chaque campagne dans
[demarche.md](demarche.md).

Quatre cent quatre-vingts vols ont été réalisés en SITL (ArduCopter, vol en cercle), numérotés de 1
à 492 : les numéros 377 à 388 correspondent à des tentatives sans décollage, dont les logs ont été
supprimés. Le numéro de vol vaut le numéro du log ArduPilot moins 14, jusqu'au vol 486 (log 500).
ArduPilot ne garde que 500 numéros de log (`LOG_MAX_FILES`, `AP_Logger.cpp:198-205`) et repart
ensuite à 1 en écrasant les anciens fichiers : les vols 487 à 492 sont les logs 1 à 6, écrits le
2026-11-03 par-dessus six logs de septembre antérieurs au projet (perdus ; aucun n'était utilisé).
Tous les logs sont archivés hors du dossier d'ArduPilot sous leur numéro de vol ; la correspondance
vol, log, journal est dans [index_vols.csv](index_vols.csv) (voir [utilisation.md](utilisation.md)).

| Vol | Pilotage | Scénario |
|-----|----------|----------|
| 1 | manuel | Nominal |
| 2 | manuel | Coupure GPS de 60 s |
| 3 | manuel | Nominal |
| 4 | manuel | Biais de 1,0 m/s² sur l'accéléromètre X des deux IMU simulées, pendant environ 60 s |
| 5 | automatique | Décalage de +150 sur `SIM_MAG1/2/3_OFS_X` (magnétomètres), pendant 60 s |
| 6 | automatique | Biais de 0,5 m/s² sur l'accéléromètre X des deux IMU simulées, pendant 60 s |
| 7 | automatique | Coupure GPS de 30 s |
| 8 | automatique | Nominal |
| 9 | automatique | Nominal |
| 10 | automatique | Coupure GPS de 60 s |
| 11 | automatique | Biais de 1,0 m/s² sur l'accéléromètre X des deux IMU simulées, pendant 60 s |
| 12, 13 | automatique | Nominal, vent 6 m/s venant de 270°, turbulence 2 (vols identiques) |
| 14, 15 | automatique | Nominal, vent 3 m/s venant de 0° puis de 90°, turbulence 1 |
| 16, 17 | automatique | Nominal, vent 6 m/s venant de 0° puis de 90°, turbulence 2 |
| 18, 19 | automatique | Nominal, vent 9 m/s venant de 0° puis de 90°, turbulence 3 |
| 20 à 23 | automatique | Sous vent 6 m/s venant de 0°, turbulence 2 : biais 0,5 m/s², biais 1,0 m/s², décalage magnétomètre, coupure GPS de 60 s |
| 24 à 31 | automatique | Mêmes quatre pannes sous vent 6 m/s venant de 90° et de 180°, injection à 128, 135 ou 143 s (deux vols par panne) |
| 32, 33 | automatique | Biais de 0,2 puis 0,3 m/s², sans vent |
| 34, 35 | automatique | Biais de 0,2 puis 0,3 m/s², vent 6 m/s venant de 0°, turbulence 2 |
| 36 à 41 | automatique | Nominal : deux vols sans vent ; 4,5 m/s venant de 45° et de 225°, turbulence 1,5 ; 7,5 m/s venant de 135° et de 315°, turbulence 2,5 |
| 42 à 46 | automatique | Sous vent 3 m/s venant de 0°, turbulence 1 : biais 0,2, 0,3 et 0,5 m/s², décalage magnétomètre, coupure GPS de 60 s |
| 47 à 50 | automatique | Biais de 0,2 puis 0,3 m/s² sous vent 6 m/s venant de 90° (injection à 135 s) et de 180° (injection à 143 s) |
| 51 à 58 | automatique | Sous vent 9 m/s venant de 0° (injection à 120 s) puis de 90° (injection à 135 s), turbulence 3 : biais 0,5 et 1,0 m/s², décalage magnétomètre, coupure GPS de 60 s |
| 59 à 64 | automatique | Vols pilotes des nouvelles pannes, sans vent, pour choisir les amplitudes : dérive 0,5 m/s², biais gyroscope 0,02 rad/s, bruit gyroscope 5, accéléromètre bloqué, bruit gyroscope 30 et 60 |
| 65 à 82 | automatique | Campagne de test, nominal : trois vols sans vent, puis trois directions de vent par vitesse (3, 4,5, 6, 7,5 et 9 m/s), directions différentes de celles déjà volées |
| 83 à 100 | automatique | Campagne de test, pannes déjà connues (trois vols chacune, vents de 0 à 9 m/s, injection à 120, 128, 135 ou 143 s) : biais 0,2, 0,3, 0,5 et 1,0 m/s², décalage magnétomètre, coupure GPS de 60 s |
| 101 à 109 | automatique | Campagne de test, dérive d'accéléromètre X des deux IMU (rampe sur 60 s jusqu'à 0,3, 0,5 et 1,0 m/s²), sans vent, 3 et 6 m/s |
| 110 à 115 | automatique | Campagne de test, biais de gyroscope X des deux IMU (0,01 et 0,02 rad/s), sans vent, 3 et 6 m/s |
| 116 à 121 | automatique | Campagne de test, bruit de gyroscope des deux IMU (`SIM_GYR*_RND` 30 et 60), sans vent, 3 et 6 m/s |
| 122 à 124 | automatique | Campagne de test, accéléromètre de l'IMU 1 seule bloqué à 0,01 m/s² sur ses trois axes, sans vent, 3 et 6 m/s |
| 125 à 128 | automatique | Détecteur en vol : nominal sous vent 6 m/s venant de 30°, turbulence 2 ; biais 0,3 m/s² sans vent ; décalage magnétomètre sous vent 6 m/s venant de 240°, turbulence 2 ; dérive 0,5 m/s² sans vent |
| 129 à 131 | automatique | Navigation sans GPS, vent 6 m/s venant de 0°, turbulence 2, vent estimé par la traînée : nominal ; coupure GPS de 60 s ; abandon volontaire du GPS par l'EKF pendant 60 s |
| 132 | automatique | Mise au point de la réponse R3 : leurre GPS de 100 m en échelon, vent 6 m/s venant de 0°, turbulence 2 |
| 133 à 149 | automatique | Récupération, même vent : brouillage GPS, leurre de 100 m en échelon, leurre en rampe jusqu'à 100 m, biais d'accéléromètre de 0,5 m/s² (vol témoin), chacun avec quatre réponses (rien, ArduPilot par défaut, ArduPilot avec traînée, R3) ; nominal avec R3 |
| 150 à 179 | automatique | Validation de R3 v2, vent 6 m/s venant de 90°, 180° ou 270°, turbulence 2 : leurres de 100 m en échelon et en rampe, leurre en rampe jusqu'à 30 m, brouillage, chacun sans réponse et avec R3 v2 ; vols témoins avec R3 v2 (biais 0,5 m/s² sous les trois vents, biais 0,3, dérive 0,5) ; trois nominaux avec R3 v2 |
| 180 à 209 | automatique | Validation de R3 v3, même plan que les vols 150 à 179 avec un vent venant de 45°, 135° ou 225° |
| 210 | automatique | Vol pilote du bruit d'IMU : coupure GPS de 60 s avec traînée, bruit de gyroscope 60 pendant tout le vol, vent 6 m/s venant de 20°, turbulence 2 |
| 211 à 228 | automatique | Bruit de gyroscope 30 (vols 211 à 219) puis 60 (220 à 228) pendant tout le vol, vent 6 m/s venant de 20°, 140° ou 260°, turbulence 2 : nominal, coupure GPS de 60 s avec traînée, biais de 0,3 m/s² |
| 229 à 231 | automatique | Références sans bruit : coupure GPS de 60 s avec traînée sous les trois mêmes vents |
| 232 | automatique | Vol pilote de la vibration des moteurs : coupure GPS de 60 s avec traînée, vibration pendant tout le vol, vent 6 m/s venant de 20°, turbulence 2 |
| 233 à 241 | automatique | Vibration des moteurs pendant tout le vol, vent 6 m/s venant de 20°, 140° ou 260°, turbulence 2 : nominal, coupure GPS de 60 s avec traînée, biais de 0,3 m/s² |
| 242 à 247 | automatique | Références sans vibration, mêmes vents : nominal, biais de 0,3 m/s² |
| 248 à 253 | automatique | R3 v3 avec vibration, mêmes vents : leurre de 100 m en échelon, brouillage |
| 254 à 258 | automatique | Vols pilotes du flux optique, vent 6 m/s venant de 20°, turbulence 2 : nominal avec flux non fusionné, sans puis avec vibration ; avec vibration et flux fusionné en permanence : nominal, coupure GPS de 60 s avec traînée, nominal (altitude corrigée) |
| 259 à 267 | automatique | R3 v3 avec vibration et flux optique, vent 6 m/s venant de 20°, 140° ou 260°, turbulence 2 : leurre de 100 m en échelon, leurre en rampe jusqu'à 100 m, brouillage |
| 268 | automatique | Vérification du désarmement : nominal avec vibration et flux optique, vent 6 m/s venant de 260°, turbulence 2 |
| 269 | automatique | Démonstration suivie en direct dans QGroundControl : leurre de 100 m en échelon avec R3, vibration et flux optique, vent 6 m/s venant de 140°, turbulence 2 |
| 270 à 272 | automatique | Vols pilotes de la campagne suivante, vibration et flux optique, sans réponse : leurre en rampe jusqu'à 30 m (9 m/s venant de 300°), accéléromètre de l'IMU 1 bloqué (6 m/s venant de 200°), nominal (9 m/s venant de 120°) |
| 273 à 328 | automatique | Campagne de l'autoencodeur, vibration et flux optique, sans réponse : 24 nominaux (sans vent à 9 m/s) et 32 pannes, quatre vols par type sous 3, 6, 6 et 9 m/s (biais d'accéléromètre 0,3 à 1,0 m/s², dérives jusqu'à 0,3 à 1,0 m/s², biais de gyroscope 0,01 et 0,02 rad/s, magnétomètre, leurres de 30 et 100 m en échelon et en rampe, brouillage, accéléromètre bloqué) ; vol 328 écrasé au décollage |
| 329 à 340 | automatique | Séparation des causes de l'invisibilité des petites pannes d'IMU, sans réponse, vent 6 m/s venant de 20° (vols 329 à 334, injection à 128 s) ou de 140° (vols 335 à 340, injection à 135 s), turbulence 2 : nominal puis biais d'accéléromètre de 0,3 m/s², avec vibration des gyroscopes seuls, des accéléromètres seuls, puis flux optique permanent sans vibration |
| 341 à 358 | automatique | Test du classifieur, sans vibration, sans réponse, vents 4 m/s (turbulence 1,5) et 7 m/s (turbulence 2,5) : biais d'accéléromètre 0,3 et 1,0 m/s², dérive jusqu'à 1,0 m/s², accéléromètre bloqué, biais de gyroscope 0,01 et 0,02 rad/s, bruit de gyroscope 60, coupure GPS 60 s, magnétomètre ; deux vols chacun |
| 359 à 376 | automatique | Test du classifieur, vibration et flux optique permanent, sans réponse, mêmes vents : biais d'accéléromètre 1,0 m/s², accéléromètre bloqué, biais de gyroscope 0,02 rad/s, magnétomètre, leurres de 100 et 30 m en échelon et en rampe, brouillage ; deux vols chacun |
| 377 à 388 | — | Pas de vol : douze tentatives à trois IMU dont l'armement a été refusé (« 3D Accel calibration needed », troisième IMU non calibrée) ; logs supprimés |
| 389 à 400 | automatique | Vols pilotes à trois IMU, panne sur l'IMU 1 seule, sans réponse, vent 6 m/s venant de 20°, turbulence 2 : nominal, biais d'accéléromètre de 0,3 et 1,0 m/s², dérive jusqu'à 1,0 m/s², biais de gyroscope de 0,01 et 0,02 rad/s, sans vibration (vols 389 à 394) puis avec vibration et flux optique permanent (vols 395 à 400) ; vol 396 écrasé au décollage, avant la panne |
| 401 à 410 | automatique | Calibration du vote R-IMU, nominaux à trois IMU : sans vent, 3 m/s venant de 100° (turbulence 1), 6 m/s de 220° (2), 7,5 m/s de 300° (2,5), 9 m/s de 160° (3), sans vibration (vols 401 à 405) puis avec vibration et flux optique permanent (vols 406 à 410) |
| 411, 412 | automatique | Validation de R-IMU : biais d'accéléromètre de 1,0 m/s² sur l'IMU 1, vent 5 m/s venant de 250°, turbulence 2, injection à 135 s ; vol 411 avec la première version du vote (fenêtres décalées d'un échantillon), vol 412 avec la version corrigée |
| 413 à 440 | automatique | Test de R-IMU, trois IMU, vents 4 m/s venant de 50° (turbulence 1,5), 7 m/s de 190° (2,5) et 8 m/s de 320° (2,5) : dix pannes sur l'IMU 1 (biais de 0,3 et 1,0 m/s², dérive jusqu'à 1,0 m/s², biais de gyroscope de 0,01 et 0,02 rad/s, sans vibration puis avec vibration et flux optique permanent), chacune volée deux fois, sans réponse puis avec R-IMU (vols 413 à 432) ; six nominaux avec R-IMU (vols 433 à 438) ; biais de 1,0 m/s² sur l'IMU 2 (vol 439) et sur l'IMU 3, témoin (vol 440), avec R-IMU |
| 441 à 444 | automatique | Vols pilotes de la boucle complète, trois IMU, vent 6 m/s venant de 20°, turbulence 2, injection à 128 s : dérive commune jusqu'à 0,5 m/s² (vol 441), leurre de 100 m en échelon (vol 442, classé accéléromètre : le classifieur n'avait jamais vu de leurre), biais de 1,0 m/s² sur l'IMU 1 (vol 443), puis leurre de 100 m refait avec le classifieur réentraîné (vol 444) |
| 445 à 492 | automatique | Test de la boucle complète, trois IMU, sans vibration, vents 6 m/s venant de 70° (injection à 128 s), 175° (135 s) et 305° (143 s), turbulence 2 : biais d'accéléromètre de 1,0 m/s² sur l'IMU 1, biais de gyroscope de 0,02 rad/s sur l'IMU 2, dérive commune jusqu'à 0,5 m/s², leurres de 100 m en échelon et en rampe, brouillage, magnétomètre, nominal ; chacun volé avec la boucle puis avec la réponse choisie à la main (R-IMU pour les trois pannes d'IMU, R3 sinon). Vols 445 à 486 = logs 459 à 500, vols 487 à 492 = logs 1 à 6 |

Les vols 8 à 11 refont les vols manuels 1 à 4 avec le pilotage automatique : les
vols 5 à 492 forment ainsi une série réalisée avec exactement le même protocole. À partir
du vol 12, les vols ajoutent du vent (`SIM_WIND_SPD`, `SIM_WIND_DIR`, `SIM_WIND_TURB`), réglé
uniforme en altitude (`SIM_WIND_T = 1`), sauf les vols indiqués sans vent. Les vols 36
à 58 ont d'abord servi de jeu de test au seuil adaptatif et au premier Isolation Forest, puis de
jeu de validation pour régler ce dernier. Les vols 65 à 124 n'ont servi à aucun réglage : ils
forment le jeu de test final.

Au vol 4, les trois biais ont été injectés l'un après l'autre, à environ 4 s
d'intervalle (une commande par IMU), puis retirés de la même façon : les deux IMU
ont été biaisées simultanément pendant environ 62 s. Dans les vols automatiques,
les paramètres des trois capteurs sont envoyés d'affilée et les durées sont exactes
(120 s de cercle, panne, 90 s de cercle).

Premières observations qualitatives, sur un seul vol par type de panne :
la coupure GPS se voit d'abord dans le statut du fix GPS, avant les innovations ;
le biais accéléromètre est une panne silencieuse (aucun effet sur le statut GPS)
qui fait réagir immédiatement les innovations de vitesse, de position et du
magnétomètre.
