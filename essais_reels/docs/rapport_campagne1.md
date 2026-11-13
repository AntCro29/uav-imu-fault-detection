# Rapport d'essai — campagne 1

Séance du 2026-11-13, 11:41 à 12:07 (heure locale, UTC−5). Critères : `plan_essai.md` (version du
2026-11-09, révisée le 2026-11-12), **figés avant les vols et non modifiés après**. Les écarts
sont consignés ici, pas corrigés dans le plan.

## Synthèse

| Exigence | Essai | Résultat | Verdict |
|---|---|---|---|
| EX-C01 stationnaire satellite, horizontal ±1,5 m | FE-01 | 95 % à moins de 0,23 à 0,30 m (journal) ; 0,10 à 0,20 m (vidéo) | **Conforme** (3 paliers sur 3) |
| EX-C02 stationnaire satellite, vertical ±0,5 m | FE-01 | 0,08 à 0,09 m (journal) ; 0,05 à 0,09 m (vidéo) | **Conforme** (3 paliers sur 3) |
| EX-C03 stationnaire vision, horizontal ±0,3 m | FE-03 | positionnement par vision jamais déclaré (`isVisionUsed` faux 100 % du temps) | **Non vérifiable** dans ces conditions |
| EX-C04 stationnaire vision, vertical ±0,1 m | FE-03 | idem | **Non vérifiable** dans ces conditions |
| EX-C07 montée, mode Normal (5 m/s) | FE-02 | 5,1 / 5,1 / 5,1 m/s | **Conforme** |
| EX-C08 descente, mode Normal (5 m/s) | FE-02 | 5,1 / 5,0 / 5,0 m/s | **Conforme** |
| EX-U01 retour au départ ≤ 1,5 m | FE-04 | 0,17 / 0,60 / 0,58 m (ruban) | **Conforme** (3 retours sur 3) |
| EX-C05 vitesse max, mode Normal (12 m/s) | FE-05 | aller 11,9 m/s ; retour non valide | **Non conclue** |
| EX-C09 inclinaison max (35°) | FE-05 | 33,1° en tangage ; 34,3° tangage et roulis combinés | Relevée : 34,3° pour 35° annoncés |
| EX-U05 journal complet | analyse | 7 journaux sur 7 de la campagne | **Conforme** |

## Conditions

| Élément | Valeur |
|---|---|
| Site | site d'essai non décrit dans ce dépôt |
| Vent (carnet, mesuré au sol) | 4 m/s (vol 1), 5 m/s (vol 2) ; 5 m/s = limite d'arrêt (« supérieur à 5 »), essai autorisé |
| Vent déduit de l'inclinaison en stationnaire à 20 m | du nord (355 à 7°), 4,5 à 7,7 m/s (voir « Vent ») |
| Température | 5 °C |
| Satellites en vol | 23 à 26 |
| Batteries | B1 : 92 → 70 % (vol 1) ; B2 : 99 → 60 % (vol 2 et ses redécollages) |
| Configuration du drone (firmware, hauteur de retour, évitement) | non relevée dans le carnet |

## Déroulé : carnet ↔ journaux

Le nom d'un journal est l'heure locale de la radiocommande à la mise en route.

| Journal | Batterie | Contenu |
|---|---|---|
| 11-42-24 | B1 | vol 1 : FE-01 (3 paliers à 20,2 m) puis FE-02 (3 montées, 3 descentes) |
| 11-52-45 | B2 | vol 2 : FE-03 (3 paliers à 2,0 m) |
| 11-58-59 | B2 | FE-04 retour 1 |
| 12-01-09 | B2 | hors essai : réatterrissage après 7 s pour enregistrer le point de départ |
| 12-01-27 | B2 | FE-04 retour 2 |
| 12-03-04 | B2 | FE-04 retour 3 |
| 12-05-07 | B2 | FE-05 aller et retour |

## Résultats par essai

Commande : `python scripts/analyser_essais.py data/carnet_campagne1/carnet 2026-11-13 data/decode/vol_2026-11-13_*.csv`.

### FE-01 — stationnaire en positionnement satellite (20 m)

Palier = 60 s à partir de l'heure du carnet. Écart à la position moyenne du palier, centile 95.

| Palier | Valide | Vision | Horizontal journal | Vertical journal | Horizontal vidéo | Vertical vidéo | Verdict |
|---|---|---|---|---|---|---|---|
| 1 (11:43:47) | oui | 0 % | 0,30 m | 0,09 m | 0,20 m | 0,05 m | conforme |
| 2 (11:45:00) | oui | 0 % | 0,28 m | 0,08 m | 0,19 m | 0,09 m | conforme |
| 3 (11:46:58) | oui | 0 % | 0,23 m | 0,08 m | 0,10 m (49 s, chaise bleue seule) | 0,05 m (13 s) | conforme |

### FE-02 — montée et descente, mode Normal

Phase = échantillons consécutifs avec `RC.throttle` en butée. Deux phases sont écartées par la
condition de mode : 0,6 s au décollage automatique, et la descente d'atterrissage.

| Répétition | Montée : vz max | Descente : vz max |
|---|---|---|
| 1 | 5,1 m/s (20,2 → 56,2 m) | 5,1 m/s (61,1 → 34,3 m) |
| 2 | 5,1 m/s (29,3 → 51,0 m) | 5,0 m/s (54,9 → 31,6 m) |
| 3 | 5,1 m/s (27,4 → 54,4 m) | 5,0 m/s (59,3 → 31,9 m) |

Toutes les valeurs sont dans la plage de 4,5 à 5,5 m/s. La vitesse est enregistrée au dixième de m/s.

### FE-03 — stationnaire à 2 m (vision visée)

| Palier | Valide | Vision | Horizontal journal | Vertical journal | Horizontal vidéo | Vertical vidéo |
|---|---|---|---|---|---|---|
| 1 (11:54:26) | **non** : manches touchées de 54 à 59 s (recentrage avant le palier 2) | 0 % | 0,37 m | 0,08 m | 0,31 m (max 1,04 m pendant le recentrage) | 0,08 m |
| 2 (11:55:35) | oui | 0 % | 0,18 m | 0,00 m | 0,17 m | 0,08 m |
| 3 (11:56:50) | oui | 0 % | 0,19 m | 0,09 m | 0,36 m | 0,06 m |

`OSD.isVisionUsed` n'est jamais vrai. Selon la règle du plan, EX-C03 et EX-C04 sont **non
vérifiables dans ces conditions**. Les paliers sont rapportés comme stationnaire à 2 m en
positionnement satellite. Ce résultat confirme l'observation faite sur les 18 vols antérieurs :
avec un bon GPS, le positionnement par vision ne peut pas être isolé.

### FE-04 — retour au départ

| Retour | Pose (ruban) | Pose d'après le journal | Verdict |
|---|---|---|---|
| 1 | 0,17 m | 0,39 m | conforme |
| 2 | 0,60 m | 1,47 m | conforme |
| 3 | 0,58 m | 0,40 m | conforme |

La pose d'après le journal est l'écart entre la position estimée au décollage et celle à la pose.
Au retour 2, elle diffère de 0,9 m de la mesure au ruban : l'estimée GPS peut se tromper
d'environ 1 m.

### FE-05 — vitesse maximale, mode Normal

| Passage | Manche | Durée en butée | Vitesse max | Route | Tangage max | Inclinaison combinée max |
|---|---|---|---|---|---|---|
| Aller | 1684 (avant) | 13,8 s | 11,9 m/s (palier stable à 11,8 m/s pendant 4 s) | 305° | 33,1° | 34,3° |
| Retour | 364 (arrière) | 18,3 s | 8,1 m/s | 118° | 16,6° | — |

Le retour a été fait **en marche arrière** : le cap est resté à −64° et la manche était tirée,
alors que la fiche demande « à fond vers l'avant » dans les deux sens. Le demi-tour n'a pas pu
être fait pendant l'essai. Le retour mesure donc une autre grandeur (la vitesse en marche
arrière, qui plafonne à 7,8-8,0 m/s) et il est déclaré **non valide**. Le critère porte sur la
moyenne de l'aller et du retour, pour compenser le vent : sans retour valide, **EX-C05 est non
conclue**.

Indication, sans valeur de verdict : l'aller seul atteint 11,9 m/s, dans la plage de 10,8 à
13,2 m/s. Il a été fait en partie face au vent (vent du nord, route au 305°), donc le vent n'a
pas augmenté la vitesse sol. Le plafond à 11,8 m/s, alors que le drone penche de 26 à 32°, fait
penser à une limite de vitesse sol imposée par le logiciel (hypothèse non vérifiée).

Autres écarts propres à FE-05 : ligne de 143 m au lieu des 200 m demandés, hauteur 44,6 m au lieu
de 20 m.

### EX-U05 — journaux complets

Commande : `python scripts/verifier_journal.py data/decode/vol_*.csv`.

- **Campagne 1 : 7 journaux sur 7 conformes** (pas maximal 0,1 s, aucune valeur manquante,
  journal terminé par la confirmation d'atterrissage).
- 18 vols antérieurs, critère appliqué au pied de la lettre et fixé après les avoir vus : 10
  conformes sur 18. Causes des 8 non-conformités :
  - 7 vols ont décollé avant le fix GPS : pendant les 4 à 37 premières secondes, le drone vole
    surtout par vision (75 à 98 % du temps) et le journal ne contient pas de position. Le journal
    n'est pas en défaut, il ne peut pas contenir une position que le drone n'a pas. Le critère
    est à préciser pour la prochaine campagne (« position présente dès le fix GPS ») ;
  - un de ces 7 vols (2026-09-30, 20:12) a aussi 19 trous, de 1,0 s au plus ;
  - le journal du 2026-10-03 à 14:03 s'arrête en vol, sans confirmation d'atterrissage.

## Dérive réelle mesurée sur la vidéo

Commande : `python scripts/analyser_video.py <vidéo> <journal> <distance entre chaises> <hauteur> <paliers>`.

**Méthode.** La caméra pointe vers le bas. Deux chaises, rouge et bleue, sont posées au sol à une
distance mesurée (5 m pour FE-01, 1,5 m pour FE-03). Le script les repère par leur couleur à
10 images/s. La distance entre les chaises en pixels donne l'échelle. Le déplacement du milieu des
chaises dans l'image donne le déplacement réel du drone, et la variation de la distance entre
chaises donne sa variation de hauteur. L'heure de la vidéo est recalée sur le journal en
superposant les trajectoires, déplacements entre paliers compris : FE-01 −10,1 s (corrélation
0,98 nord, 0,95 est), FE-03 +1,2 s (0,76 et 0,80).

**Résultat.** EX-C01 et EX-C02 restent conformes avec la position **réelle**, pas seulement
estimée. À l'échelle de 20 à 30 cm, l'estimée et la réalité divergent, et pas toujours dans le
même sens :

- à 20 m, l'estimée bouge **plus** que le drone (0,28 à 0,30 m contre 0,19 à 0,20 m) : c'est le
  bruit GPS, que le drone ne suit pas entièrement ;
- à 2 m (FE-03, palier 3), le drone dérive **deux fois plus** que ce qu'indique le journal
  (0,36 m contre 0,19 m) ; sur l'axe est, la corrélation entre vidéo et journal tombe à 0,05.

Une mesure de précision de positionnement faite avec le seul journal du drone se juge elle-même.
La vidéo apporte une référence indépendante.

**Imprévu.** La chaise rouge a été déplacée deux fois par le vent pendant le palier 3 de FE-01
(vers 11:47:09 et 11:47:34). Le changement est détecté par la rotation de la ligne entre les
chaises (plus de 0,5°, alors que cet angle reste stable à ±0,1° le reste du temps). Le palier est
mesuré sur la chaise bleue seule, et la hauteur sur les 13 s où les deux chaises étaient en place.

**Limites.**

- La vidéo mesure la dérive autour de la position moyenne du palier, pas l'erreur absolue de
  position (pour celle-ci, voir FE-04).
- La distorsion de l'objectif est ignorée. À 2 m, les chaises parcourent une grande partie de
  l'image : la dérive verticale de FE-03 (0,06 à 0,08 m) peut en partie venir de la distorsion.
  Pour la même raison, l'angle apparent entre chaises y varie lentement de ±1° sans saut ; la
  tolérance de détection d'une chaise déplacée y est donc de 3°.
- La caméra est supposée verticale (nacelle en butée).
- Le recalage horaire s'appuie sur le journal. Il favorise donc légèrement l'accord entre vidéo et
  journal, surtout sur les grands déplacements entre paliers plutôt qu'à l'intérieur des paliers.
- La hauteur `OSD.height` du journal est enregistrée au dixième de mètre.

## Vent

En stationnaire, le drone s'incline face au vent pour équilibrer la traînée : `m·g·tan θ = D`. À
20 m, l'inclinaison moyenne vaut 7,2 à 8,2° sur les 3 paliers de FE-01, toujours vers le nord (355
à 7°). Avec m = 0,249 kg, cela donne D = 0,31 à 0,35 N. La traînée de référence vient des vols
antérieurs : 0,81 N à 11,7 m/s pour 18,3° d'inclinaison. Le vent vaut alors 4,5 à 5,1 m/s si la
traînée varie comme v, et 7,2 à 7,7 m/s si elle varie comme v². C'est cohérent avec les 4 à 5 m/s
du carnet. À 2 m au-dessus du sol (FE-03), l'inclinaison n'est plus que de 0,6 à 1,0° : le vent y
est beaucoup plus faible (gradient près de la surface, abri).

Hypothèses : zéro d'attitude de la centrale inertielle non étalonné ; convention de signe déduite
de l'aller de FE-05 (tangage négatif en avançant, roulis positif avec l'aileron à droite).

## Comparaison avec le banc de simulation (ArduPilot SITL)

Mêmes statistiques que ci-dessus, sur 4 vols SITL de stationnaire faits le 2026-11-13 (vols 545 à
548 du projet de détection de défauts IMU) : vent de 5 m/s du nord, turbulence 1 m/s, LOITER
pendant 200 s, 3 paliers de 60 s. La position vraie du simulateur (`SIM`) joue le rôle de la vidéo,
l'estimée de l'EKF (`XKF1`, cœur principal) celui du journal. Commande :
`python scripts/comparer_stationnaire.py <log.BIN> [...]` (dépôt du projet SITL).

| | DJI réel | SITL sans vibration | SITL avec vibration |
|---|---|---|---|
| 20 m, horizontal vrai | 0,10-0,20 m | 0,03 m | 0,90-1,01 m |
| 20 m, horizontal estimé | 0,23-0,30 m | 0,02-0,03 m | 0,60-0,63 m |
| 20 m, vertical vrai | 0,05-0,09 m | 0,02 m | 1,00-1,60 m |
| 2 m, horizontal vrai | 0,17-0,36 m (GPS) | 0,03-0,05 m (flux optique) | 0,17-3,02 m (flux optique) |
| Inclinaison moyenne, direction | 7-8°, vers 355-7° | 11,7°, vers 359-360° | 11,3-11,5°, vers 354-356° |
| Écart-type tangage / roulis | 1,1-2,4° | 0,1-0,3° | 1,6-3,2° |

- Le drone réel se situe entre les deux bancs. Sans vibration, la simulation est trop idéale
  (cause non cherchée). Avec la vibration utilisée dans les campagnes SITL (valeurs du test
  ArduPilot d'un quadricoptère de 180 mm), elle est environ 5 fois plus pessimiste en horizontal
  et 10 à 20 fois en vertical que le DJI mesuré. Les résultats SITL « sous vibration »
  correspondent donc à un cas sévère, pas au cas représentatif de ce drone.
- Le SITL penche vers 359-360° pour un vent venant du 0°. Cela confirme le raisonnement utilisé
  plus haut pour déduire la direction du vent de l'attitude du DJI. Les inclinaisons ne se
  comparent pas en valeur, car les masses et les traînées diffèrent.
- Sous vibration, comme pour le DJI à 2 m, le drone se déplace plus que ce qu'estime son filtre.
- À 2 m sous vibration (vol 548), la hauteur estimée dérive : le drone est descendu jusqu'à
  0,74 m du sol au palier 1, l'EKF a changé de cœur, puis le drone a tenu environ 1,5 m au lieu
  de 2 m. Rien de tel n'a été observé sur le DJI.

Limites : un vol par configuration ; appareils et estimateurs différents (EKF3 d'ArduPilot contre
celui de DJI), donc comparaison en ordre de grandeur ; à 2 m, le SITL garde 5 m/s de vent, alors
que le DJI n'en ressentait presque plus.

## Écarts au plan

| Écart | Effet |
|---|---|
| Site différent de la pelouse prévue | aucun sur les verdicts |
| 2 batteries au lieu de 3 ; FE-04 et FE-05 sur B2 avec redécollages | aucun : B2 à 60 % au plus bas, au-dessus du seuil de 30 % |
| Configuration du drone non relevée | à relever lors de la prochaine séance |
| FE-01 : vidéo commencée vers le début du palier 1 | palier couvert sur 60 s après recalage |
| FE-03 palier 1 : manches touchées à la fin | palier non valide ; 2 paliers valides sur 3 |
| FE-05 : retour en marche arrière, ligne de 143 m, hauteur 44,6 m | EX-C05 non conclue |
| Journal 12-01-09 hors carnet | hors essai |

## Traçabilité

| Exigence | Essai | Résultat |
|---|---|---|
| EX-C01 | FE-01 | conforme |
| EX-C02 | FE-01 | conforme |
| EX-C03 | FE-03 | non vérifiable (vision non déclarée) |
| EX-C04 | FE-03 | non vérifiable (vision non déclarée) |
| EX-C05 | FE-05 | non conclue (retour non valide) |
| EX-C07 (Normal) | FE-02 | conforme |
| EX-C08 (Normal) | FE-02 | conforme |
| EX-C09 | FE-05 | relevée : 34,3° pour 35° annoncés |
| EX-U01 | FE-04 | conforme |
| EX-U05 | analyse | conforme sur la campagne (7 / 7) |

## Pour la campagne suivante

- FE-05 : aller-retour en marche avant, sur une ligne d'au moins 200 m.
- FE-03 : la vision ne s'isole pas avec un bon GPS. Il faut chercher dans le manuel (S2) un
  réglage qui la force, ou déclarer EX-C03 et EX-C04 hors périmètre.
- Lester les cibles au sol.
- EX-U05 : préciser « position présente dès le fix GPS ».
- Relever la configuration du drone avant le premier vol.
