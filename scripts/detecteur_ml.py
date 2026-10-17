"""Détecteur par Isolation Forest, entraîné uniquement sur des vols nominaux.

Usage : python scripts/detecteur_ml.py <dossier_jeu_donnees> <dernier_log_apprentissage>
Les lignes « nominal » du cercle (sans les 10 premières s) des logs ≤ dernier_log_apprentissage
servent à l'entraînement ; les logs suivants servent de test.

Variables d'entrée, pour chaque canal SV, SP, SM, calculées sur le passé uniquement :
valeur instantanée, moyenne et maximum sur 3 s, écart-type sur 30 s décalé de 2 s (niveau
d'agitation du moment, indicateur indirect du vent). Pas de décision tant que la fenêtre de
30 s n'est pas remplie (32 premières secondes du cercle).
Isolation Forest : des arbres découpent les données au hasard ; un point anormal est isolé en
peu de coupes. Score d'anomalie = opposé de `score_samples` (plus haut = plus anormal).
Alarme si le score dépasse le plus haut score vu sur le nominal d'apprentissage pendant
0,5 s, ou si le GPS n'a pas de fix 3D (même règle que les autres détecteurs).
Métriques : celles de detecteur_seuil.py (fonction `mesurer`), plus la part de la panne
pendant laquelle l'alarme est active.
"""
import os
import sys
import pandas as pd
from sklearn.ensemble import IsolationForest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import detecteur_seuil as ds
import detecteur_adaptatif as da

COURT = 30          # échantillons (3 s)
LONG = 300          # échantillons (30 s)
RETARD = 20         # échantillons (2 s)
PERSISTANCE = 5     # échantillons (0,5 s)
N_ARBRES = 200
GRAINE = 0          # forêt tirée au hasard : graine fixée pour un résultat reproductible


def caracteristiques(cercle):
    f = {}
    for c in ds.CANAUX:
        x = cercle[c]
        f[c] = x
        f[f"{c}_moy3"] = x.rolling(COURT, min_periods=COURT).mean()
        f[f"{c}_max3"] = x.rolling(COURT, min_periods=COURT).max()
        f[f"{c}_std30"] = x.shift(RETARD).rolling(LONG, min_periods=LONG).std(ddof=0)
    return pd.DataFrame(f)


def cercle_de(df):
    return df[df.phase == "cercle"].reset_index(drop=True)


def entrainer(vols, logs):
    X = []
    for n in logs:
        cercle = cercle_de(vols[n])
        nominal = (cercle.etiquette == "nominal") & (cercle.t_cercle_s >= ds.DEBUT_CALIBRATION)
        X.append(caracteristiques(cercle)[nominal])
    X = pd.concat(X).dropna()
    modele = IsolationForest(n_estimators=N_ARBRES, random_state=GRAINE).fit(X)
    seuil = (-modele.score_samples(X)).max()
    return modele, seuil, len(X)


def scores(modele, cercle):
    F = caracteristiques(cercle)
    valide = F.notna().all(axis=1)
    s = pd.Series(float("nan"), index=cercle.index)
    s[valide] = -modele.score_samples(F[valide])
    return s


def evaluer_vol(df, modele, seuil):
    cercle = cercle_de(df)
    par_canal = {"ML": ds.persistant(scores(modele, cercle) > seuil, PERSISTANCE),
                 "GPS": ds.persistant(cercle.gps_fix.fillna(0) < ds.FIX_3D, PERSISTANCE)}
    r = ds.mesurer(cercle, par_canal)
    panne = cercle.etiquette == "panne"
    if panne.any():
        alarme = pd.concat(par_canal.values(), axis=1).any(axis=1)
        r["couverture"] = alarme[panne].mean()
    return r


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    vols = ds.charger(sys.argv[1])
    dernier = int(sys.argv[2])
    appr = [n for n in vols if n <= dernier]
    test = [n for n in vols if n > dernier]
    modele, seuil, n_ech = entrainer(vols, appr)
    print(f"Entraînement : {n_ech} échantillons nominaux ({n_ech / 10:.0f} s), logs {min(appr)} à {max(appr)} ; "
          f"seuil du score {seuil:.3f}")
    print(f"Test : logs {min(test)} à {max(test)}\n")
    print(f"{'log':>4} {'panne':<10} {'délai':>8} {'canal':<6} {'couverture':>10} {'FA nom.':>8} "
          f"{'état dégradé après retrait':>27}")
    res = []
    for n in test:
        r = evaluer_vol(vols[n], modele, seuil)
        res.append(r)
        if "couverture" in r:
            delai = ds.fmt(r.get("delai_s")) if r.get("pendant_panne") else "manqué"
            cols = f"{delai:>8} {r.get('canal', '—'):<6} {100 * r['couverture']:>9.0f} %"
        else:
            cols = f"{'—':>8} {'—':<6} {'—':>10}"
        print(f"{n:>4} {da.nom_panne(vols[n]):<10} {cols} {r['fa_nominal']:>8} {ds.degrade(r):>27}")
    avec_panne = [r for r in res if "degrade_s" in r]
    print(f"\n{sum(bool(r.get('pendant_panne')) for r in avec_panne)} / {len(avec_panne)} pannes détectées ; "
          f"{sum(r['fa_nominal'] for r in res)} fausse(s) alarme(s) sur "
          f"{sum(r['duree_nominal_s'] for r in res):.0f} s de nominal.")
