# Plan d'essai — campagne 1

Version du 2026-11-09, critères validés par Antoine avant les vols. Aucun critère ne sera modifié
après les vols ; un écart ou un imprévu est consigné dans le rapport, pas corrigé dans ce plan.

**Révision du 2026-11-12, avant tout vol de la campagne** (validée par Antoine) :

- « manches au neutre » et « manche en butée » définis par des valeurs du journal (mesurées sur
  les 18 vols antérieurs : une manche relâchée revient exactement à 1024, une butée vaut
  exactement 364 ou 1684) ;
- début d'un palier de stationnaire : 3 s après que le drone est immobile, pour que le freinage
  ne compte pas dans le palier ;
- FE-03 : `OSD.isVisionUsed` relevé et non plus exigé. Sur les 18 vols antérieurs, il n'est vrai
  que lorsque le GPS n'est pas utilisé (7 épisodes, 85 s au total) : avec un bon GPS, le
  positionnement par vision seul ne peut sans doute pas être isolé.

## Périmètre

Première campagne réduite : une séance de 30 à 60 min sur une grande pelouse, 3 batteries,
3 vols d'environ 10 min, atterrissage au plus tard à 30 % de batterie.

| Essai | Exigences | Vol | Fiche |
|---|---|---|---|
| FE-01 Stationnaire en positionnement satellite | EX-C01, EX-C02 | 1 | `fiches/FE-01_stationnaire_satellite.md` |
| FE-02 Montée et descente, mode Normal | EX-C07, EX-C08 (mode Normal) | 1 | `fiches/FE-02_montee_descente.md` |
| FE-03 Stationnaire en positionnement par vision | EX-C03, EX-C04 | 2 | `fiches/FE-03_stationnaire_vision.md` |
| FE-04 Retour au départ | EX-U01 | 2 et 3 | `fiches/FE-04_retour_depart.md` |
| FE-05 Vitesse maximale, mode Normal (si la pelouse offre 200 m dégagés) | EX-C05, EX-C09 | 3 | `fiches/FE-05_vitesse_max.md` |

Non couvertes par cette campagne : EX-C06 (mode Sport), EX-C07/C08 en modes Cine et Sport,
EX-U02 (perte de liaison), EX-U03 (répétabilité), EX-U04 (autonomie), EX-C12 (analyse à part).

## Critères d'acceptation

| Essai | Critère | Raison |
|---|---|---|
| FE-01, FE-03 | Pour chaque palier de 60 s, **95 % des échantillons** à moins de la valeur annoncée de la position moyenne du palier, séparément en horizontal et en vertical (FE-01 : 1,5 m et 0,5 m ; FE-03 : 0,3 m et 0,1 m). Exigence satisfaite si les 3 paliers le sont. | La fiche technique ne précise pas la statistique garantie ; 95 % est une convention courante. |
| FE-02 | Vitesse verticale maximale mesurée à ±10 % de 5 m/s (soit 4,5 à 5,5 m/s), en montée et en descente, sur chacune des 3 répétitions. | Tolérance de mesure. |
| FE-04 | Point de pose à **1,5 m au plus** du repère de décollage, sur chacun des retours. | Reprend la précision horizontale annoncée en positionnement satellite. |
| FE-05 | Vitesse horizontale maximale sur le sol, moyenne de l'aller et du retour, à ±10 % de 12 m/s. Inclinaison maximale relevée et comparée à 35° (EX-C09). | L'aller-retour compense en partie le vent. |

## Conditions de validité d'un essai

Un palier ou une répétition qui ne remplit pas ces conditions est déclaré **non valide** (ni
réussi ni échoué) et rapporté comme tel.

| Condition | Essais |
|---|---|
| Satellites ≥ 10 pendant tout le palier | tous |
| `OSD.isVisionUsed` faux pendant tout le palier | FE-01 |
| Aucune action sur les manches pendant le palier : `RC.aileron`, `RC.elevator`, `RC.throttle` et `RC.rudder` valent **exactement 1024** sur tous les échantillons du palier | FE-01, FE-03 |
| Manche concernée en butée : valeur **exactement 364 ou 1684** ; la phase mesurée est l'ensemble des échantillons consécutifs en butée | FE-02 (`RC.throttle`), FE-05 (`RC.elevator`) |
| Mode de vol Normal (`GPSAtti` dans le journal) | tous |

**Début d'un palier de stationnaire (FE-01, FE-03)** : après avoir relâché les manches, attendre
3 s que le drone soit immobile, puis lancer le chrono. Le palier est la fenêtre de 60 s qui
commence à l'heure notée dans le carnet.

**FE-03 et le positionnement par vision** : `OSD.isVisionUsed` est relevé sur chaque palier.
S'il est vrai pendant tout le palier, le palier compte pour EX-C03 et EX-C04. Sinon, le palier
est rapporté comme stationnaire à 2 m sans positionnement par vision déclaré, et EX-C03 et
EX-C04 sont déclarées **non vérifiables dans ces conditions** (ni conformes ni non conformes).

## Critères d'arrêt

Arrêt immédiat de l'essai en cours (atterrissage), sans reprise tant que la cause persiste :

- vent supérieur à 5 m/s (moitié de la résistance annoncée de 10,7 m/s) ;
- batterie sous 30 % ;
- moins de 10 satellites pour un essai en positionnement satellite ;
- une personne qui s'approche de la zone d'évolution ;
- tout message d'alerte de l'application (compas, IMU, GPS, liaison).

## Moyens

| Moyen | Usage |
|---|---|
| Journal de vol DJI (10 Hz), décodé avec dji-log-parser | position et hauteur estimées, vitesses, attitude, satellites, mode, manches, batterie |
| Vidéo de la caméra pointée vers le bas, cible au sol de taille connue | dérive réelle en stationnaire (FE-01, FE-03), analysée après coup si la qualité le permet |
| Mètre ruban, repère de décollage | distance de pose (FE-04) |
| Anémomètre ou application météo | vent au début de chaque vol |
| Carnet de vol | correspondance vol ↔ journal, conditions, imprévus |

Limite connue : le journal donne la position **estimée** par le drone. Si la vidéo ne permet pas
de mesurer la dérive réelle, FE-01 et FE-03 sont rapportés sur l'estimée, avec cette limite.

## Configuration du drone (relevée avant le premier vol, inchangée pendant la séance)

À noter dans le carnet : version du firmware et de l'application DJI Fly, hauteur maximale
(**120 m**), distance maximale, hauteur de retour au départ, réglage de l'évitement d'obstacles,
atterrissage de précision activé ou non, mode débutant **désactivé**.

## Traçabilité

| Exigence | Essai | Résultat |
|---|---|---|
| EX-C01 | FE-01 | conforme (campagne 1, `rapport_campagne1.md`) |
| EX-C02 | FE-01 | conforme (campagne 1, `rapport_campagne1.md`) |
| EX-C03 | FE-03 | non vérifiable (campagne 1, `rapport_campagne1.md`) |
| EX-C04 | FE-03 | non vérifiable (campagne 1, `rapport_campagne1.md`) |
| EX-C05 | FE-05 | non conclue (campagne 1, `rapport_campagne1.md`) |
| EX-C07 (Normal) | FE-02 | conforme (campagne 1, `rapport_campagne1.md`) |
| EX-C08 (Normal) | FE-02 | conforme (campagne 1, `rapport_campagne1.md`) |
| EX-C09 | FE-05 | relevée : 34,3° (campagne 1, `rapport_campagne1.md`) |
| EX-U01 | FE-04 | conforme (campagne 1, `rapport_campagne1.md`) |
