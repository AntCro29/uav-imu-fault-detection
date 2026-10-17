# Détection de défauts IMU — ArduPilot SITL

Projet personnel : détecter des pannes capteurs sur un drone simulé à partir des
innovations de l'EKF3 d'ArduPilot, d'abord avec un seuil statistique, puis avec un
modèle de machine learning entraîné sur des vols nominaux.

## État actuel

Projet en cours : collecte de vols, analyse des innovations, détecteurs à seuil (seuil fixe,
puis seuil qui s'adapte au niveau des innovations) et premier détecteur par machine learning
(Isolation Forest entraîné sur des vols nominaux), comparés sur des vols de test. La
classification du type de panne et la récupération ne sont pas encore abordées.

Cinquante-huit vols ont été réalisés en SITL (ArduCopter, vol en cercle) :

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

Les vols 8 à 11 refont les vols manuels 1 à 4 avec le pilotage automatique : les
vols 5 à 58 forment ainsi une série réalisée avec exactement le même protocole. À partir
du vol 12, les vols ajoutent du vent (`SIM_WIND_SPD`, `SIM_WIND_DIR`, `SIM_WIND_TURB`), réglé
uniforme en altitude (`SIM_WIND_T = 1`), sauf les vols 32, 33, 36 et 37, sans vent. Les vols 36
à 58 n'ont servi à aucun réglage : ils forment le jeu de test du seuil adaptatif.

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
  `dernier_log_calibration`, seuil adaptatif ; tous évalués sur les logs suivants (vols jamais vus).
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
trois axes, `SIM_ACCEL1_FAIL`). Le bruit d'accéléromètre `SIM_ACC*_RND` n'est pas utilisé : dans
le simulateur, il n'agit que si une vibration (`SIM_VIB_FREQ` ou `SIM_VIB_MOT_MAX`) est réglée.
Le vent optionnel (m/s, degrés d'où il vient, m/s) est réglé avant
le décollage, uniforme en altitude. `--injection` fixe l'instant d'injection après l'entrée en
CIRCLE (120 s par défaut) : le cercle étant très régulier (un tour ≈ 31 s), il fixe aussi le cap
du drone au début de la panne. `--amplitude` fixe le biais (m/s²) ou le décalage magnétomètre. Par vent fort, le drone posé peut rester armé (le détecteur
d'atterrissage d'ArduPilot ne conclut pas tant que le régulateur demande de
l'inclinaison contre le vent) : le script le désarme alors après 15 s au sol.

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

- Répéter les vols de test pour mesurer la variabilité du seuil adaptatif (un seul vol par
  configuration pour l'instant), et traiter le cas des pannes lentes « absorbées » par le seuil.
- Traitement de la phase qui suit le retrait d'une panne.
- Pannes sur un seul capteur (comparaison entre capteurs redondants), dérive, bruit, capteur bloqué.
- Détecteur ML : nouvelle campagne de vols de test (le seuil du score n'a pas pu être réglé sans
  biaiser le test actuel), combinaison avec le seuil adaptatif, autoencodeur.
- Classification du type de panne, puis stratégies de récupération.
