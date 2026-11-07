# Utilisation : contenu du dépôt, vols et analyses

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
- `scripts/comparer_detecteurs.py <dossier_jeu_donnees> <dernier_log_calibration | roles.csv> [k ...]` :
  seuil fixe calibré et Isolation Forest entraîné sur les logs jusqu'à
  `dernier_log_calibration`, seuil adaptatif et combinaison « ML + adaptatif » ; tous évalués sur
  les logs suivants (vols jamais vus). Avec un fichier de rôles (`docs/roles_campagne_nuit.csv`) :
  calibration sur les logs d'apprentissage, autoencodeur en plus (seuil sur les logs de
  validation), test sur les logs de test et de panne.
- `scripts/detecteur_ae.py <dossier_jeu_donnees> <roles.csv> [--test]` : autoencodeur entraîné sur
  le nominal des logs d'apprentissage, seuil fixé sur les logs de validation ; sans `--test`,
  s'arrête là sans lire les logs de test, avec `--test`, détail vol par vol.
- `docs/roles_campagne_nuit.csv` : rôle de chaque log de la campagne des vols 273 à 328
  (apprentissage, validation, test, panne), fixé avant la campagne.
- `scripts/classifieur.py <dossier_jeu_donnees> <dernier_log_calibration | roles.csv> [--test <dossier_test>]` :
  famille de chaque panne détectée (accéléromètre, gyroscope, GPS, magnétomètre), 3 s après la
  première alarme du détecteur « Isolation Forest + adaptatif » ; règles écrites à la main et
  forêt aléatoire, évaluées en laissant de côté un vol à la fois. Avec `--test`, la forêt apprise
  sur toutes les pannes du premier dossier classe celles du dossier de test.
- `scripts/classifieur_en_ligne.py preparer <dossier> <dernier_log_detecteur> <fichier.joblib>` puis
  `rejouer <classifieur.joblib> <detecteur.joblib> <dossier_test> [log ...]` : le même classifieur,
  un échantillon à la fois, pour le vol (`vol_auto.py --reponse boucle`) ; le rejeu vérifie qu'il
  donne la même famille, au même échantillon et avec les mêmes variables que l'analyse après coup.
  Fichier utilisé en vol : `data/classifieur_boucle.joblib`, préparé par
  `python scripts/classifieur_en_ligne.py preparer data/jeu_boucle 49 data/classifieur_boucle.joblib`.
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
- `scripts/erreur_navigation.py [--coeur0] <log.BIN> [image.png [titre]]` : erreur de navigation
  réelle (position du simulateur contre position estimée par le cœur EKF principal, invalide après
  un « stopped aiding » ; `--coeur0` : ancien calcul sur le cœur 0), distance au centre du cercle, temps
  passé dans la zone surveillée et vent estimé, avant, pendant et après une perturbation GPS ;
  figure de la trajectoire vue de dessus et des erreurs. Résultats :
  `docs/figures/coupure_gps_sans_trainee_vol23.png` et `coupure_gps_avec_trainee_vol130.png`.
- `scripts/recuperation.py` : la réponse R3 aux pannes GPS (automate : écarter le GPS, revenir
  au GPS, dernier recours), utilisée par `vol_auto.py --reponse r3`.
- `scripts/trois_imu.parm` : troisième IMU simulée et sa calibration factice (sans elle,
  l'armement est refusé), chargé au démarrage par `lancer_vol.sh --imus 3`.
- `scripts/vote_imu.py` : la réponse R-IMU (vote entre les trois IMU sur des moyennes de 2 s,
  persistance de 0,5 s, seuils figés), utilisée par `vol_auto.py --reponse rimu`.
- `scripts/verifier_rimu.py <premier_log> <journal> [...]` : déroulé d'une campagne à trois IMU
  (réglages, panne sur la seule IMU demandée, instants, désarmement, trous dans le log), sans lire
  aucun résultat. Les journaux sont triés par date et associés aux logs consécutifs.
- `scripts/evaluer_rimu.py <premier_log> <journal> [...]` : résultats d'une campagne à trois IMU
  (IMU déclarée par le vote et délai, changements de cœur principal, erreurs d'attitude et de
  position vraies du cœur principal avant, pendant et après la panne). Exemple :
  `python scripts/evaluer_rimu.py 427 data/journal_*20261102-1[4-9]*.txt`.
- `scripts/verifier_boucle.py [--depuis AAAAMMJJ-HHMMSS] <logs> <journal> [...]` et
  `scripts/evaluer_boucle.py` (mêmes arguments) : déroulé puis résultats d'une campagne de la
  boucle complète (décision, IMU déclarée, exclusions et retours au GPS, dernier recours,
  conformité au résultat attendu, erreurs vraies, temps dans la zone). `<logs>` donne les numéros
  dans l'ordre des vols, en plages (la numérotation d'ArduPilot repart à 1 après 500). Exemple :
  `python scripts/evaluer_boucle.py --depuis 20261103-182500 459-500,1-6 data/journal_*_20261103-*.txt data/journal_*_20261104-0*.txt`
  (sans vibration, vols 445 à 492) et
  `python scripts/evaluer_boucle.py --depuis 20261104-185000 10-57 data/journal_*_2026110[45]-*.txt`
  (sous vibration, vols 496 à 543). `verifier_boucle.py` attend vibration et flux optique quand le
  nom du journal les demande.
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
  de paramètres `SIM_*` enregistrés dans le log pendant le cercle (un réglage fait avant, comme
  le bruit de `--bruit`, sert de référence). Les CSV sont régénérables et ne sont
  pas versionnés (`data/`).
- `scripts/tracer_cap_magneto.py <log.BIN> <image.png>` : cap du drone, intensité du
  champ mesuré par le compas 1 et innovation magnétomètre (SM) sur un axe de temps
  commun, avec les instants d'injection et de retrait ; affiche la durée mesurée d'un
  tour de cercle. Résultat sur le vol 5 : `docs/figures/cap_champ_magneto_vol5.png`.
- `scripts/comparer_vols.py <image.png>` : innovations des vols automatiques à
  échelles communes (une colonne par type de panne, une ligne par innovation, vol
  nominal en référence). Résultat : `docs/figures/comparaison_vols_auto.png`.
- `scripts/lancer_vol.sh <scénario>` et `scripts/vol_auto.py` : vol SITL automatique
  (voir « Relancer un vol »). `scripts/flux_optique.parm` : paramètres du flux optique et du
  télémètre simulés, chargés au démarrage par `lancer_vol.sh --flux_optique`.
- `scripts/animer_leurre.py <log_sans.BIN> <log_avec.BIN> <sortie.mp4> [t_debut t_fin]` : vidéo de
  démonstration de deux vols face au même leurre (vue de dessus : position vraie, GPS, estimée du
  cœur principal ; erreur de l'estimée), accélérée ×4 (ffmpeg nécessaire).
- `scripts/animer_qgc.py <log.BIN> <enregistrement.mov> <décalage_s> <sortie.mp4> [t_debut t_fin]` :
  enregistrement d'écran de QGroundControl (connecté au SITL en TCP sur le port 5762) à côté de la
  vérité du même vol, synchronisés sur un changement de mode visible dans QGC.
- `scripts/figures_readme.py [dossier]` : les trois figures du README, lues dans l'archive des logs
  (le chronogramme de la boucle lit aussi la trace de vol, dans `data/`, non versionné).
- `scripts/exporter_dashboard.py [sortie]` : données du tableau de bord `docs/dashboard/` (48 vols de
  test de la boucle sous vibration : résultats d'`evaluer_boucle.py`, traces de vol, erreurs vraies,
  positions), écrites dans `docs/dashboard/donnees.js`. La page (`index.html`, avec Plotly copié à
  côté) s'ouvre aussi hors ligne.
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
`--amplitude` : `biais` (biais d'accéléromètre X des deux IMU, m/s²), `derive` (même biais en
rampe sur les 60 s de panne, valeur finale en m/s²), `gyro` (biais de gyroscope X des deux IMU,
rad/s), `bruit_gyro` (bruit aléatoire de gyroscope des deux IMU, `SIM_GYR*_RND`, amplitude
radians(valeur) × gaz) et `bloque` (accéléromètre de l'IMU 1 seule forcé à cette valeur sur ses
trois axes, `SIM_ACCEL1_FAIL`). Pour le GPS, en plus des coupures : `jam` (brouillage simulé,
`SIM_GPS1_JAM` : perte du signal puis fix, satellites, vitesse et position erratiques), et avec
`--amplitude` en mètres, `leurre` et `leurre_rampe` (position GPS décalée vers le nord,
`SIM_GPS1_GLTCH_X`, d'un coup ou progressivement sur 60 s, le fix et la vitesse restant
corrects). Le bruit d'accéléromètre `SIM_ACC*_RND` n'est pas un scénario de panne : dans
le simulateur, il n'agit que si une vibration (`SIM_VIB_FREQ` ou `SIM_VIB_MOT_MAX`) est réglée
(voir `--vibration`).
Le vent optionnel (m/s, degrés d'où il vient, m/s) est réglé avant
le décollage, uniforme en altitude. `--injection` fixe l'instant d'injection après l'entrée en
CIRCLE (120 s par défaut) : le cercle étant très régulier (un tour ≈ 31 s), il fixe aussi le cap
du drone au début de la panne. `--amplitude` fixe le biais (m/s²) ou le décalage magnétomètre. Par vent fort, le drone posé peut rester armé (le détecteur
d'atterrissage d'ArduPilot ne conclut pas tant que le régulateur demande de
l'inclinaison contre le vent) : le script le désarme alors après 15 s posé, d'après l'état vrai du
simulateur (`SIM_STATE` : vitesse verticale sous 0,3 m/s et altitude stable à 0,3 m près pendant
15 s ; le terrain du simulateur n'est pas plat). Si le drone n'est pas posé au bout de 120 s, il s'arrête en erreur sans couper les moteurs.

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
`scripts/recuperation.py`). `--bruit R` ajoute un bruit de gyroscope aux deux IMU pendant tout
le vol (`SIM_GYR*_RND = R`, réglé avant le décollage). `--vibration` ajoute pendant tout le vol la
vibration des moteurs du test `MotorVibration` d'ArduPilot (`SIM_VIB_MOT_MAX` 350,
`SIM_GYR*_RND` 20, `SIM_ACC*_RND` 5, deux IMU). `--flux_optique` (à passer aussi à
`lancer_vol.sh`, qui charge `scripts/flux_optique.parm` au démarrage du SITL) ajoute le capteur de
flux optique et le télémètre simulés ; `vol_auto.py` vérifie leurs paramètres avant le vol.
`--flux_permanent` (avec `--flux_optique`) fait fusionner le flux en permanence et l'ajoute au jeu
de sources sans GPS.

`--imus 3` (à passer aussi à `lancer_vol.sh`, qui charge `scripts/trois_imu.parm` au démarrage)
simule trois IMU au lieu de deux ; l'EKF garde ses deux cœurs sur les IMU 1 et 2
(`EK3_IMU_MASK` = 3), la troisième sert de témoin. `--imu N` met la panne d'IMU sur la seule
IMU N (1 à 3, numérotation des paramètres `SIM_ACCn_*`, `SIM_GYRn_*`) ; l'IMU 1 est celle du
cœur 0, principal par défaut. `--reponse rimu` (avec `--imus 3`) fait voter les trois IMU
pendant le cercle (`scripts/vote_imu.py`) et, si l'IMU déclarée en panne est celle d'un cœur,
force l'autre cœur principal jusqu'à la fin du vol. Exemple :

```bash
# biais de 1,0 m/s² sur l'IMU 1 seule, vent de 7 m/s venant de 190°, réponse R-IMU
scripts/lancer_vol.sh biais 7 190 2.5 --imus 3 --imu 1 --injection 128 --amplitude 1.0 --reponse rimu
```

`--reponse boucle` (avec `--imus 3`) fait tourner ensemble le détecteur, le classifieur en vol, le
vote R-IMU et R3 sans sa règle « SP en premier » : 3 s après la première alarme, la famille de la
panne décide une fois pour tout le vol (GPS → GPS écarté, sauf si le vote a déjà désigné une IMU ;
accéléromètre ou gyroscope → GPS gardé ; magnétomètre → signalé). La perte du fix écarte le GPS
sans attendre. Exemple :

```bash
# leurre GPS de 100 m, vent de 6 m/s venant de 20°, boucle complète
scripts/lancer_vol.sh leurre 6 20 2 --imus 3 --injection 128 --amplitude 100 --reponse boucle
```

Avec `--vibration`, la boucle passe à sa version 2 : déclencheur autoencodeur OU Isolation Forest OU
règle GPS, et aucun épisode commencé avant 10 s de cercle n'est classé. Ses fichiers se préparent par
`python scripts/detecteur_en_ligne.py preparer data/jeu_boucle_v docs/roles_boucle_v.csv data/detecteur_vibration.joblib`
puis `python scripts/classifieur_en_ligne.py preparer data/jeu_boucle_v docs/roles_boucle_v.csv data/classifieur_boucle_v.joblib --ae`
(`classifieur.py ... --ae` pour la validation croisée). La trace contient en plus les colonnes
`autoencodeur`, `AE + ML` et `score_ae` ; le journal donne les canaux qui ont déclenché chaque
classification.

```bash
scripts/lancer_vol.sh leurre 6 20 2 --imus 3 --injection 128 --amplitude 100 --vibration --flux_optique --flux_permanent --reponse boucle
```

### Archive des logs

ArduPilot ne garde que 500 numéros de log (`LOG_MAX_FILES`, au plus 500) : après le log 500, il
repart à 1 en écrasant les anciens fichiers (c'est arrivé le 2026-11-03). Il supprime aussi les plus
anciens quand il reste moins de 500 Mo libres sur le disque (`LOG_FILE_MB_FREE` en SITL). Chaque
log est donc archivé sous son **numéro de vol**, qui ne revient jamais :

- `~/drone/archive_logs/vols/vol_NNNN.BIN` (ou le dossier de la variable `ARCHIVE_LOGS`) ; les six
  logs de septembre antérieurs au projet sont dans `hors_projet/` ;
- `docs/index_vols.csv` (copié dans l'archive) : pour chaque vol, le numéro du log ArduPilot
  d'origine, la fin d'écriture, la taille, le fichier archivé et le journal du vol ;
- `lancer_vol.sh` appelle `scripts/archiver_log.py` : avant le vol, il refuse de démarrer si
  ArduPilot allait écraser un log sans copie identique dans l'archive ; après le vol, il copie le
  nouveau log (vérifié octet par octet) et ajoute sa ligne à l'index.

Les scripts d'analyse lisent toujours `~/drone/ardupilot/logs/<log>.BIN` : pour un vol dont le log a
été écrasé, utiliser le fichier de l'archive indiqué dans l'index.

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

# Biais accéléromètre X sur les deux IMU simulées (retrait : remettre à 0)
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
