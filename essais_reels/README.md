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

**Campagne 1 faite le 2026-11-13** (rapport : `docs/rapport_campagne1.md`) : 2 vols, 7 journaux,
critères figés avant les vols.

| Exigence | Verdict |
|---|---|
| EX-C01 / EX-C02 stationnaire satellite (±1,5 m / ±0,5 m) | conformes : dérive **réelle** mesurée sur la vidéo 0,10 à 0,20 m et 0,05 à 0,09 m |
| EX-C07 / EX-C08 montée et descente, mode Normal (5 m/s) | conformes : 5,0 à 5,1 m/s |
| EX-U01 retour au départ ≤ 1,5 m | conforme : 0,17 / 0,60 / 0,58 m au ruban |
| EX-U05 journal complet | conforme sur les 7 journaux de la campagne |
| EX-C03 / EX-C04 stationnaire par vision | non vérifiables : la vision n'est jamais déclarée avec un bon GPS |
| EX-C05 vitesse max (12 m/s) | non conclue : retour non valide ; aller à 11,9 m/s |
| EX-C09 inclinaison max (35°) | relevée : 34,3° |

Résultat principal : à l'échelle de 20 à 30 cm, la position estimée par le drone et sa position
réelle (vidéo) divergent, dans un sens ou dans l'autre selon les paliers. Un journal seul ne
suffit pas à valider la précision de positionnement.

Les 18 vols antérieurs, faits sans protocole, ont servi à mettre au point l'analyse. Ils ne
valident aucune exigence de performance. Les performances annoncées viennent d'une source
secondaire (revendeur reprenant la fiche DJI), encore à confirmer sur la documentation officielle.

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
data/      journaux bruts et décodés, carnet de terrain, vidéos (local uniquement)
```

Scripts (Python, `requirements.txt`) :

- `charger_vol.py` : lecture d'un journal décodé, temps depuis le décollage, position en mètres ;
  supprime les coordonnées absolues et les numéros de série ;
- `analyser_essais.py` : rattache le carnet aux journaux et applique les critères de FE-01 à FE-05 ;
- `analyser_video.py` : dérive réelle en stationnaire, mesurée sur la vidéo à partir de deux
  cibles au sol, comparée au journal ;
- `verifier_journal.py` : EX-U05.
