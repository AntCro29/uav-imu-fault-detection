# FE-01 — Stationnaire en positionnement satellite

**Exigences :** EX-C01 (horizontal ±1,5 m), EX-C02 (vertical ±0,5 m) · **Vol :** 1 · **Durée :** ≈ 5 min

## Préconditions

- Check-list avant vol faite, vent < 5 m/s, satellites ≥ 10.
- Cible au sol posée au centre de la zone (la plus grande possible, au moins 1 m de côté).
- Hauteur choisie : **20 m**. Le drone doit naviguer sur les satellites et non sur la vision :
  vérifié dans le journal (`OSD.isVisionUsed` faux). Note du 2026-11-12 : sur les 18 vols
  antérieurs, la vision a été utilisée jusqu'à 29,9 m, mais seulement quand le GPS ne l'était pas.

## Procédure

1. Décoller, monter à 20 m, se placer à la verticale de la cible.
2. Pointer la caméra vers le bas (nacelle à −90° si possible) et **lancer l'enregistrement vidéo**.
3. Palier 1 : relâcher les deux manches, attendre **3 s** que le drone soit immobile, puis lancer
   le chrono : **ne plus toucher la radiocommande pendant 60 s**. Noter l'heure de début dans le
   carnet.
4. Déplacer le drone de 2 à 3 m puis le ramener au-dessus de la cible (paliers indépendants).
5. Paliers 2 et 3 : refaire les étapes 3 et 4.
6. Arrêter la vidéo. Enchaîner sur FE-02.

## Données

Journal de vol ; vidéo (nom du fichier dans le carnet) ; heures de début des paliers ; vent.

## Critère

Pour chaque palier : 95 % des échantillons à moins de 1,5 m (horizontal) et 0,5 m (vertical) de
la position moyenne du palier. Exigence satisfaite si les 3 paliers le sont.

**Validité :** satellites ≥ 10, `OSD.isVisionUsed` faux, manches au neutre (les 4 voies `RC.*`
exactement à 1024), mode Normal, pendant tout le palier.

## Résultat

| Palier | Valide | Horizontal (95 %) | Vertical (95 %) | Verdict |
|---|---|---|---|---|
| 1 | | | | |
| 2 | | | | |
| 3 | | | | |
