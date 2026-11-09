# Validation en vol d'un DJI Lito X1

Dossier de validation d'un drone grand public, conduit comme en entreprise : des **exigences**
tirées des performances annoncées par le constructeur, un **plan d'essai** dont les critères
d'acceptation sont fixés avant de voler, des **fiches d'essai** pas à pas, puis un **rapport** qui
confronte les mesures aux critères.

## Démarche

1. **Exigences** (`docs/exigences.md`) : performances annoncées par DJI, et exigences d'usage.
   Chaque exigence a un identifiant (EX-xx) et une source.
2. **Plan d'essai** (`docs/plan_essai.md`) : pour chaque exigence, l'essai qui la couvre, les
   moyens, les conditions et le critère d'acceptation.
3. **Fiches d'essai** (`docs/fiches/`) : préconditions, procédure, données enregistrées, critère,
   résultat.
4. **Analyse** (`scripts/`) : lecture des journaux de vol, calcul des indicateurs de chaque essai.
5. **Rapport** : résultats contre critères, matrice de traçabilité, écarts et limites.

## État actuel

- Aucun essai réalisé pour l'instant.
- 18 vols antérieurs, faits sans protocole, servent à découvrir le contenu des journaux et à
  mettre au point les scripts d'analyse. Ils ne valident aucune exigence.
- Les performances annoncées viennent pour l'instant d'une source secondaire (revendeur
  reprenant la fiche DJI) : à confirmer sur la documentation officielle.

## Contraintes

- **Réglementation** : les essais se feront sur un terrain autorisé. Les conditions
  réglementaires (espace aérien, autorisations, hauteur maximale de 120 m) sont des préconditions
  de chaque fiche d'essai.
- **Vérité terrain** : le journal DJI donne la position *estimée* par le drone, pas sa position
  vraie. Les essais de précision s'appuient sur des moyens externes (repère au sol filmé par la
  caméra, mètre ruban).
- **Données** : les journaux de vol (positions GPS, numéros de série) restent locaux et ne sont
  pas publiés (`data/` est exclu du dépôt).

## Outils

Les journaux DJI (format 14) sont chiffrés. Ils sont décodés en local avec
[dji-log-parser](https://github.com/lvauvillier/dji-log-parser) (licence MIT), qui obtient les
clés de déchiffrement auprès de DJI avec une clé de développeur personnelle. Le journal décodé
contient, à 10 Hz : attitude, vitesses, hauteurs, position GPS, nombre de satellites, mode de
vol, batterie, commandes de la radiocommande et alertes. Il ne contient ni les mesures brutes
des IMU ni l'état interne du filtre de navigation.

## Organisation

```
docs/      exigences, plan d'essai, fiches d'essai, rapport
scripts/   analyse des journaux
data/      journaux bruts et décodés (local uniquement)
```
