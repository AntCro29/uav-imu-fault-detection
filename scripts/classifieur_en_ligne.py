"""Le classifieur de famille de panne, échantillon par échantillon, pour tourner pendant le vol.

Usage :
  python scripts/classifieur_en_ligne.py preparer <dossier_jeu_donnees> <dernier_log_apprentissage_detecteur | roles.csv> <fichier.joblib> [--ae]
      Entraîne la forêt aléatoire exactement comme classifieur.py ... --test (détecteur appris sur
      les logs ≤ dernier ou « apprentissage », forêt sur toutes les pannes détectées du dossier),
      puis l'enregistre. Avec --ae : déclencheur autoencodeur OU Isolation Forest (classifieur.py --ae).
  python scripts/classifieur_en_ligne.py rejouer <classifieur.joblib> <detecteur.joblib> <dossier_test> [log ...]
      Fait passer les CSV un échantillon à la fois dans le détecteur et le classifieur en ligne, et
      vérifie que la première classification pendant la panne a lieu au même échantillon, avec les
      mêmes variables et la même famille, que l'analyse après coup (classifieur.tableau). Liste
      aussi les classifications faites hors de la panne.

Déclenchement : début d'un épisode d'alarme du détecteur combiné (Isolation Forest OU seuil
adaptatif OU règle GPS, la colonne « ML + adaptatif » de detecteur_en_ligne.py ; avec --ae,
autoencodeur OU Isolation Forest OU règle GPS, la colonne « AE + ML »). Les canaux sont ceux des
variables alarme_* de la forêt. Avec --ae, un épisode qui commence avant DEBUT_CALIBRATION (10 s de
cercle) n'est pas classé (choix d'Antoine du 2026-11-04, après l'incident au décollage du log 379). La famille est
donnée 3 s plus tard (classifieur.APRES échantillons, l'échantillon de l'alarme compris), avec
classifieur.variables sur l'historique du cercle : même calcul qu'après coup, sans copie. Un
nouvel épisode n'est classé qu'après la fin de la classification en cours.
"""
import os
import sys
import joblib
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import detecteur_seuil as ds
import detecteur_ml as ml
import detecteur_en_ligne as dl
import classifieur as cl


class ClassifieurEnLigne:
    def __init__(self, foret, debut=0):
        self.foret = foret
        self.debut = debut        # premier échantillon du cercle où un épisode peut être classé
        # canaux du déclencheur, dans l'ordre des variables de la forêt (ML, GPS, SV, SP, SM ; ou ML, GPS, AE)
        self.canaux = [f[len("alarme_"):] for f in foret.feature_names_in_ if f.startswith("alarme_")]
        self.historique = []                              # échantillons du cercle (SV, SP, SH, SM, fix, nsats)
        self.par_canal = {c: [] for c in self.canaux}     # alarme de chaque canal, échantillon par échantillon
        self.precedente = False   # alarme combinée à l'échantillon précédent
        self.k = None             # échantillon de début de l'épisode en cours de classification

    def ajouter(self, sv, sp, sh, sm, gps_fix, gps_nsats, det):
        """Un échantillon, après det.ajouter(...) ; renvoie (famille, k, variables) quand une
        classification se termine, sinon None."""
        self.historique.append({"SV": sv, "SP": sp, "SH": sh, "SM": sm,
                                "gps_fix": np.nan if gps_fix is None else gps_fix,
                                "gps_nsats": np.nan if gps_nsats is None else gps_nsats})
        etat = {"ML": det.ml.compte >= det.ml.n, "GPS": det.alarme_gps, "AE": det.ae.compte >= det.ae.n,
                **det.canaux}
        for c in self.canaux:
            self.par_canal[c].append(bool(etat[c]))
        alarme = any(etat[c] for c in self.canaux)
        k = len(self.historique) - 1
        if alarme and not self.precedente and self.k is None and k >= self.debut:
            self.k = k
        self.precedente = alarme
        if self.k is not None and k - self.k + 1 >= cl.APRES:
            v = cl.variables(pd.DataFrame(self.historique), self.par_canal, self.k)
            X = pd.DataFrame([v])[self.foret.feature_names_in_]
            resultat = (self.foret.predict(X)[0], self.k, v)
            self.k = None
            return resultat
        return None

    def suspendre(self, depuis):
        """Oublie les échantillons à partir du numéro `depuis`, comme DetecteurEnLigne.suspendre."""
        del self.historique[depuis:]
        for c in self.canaux:
            del self.par_canal[c][depuis:]
        self.precedente, self.k = False, None


def charger(fichier):
    p = joblib.load(fichier)
    return ClassifieurEnLigne(p["foret"], p.get("debut", 0))


def preparer(dossier, calibration, sortie, avec_ae=False):
    vols = ds.charger(dossier)
    appr, modele, seuil, autoencodeur = cl.preparer_detecteur(vols, calibration, avec_ae)
    t, manquees = cl.tableau(vols, modele, seuil, autoencodeur)
    foret = cl.nouvelle_foret().fit(cl.entrees(t), t.famille)
    joblib.dump({"foret": foret, "logs_apprentissage_detecteur": appr, "seuil_ml": seuil,
                 "seuil_ae": autoencodeur[1] if autoencodeur else None, "pannes": t.log.tolist(),
                 "debut": round(ds.DEBUT_CALIBRATION * 10) if autoencodeur else 0}, sortie)
    print(f"Détecteur appris sur {len(appr)} logs ({min(appr)} à {max(appr)}), seuil du score {seuil:.3f}"
          + (f", seuil de l'autoencodeur {autoencodeur[1]:.4f}" if autoencodeur else "") + " ; "
          f"forêt sur {len(t)} pannes ({t.famille.value_counts().to_dict()}) ; "
          f"non détectées : {len(manquees)} -> {sortie}")


def rejouer(fichier, fichier_detecteur, dossier, logs):
    p, pd_ = joblib.load(fichier), joblib.load(fichier_detecteur)
    if (p["seuil_ml"] != pd_["seuil_ml"] or p["logs_apprentissage_detecteur"] != pd_["logs_calibration"]
            or p.get("seuil_ae") != pd_.get("seuil_ae")):
        sys.exit("Classifieur et détecteur appris sur des données différentes")
    autoencodeur = (pd_["modele_ae"], pd_["seuil_ae"]) if p.get("seuil_ae") is not None else None
    vols = ds.charger(dossier)
    logs = logs or sorted(vols)
    apres, _ = cl.tableau({n: vols[n] for n in logs}, pd_["modele"], pd_["seuil_ml"], autoencodeur)
    apres["foret"] = p["foret"].predict(cl.entrees(apres)) if len(apres) else []
    apres_coup = {r.log: r for r in apres.itertuples()}
    ecarts = 0
    for n in logs:
        c = ml.cercle_de(vols[n])
        det, clf = dl.charger(fichier_detecteur), charger(fichier)
        faites = []
        for r in c.itertuples():
            det.ajouter(r.SV, r.SP, r.SM, None if pd.isna(r.gps_fix) else r.gps_fix, r.SH)
            res = clf.ajouter(r.SV, r.SP, r.SH, r.SM, None if pd.isna(r.gps_fix) else r.gps_fix,
                              None if pd.isna(r.gps_nsats) else r.gps_nsats, det)
            if res:
                faites.append(res)
        panne = (c.etiquette == "panne").to_numpy()
        hors = [f"{f} à {c.t_cercle_s[k]:.1f} s ({c.etiquette[k]})" for f, k, _ in faites if not panne[k]]
        ligne = f"log {n:>4} ({cl.FAMILLES.get(c.type_panne[panne].iloc[0], '?') if panne.any() else 'nominal'})"
        if n in apres_coup:
            a = apres_coup[n]
            meme = [f for f in faites if panne[f[1]]]
            if not meme:
                ecarts += 1
                ligne += f" : ÉCART, après coup {a.foret} à +{a.delai_s:.1f} s, aucune classification en ligne pendant la panne"
            else:
                f, k, v = meme[0]
                delai = c.t_cercle_s[k] - c.t_cercle_s[panne].iloc[0]
                attendu = {col: getattr(a, col) for col in cl.entrees(apres).columns}
                diff = [col for col in attendu if not (attendu[col] == v[col] or (pd.isna(attendu[col]) and pd.isna(v[col])))]
                ok = f == a.foret and abs(delai - a.delai_s) < 1e-6 and not diff
                ecarts += not ok
                ligne += (f" : {'identique' if ok else 'ÉCART'}, en ligne {f} à +{delai:.1f} s, après coup {a.foret} "
                          f"à +{a.delai_s:.1f} s" + (f", variables différentes : {diff}" if diff else ""))
        elif panne.any():
            ligne += " : non détectée après coup" + (" ; ÉCART, classée en ligne" if any(panne[k] for _, k, _ in faites) else "")
            ecarts += any(panne[k] for _, k, _ in faites)
        ligne += f" ; hors panne : {', '.join(hors) or 'aucune'}"
        print(ligne, flush=True)
    print(f"\n{len(logs)} logs rejoués : {ecarts} écart(s)")
    return ecarts


if __name__ == "__main__":
    if len(sys.argv) in (5, 6) and sys.argv[1] == "preparer" and sys.argv[5:] in ([], ["--ae"]):
        preparer(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5:] == ["--ae"])
    elif len(sys.argv) >= 5 and sys.argv[1] == "rejouer":
        sys.exit(1 if rejouer(sys.argv[2], sys.argv[3], sys.argv[4], [int(x) for x in sys.argv[5:]]) else 0)
    else:
        sys.exit(__doc__)
