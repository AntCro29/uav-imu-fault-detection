# Détection de défauts IMU — ArduPilot SITL

Projet personnel : détecter des pannes capteurs sur un drone simulé à partir des
innovations de l'EKF3 d'ArduPilot, d'abord avec un seuil statistique, puis avec un
modèle de machine learning entraîné sur des vols nominaux.

## État actuel

Projet en phase exploratoire : collecte de vols et premières analyses.
Aucun détecteur n'est encore implémenté.

Onze vols ont été réalisés en SITL (ArduCopter, vol en cercle) :

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

Les vols 8 à 11 refont les vols manuels 1 à 4 avec le pilotage automatique : les
vols 5 à 11 forment ainsi une série réalisée avec exactement le même protocole.

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
scripts/lancer_vol.sh <nominal|gps60|gps30|biais10|biais05|magneto>
```

Le script démarre le SITL (`sim_vehicle.py -v ArduCopter -w -N --no-mavproxy`),
exécute la procédure manuelle décrite ci-dessous en pymavlink, attend le
désarmement puis arrête le SITL. Il attend que les deux cœurs EKF utilisent le GPS
avant de passer en GUIDED, vérifie chaque réglage et l'acceptation du décollage, et
retire la panne si l'altitude descend sous 8 m. Le journal du vol est écrit dans
`data/`.

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

- Analyse des innovations sur les vols automatiques (5 à 11).
- Construction d'un jeu de données étiqueté à partir des logs.
- Détecteur à seuil statistique, puis détecteur ML, comparés sur les mêmes vols.
