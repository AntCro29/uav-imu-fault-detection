# Détection de défauts IMU — ArduPilot SITL

Projet personnel : détecter des pannes capteurs sur un drone simulé à partir des
innovations de l'EKF3 d'ArduPilot, d'abord avec un seuil statistique, puis avec un
modèle de machine learning entraîné sur des vols nominaux.

## État actuel

Projet en phase exploratoire : collecte de vols et premières analyses.
Aucun détecteur n'est encore implémenté.

Quatre vols ont été réalisés en SITL (ArduCopter, vol en cercle) :

| Vol | Scénario |
|-----|----------|
| 1 | Nominal |
| 2 | Coupure GPS de 60 s |
| 3 | Nominal |
| 4 | Biais de 1,0 m/s² sur l'accéléromètre X des trois IMU simulées, pendant environ 60 s |

Au vol 4, les trois biais ont été injectés l'un après l'autre, à environ 4 s
d'intervalle (une commande par IMU), puis retirés de la même façon : les trois IMU
ont été biaisées simultanément pendant environ 62 s.

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
- `docs/figures/` : figures issues des premiers vols.

Les logs de vol (`.BIN`, `.tlog`) ne sont pas versionnés.

## Relancer un vol

### 1. Lancer la simulation

```bash
cd ~/drone/ardupilot
./Tools/autotest/sim_vehicle.py -v ArduCopter -w --console --map
```

`-w` remet les paramètres à leurs valeurs par défaut, pour que chaque vol parte
du même état. Sur la machine de développement, les fenêtres `--console` et `--map`
ne s'ouvrent pas : le vol se pilote depuis le prompt MAVProxy et se suit dans
QGroundControl.

### 2. Paramètres, décollage et cercle (prompt MAVProxy)

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

### 3. Injection d'une panne

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

### 4. Atterrir

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

- Vols supplémentaires : panne magnétomètre, biais accéléromètre de 0,5 m/s², coupure GPS de 30 s.
- Construction d'un jeu de données étiqueté à partir des logs.
- Détecteur à seuil statistique, puis détecteur ML, comparés sur les mêmes vols.
