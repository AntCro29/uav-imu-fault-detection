# Exigences

Version du 2026-11-09, validée par Antoine (critères d'acceptation dans `plan_essai.md`).

## Sources

| Réf. | Document | Statut |
|---|---|---|
| S1 | Fiche technique DJI Lito X1, reprise par DrDrone.ca (« DJI Lito X1 Technical Specifications ») | source secondaire : valeurs à confirmer sur la documentation officielle DJI |
| S2 | Manuel utilisateur DJI Lito X1 | à obtenir |
| S3 | Réglementation applicable sur le lieu d'essai (FAA, règles locales) | à établir pour le lieu retenu |

## Méthodes de vérification

- **Essai** : vol dédié, selon une fiche d'essai, critère fixé avant le vol.
- **Analyse** : calcul sur des journaux de vol existants ou d'essai, sans vol dédié.
- **Hors périmètre** : non vérifiée dans ce dossier, avec la raison.

Les 18 vols enregistrés avant ce dossier n'ont pas de protocole : ils servent à mettre au point
l'analyse et ne valident aucune exigence de performance (seulement EX-U05, qui porte sur les
journaux eux-mêmes).

## Exigences constructeur

Valeurs annoncées par DJI (S1). Les conditions de mesure sont celles des notes de la fiche.

| ID | Exigence | Valeur annoncée | Conditions annoncées | Vérification |
|---|---|---|---|---|
| EX-C01 | Précision du stationnaire horizontale, positionnement satellite | ±1,5 m | non précisées | Essai |
| EX-C02 | Précision du stationnaire verticale, positionnement satellite | ±0,5 m | non précisées | Essai |
| EX-C03 | Précision du stationnaire horizontale, positionnement par vision | ±0,3 m | surface texturée, éclairage > 5 lux | Essai |
| EX-C04 | Précision du stationnaire verticale, positionnement par vision | ±0,1 m | surface texturée, éclairage > 5 lux | Essai |
| EX-C05 | Vitesse horizontale maximale, mode Normal | 12 m/s | soufflerie sans vent, niveau de la mer | Essai |
| EX-C06 | Vitesse horizontale maximale, mode Sport | 18 m/s | soufflerie sans vent, niveau de la mer | Essai |
| EX-C07 | Vitesse de montée maximale (Cine / Normal / Sport) | 3 / 5 / 7 m/s | non précisées | Essai |
| EX-C08 | Vitesse de descente maximale (Cine / Normal / Sport) | 3 / 5 / 7 m/s | non précisées | Essai |
| EX-C09 | Inclinaison maximale | 35° | non précisées | Analyse (pendant EX-C05 et EX-C06) |
| EX-C10 | Autonomie maximale, batterie standard | 36 min | niveau de la mer, vol en avant à 21,6 km/h constants, évitement d'obstacles sur « Frein », caméra 1080p/24 sans enregistrement, jusqu'à batterie vide | Hors périmètre en l'état : conditions non reproductibles (vol rectiligne de 36 min à vitesse constante, batterie vidée) ; remplacée par EX-U04 |
| EX-C11 | Résistance au vent | 10,7 m/s | non précisées | Hors périmètre : essai risqué pour le drone ; le vent rencontré pendant les essais sera mesuré et rapporté |
| EX-C12 | Portée de mesure du capteur infrarouge vers le bas | 0,3 à 8 m | réflectivité > 10 % | Analyse (hauteur `vpsHeight` du journal) |
| EX-C13 | Altitude maximale de décollage, température d'utilisation, distance maximale, détection d'obstacles | voir S1 | — | Hors périmètre : moyens ou risques hors de portée de ce dossier |

Points à éclaircir avant de fixer les critères :

- **EX-C01 à EX-C04** : la fiche ne dit pas quelle statistique est garantie (écart maximal,
  95 % du temps, écart-type…). Le critère retenu sera écrit dans le plan d'essai, avant les vols.
- **EX-C01, EX-C03** : le journal donne la position *estimée* par le drone. Une précision
  annoncée porte sur la position *réelle*. La mesure demande un moyen externe (repère au sol
  filmé par la caméra pointée vers le bas).
- **EX-C12** : sur le vol du 2026-11-06, `vpsHeight` plafonne à 9,0 m, au-delà des 8 m annoncés
  pour l'infrarouge. Le champ peut venir d'un autre capteur (vision) : à comprendre avant l'essai.

## Exigences d'usage

Comportements attendus que la fiche technique ne chiffre pas. Les critères sont à fixer avant
les essais ; aucune valeur n'est retenue à ce stade.

| ID | Exigence | Critère | Vérification |
|---|---|---|---|
| EX-U01 | Sur demande de retour au départ, le drone revient et se pose près du point de décollage | distance de pose au repère de décollage ≤ 1,5 m sur chaque retour (validé le 2026-11-09, voir plan d'essai) | Essai (mètre ruban + journal) |
| EX-U02 | En cas de perte de liaison avec la radiocommande, le drone applique l'action prévue par son réglage (retour au départ par défaut, à confirmer dans S2) | action déclenchée et délai : **à fixer** | Essai, à basse hauteur en terrain dégagé, après les autres essais |
| EX-U03 | Un même trajet, répété, donne des trajectoires proches | dispersion entre passages : **à fixer** ; mode de vol permettant un trajet reproductible : à identifier dans S2 | Essai |
| EX-U04 | Autonomie en stationnaire, batterie standard, de 100 % au seuil d'alerte de batterie faible | durée : **à mesurer**, comparée à l'autonomie annoncée à titre indicatif | Essai |
| EX-U05 | Chaque vol produit un journal complet et décodable : 10 Hz sans trou, attitude, vitesses, position et batterie présentes du décollage à l'arrêt des moteurs | 100 % des vols | Analyse (vérifiable dès maintenant sur les 18 vols existants) |

## Traçabilité

La matrice exigence → essai → résultat sera tenue dans le plan d'essai puis dans le rapport.
