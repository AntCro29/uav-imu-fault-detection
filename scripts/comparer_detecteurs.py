"""Compare le seuil fixe, le seuil adaptatif et l'Isolation Forest sur des vols jamais vus.

Usage : python scripts/comparer_detecteurs.py <dossier_jeu_donnees> <dernier_log_calibration> [k ...]
Les logs dont le numéro est ≤ dernier_log_calibration servent à calibrer le seuil fixe (facteur 2 ×
max nominal, persistance 0,5 s, sans validation croisée) et à entraîner l'Isolation Forest
(detecteur_ml.py). Les logs suivants servent de test, pour tous les détecteurs. Le détecteur
adaptatif n'utilise pas de calibration (k = 6 par défaut, plusieurs valeurs possibles). Dernière
colonne : alarme si l'Isolation Forest OU le seuil adaptatif (k = 6) se déclenche.
Exemple (2026-10-17) : calibration sur les logs 19 à 49, test sur les logs 50 à 72 :
    python scripts/comparer_detecteurs.py data/jeu_donnees 49 4 6
Test final (2026-10-18) : dossier contenant les logs 19 à 49 et la campagne 79 à 138 :
    python scripts/comparer_detecteurs.py data/jeu_test 49
"""
import os
import sys
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import detecteur_seuil as ds
import detecteur_adaptatif as da
import detecteur_ml as ml

FACTEUR = 2
PERSISTANCE = 5


def delai(r):
    if not r.get("pendant_panne"):
        return "manqué"
    return f"{r['delai_s']:.1f} s ({r['canal']})"


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    vols = ds.charger(sys.argv[1])
    dernier = int(sys.argv[2])
    ks = [float(k) for k in sys.argv[3:]] or [da.K]
    calib = [n for n in vols if n <= dernier]
    test = [n for n in vols if n > dernier]
    if not calib or not test:
        sys.exit("Il faut au moins un log de calibration et un log de test.")

    nominal = pd.concat([ds.lignes_calibration(vols[n]) for n in calib])
    seuil = {c: FACTEUR * nominal[c].max() for c in ds.CANAUX}
    print(f"Calibration du seuil fixe sur {len(calib)} logs ({min(calib)} à {max(calib)}) : "
          + ", ".join(f"{c} {v:.2f}" for c, v in seuil.items()))
    modele, seuil_ml, n_ech = ml.entrainer(vols, calib)
    print(f"Entraînement de l'Isolation Forest : {n_ech / 10:.0f} s de nominal, seuil du score {seuil_ml:.3f}")
    print(f"Test sur {len(test)} logs ({min(test)} à {max(test)})\n")

    noms = ["fixe"] + [f"adaptatif k={k:g}" for k in ks] + ["isolation forest", "ML + adaptatif"]
    print(f"{'log':>4} {'panne':<10} " + " ".join(f"{nm:<16}" for nm in noms) + "  FA nominal")
    res = {nm: [] for nm in noms}
    for n in test:
        df = vols[n]
        rs = ([ds.evaluer_vol(df, seuil, PERSISTANCE)] + [da.evaluer_vol(df, k) for k in ks]
              + [ml.evaluer_vol(df, modele, seuil_ml), ml.evaluer_vol(df, modele, seuil_ml, combine=True)])
        for nm, r in zip(noms, rs):
            res[nm].append(r)
        panne = da.nom_panne(df)
        cols = ["—"] * len(rs) if panne == "nominal" else [delai(r) for r in rs]
        print(f"{n:>4} {panne:<10} " + " ".join(f"{c:<16}" for c in cols) + "  "
              + " / ".join(str(r["fa_nominal"]) for r in rs))

    duree = sum(r["duree_nominal_s"] for r in res["fixe"])
    print(f"\nSynthèse ({duree:.0f} s de nominal) :")
    for nm in noms:
        avec_panne = [r for r in res[nm] if "degrade_s" in r]
        print(f"  {nm:<16} : {sum(r['fa_nominal'] for r in res[nm])} fausse(s) alarme(s), "
              f"{sum(bool(r.get('pendant_panne')) for r in avec_panne)} / {len(avec_panne)} pannes détectées")
