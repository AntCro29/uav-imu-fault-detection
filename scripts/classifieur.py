"""Classification de la famille d'une panne, 3 s après la première alarme du détecteur.

Usage : python scripts/classifieur.py <dossier_jeu_donnees> <dernier_log_apprentissage_detecteur | roles.csv>
                                      [--test <dossier_test>]
Les logs ≤ dernier_log_apprentissage_detecteur (ou les logs « apprentissage » du fichier de rôles)
servent à entraîner l'Isolation Forest du détecteur (comme comparer_detecteurs.py) ; tous les vols
avec panne sont ensuite classés.

Déclenchement : première alarme du détecteur combiné (Isolation Forest OU seuil adaptatif k = 6,
règle GPS comprise) pendant la panne. Une panne non détectée n'est pas classée.
Familles : accéléromètre (acc, derive, bloque), gyroscope (gyr, bruit_gyr), GPS (gps, jam, leurre,
leurre_rampe), magnétomètre (mag).
Variables, à l'instant de l'alarme k (10 Hz) :
  - pour SV, SP, SH, SM : max et moyenne sur les 3 s qui suivent (échantillons k à k + 29),
    moyenne sur les 30 s qui précèdent, décalées de 2 s (k − 320 à k − 21 : niveau de fond du vent) ;
  - fix et nombre de satellites GPS les plus bas sur les 3 s qui suivent ;
  - canaux de l'alarme à l'instant k (ML, SV, SP, SM, GPS), en 0 / 1.
Deux classifieurs, évalués en laissant de côté un vol à la fois :
  - règles écrites à la main (référence) : GPS si le fix tombe sous 3D ; sinon magnétomètre si
    max SM > max SV ; sinon accéléromètre (ne prédit jamais le gyroscope) ;
  - forêt aléatoire (200 arbres, graine 0, classes pondérées pour compenser leur déséquilibre).
Réglages figés le 2026-10-25 avant tout calcul.
Avec --test <dossier_test> : la forêt est entraînée sur toutes les pannes classées du premier
dossier, puis classe les pannes du dossier de test (même détecteur, entraîné sur le premier).
"""
import os
import sys
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import detecteur_seuil as ds
import detecteur_adaptatif as da
import detecteur_ml as ml
import detecteur_ae as ae

FAMILLES = {"acc": "accéléro", "derive": "accéléro", "bloque": "accéléro",
            "gyr": "gyro", "bruit_gyr": "gyro",
            "gps": "GPS", "jam": "GPS", "leurre": "GPS", "leurre_rampe": "GPS",
            "mag": "magnéto"}
ORDRE = ["accéléro", "gyro", "GPS", "magnéto"]
INNOVATIONS = ["SV", "SP", "SH", "SM"]
APRES = 30       # échantillons (3 s) après l'alarme
AVANT = 300      # échantillons (30 s) avant l'alarme
RETARD = 20      # échantillons (2 s)
N_ARBRES = 200
GRAINE = 0


def variables(cercle, par_canal, k):
    apres = cercle.iloc[k:k + APRES]
    avant = cercle.iloc[max(0, k - RETARD - AVANT):k - RETARD]
    v = {}
    for c in INNOVATIONS:
        v[f"{c}_max"] = apres[c].max()
        v[f"{c}_moy"] = apres[c].mean()
        v[f"{c}_fond"] = avant[c].mean()
    v["fix_min"] = apres.gps_fix.fillna(0).min()
    v["nsats_min"] = apres.gps_nsats.fillna(0).min()
    for nom, a in par_canal.items():
        v[f"alarme_{nom}"] = int(a[k])
    return v


def regles(v):
    if v["fix_min"] < ds.FIX_3D:
        return "GPS"
    return "magnéto" if v["SM_max"] > v["SV_max"] else "accéléro"


def matrice(vraies, predites):
    m = pd.crosstab(pd.Categorical(vraies, ORDRE), pd.Categorical(predites, ORDRE),
                    rownames=["vraie"], colnames=["prédite"], dropna=False)
    return m


def tableau(vols, modele, seuil):
    """Une ligne par vol avec panne détectée : variables à la première alarme pendant la panne."""
    lignes, manquees = [], []
    for n, df in vols.items():
        if not (df.etiquette == "panne").any():
            continue
        cercle = ml.cercle_de(df)
        par_canal = ml.alarmes(cercle, modele, seuil, combine=True)
        alarme = pd.concat(par_canal.values(), axis=1).any(axis=1)
        panne = cercle.etiquette == "panne"
        if not (alarme & panne).any():
            manquees.append(f"{n} ({da.nom_panne(df)})")
            continue
        k = (alarme & panne).idxmax()
        v = variables(cercle, par_canal, k)
        v.update(log=n, panne=da.nom_panne(df), famille=FAMILLES[cercle.type_panne[panne].iloc[0]],
                 delai_s=cercle.t_cercle_s[k] - cercle.t_cercle_s[panne].iloc[0])
        lignes.append(v)
    t = pd.DataFrame(lignes)
    t["regles"] = [regles(v) for v in t.to_dict("records")]
    return t, manquees


def entrees(t):
    return t.drop(columns=["log", "panne", "famille", "delai_s", "regles", "foret"], errors="ignore")


def nouvelle_foret():
    return RandomForestClassifier(n_estimators=N_ARBRES, random_state=GRAINE, class_weight="balanced")


def afficher(t, manquees):
    print(f"{len(t)} pannes classées ; non détectées donc non classées : {', '.join(manquees) or 'aucune'}\n")
    for nom in ("regles", "foret"):
        juste = (t[nom] == t.famille).sum()
        print(f"{'Règles écrites à la main' if nom == 'regles' else 'Forêt aléatoire'} : "
              f"{juste} / {len(t)} familles justes")
        print(matrice(t.famille, t[nom]).to_string(), "\n")
    erreurs = t[(t.regles != t.famille) | (t.foret != t.famille)]
    print("Vols mal classés (par l'un ou l'autre) :")
    print(erreurs[["log", "panne", "famille", "regles", "foret", "delai_s"]].to_string(index=False), "\n")


if __name__ == "__main__":
    if len(sys.argv) not in (3, 5) or (len(sys.argv) == 5 and sys.argv[3] != "--test"):
        sys.exit(__doc__)
    vols = ds.charger(sys.argv[1])
    if sys.argv[2].endswith(".csv"):
        appr = ae.lire_roles(sys.argv[2])["apprentissage"]
    else:
        appr = [n for n in vols if n <= int(sys.argv[2])]
    modele, seuil, _ = ml.entrainer(vols, appr)
    t, manquees = tableau(vols, modele, seuil)
    X = entrees(t)

    if len(sys.argv) == 5:
        # Test : forêt entraînée sur toutes les pannes du premier dossier, détecteur inchangé
        foret = nouvelle_foret().fit(X, t.famille)
        test, manquees_test = tableau(ds.charger(sys.argv[4]), modele, seuil)
        test["foret"] = foret.predict(entrees(test)) if len(test) else []
        print(f"Apprentissage : {len(t)} pannes de {sys.argv[1]} ; test : {sys.argv[4]}")
        afficher(test, manquees_test)
        sys.exit(0)

    t["foret"] = ""
    for i in range(len(t)):
        garde = np.arange(len(t)) != i
        t.loc[i, "foret"] = nouvelle_foret().fit(X[garde], t.famille[garde]).predict(X.iloc[[i]])[0]
    afficher(t, manquees)
    foret = nouvelle_foret().fit(X, t.famille)
    imp = pd.Series(foret.feature_importances_, index=X.columns).sort_values(ascending=False)
    print("Importance des variables (forêt entraînée sur toutes les pannes) :")
    print(imp.head(10).round(3).to_string())
