"""Détecteur par autoencodeur, entraîné uniquement sur des vols nominaux.

Usage : python scripts/detecteur_ae.py <dossier_jeu_donnees> <roles.csv> [--test]
roles.csv (colonnes log, role) donne le rôle de chaque log : apprentissage (entraînement du
réseau), validation (seuil du score), test et panne (évaluation). Sans --test, le script
s'arrête après la validation et n'ouvre aucun log de test.

Entrée : fenêtre des 3 dernières secondes (30 échantillons à 10 Hz) de SV, SP, SH, SM (cœur 0),
chaque canal divisé par l'écart-type de ses valeurs nominales d'apprentissage, soit 120 valeurs.
Le réseau (120 → 32 → 8 → 32 → 120, MLPRegressor de scikit-learn) apprend à recopier son entrée
en passant par un goulot de 8 neurones. Score = erreur quadratique moyenne de reconstruction de
la fenêtre qui se termine à l'instant t : faible sur ce qui ressemble au nominal appris, d'autant
plus grand que la fenêtre s'en écarte (pas de plafond, contrairement à l'Isolation Forest).
Seuil = plus haut score sur le nominal de validation × (1 + MARGE). Alarme si le score dépasse le
seuil pendant 0,5 s, ou si le GPS n'a pas de fix 3D (même règle que les autres détecteurs).
Réglages figés le 2026-10-23 avant tout calcul (fenêtre, goulot, marge, graine) ; les vols de
validation ne contiennent pas de panne et ne servent qu'au seuil.
"""
import os
import sys
import numpy as np
import pandas as pd
from sklearn.neural_network import MLPRegressor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import detecteur_seuil as ds
import detecteur_adaptatif as da

CANAUX = ["SV", "SP", "SH", "SM"]
FENETRE = 30            # échantillons (3 s)
COUCHES = (32, 8, 32)   # le goulot est la couche du milieu
PERSISTANCE = 5         # échantillons (0,5 s)
MARGE = 0.10            # seuil = 1,10 × plus haut score nominal de validation
GRAINE = 0              # poids initiaux tirés au hasard : graine fixée pour un résultat reproductible
ITERATIONS = 500


def lire_roles(chemin):
    roles = pd.read_csv(chemin)
    return {r: list(roles.log[roles.role == r]) for r in roles.role.unique()}


def cercle_de(df):
    return df[df.phase == "cercle"].reset_index(drop=True)


def fenetres(cercle, echelle):
    """Une ligne par instant : les FENETRE derniers échantillons de chaque canal (NaN au début)."""
    x = cercle[CANAUX].to_numpy() / echelle
    X = np.full((len(x), FENETRE * len(CANAUX)), np.nan)
    if len(x) >= FENETRE:
        v = np.lib.stride_tricks.sliding_window_view(x, FENETRE, axis=0)   # (n - F + 1, canaux, F)
        X[FENETRE - 1:] = v.reshape(len(v), -1)
    return X


def lignes_nominales(cercle):
    return ((cercle.etiquette == "nominal") & (cercle.t_cercle_s >= ds.DEBUT_CALIBRATION)).to_numpy()


def entrainer(vols, logs, graine=GRAINE):
    nominal = pd.concat([ds.lignes_calibration(vols[n]) for n in logs])
    echelle = nominal[CANAUX].std(ddof=0).to_numpy()
    X = []
    for n in logs:
        cercle = cercle_de(vols[n])
        F = fenetres(cercle, echelle)[lignes_nominales(cercle)]
        X.append(F[~np.isnan(F).any(axis=1)])
    X = np.concatenate(X)
    reseau = MLPRegressor(hidden_layer_sizes=COUCHES, max_iter=ITERATIONS, random_state=graine).fit(X, X)
    return {"reseau": reseau, "echelle": echelle}, len(X)


def scores(modele, cercle):
    F = fenetres(cercle, modele["echelle"])
    valide = ~np.isnan(F).any(axis=1)
    s = np.full(len(F), np.nan)
    if valide.any():
        s[valide] = ((modele["reseau"].predict(F[valide]) - F[valide]) ** 2).mean(axis=1)
    return pd.Series(s, index=cercle.index)


def max_nominal(modele, df):
    cercle = cercle_de(df)
    return scores(modele, cercle)[lignes_nominales(cercle)].max()


def fixer_seuil(modele, vols, logs):
    return max(max_nominal(modele, vols[n]) for n in logs) * (1 + MARGE)


def evaluer_vol(df, modele, seuil):
    cercle = cercle_de(df)
    par_canal = {"AE": ds.persistant(scores(modele, cercle) > seuil, PERSISTANCE),
                 "GPS": ds.persistant(cercle.gps_fix.fillna(0) < ds.FIX_3D, PERSISTANCE)}
    r = ds.mesurer(cercle, par_canal)
    panne = cercle.etiquette == "panne"
    if panne.any():
        alarme = pd.concat(par_canal.values(), axis=1).any(axis=1)
        r["couverture"] = alarme[panne].mean()
    return r


if __name__ == "__main__":
    if len(sys.argv) not in (3, 4) or (len(sys.argv) == 4 and sys.argv[3] != "--test"):
        sys.exit(__doc__)
    roles = lire_roles(sys.argv[2])
    a_lire = roles["apprentissage"] + roles["validation"]
    if len(sys.argv) == 4:
        a_lire += roles["test"] + roles["panne"]
    vols = {n: df for n, df in ds.charger(sys.argv[1]).items() if n in a_lire}
    modele, n_ech = entrainer(vols, roles["apprentissage"])
    reseau = modele["reseau"]
    print(f"Entraînement : {n_ech} fenêtres nominales ({n_ech / 10:.0f} s), {len(roles['apprentissage'])} logs ; "
          f"{reseau.n_iter_} itérations, erreur finale {reseau.loss_:.4f}")
    print("Écart-type nominal des canaux (normalisation) : "
          + ", ".join(f"{c} {e:.4f}" for c, e in zip(CANAUX, modele["echelle"])))
    print("Plus haut score sur le nominal d'apprentissage : "
          f"{max(max_nominal(modele, vols[n]) for n in roles['apprentissage']):.4f}")
    for n in roles["validation"]:
        print(f"  validation log {n} : plus haut score {max_nominal(modele, vols[n]):.4f}")
    seuil = fixer_seuil(modele, vols, roles["validation"])
    print(f"Seuil du score : {seuil:.4f}")
    if len(sys.argv) == 3:
        sys.exit(0)

    print(f"\n{'log':>4} {'panne':<14} {'délai':>8} {'canal':<6} {'couverture':>10} {'FA nom.':>8} "
          f"{'état dégradé après retrait':>27}")
    res = []
    for n in sorted(roles["test"] + roles["panne"]):
        r = evaluer_vol(vols[n], modele, seuil)
        res.append(r)
        if "couverture" in r:
            delai = ds.fmt(r.get("delai_s")) if r.get("pendant_panne") else "manqué"
            cols = f"{delai:>8} {r.get('canal', '—'):<6} {100 * r['couverture']:>9.0f} %"
        else:
            cols = f"{'—':>8} {'—':<6} {'—':>10}"
        print(f"{n:>4} {da.nom_panne(vols[n]):<14} {cols} {r['fa_nominal']:>8} {ds.degrade(r):>27}")
    avec_panne = [r for r in res if "degrade_s" in r]
    print(f"\n{sum(bool(r.get('pendant_panne')) for r in avec_panne)} / {len(avec_panne)} pannes détectées ; "
          f"{sum(r['fa_nominal'] for r in res)} fausse(s) alarme(s) sur "
          f"{sum(r['duree_nominal_s'] for r in res):.0f} s de nominal.")
