# Vols réalisés

Numérotation : les vols manuels 1 à 4 sont les logs ArduPilot 13 à 16 ; à partir du vol 5,
numéro du log = numéro du vol + 14 (vol 5 = `00000019.BIN`). Détail de chaque campagne dans
[demarche.md](demarche.md).

Trois cent quarante vols ont été réalisés en SITL (ArduCopter, vol en cercle) :

| Vol | Pilotage | Scénario |
|-----|----------|----------|
| 1 | manuel | Nominal |
| 2 | manuel | Coupure GPS de 60 s |
| 3 | manuel | Nominal |
| 4 | manuel | Biais de 1,0 m/s² sur l'accéléromètre X des trois IMU simulées, pendant environ 60 s |
| 5 | automatique | Décalage de +150 sur `SIM_MAG1/2/3_OFS_X` (magnétomètres), pendant 60 s |
| 6 | automatique | Biais de 0,5 m/s² sur l'accéléromètre X des trois IMU simulées, pendant 60 s |
| 7 | automatique | Coupure GPS de 30 s |
| 8 | automatique | Nominal |
| 9 | automatique | Nominal |
| 10 | automatique | Coupure GPS de 60 s |
| 11 | automatique | Biais de 1,0 m/s² sur l'accéléromètre X des trois IMU simulées, pendant 60 s |
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
| 101 à 109 | automatique | Campagne de test, dérive d'accéléromètre X des trois IMU (rampe sur 60 s jusqu'à 0,3, 0,5 et 1,0 m/s²), sans vent, 3 et 6 m/s |
| 110 à 115 | automatique | Campagne de test, biais de gyroscope X des trois IMU (0,01 et 0,02 rad/s), sans vent, 3 et 6 m/s |
| 116 à 121 | automatique | Campagne de test, bruit de gyroscope des trois IMU (`SIM_GYR*_RND` 30 et 60), sans vent, 3 et 6 m/s |
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

Les vols 8 à 11 refont les vols manuels 1 à 4 avec le pilotage automatique : les
vols 5 à 340 forment ainsi une série réalisée avec exactement le même protocole. À partir
du vol 12, les vols ajoutent du vent (`SIM_WIND_SPD`, `SIM_WIND_DIR`, `SIM_WIND_TURB`), réglé
uniforme en altitude (`SIM_WIND_T = 1`), sauf les vols indiqués sans vent. Les vols 36
à 58 ont d'abord servi de jeu de test au seuil adaptatif et au premier Isolation Forest, puis de
jeu de validation pour régler ce dernier. Les vols 65 à 124 n'ont servi à aucun réglage : ils
forment le jeu de test final.

Au vol 4, les trois biais ont été injectés l'un après l'autre, à environ 4 s
d'intervalle (une commande par IMU), puis retirés de la même façon : les trois IMU
ont été biaisées simultanément pendant environ 62 s. Dans les vols automatiques,
les paramètres des trois capteurs sont envoyés d'affilée et les durées sont exactes
(120 s de cercle, panne, 90 s de cercle).

Premières observations qualitatives, sur un seul vol par type de panne :
la coupure GPS se voit d'abord dans le statut du fix GPS, avant les innovations ;
le biais accéléromètre est une panne silencieuse (aucun effet sur le statut GPS)
qui fait réagir immédiatement les innovations de vitesse, de position et du
magnétomètre.
