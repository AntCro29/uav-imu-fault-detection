# FE-05 — Vitesse maximale, mode Normal

**Exigences :** EX-C05 (12 m/s), EX-C09 (inclinaison 35°) · **Vol :** 3 · **Durée :** ≈ 2 min

**À faire seulement si** la pelouse offre une ligne droite dégagée d'au moins 200 m, que le
drone reste à vue sur toute sa longueur et que personne ne se trouve sous la trajectoire.

## Préconditions

- Mode Normal, 20 m de hauteur (plus haut si des obstacles l'exigent, jamais plus de 120 m).
- Direction de la ligne et direction du vent notées.

## Procédure

1. Se placer à une extrémité de la ligne, en stationnaire.
2. Aller : manche de tangage **à fond vers l'avant** jusqu'à ce que la vitesse se stabilise,
   puis relâcher **avant la fin de la ligne**.
3. Retour : même chose dans l'autre sens.
4. Noter les heures de l'aller et du retour.

## Données

Journal de vol (`OSD.xSpeed`, `OSD.ySpeed`, `OSD.pitch`, `OSD.roll`) ; heures ; vent.

## Critère

Vitesse horizontale maximale, moyenne de l'aller et du retour, entre 10,8 et 13,2 m/s
(±10 % de 12 m/s). Inclinaison maximale relevée et comparée à 35°.

**Validité :** mode Normal, manche de tangage en butée (`RC.elevator` exactement 364 ou 1684) ;
la phase mesurée est l'ensemble des échantillons consécutifs en butée.

## Résultat

| Passage | Vitesse max (m/s) | Inclinaison max (°) |
|---|---|---|
| Aller | | |
| Retour | | |
| **Moyenne / verdict** | | |
