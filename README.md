# Détection de défauts IMU — ArduPilot SITL

Projet personnel : détecter des pannes capteurs sur un drone simulé à partir des
innovations de l'EKF3 d'ArduPilot, d'abord avec un seuil statistique, puis avec un
modèle de machine learning entraîné sur des vols nominaux.

## État actuel

Projet en cours : collecte de vols, analyse des innovations, détecteurs à seuil (seuil fixe,
puis seuil qui s'adapte au niveau des innovations) et premier détecteur par machine learning
(Isolation Forest entraîné sur des vols nominaux), comparés puis combinés sur une campagne de
test de 60 vols neufs, dont quatre types de panne jamais vus pendant les réglages. Les quatre
détecteurs tournent aussi en vol, sur le flux MAVLink, avec les mêmes alarmes que l'analyse des
logs. Récupération : une première réponse aux pannes GPS (écarter le GPS, continuer la mission de
surveillance à l'estime, revenir au GPS) bat les réactions par défaut d'ArduPilot sur le brouillage
et sur un leurre en échelon, mais pas encore sur un leurre lent. La classification du type de panne
n'est pas encore abordée.

Cent quarante-neuf vols ont été réalisés en SITL (ArduCopter, vol en cercle) :

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

Les vols 8 à 11 refont les vols manuels 1 à 4 avec le pilotage automatique : les
vols 5 à 149 forment ainsi une série réalisée avec exactement le même protocole. À partir
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

### Premier détecteur à seuil (vols 5 à 11)

Alarme si une innovation (SV, SP ou SM, cœur 0) dépasse un seuil calibré sur les phases
nominales, ou si le GPS perd son fix 3D, pendant 0,5 s consécutives. Seuil = 2 × maximum
nominal du canal, calibré en validation croisée (le vol évalué est exclu de la calibration).

| Panne | Délai de détection | Délai de l'EKF (innovation ≥ 1) |
|---|---|---|
| Biais accéléromètre 0,5 et 1,0 m/s² | 0,7 s (SV) | jamais atteint |
| Décalage magnétomètre | 0,5 s (SM) | 48,7 s |
| Coupure GPS 30 et 60 s | 0,7 s (perte du fix) ; 17,3 s avec les innovations seules | jamais atteint |

Aucune fausse alarme sur 890 s de vol nominal. **Ces résultats sont optimistes** : la
simulation est sans vent ni perturbations, le nominal plafonne à 0,01 et le problème est
donc trop facile. Point ouvert : après le retrait d'une panne magnétomètre ou d'un biais de
1,0 m/s², l'alarme reste active pendant toute la phase d'observation (90 s), car l'état
estimé par l'EKF reste faux alors que le capteur est redevenu sain. Dans l'évaluation,
cette alarme est comptée comme un « état dégradé » (navigation en récupération), mesuré
à part, et non comme une fausse alarme.

### Effet du vent (vols 12 à 19)

Le vent dégrade la tenue du cercle et fait monter les innovations nominales : le
maximum de SV passe de 0,01 sans vent à 0,03-0,04 (3 m/s), 0,07-0,08 (6 m/s) et
0,11-0,12 (9 m/s). À 9 m/s, plus rapide que le drone sur son cercle (≈ 6 m/s), la
trajectoire n'est plus un cercle.

![Trajectoires sous vent](docs/figures/trajectoires_vent.png)

**Détecteur réglé sans vent, évalué sur les vols venteux** (fausses alarmes par vol) :

| Seuil | 3 m/s | 6 m/s | 9 m/s |
|---|---|---|---|
| 2 × max nominal (0,02) | 0 | 10 à 16 | 58 et 70 |
| 3 × max nominal (0,03) | 0 | 0 à 4 | 20 et 30 |
| 5 × max nominal (0,05), persistance 0,5 s | 0 | 0 | 0 et 1 |

**Détecteur calibré en incluant le vent** (validation croisée sur les vols 5 à 19) : aucune
fausse alarme sur 2 250 s, mais le seuil de SV monte de 0,02 à 0,24 ; le biais de
0,5 m/s² n'est plus détecté qu'en 2,1 s (par SP) au lieu de 0,7 s, et plus du tout avec
un seuil de 5 × max nominal. C'est le compromis entre sensibilité et fausses alarmes.

**Pannes sous vent (vols 20 à 31, 6 m/s)** : trois vols par panne, avec trois directions de
vent (0°, 90°, 180°) et trois instants d'injection, donc trois caps différents au début de
la panne. Même détecteur calibré en validation croisée sur les vols 5 à 31 (seuil 2 × max
nominal, persistance 0,5 s) : les 17 pannes de la série sont détectées, aucune fausse
alarme sur 3 693 s de nominal.

| Panne | Sans vent | Sous vent de 6 m/s (3 vols) | Délai de l'EKF (≥ 1) sous vent |
|---|---|---|---|
| Biais 0,5 m/s² | 2,1 s (SP) | 2,2 s en moyenne (2,1 à 2,3 s, SP) | jamais |
| Biais 1,0 m/s² | 1,5 s (SV + SP) | 1,5 s (×3) | jamais |
| Magnétomètre | 0,5 s (SM) | 0,5 s (×3) | 29,8 s, 29,1 s, jamais (selon le cap) |
| Coupure GPS 60 s | 0,7 s (perte du fix) | 0,7 s (×3) | jamais |

Les délais sont quasi identiques d'un vol à l'autre, quels que soient la direction du vent et
le cap d'injection. Les délais de 0,5 et 0,7 s correspondent au plancher imposé par la
persistance de 0,5 s. Avec un seuil de 5 × max nominal, 3 pannes sur 17 sont manquées. Ce qui
varie le plus est la durée de l'état dégradé après le retrait (biais 1,0 : 37 à 53 s ;
magnétomètre : 82 à 90 s). Limites : trois vols par panne, un seul niveau de vent, direction
du vent et cap d'injection modifiés ensemble.

### Limite de détection (vols 32 à 35)

Biais de 0,2 et 0,3 m/s², sans vent et sous vent de 6 m/s, avec le même détecteur
(validation croisée sur les vols 5 à 35, seuils SV / SP / SM = 0,24 / 0,04 / 0,08) : le biais
de 0,2 m/s² n'est détecté ni sans vent ni sous vent ; le biais de 0,3 m/s² l'est en 3,1 s
sans vent et 3,7 s sous vent (par SP). La limite de détection de ce détecteur se situe entre
0,2 et 0,3 m/s². Sans vent, le maximum de SV pendant la panne suit à peu près le biais
(0,08 / 0,12 / 0,21 / 0,42 pour 0,2 / 0,3 / 0,5 / 1,0 m/s², soit SV ≈ 0,42 × biais). Un
détecteur calibré uniquement sur les vols sans vent (seuils 0,02) détecte le biais de 0,2 m/s²
en 1,1 s, mais il est inutilisable dès qu'il y a du vent (voir le tableau plus haut). Un vol
par amplitude.

### Seuil adaptatif, testé sur des vols jamais vus (vols 36 à 58)

Plutôt qu'un seuil unique, réglé pour le pire vent rencontré, le seuil de chaque canal suit le
niveau récent des innovations : seuil = max(0,02 ; moyenne + k × écart-type) sur les 30 s qui
précèdent (fenêtre décalée de 2 s), figé pendant une alarme pour que la panne ne relève pas son
propre seuil. Persistance 0,5 s et règle GPS identiques au seuil fixe. Le réglage (k, fenêtre,
plancher) a été choisi sur les vols 5 à 35, puis figé avant les vols 36 à 58, qui servent de
test : 3 026 s de nominal et 17 pannes, sous des vents de 0 à 9 m/s, dont des vitesses et des
directions jamais vues. Le seuil fixe est calibré sur les vols 5 à 35.

| Panne (vols de test) | Seuil fixe | Seuil adaptatif, k = 6 |
|---|---|---|
| Biais 0,2 m/s², 3 m/s | manqué | 1,5 s (SV) |
| Biais 0,2 m/s², 6 m/s (×2) | 22,7 et 23,7 s (SP) | 4,6 s (SM, ×2) |
| Biais 0,3 m/s², 3 m/s | 2,9 s (SP) | 1,1 s (SV) |
| Biais 0,3 m/s², 6 m/s (×2) | 3,5 et 3,7 s (SP) | 1,5 et 1,9 s (SV) |
| Biais 0,5 m/s², 3 et 9 m/s (×3) | 2,1 à 2,9 s (SP) | 0,9 à 1,9 s (SV) |
| Biais 1,0 m/s², 9 m/s (×2) | 1,7 s (SV) | 1,1 et 1,3 s (SV) |
| Magnétomètre, 3 et 9 m/s (×3) | 0,5 s (SM) | 0,5 s (SM) |
| Coupure GPS 60 s, 3 et 9 m/s (×3) | 0,7 s (perte du fix) | 0,7 s (perte du fix) |
| **Fausses alarmes (3 026 s de nominal)** | **0** | **0** |

Avec k = 4, les 17 pannes sont aussi détectées, un peu plus vite, mais avec 2 fausses alarmes
(vol 40, 7,5 m/s) : SM passe à 0,03 alors que le seuil est au plancher de 0,02, les
innovations étant arrondies au centième. Sur les vols de réglage, k = 4 semblait pourtant le
meilleur choix (k = 6 y manquait le biais de 0,2 m/s² sous vent) : le test sur des vols
nouveaux a inversé le classement. Le seuil calibré sans vent (0,02) fait 501 fausses alarmes
sur ces mêmes vols.

Limites : un seul vol par configuration ; pour les petits biais sous vent, l'alarme ne reste
pas active pendant toute la panne (20 à 36 % de la durée de panne pour les vols 47 à 49) :
une fois l'alarme retombée, la fenêtre contient des valeurs de panne et le seuil remonte. Un
seuil adaptatif peut ainsi « absorber » une panne lente.

**Vent fort (9 m/s)** : les innovations pendant un biais sont plus fortes que sans vent
(maximum de SV 0,33-0,35 pour 0,5 m/s², 0,58-0,61 pour 1,0 m/s², contre 0,21 et 0,42), la
relation SV ≈ 0,42 × biais ne vaut donc que sans vent. Au vol 58 (coupure GPS sous 9 m/s
venant de 90°), le drone a dérivé sous le vent jusqu'à environ 900 m du point de départ
pendant la coupure, sans que l'EKF le voie (sans GPS, il suppose une vitesse nulle et
n'estime pas le vent dans cette configuration) ; au retour du GPS, il remonte le vent en
butée d'inclinaison (30°, `ATC_ANGLE_MAX`) à environ 1 m/s et n'était pas revenu à la fin du
vol. La panne et les 90 s qui suivent sont complètes dans le log. Au vol 54 (même panne, vent
de 0°), la dérive mesurée n'a pas dépassé 116 m : différence non expliquée.

### Détecteur ML : Isolation Forest (mêmes vols de test)

Un Isolation Forest (scikit-learn) est entraîné **uniquement sur du vol nominal** (vols 5 à 35,
3 454 s) : il n'a jamais vu de panne. Ses arbres découpent les données au hasard ; un point
anormal est isolé en peu de coupes. Pour chaque canal (SV, SP, SM), il reçoit 4 variables
calculées sur le passé seulement : valeur instantanée, moyenne et maximum sur 3 s, et
écart-type sur 30 s décalé de 2 s, qui mesure l'agitation du moment (indicateur indirect du
vent, que l'EKF n'estime pas ici). Alarme si le score d'anomalie dépasse le plus haut score
vu sur le nominal d'entraînement pendant 0,5 s, ou si le GPS perd son fix 3D. Réglages fixés
avant le test.

| Panne (vols de test) | Seuil fixe | Seuil adaptatif, k = 6 | Isolation Forest |
|---|---|---|---|
| Biais 0,2 m/s², 3 m/s | manqué | 1,5 s | 2,8 s |
| Biais 0,2 m/s², 6 m/s (×2) | 22,7 et 23,7 s | 4,6 s (×2) | 3,5 et 3,0 s |
| Biais 0,3 m/s² (×3) | 2,9 à 3,7 s | 1,1 à 1,9 s | 2,0 à 2,8 s |
| Biais 0,5 m/s² (×3) | 2,1 à 2,9 s | 0,9 à 1,9 s | 1,5 à 2,0 s |
| Biais 1,0 m/s² (×2) | 1,7 s | 1,1 et 1,3 s | 1,5 et 1,6 s |
| Magnétomètre (×3) | 0,5 s | 0,5 s | 1,7 à 2,7 s |
| Coupure GPS 60 s (×3) | 0,7 s | 0,7 s | 0,7 s |
| Part de la panne en alarme, biais 0,2-0,3 sous 6 m/s (vols 47 à 49) | 2 à 17 % | 20 à 36 % | 64 à 82 % |
| **Fausses alarmes (3 026 s de nominal)** | **0** | **0** | **0** |

Le modèle détecte les 17 pannes. Il est un peu plus lent que le seuil adaptatif sur la
plupart d'entre elles, mais plus rapide sur le cas le plus difficile (biais de 0,2 m/s² sous
vent), et surtout il garde l'alarme active pendant la panne au lieu de l'« absorber ». Son
état dégradé après retrait dure plus longtemps (souvent encore actif 90 s après le retrait
pour le biais de 1,0 m/s² et le magnétomètre).

**Lenteur sur la panne magnétomètre (vérifiée au vol 45)** : le score saute dès le premier
échantillon de panne puis plafonne, que SM vaille 0,39 ou 0,98. Un Isolation Forest mesure
combien de variables sortent du domaine vu à l'entraînement, pas de combien elles en sortent :
il n'extrapole pas. L'alarme n'est franchie qu'une fois la moyenne sur 3 s sortie à son tour
du domaine connu.

**Robustesse au tirage aléatoire** (graines 0 à 4, mêmes réglages) : 17 / 17 pannes détectées
pour les cinq graines, délais stables à ± 0,5 s près ; 0 fausse alarme pour quatre graines,
3 pour la cinquième (vols 40 et 51, score à peine au-dessus du seuil, aux mêmes instants que
les fausses alarmes du seuil adaptatif avec k = 4). Le tableau ci-dessus utilise la graine 0,
un tirage plutôt favorable. Avec un seuil égal au maximum vu à l'entraînement, la marge est
mince ; il n'a pas été retouché après avoir vu les vols de test. Un seul vol par configuration
de test.

### Test final : 60 vols neufs, dont quatre nouveaux types de panne (vols 65 à 124)

**Réglages faits sur le jeu de validation (vols 36 à 58), avant la campagne** : le seuil de
l'Isolation Forest devient le plus haut score nominal d'entraînement + 0,02 (sur cinq graines, une
marge de 0,01 suffit à supprimer les fausses alarmes, 0,02 en garde une de plus) ; 200 arbres
(500 n'apportent rien) ; et une combinaison, alarme si l'Isolation Forest **ou** le seuil
adaptatif se déclenche, qui ramène le délai moyen d'environ 2,3 s à environ 1,4 s sans ajouter
de fausse alarme. Les quatre détecteurs ont ensuite été figés, puis évalués **une seule fois**
sur la campagne de test. Entraînement et calibration : vols 5 à 35, comme avant. La campagne
comprend 18 vols nominaux, 18 vols avec les pannes déjà connues et 24 vols avec quatre pannes
nouvelles : dérive lente d'accéléromètre (biais qui croît linéairement de 0 à sa valeur finale
pendant les 60 s de panne), biais de gyroscope, bruit de gyroscope et accéléromètre bloqué sur
une seule IMU.

| Panne (vols de test) | Seuil fixe | Seuil adaptatif, k = 6 | Isolation Forest | ML + adaptatif |
|---|---|---|---|---|
| Biais 0,2 m/s² (×3) | manqué (×3) | 1,3 à 2,6 s | 3,2 à 4,3 s | 1,3 à 2,6 s |
| Biais 0,3, 0,5 et 1,0 m/s² (×9) | 1,5 à 3,3 s | 0,7 à 1,7 s | 1,5 à 2,8 s | 0,7 à 1,5 s |
| Magnétomètre (×3) | 0,5 s | 0,5 s | 2,3 à 2,7 s | 0,5 s |
| Coupure GPS 60 s (×3) | 0,7 s | 0,7 s | 0,7 s | 0,7 s |
| Dérive 0,3 m/s² (×3) | 1 / 3 (53,7 s) | manqué (×3) | 21,9 à 30,1 s | 21,9 à 30,1 s |
| Dérive 0,5 m/s² (×3) | 28,3 à 54,0 s | manqué (×3) | 16,5 à 23,9 s | 16,5 à 23,9 s |
| Dérive 1,0 m/s² (×3) | 19,1 à 19,4 s | 1 / 3 (13,4 s) | 10,3 à 12,9 s | 10,3 à 12,9 s |
| Biais gyroscope 0,01 et 0,02 rad/s (×6) | 1,7 à 4,3 s | 0,8 à 1,5 s | 1,9 à 3,1 s | 0,8 à 1,5 s |
| Bruit gyroscope 30 (×3) | manqué (×3) | manqué (×3) | 2 / 3 (4,5 et 12,3 s) | 2 / 3 |
| Bruit gyroscope 60 (×3) | 1 / 3 (12,9 s) | 2,3 à 9,1 s | 3,7 à 8,7 s | 2,3 à 8,7 s |
| Accéléromètre bloqué, IMU 1 (×3) | 0,5 à 0,7 s | 0,5 à 0,7 s | 1,4 à 9,5 s | 0,5 à 0,7 s |
| **Pannes détectées** | **32 / 42** | **31 / 42** | **41 / 42** | **41 / 42** |
| **Fausses alarmes (8 217 s de nominal)** | **0** | **0** | **0** | **0** |

**La dérive lente piège le seuil adaptatif**, comme on pouvait le craindre : sa fenêtre de 30 s
suit la montée de la panne et le seuil reste toujours au-dessus de l'innovation (8 dérives
manquées sur 9). L'Isolation Forest, dont la référence est le nominal d'entraînement, fixe, les
détecte toutes. Les délais sur les dérives sont longs par nature : au moment de la détection, le
biais n'a atteint qu'une fraction de sa valeur finale.

![Vol 104 : ce que voient les quatre détecteurs pendant une dérive](docs/figures/test_derive_vol104.png)

**La combinaison prend le meilleur des deux** sur chaque vol : la réactivité du seuil adaptatif
sur les pannes franches (magnétomètre en 0,5 s au lieu de 2,3-2,7 s, accéléromètre bloqué en
0,5-0,7 s au lieu de 1,4-9,5 s, la saturation du score de l'Isolation Forest le ralentissant) et
la sensibilité de l'Isolation Forest aux pannes lentes, sans aucune fausse alarme ajoutée. Le
seuil fixe, calibré pour le vent le plus fort, ne voit plus le biais de 0,2 m/s². La seule panne
manquée par les quatre détecteurs est le bruit de gyroscope le plus faible, sans vent (vol 116) :
les innovations restent sous 0,03, l'EKF filtre presque tout ce bruit.

Observations sur le déroulé : l'accéléromètre bloqué fait basculer ArduPilot sur son second cœur
EKF 0,3 s après l'injection (les détecteurs lisent le cœur 0, qui voit une panne très franche) ;
pendant les coupures GPS, le drone dérive de 390 à 540 m sous le vent avant de revenir ; au vol 94
(biais de 1,0 m/s² sous 9 m/s), l'altitude descend à 13,8 m juste après le retrait de la panne.

Limites : trois vols par configuration ; 0 fausse alarme sur 60 vols signifie seulement, d'après
la règle de trois, que le taux réel est probablement inférieur à environ 5 % des vols ;
simulation sans vibrations des moteurs ; une seule graine pour l'Isolation Forest.

### Détecteur en vol (vols 125 à 128)

Jusqu'ici, les alarmes étaient calculées après le vol, sur le log complet. Pour pouvoir un jour
déclencher une récupération, le détecteur doit décider pendant le vol, à chaque nouvelle mesure,
sans connaître la suite. Les quatre détecteurs ont donc été réécrits pour traiter un échantillon
à la fois (`scripts/detecteur_en_ligne.py`), avec les réglages figés du test final, et branchés
sur le vol automatique (`vol_auto.py --detecteur`). En vol, les innovations arrivent par le
message MAVLink `EKF_STATUS_REPORT`, demandé à 10 Hz : d'après le code d'ArduPilot, ce sont les
mêmes grandeurs que XKF4, mais celles du cœur EKF principal et sans l'arrondi au centième du log,
que le détecteur reproduit. Le détecteur ne fait que signaler : il n'agit pas sur le drone.

Deux vérifications :

- **Sans voler** : les 60 vols de test, rejoués un échantillon à la fois dans le détecteur en
  vol, donnent exactement les mêmes alarmes que l'analyse après coup, à chaque instant (0 écart).
  Les résultats du test final n'utilisaient donc aucune mesure future. Calcul : environ 6 ms par
  échantillon, pour 100 ms disponibles.
- **En vol** (vols 125 à 128, `scripts/comparer_en_ligne.py`) : la trace écrite pendant le vol
  est comparée à l'analyse du log du même vol. Un message toutes les 100 ms (99,9 % des
  intervalles entre 80 et 120 ms, plus long trou 120 ms) ; horloges décalées d'au plus 0,05 s ;
  valeurs identiques à celles du log à 100 % sur trois vols, et à 95,4 % sur le vol 126, où les
  écarts sont presque tous un décalage d'un échantillon (8 échantillons sur 2 700 restent
  inexpliqués).

| Vol | Panne | Seuil fixe | Seuil adaptatif | Isolation Forest | ML + adaptatif |
|---|---|---|---|---|---|
| 125 | aucune (vent 6 m/s) | — | — | — | — |
| 126 | biais 0,3 m/s² | 3,0 s (2,9 s après coup) | 1,1 s | 2,4 s | 1,1 s |
| 127 | magnétomètre | 0,5 s | 0,5 s | 2,5 s | 0,5 s |
| 128 | dérive 0,5 m/s² | 55,3 s | après le retrait | 19,8 s | 19,8 s |

Délais en vol, identiques à l'analyse après coup sauf mention, et aucune fausse alarme. Critère
fixé avant les vols (mêmes pannes détectées, délais à ± 0,3 s, aucune fausse alarme) : respecté
sur les quatre vols. Limites : un vol par panne ; le détecteur tourne sur l'ordinateur qui pilote
la simulation, comme sur une station sol, et la simulation tourne sur la même machine (ni vraie
radio, ni pertes de messages).

### Récupération, partie A : naviguer sans GPS (vols 129 à 131)

Atterrir dès qu'une panne est détectée, c'est ce que fait déjà ArduPilot par défaut, et c'est
abandonner la mission, ce qui n'a pas de sens dans un environnement où le GPS est brouillé. La
récupération visée est donc un **mode dégradé** : écarter le capteur fautif et continuer la
mission (ici, le cercle de surveillance), l'atterrissage restant le dernier recours. Cette
première partie vérifie les moyens que donne ArduPilot pour naviguer sans GPS, lus dans son code
(commit `14c871f`) puis testés en vol :

- **Pourquoi le drone dérive sans GPS** : l'EKF n'estime pas le vent sur un multicoptère tant
  que le modèle de traînée est désactivé (par défaut). Sans GPS, il suppose une vitesse nulle, et
  au bout de 15 s il cesse de naviguer (« stopped aiding ») : le drone dérive sans le savoir.
- **Le levier** : les coefficients de traînée (`EK3_DRAG_BCOEF_X/Y` 9,5, `EK3_DRAG_MCOEF` 0,082,
  valeurs du test `DeadReckoningInWind` d'ArduPilot pour ce simulateur) font estimer le vent
  tant que le GPS est là, et la traînée compte alors comme une mesure : sans GPS, l'EKF ne
  passe pas en « stopped aiding » et continue de naviguer à l'estime.
- **Ce que la traînée ne fait pas** (vérifié après coup dans le code) : pendant la navigation à
  l'estime, l'EKF tient son estimation du vent pour exacte (variance mise à zéro,
  `AP_NavEKF3_core.cpp:1112-1117`), et la fusion de la traînée ne corrige que les états de vent
  (`AP_NavEKF3_AirDataFusion.cpp:505-508`). Elle ne corrige donc plus ni la vitesse ni la
  position : la navigation à l'estime est une intégration inertielle pure (au vol 130, le vent
  estimé reste figé au centième près pendant toute la coupure).
- **Ignorer le GPS volontairement** : ArduPilot a trois jeux de sources de navigation, et la
  commande MAVLink `MAV_CMD_SET_EKF_SOURCE_SET` fait passer de l'un à l'autre en vol. Un jeu
  sans GPS permettrait d'écarter un GPS leurré, qui se dit sain.

Erreur de navigation réelle (position du simulateur contre position estimée par l'EKF, cœur 0,
`scripts/erreur_navigation.py`), sous un vent de 6 m/s venant du nord :

| Vol | Situation | Vent estimé | Erreur de navigation max | Temps dans la zone surveillée (< 60 m du centre) |
|---|---|---|---|---|
| 16 | nominal, sans traînée | non estimé | 0,3 m | 100 % |
| 129 | nominal, avec traînée | 5,84 m/s venant de 359° | 0,3 m | 100 % |
| 23 | coupure GPS de 60 s, sans traînée | non estimé | **232 m** | **40 %** de la coupure (jusqu'à 266 m du centre) |
| 130 | coupure GPS de 60 s, avec traînée | 5,85 m/s venant de 359° | **7,6 m** | **100 %** |
| 131 | GPS écarté par l'EKF pendant 60 s, avec traînée | 5,86 m/s venant de 359° | 17 m | 100 % |

![Vol 23 : coupure GPS sans estimation du vent](docs/figures/coupure_gps_sans_trainee_vol23.png)
![Vol 130 : même coupure, vent estimé par la traînée](docs/figures/coupure_gps_avec_trainee_vol130.png)

Avec la traînée, le drone reste sur son cercle pendant toute la coupure. Ce résultat est à lire
avec prudence : la traînée évite le passage en « stopped aiding », mais la précision pendant la
coupure vient de l'IMU simulée, sans bruit ni vibration dans nos vols. Sur un vrai drone,
l'intégration inertielle pure dériverait beaucoup plus vite (non mesuré ici). Elle varie aussi
d'un vol à l'autre : sur la campagne suivante (R3 v2, pas encore décrite ici), sous un vent venant
de l'est, l'erreur a atteint 50 m après 60 s sans GPS. Le détecteur ne fait
aucune fausse alarme sur le vol nominal avec traînée (innovations maximales identiques à celles
du vol 16). Limites : un vol par cas, un seul vent, constant pendant la coupure (le test
d'ArduPilot signale qu'un vent qui change pendant la navigation à l'estime est le cas
difficile) ; au vol 131, ArduPilot change de cœur EKF principal au bout de 41 s sans GPS, alors
que l'erreur est mesurée sur le cœur 0. Une fois le GPS écarté, ses innovations ne sont plus mises
à jour : le détecteur ne peut plus dire quand le GPS redevient fiable, il faudra un autre critère.

### Récupération, partie B : brouillage et leurrage GPS (vols 132 à 149)

**La réponse proposée, R3** (`scripts/recuperation.py`, `vol_auto.py --reponse r3`), traînée activée :

- **écarter le GPS** (bascule sur le jeu de sources sans GPS) si le fix 3D est perdu pendant
  0,5 s, ou si le seuil adaptatif donne l'alarme d'abord sur l'innovation de position (SP) seule
  alors que le fix est bon. Les innovations disent qu'il y a un désaccord, pas qui a tort : un
  biais d'accéléromètre peut aussi faire monter SP, d'où un vol témoin. Seul le seuil adaptatif
  sert à cette décision, car l'Isolation Forest ne dit pas quel canal est en cause ;
- une fois le GPS écarté, ses innovations ne sont plus mises à jour (ArduPilot renvoie la dernière
  valeur calculée), le détecteur ne peut donc plus juger le GPS : la décision est mémorisée. **Retour au GPS** quand sa position reste à moins de 25 m de la position estimée à
  l'estime pendant 5 s (25 m : rayon au-delà duquel l'EKF se recale lui-même sur le GPS) ;
  pas de nouvelle exclusion pendant 10 s après un retour ; **RTL en dernier recours** après
  2 minutes sans GPS fiable.

**Comparée à** : R0 rien (`FS_EKF_ACTION 0`) ; R1 ArduPilot par défaut (atterrissage sur
failsafe EKF) ; R2 ArduPilot par défaut avec la traînée (et donc son retour au point de départ dès
qu'il navigue à l'estime). Pannes simulées : brouillage (`SIM_GPS1_JAM` : perte du signal puis
fix, satellites, position et vitesse erratiques), leurre de 100 m vers le nord en échelon ou en
rampe sur 60 s (`SIM_GPS1_GLTCH_X`, fix et vitesse GPS corrects). Un vol par case, vent 6 m/s
venant du nord, panne de 120 à 180 s ; mesures de `scripts/erreur_navigation.py` pendant la
panne (zone surveillée : 60 m autour du centre du cercle).

| Panne | R0 rien | R1 ArduPilot | R2 ArduPilot + traînée | R3 |
|---|---|---|---|---|
| Brouillage (vols 133 à 136) | erreur 2 657 m, 51 % dans la zone | atterrissage à 124,9 s, posé à ≈ 180 m | atterrissage à 124,9 s | **erreur 14 m, 100 %, mission poursuivie** |
| Leurre en échelon (137 à 140) | 100 m, 34 % | 100 m, 33 %, aucun failsafe | retour au départ à 130 s, vers une position faussée | **5,3 m, 100 %** |
| Leurre en rampe (141 à 144) | 98,5 m, 57 % | identique | identique, retour au départ à 190 s | **98,5 m, 57 % : échec** |
| Témoin : biais d'accéléromètre 0,5 m/s² (145 à 148) | 0,5 m, 100 % | identique | identique | identique, **GPS non écarté** |
| Nominal (149) | | | | aucune action |

![Brouillage : les quatre réponses](docs/figures/brouillage_4_reponses.png)
![Leurre en échelon : les quatre réponses](docs/figures/leurre_echelon_4_reponses.png)

- **Brouillage** : le récepteur brouillé fournit par moments des positions et des vitesses fausses
  avec un fix valide, et l'EKF les accepte (plus de 2,6 km d'erreur). ArduPilot atterrit en
  4,9 s, sous le vent et hors de la zone. R3 écarte le GPS en 0,6 s et garde le cercle.
- **Leurre en échelon** : l'EKF rejette d'abord le saut, puis, son incertitude dépassant 25 m,
  se recale sur la fausse position au bout d'environ 10 s ; le drone tourne alors 100 m trop au
  sud en croyant être sur son cercle. Le failsafe d'ArduPilot ne voit rien ; avec la traînée, son
  retour au départ se fait vers la position faussée. R3 écarte le GPS en 0,5 s, avant que l'EKF
  ne l'accepte : c'est le cas où un détecteur par innovations apporte le plus.
- **Leurre en rampe : R3 échoue.** Il écarte le GPS en 0,6 s, mais 5 s plus tard le leurre n'a
  décalé la position que de 8,6 m, sous les 25 m : R3 conclut que le GPS est redevenu cohérent et
  y revient, puis l'EKF suit le leurre. Un leurre qui avance à la vitesse *v* ne dépasse 25 m
  qu'au bout de 25 / *v* secondes : il faudrait observer plus longtemps avant de revenir, et un
  leurre plus lent que la dérive de la navigation à l'estime resterait de toute façon invisible
  avec cette méthode.

![Leurre en rampe : R3 revient au GPS trop tôt](docs/figures/leurre_rampe_4_reponses.png)

- **Témoin** : le biais d'accéléromètre fait monter SV en premier, R3 n'écarte pas le GPS ; avec
  un GPS sain, l'EKF compense ce biais seul (0,5 m d'erreur pour toutes les réponses).
- R3 a fait une exclusion à tort, brève (5 s), 10 s après son retour au GPS à la fin du
  brouillage, pendant le recalage de l'EKF.

Limites : un vol par case, un seul vent et un seul cap à l'injection ; le vol témoin ne couvre
qu'une configuration, alors que d'autres vents avaient fait réagir SP en premier à un biais
d'accéléromètre avec le seuil fixe ; leurres simplifiés (vitesse GPS non décalée). Constaté
après la campagne dans les traces : pendant l'exclusion, la valeur figée de SP (26,41 après le
leurre en échelon) continue d'alimenter le détecteur, si bien qu'après le retour au GPS le seuil
adaptatif de SP, calculé sur les 30 dernières secondes, reste très haut et ce canal est aveugle
environ 30 s ; l'exclusion à tort après le brouillage vient d'une alarme due au recalage de
l'EKF, commencée pendant le délai de 10 s et encore active à sa fin.

## Version d'ArduPilot

ArduCopter V4.8.0-dev, commit `14c871f` (2026-09-09). ArduPilot est cloné hors de
ce dépôt, dans `~/drone/ardupilot`.

## Contenu du dépôt

- `scripts/analyse_vol.py <log.BIN> <image.png>` : chronologie des événements
  (armement, modes, changements de `SIM_GPS1_ENABLE` et `SIM_ACC1_BIAS_X`) et tracé
  des innovations EKF (XKF4, cœur 0), du nombre de satellites et du fix GPS.
- `scripts/extraire_innovations.py <log.BIN> <sortie.csv>` : export CSV des
  innovations XKF4.
- `scripts/trouver_param.py <log.BIN>` : instants où `SIM_GPS1_ENABLE` change.
- `scripts/verif_biais.py <log.BIN>` : biais accéléromètre X estimé par l'EKF
  (XKF2.AX, cœur 0) face aux changements de `SIM_ACC1_BIAS_X`.
- `scripts/superposer_biais_magneto.py <log.BIN> <image.png>` : biais accéléromètre
  X estimé par l'EKF (XKF2.AX) et innovation magnétomètre (XKF4.SM), cœur 0, avec
  les instants d'injection et de retrait de `SIM_ACC1/2/3_BIAS_X` ; temps depuis
  l'entrée en mode CIRCLE.
- `scripts/tracer_trajectoires.py <image.png> <log.BIN> [...]` : trajectoires pendant le
  cercle vues de dessus, côte à côte, avec le vent réglé. Résultat :
  `docs/figures/trajectoires_vent.png`.
- `scripts/detecteur_seuil.py <dossier_jeu_donnees> [facteur persistance]` : détecteur
  à seuil évalué en validation croisée. Sans argument, balaye plusieurs réglages ; avec,
  détail vol par vol (délai, canal, comparaison avec la porte de l'EKF, alarmes après panne).
- `scripts/detecteur_adaptatif.py <dossier_jeu_donnees> [k]` : détecteur à seuil adaptatif
  (k = 6 par défaut), détail vol par vol avec les mêmes métriques que le seuil fixe.
- `scripts/comparer_detecteurs.py <dossier_jeu_donnees> <dernier_log_calibration> [k ...]` :
  seuil fixe calibré et Isolation Forest entraîné sur les logs jusqu'à
  `dernier_log_calibration`, seuil adaptatif et combinaison « ML + adaptatif » ; tous évalués sur
  les logs suivants (vols jamais vus).
- `scripts/tracer_detecteurs.py <dossier_jeu_donnees> <dernier_log_calibration> <log> <image.png> [titre]` :
  un vol avec ce que voient les quatre détecteurs (innovations et seuils, score de l'Isolation
  Forest, alarmes). Résultat sur le vol 104 : `docs/figures/test_derive_vol104.png`.
- `scripts/detecteur_en_ligne.py preparer <dossier_jeu_donnees> <dernier_log_calibration> <fichier.joblib>` :
  calibre et entraîne les quatre détecteurs comme `comparer_detecteurs.py` et les enregistre ;
  `scripts/detecteur_en_ligne.py rejouer <fichier.joblib> <dossier_jeu_donnees> [log ...]` : fait
  passer les CSV un échantillon à la fois dans le détecteur en vol et vérifie que ses alarmes sont
  identiques à celles de l'analyse après coup.
- `scripts/comparer_en_ligne.py <trace.csv> <dossier_jeu_donnees> <log>` : compare la trace d'un
  vol fait avec `--detecteur` à l'analyse du log du même vol (débit, décalage d'horloge, valeurs,
  délais et fausses alarmes).
- `scripts/erreur_navigation.py <log.BIN> [image.png [titre]]` : erreur de navigation réelle
  (position du simulateur contre position estimée, cœur 0), distance au centre du cercle, temps
  passé dans la zone surveillée et vent estimé, avant, pendant et après une perturbation GPS ;
  figure de la trajectoire vue de dessus et des erreurs. Résultats :
  `docs/figures/coupure_gps_sans_trainee_vol23.png` et `coupure_gps_avec_trainee_vol130.png`.
- `scripts/recuperation.py` : la réponse R3 aux pannes GPS (automate : écarter le GPS, revenir
  au GPS, dernier recours), utilisée par `vol_auto.py --reponse r3`.
- `scripts/comparer_reponses.py <image.png> <titre> <log:étiquette> [...]` : plusieurs vols
  d'une même panne, une ligne par réponse (trajectoire, positions vraie et estimée en fonction du
  temps, erreur de navigation, décisions de R3 et d'ArduPilot). Résultats :
  `docs/figures/brouillage_4_reponses.png`, `leurre_echelon_4_reponses.png`,
  `leurre_rampe_4_reponses.png`.
- `scripts/detecteur_ml.py <dossier_jeu_donnees> <dernier_log_apprentissage>` : Isolation
  Forest entraîné sur le nominal des logs jusqu'à `dernier_log_apprentissage`, détail vol par vol
  sur les logs suivants (délai, part de la panne en alarme, fausses alarmes, état dégradé).
  Pour l'affiner avec de nouveaux vols : générer leurs CSV avec `construire_jeu_donnees.py`
  et relancer, le modèle est ré-entraîné à chaque exécution.
- `scripts/construire_jeu_donnees.py <dossier> <log.BIN> [...]` : jeu de données
  étiqueté, un CSV par log (innovations du cœur 0 à 10 Hz, statut GPS, phase du vol,
  type et amplitude de panne, étiquette `nominal` / `panne` / `apres_panne`, temps
  depuis l'injection et le retrait). Étiquettes tirées automatiquement des changements
  de paramètres `SIM_*` enregistrés dans le log. Les CSV sont régénérables et ne sont
  pas versionnés (`data/`).
- `scripts/tracer_cap_magneto.py <log.BIN> <image.png>` : cap du drone, intensité du
  champ mesuré par le compas 1 et innovation magnétomètre (SM) sur un axe de temps
  commun, avec les instants d'injection et de retrait ; affiche la durée mesurée d'un
  tour de cercle. Résultat sur le vol 5 : `docs/figures/cap_champ_magneto_vol5.png`.
- `scripts/comparer_vols.py <image.png>` : innovations des vols automatiques à
  échelles communes (une colonne par type de panne, une ligne par innovation, vol
  nominal en référence). Résultat : `docs/figures/comparaison_vols_auto.png`.
- `scripts/lancer_vol.sh <scénario>` et `scripts/vol_auto.py` : vol SITL automatique
  (voir « Relancer un vol »).
- `docs/figures/` : figures issues des premiers vols.

Les logs de vol (`.BIN`, `.tlog`) ne sont pas versionnés.

## Relancer un vol

### Vol automatique

```bash
scripts/lancer_vol.sh <scénario> [vitesse direction turbulence] [--injection T] [--amplitude A]
# exemple : biais de 0,5 m/s² sous un vent de 6 m/s venant du nord, turbulence 2
scripts/lancer_vol.sh biais05 6 0 2
# exemple : biais de 0,2 m/s² sans vent, injecté 135 s après l'entrée en CIRCLE
scripts/lancer_vol.sh biais --amplitude 0.2 --injection 135
```

Le script démarre le SITL (`sim_vehicle.py -v ArduCopter -w -N --no-mavproxy`),
exécute la procédure manuelle décrite ci-dessous en pymavlink, attend le
désarmement puis arrête le SITL. Il attend que les deux cœurs EKF utilisent le GPS
avant de passer en GUIDED, vérifie chaque réglage et l'acceptation du décollage, et
retire la panne si l'altitude descend sous 8 m. Le journal du vol est écrit dans
`data/`. Scénarios : `nominal`, `gps60`, `gps30`, `biais10`, `biais05`, `magneto`, et avec
`--amplitude` : `biais` (biais d'accéléromètre X des trois IMU, m/s²), `derive` (même biais en
rampe sur les 60 s de panne, valeur finale en m/s²), `gyro` (biais de gyroscope X des trois IMU,
rad/s), `bruit_gyro` (bruit aléatoire de gyroscope des trois IMU, `SIM_GYR*_RND`, amplitude
radians(valeur) × gaz) et `bloque` (accéléromètre de l'IMU 1 seule forcé à cette valeur sur ses
trois axes, `SIM_ACCEL1_FAIL`). Pour le GPS, en plus des coupures : `jam` (brouillage simulé,
`SIM_GPS1_JAM` : perte du signal puis fix, satellites, vitesse et position erratiques), et avec
`--amplitude` en mètres, `leurre` et `leurre_rampe` (position GPS décalée vers le nord,
`SIM_GPS1_GLTCH_X`, d'un coup ou progressivement sur 60 s, le fix et la vitesse restant
corrects). Le bruit d'accéléromètre `SIM_ACC*_RND` n'est pas utilisé : dans
le simulateur, il n'agit que si une vibration (`SIM_VIB_FREQ` ou `SIM_VIB_MOT_MAX`) est réglée.
Le vent optionnel (m/s, degrés d'où il vient, m/s) est réglé avant
le décollage, uniforme en altitude. `--injection` fixe l'instant d'injection après l'entrée en
CIRCLE (120 s par défaut) : le cercle étant très régulier (un tour ≈ 31 s), il fixe aussi le cap
du drone au début de la panne. `--amplitude` fixe le biais (m/s²) ou le décalage magnétomètre. Par vent fort, le drone posé peut rester armé (le détecteur
d'atterrissage d'ArduPilot ne conclut pas tant que le régulateur demande de
l'inclinaison contre le vent) : le script le désarme alors après 15 s au sol.

Avec `--detecteur`, les quatre détecteurs tournent pendant le cercle : chaque début et fin
d'alarme est écrit dans le journal, et toutes les mesures dans `data/en_ligne_<date>.csv`. Le
détecteur se prépare une fois, à partir du jeu de données des vols d'apprentissage :

```bash
python scripts/detecteur_en_ligne.py preparer data/jeu_donnees 49 data/detecteur_en_ligne.joblib
scripts/lancer_vol.sh biais --amplitude 0.3 --detecteur
```

`--trainee` active l'estimation du vent par la traînée et désactive le failsafe de navigation à
l'estime (`FS_DR_ENABLE 0`, qui sinon ferait rentrer le drone). `--bascule T` (vol nominal) fait
passer l'EKF, à T s de cercle, sur un jeu de sources sans GPS pendant 60 s, puis le ramène au GPS.
`--reponse` choisit la réponse à la panne : `rien` (défaut), `natif` (`FS_EKF_ACTION 1`),
`natif_trainee` (idem avec la traînée et `FS_DR_ENABLE 2`) ou `r3` (détecteur, traînée et
`scripts/recuperation.py`).

### Vol manuel

#### 1. Lancer la simulation

```bash
cd ~/drone/ardupilot
./Tools/autotest/sim_vehicle.py -v ArduCopter -w --console --map
```

`-w` remet les paramètres à leurs valeurs par défaut, pour que chaque vol parte
du même état. Sur la machine de développement, les fenêtres `--console` et `--map`
ne s'ouvrent pas : le vol se pilote depuis le prompt MAVProxy et se suit dans
QGroundControl.

#### 2. Paramètres, décollage et cercle (prompt MAVProxy)

```
param set FS_EKF_ACTION 0      # failsafe EKF en « report only » : pas de changement de mode
param set CIRCLE_RADIUS_M 30   # rayon du cercle (m)
param set CIRCLE_RATE 15       # vitesse de rotation (deg/s)
mode guided
```

Attendre environ 30 s, que les messages `PreArm` sur le GPS disparaissent, puis :

```
arm throttle
takeoff 15
```

Une fois stable à 15 m :

```
rc 3 1500                      # throttle à mi-course, nécessaire avant CIRCLE
mode circle
```

#### 3. Injection d'une panne

Après 2 min de cercle nominal, injecter la panne, la maintenir environ 60 s, la
retirer, puis laisser 90 s de cercle.

```
# Coupure GPS
param set SIM_GPS1_ENABLE 0    # retrait : param set SIM_GPS1_ENABLE 1

# Biais accéléromètre X sur les trois IMU simulées (retrait : remettre à 0)
param set SIM_ACC1_BIAS_X 1.0
param set SIM_ACC2_BIAS_X 1.0
param set SIM_ACC3_BIAS_X 1.0
```

Un vol nominal comporte environ 3 min de cercle, sans panne.

#### 4. Atterrir

```
mode rtl
```

Attendre `DISARMED` avant de fermer le terminal pour que le log soit complet.
Les logs sont écrits dans `~/drone/ardupilot/logs/` (`ls -lt logs/*.BIN | head`
pour trouver le plus récent).

## Analyser un log

```bash
python scripts/analyse_vol.py ~/drone/ardupilot/logs/00000014.BIN docs/figures/vol.png
```

## Prochaines étapes

- Récupération, R3 v2 : observer le GPS plus longtemps avant d'y revenir (leurre lent) et
  allonger le délai après un retour ; validation sur des vols neufs (autres vents et caps,
  plusieurs vols témoins, leurre plus lent pour mesurer la limite).
- Remplacer la règle de R3 par un classifieur appris du type de panne, et comparer les deux.
- Autoencodeur, dont l'erreur de reconstruction croît avec l'écart au nominal (pas de
  saturation du score comme l'Isolation Forest), comparé sur le même jeu de test.
- Pannes sur un seul capteur (comparaison entre capteurs redondants) ; ajout de vibrations des
  moteurs dans la simulation, pour un nominal plus réaliste.
- Traitement de la phase qui suit le retrait d'une panne.
- Classification du type de panne.
