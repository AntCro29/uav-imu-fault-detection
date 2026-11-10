# FE-03 — Stationnaire en positionnement par vision

**Exigences :** EX-C03 (horizontal ±0,3 m), EX-C04 (vertical ±0,1 m) · **Vol :** 2 · **Durée :** ≈ 5 min

## Préconditions

- Check-list avant vol faite, vent < 5 m/s, satellites ≥ 10.
- Pelouse texturée et bien éclairée (jour), cible au sol en place.
- Hauteur choisie : **2 m**, dans la portée des capteurs du dessous.

## Procédure

1. Décoller, se placer à 2 m à la verticale de la cible.
2. Caméra vers le bas, **lancer l'enregistrement vidéo**.
3. Palier 1 : relâcher les manches, **ne plus toucher la radiocommande pendant 60 s**. Noter
   l'heure de début.
4. Déplacer le drone de 1 m puis le ramener au-dessus de la cible.
5. Paliers 2 et 3 : refaire les étapes 3 et 4.
6. Arrêter la vidéo. Enchaîner sur FE-04 (premier retour au départ).

## Données

Journal de vol ; vidéo ; heures de début des paliers ; vent.

## Critère

Pour chaque palier : 95 % des échantillons à moins de 0,3 m (horizontal) et 0,1 m (vertical) de
la position moyenne du palier. Exigence satisfaite si les 3 paliers le sont.

**Validité :** satellites ≥ 10, `OSD.isVisionUsed` vrai, manches au neutre, mode Normal, pendant
tout le palier.

**Limite (vérifiée sur le vol du 2026-11-06) :** la latitude et la longitude du journal ont une
résolution très fine, suffisante pour 0,3 m. En revanche, la hauteur `OSD.height` n'est
enregistrée qu'**au dixième de mètre**, la même valeur que la tolérance verticale de ±0,1 m :
le critère vertical ne peut être jugé qu'à cette résolution près, et le verdict vertical sera
rapporté avec cette limite.

## Résultat

| Palier | Valide | Horizontal (95 %) | Vertical (95 %) | Verdict |
|---|---|---|---|---|
| 1 | | | | |
| 2 | | | | |
| 3 | | | | |
