"""Détecteur à seuil auto-adaptatif : le seuil de chaque canal suit le niveau récent des innovations.

Usage : python scripts/detecteur_adaptatif.py <dossier_jeu_donnees> [k]
Affiche le détail vol par vol (k = 6 par défaut).

Règle : seuil d'un canal (SV, SP, SM) à l'instant t = max(plancher, moyenne + k × écart-type) des
innovations sur la fenêtre [t − retard − fenêtre, t − retard] (30 s, décalée de 2 s). Alarme si le
canal dépasse son seuil pendant `PERSISTANCE` échantillons consécutifs (10 Hz), ou si le GPS n'a
pas de fix 3D pendant la même durée (même règle que detecteur_seuil.py). Pendant une alarme, le
seuil est figé : la panne ne doit pas relever son propre seuil. Pas de décision avant que la
fenêtre soit remplie (32 premières secondes du cercle).
Intérêt : par vent fort, le nominal monte et le seuil suit ; par temps calme, il redescend au
plancher et le détecteur garde sa sensibilité. Aucune calibration sur des vols : seul k est réglé.
Réglages figés le 2026-10-16 sur les logs 19 à 49, avant le test sur les logs 50 à 72.
Métriques : celles de detecteur_seuil.py (fonction `mesurer`).
"""
import os
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import detecteur_seuil as ds

K = 6
FENETRE = 300      # échantillons (30 s à 10 Hz)
RETARD = 20        # échantillons (2 s) : la fenêtre ne contient pas les tout derniers instants
PLANCHER = 0.02    # innovations quantifiées à 0,01 : sans plancher, le seuil tomberait à 0 par temps calme
PERSISTANCE = 5    # échantillons (0,5 s)


class SeuilAdaptatif:
    """Seuil adaptatif d'un canal, un échantillon à la fois : sert après coup et en vol."""

    def __init__(self, k=K):
        self.k = k
        self.passe = []       # innovations reçues depuis l'entrée en cercle
        self.compte = 0       # échantillons consécutifs au-dessus du seuil
        self.fige = None
        self.seuil = None     # seuil appliqué au dernier échantillon (None : fenêtre pas remplie)

    def ajouter(self, x):
        """Ajoute une innovation, renvoie l'alarme (persistante) à cet instant."""
        self.passe.append(x)
        i = len(self.passe) - 1
        if self.fige is not None:
            s = self.fige
        elif i >= FENETRE + RETARD:
            w = np.asarray(self.passe[i - RETARD - FENETRE:i - RETARD])
            s = max(PLANCHER, w.mean() + self.k * w.std())
        else:
            s = None          # fenêtre pas encore remplie : pas de décision
        self.seuil = s
        self.compte = self.compte + 1 if s is not None and x > s else 0
        actif = self.compte >= PERSISTANCE
        if actif and self.fige is None:
            self.fige = s     # début d'alarme : on fige le seuil
        elif not actif and self.compte == 0:
            self.fige = None
        return actif


def alarme_canal(x, k):
    """Alarme (persistante) d'un canal, x étant le tableau numpy des innovations du cercle."""
    canal = SeuilAdaptatif(k)
    return pd.Series([canal.ajouter(v) for v in x])


def evaluer_vol(df, k=K):
    cercle = df[df.phase == "cercle"].reset_index(drop=True)
    par_canal = {c: alarme_canal(cercle[c].to_numpy(), k) for c in ds.CANAUX}
    par_canal["GPS"] = ds.persistant(cercle.gps_fix.fillna(0) < ds.FIX_3D, PERSISTANCE)
    return ds.mesurer(cercle, par_canal)


def nom_panne(df):
    p = df[df.etiquette == "panne"]
    if p.empty:
        return "nominal"
    a = p.amplitude.iloc[0]
    return f"{p.type_panne.iloc[0]} {'' if pd.isna(a) else a}".strip()


if __name__ == "__main__":
    if len(sys.argv) not in (2, 3):
        sys.exit(__doc__)
    vols = ds.charger(sys.argv[1])
    k = float(sys.argv[2]) if len(sys.argv) == 3 else K
    print(f"Réglage : k = {k:g}, fenêtre {FENETRE / 10:.0f} s décalée de {RETARD / 10:.0f} s, "
          f"plancher {PLANCHER}, persistance {PERSISTANCE / 10:.1f} s\n")
    print(f"{'log':>4} {'panne':<10} {'délai':>8} {'canal':<9} {'FA nom.':>8} {'état dégradé après retrait':>27}")
    resultats = {}
    for n, df in vols.items():
        r = resultats[n] = evaluer_vol(df, k)
        delai = ds.fmt(r.get("delai_s")) + ("" if r.get("pendant_panne", True) else " (après retrait)")
        print(f"{n:>4} {nom_panne(df):<10} {delai:>8} {r.get('canal', '—'):<9} {r['fa_nominal']:>8} "
              f"{ds.degrade(r):>27}")
    avec_panne = [r for r in resultats.values() if "degrade_s" in r]
    print(f"\n{sum(bool(r.get('pendant_panne')) for r in avec_panne)} / {len(avec_panne)} pannes détectées "
          f"pendant la panne ; {sum(r['fa_nominal'] for r in resultats.values())} fausse(s) alarme(s) sur "
          f"{sum(r['duree_nominal_s'] for r in resultats.values()):.0f} s de nominal.")
