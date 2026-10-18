"""Les quatre détecteurs, échantillon par échantillon, pour tourner pendant le vol.

Usage :
  python scripts/detecteur_en_ligne.py preparer <dossier_jeu_donnees> <dernier_log_calibration> <fichier.joblib>
      Calibre le seuil fixe et entraîne l'Isolation Forest exactement comme comparer_detecteurs.py,
      puis enregistre seuils et modèle (vol_auto.py --detecteur <fichier.joblib> les charge).
  python scripts/detecteur_en_ligne.py rejouer <fichier.joblib> <dossier_jeu_donnees> [log ...]
      Fait passer les CSV un échantillon à la fois dans le détecteur en ligne et vérifie que ses
      alarmes sont identiques à celles de l'analyse après coup (tous les logs du dossier au-delà du
      dernier log de calibration, ou ceux donnés).

Mêmes règles que l'analyse après coup, sans copie : seuil adaptatif par da.SeuilAdaptatif,
variables de l'Isolation Forest par ml.caracteristiques sur les 32 dernières secondes.
Détecteurs : fixe, adaptatif (k = 6), isolation forest, ML + adaptatif ; chacun avec la règle GPS.
En vol, les innovations arrivent par EKF_STATUS_REPORT (mêmes valeurs que XKF4, vérifié dans le
code d'ArduPilot, mais du cœur principal et non arrondies) : `quantifier` les tronque au
centième comme le log.
"""
import os
import sys
from collections import deque
import joblib
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import detecteur_seuil as ds
import detecteur_adaptatif as da
import detecteur_ml as ml
import comparer_detecteurs as cd

NOMS = ["fixe", "adaptatif", "isolation forest", "ML + adaptatif"]


def quantifier(v):
    """Troncature au centième, comme XKF4 : (int16_t)(100 * valeur) (AP_NavEKF3_Logging.cpp:168-171)."""
    return int(100 * v) / 100


class Persistance:
    """Vrai quand la condition est vraie depuis `n` échantillons consécutifs."""

    def __init__(self, n):
        self.n, self.compte = n, 0

    def ajouter(self, condition):
        self.compte = self.compte + 1 if condition else 0
        return self.compte >= self.n


class DetecteurEnLigne:
    def __init__(self, seuil_fixe, modele, seuil_ml):
        self.seuil_fixe, self.modele, self.seuil_ml = seuil_fixe, modele, seuil_ml
        self.fixe = {c: Persistance(cd.PERSISTANCE) for c in ds.CANAUX}
        self.adaptatif = {c: da.SeuilAdaptatif(da.K) for c in ds.CANAUX}
        self.ml = Persistance(ml.PERSISTANCE)
        self.gps = Persistance(cd.PERSISTANCE)
        self.recent = deque(maxlen=ml.LONG + ml.RETARD)   # assez pour l'écart-type 30 s décalé de 2 s
        self.score = np.nan

    def ajouter(self, sv, sp, sm, gps_fix):
        """Un échantillon (10 Hz) ; renvoie l'état d'alarme des quatre détecteurs."""
        x = {"SV": sv, "SP": sp, "SM": sm}
        self.recent.append(x)
        gps = self.gps.ajouter((gps_fix or 0) < ds.FIX_3D)
        # listes et non générateurs : any() s'arrêterait au premier canal en alarme, et les
        # canaux suivants ne verraient pas l'échantillon
        fixe = any([self.fixe[c].ajouter(x[c] > self.seuil_fixe[c]) for c in ds.CANAUX])
        adaptatif = any([self.adaptatif[c].ajouter(x[c]) for c in ds.CANAUX])
        self.score = np.nan
        if len(self.recent) == self.recent.maxlen:
            F = ml.caracteristiques(pd.DataFrame(list(self.recent))).iloc[[-1]]
            if F.notna().all(axis=1).iloc[0]:
                self.score = -self.modele.score_samples(F)[0]
        iso = self.ml.ajouter(self.score > self.seuil_ml)
        return {"fixe": fixe or gps, "adaptatif": adaptatif or gps,
                "isolation forest": iso or gps, "ML + adaptatif": iso or adaptatif or gps}


def charger(fichier):
    p = joblib.load(fichier)
    return DetecteurEnLigne(p["seuil_fixe"], p["modele"], p["seuil_ml"])


def preparer(dossier, dernier, sortie):
    vols = ds.charger(dossier)
    calib = [n for n in vols if n <= dernier]
    nominal = pd.concat([ds.lignes_calibration(vols[n]) for n in calib])
    seuil_fixe = {c: cd.FACTEUR * nominal[c].max() for c in ds.CANAUX}
    modele, seuil_ml, n_ech = ml.entrainer(vols, calib)
    joblib.dump({"seuil_fixe": seuil_fixe, "modele": modele, "seuil_ml": seuil_ml,
                 "logs_calibration": calib}, sortie)
    print(f"Calibration sur {len(calib)} logs ({min(calib)} à {max(calib)}) : seuils fixes "
          + ", ".join(f"{c} {v:.2f}" for c, v in seuil_fixe.items())
          + f" ; Isolation Forest sur {n_ech / 10:.0f} s, seuil du score {seuil_ml:.3f} -> {sortie}")


def alarmes_apres_coup(df, p):
    """Alarmes de l'analyse après coup, avec les fonctions de comparer_detecteurs.py."""
    c = ml.cercle_de(df)
    gps = ds.persistant(c.gps_fix.fillna(0) < ds.FIX_3D, cd.PERSISTANCE)
    fixe = pd.concat([ds.persistant(c[k] > p["seuil_fixe"][k], cd.PERSISTANCE) for k in ds.CANAUX], axis=1).any(axis=1)
    adapt = pd.concat([da.alarme_canal(c[k].to_numpy(), da.K) for k in ds.CANAUX], axis=1).any(axis=1)
    iso = ds.persistant(ml.scores(p["modele"], c) > p["seuil_ml"], ml.PERSISTANCE)
    return pd.DataFrame({"fixe": fixe | gps, "adaptatif": adapt | gps,
                         "isolation forest": iso | gps, "ML + adaptatif": iso | adapt | gps})


def rejouer(fichier, dossier, logs):
    p = joblib.load(fichier)
    vols = ds.charger(dossier)
    logs = logs or [n for n in vols if n > max(p["logs_calibration"])]
    ecarts = 0
    for n in logs:
        c = ml.cercle_de(vols[n])
        det = charger(fichier)
        en_ligne = pd.DataFrame([det.ajouter(r.SV, r.SP, r.SM, None if pd.isna(r.gps_fix) else r.gps_fix)
                                 for r in c.itertuples()])
        apres = alarmes_apres_coup(vols[n], p)
        diff = (en_ligne[NOMS] != apres[NOMS]).sum()
        ecarts += int(diff.sum())
        print(f"log {n:>4} : {len(c)} échantillons, écarts " + ", ".join(f"{k} {v}" for k, v in diff.items()))
    print(f"\n{len(logs)} logs rejoués : {ecarts} échantillon(s) différent(s) au total")
    return ecarts


if __name__ == "__main__":
    if len(sys.argv) >= 5 and sys.argv[1] == "preparer":
        preparer(sys.argv[2], int(sys.argv[3]), sys.argv[4])
    elif len(sys.argv) >= 4 and sys.argv[1] == "rejouer":
        sys.exit(1 if rejouer(sys.argv[2], sys.argv[3], [int(x) for x in sys.argv[4:]]) else 0)
    else:
        sys.exit(__doc__)
