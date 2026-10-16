"""Détecteur à seuil sur les innovations, évalué en validation croisée « un vol mis de côté ».

Usage : python scripts/detecteur_seuil.py <dossier_jeu_donnees> [facteur] [persistance]
Sans facteur ni persistance : balaye plusieurs réglages et affiche un tableau de synthèse.
Avec : affiche le détail vol par vol pour ce réglage.

Règle : alarme si au moins un canal (SV, SP, SM) dépasse son seuil pendant `persistance`
échantillons consécutifs (10 Hz), ou si le GPS n'a pas de fix 3D (gps_fix < 3) pendant la même
durée. Seuil d'un canal = facteur × maximum nominal du canal. Le détail vol par vol donne aussi
le délai sans la règle GPS (innovations seules), pour comparaison.
Calibration : lignes « nominal » de la phase cercle, sans les 10 premières secondes, des
AUTRES vols que celui évalué (validation croisée), pour ne pas mesurer les fausses alarmes
sur les données qui ont fixé le seuil.
Métriques (phase cercle uniquement) : délai de détection après l'injection, canal qui détecte
en premier, nombre de fausses alarmes pendant le nominal, et durée d'« état dégradé » après le
retrait (alarme active alors que le capteur est redevenu sain : navigation en récupération,
compté à part et non comme fausse alarme), avec l'indication si l'alarme est encore active à
la fin de l'observation. Pour comparaison : délai auquel l'EKF atteint sa propre porte
(innovation ≥ 1, mesure rejetée).
"""
import glob
import os
import sys
import pandas as pd

CANAUX = ["SV", "SP", "SM"]
DEBUT_CALIBRATION = 10.0   # s après l'entrée en CIRCLE (transition de mode écartée)
FACTEURS = [1.5, 2, 3, 5]
PERSISTANCES = [1, 5, 10]
FIX_3D = 3                  # gps_fix < 3 : pas de fix 3D


def charger(dossier):
    fichiers = sorted(glob.glob(os.path.join(dossier, "log_*.csv")))
    if not fichiers:
        sys.exit(f"Aucun CSV dans {dossier}")
    return {int(os.path.basename(f)[4:12]): pd.read_csv(f) for f in fichiers}


def lignes_calibration(df):
    return df[(df.phase == "cercle") & (df.etiquette == "nominal") & (df.t_cercle_s >= DEBUT_CALIBRATION)]


def seuils(vols, exclu, facteur):
    nominal = pd.concat([lignes_calibration(df) for n, df in vols.items() if n != exclu])
    return {c: facteur * nominal[c].max() for c in CANAUX}


def persistant(depasse, persistance):
    """Vrai à l'instant k si le dépassement dure depuis `persistance` échantillons."""
    return depasse.rolling(persistance, min_periods=persistance).sum().eq(persistance)


def evaluer_vol(df, seuil, persistance, regle_gps=True):
    cercle = df[df.phase == "cercle"].reset_index(drop=True)
    par_canal = {c: persistant(cercle[c] > seuil[c], persistance) for c in CANAUX}
    if regle_gps:
        # Pas de fix 3D : le GPS s'annonce lui-même en panne, sans attendre les innovations
        par_canal["GPS"] = persistant(cercle.gps_fix.fillna(0) < FIX_3D, persistance)
    alarme = pd.concat(par_canal.values(), axis=1).any(axis=1)
    fronts = alarme & ~alarme.shift(1, fill_value=False)   # début de chaque alarme

    nominal = (cercle.etiquette == "nominal") & (cercle.t_cercle_s >= DEBUT_CALIBRATION)
    res = {"fa_nominal": int((fronts & nominal).sum()),
           "duree_nominal_s": nominal.sum() / 10}

    panne = cercle.etiquette == "panne"
    if panne.any():
        t_inj = cercle.loc[panne, "t_cercle_s"].iloc[0]
        apres_inj = cercle.t_cercle_s >= t_inj
        if (alarme & apres_inj).any():
            k = (alarme & apres_inj).idxmax()
            res["delai_s"] = cercle.t_cercle_s[k] - t_inj
            res["pendant_panne"] = bool(panne[k])
            res["canal"] = "+".join(c for c in par_canal if par_canal[c][k])
        porte = (cercle[CANAUX].max(axis=1) >= 1.0) & apres_inj
        res["delai_ekf_s"] = cercle.t_cercle_s[porte.idxmax()] - t_inj if porte.any() else None
        # Après le retrait, une alarme active n'est pas une fausse alarme mais un « état dégradé »
        # (navigation en récupération, choix du 2026-10-16) : on mesure sa durée à part
        retrait = pd.to_numeric(cercle.t_depuis_retrait_s, errors="coerce")
        apres = retrait >= 0
        res["degrade_s"] = (alarme & apres).sum() / 10
        res["observation_s"] = apres.sum() / 10
        res["encore_actif"] = bool(alarme[apres].iloc[-1]) if apres.any() else False
    return res


def fmt(x, unite=" s"):
    return "—" if x is None or (isinstance(x, float) and pd.isna(x)) else f"{x:.1f}{unite}"


def detail(vols, facteur, persistance):
    print(f"Réglage : seuil = {facteur} × max nominal, persistance {persistance} échantillon(s) "
          f"({persistance / 10:.1f} s)\n")
    print(f"{'log':>4} {'panne':<10} {'seuils SV/SP/SM':<17} {'innov. seules':>13} {'délai':>8} {'canal':<9} "
          f"{'EKF ≥ 1':>8} {'FA nom.':>8} {'état dégradé après retrait':>27}")
    for n, df in vols.items():
        s = seuils(vols, n, facteur)
        r = evaluer_vol(df, s, persistance)
        sans_gps = evaluer_vol(df, s, persistance, regle_gps=False).get("delai_s")
        lignes_panne = df[df.etiquette == "panne"]
        panne = "nominal" if lignes_panne.empty else \
            f"{lignes_panne.type_panne.iloc[0]} {'' if pd.isna(lignes_panne.amplitude.iloc[0]) else lignes_panne.amplitude.iloc[0]}".strip()
        delai = fmt(r.get("delai_s")) + ("" if r.get("pendant_panne", True) else " (après retrait)")
        print(f"{n:>4} {panne:<10} {'/'.join(f'{s[c]:.3f}' for c in CANAUX):<17} {fmt(sans_gps):>13} {delai:>8} "
              f"{r.get('canal', '—'):<9} {fmt(r.get('delai_ekf_s')):>8} {r['fa_nominal']:>8} "
              f"{degrade(r):>27}")


def degrade(r):
    if "degrade_s" not in r:
        return "—"
    fin = ", encore actif à la fin" if r["encore_actif"] else ""
    return f"{r['degrade_s']:.1f} s sur {r['observation_s']:.0f} s{fin}"


def balayage(vols):
    print(f"{'facteur':>7} {'persist.':>8} {'détectées':>10} {'délai max':>10} "
          f"{'FA nominal':>11} {'état dégradé total':>19}")
    for facteur in FACTEURS:
        for persistance in PERSISTANCES:
            resultats = [evaluer_vol(df, seuils(vols, n, facteur), persistance) for n, df in vols.items()]
            avec_panne = [r for r in resultats if "degrade_s" in r]
            detectees = [r for r in avec_panne if r.get("pendant_panne")]
            delai_max = max((r["delai_s"] for r in detectees), default=None)
            print(f"{facteur:>7} {persistance:>8} {len(detectees):>5} / {len(avec_panne):<3} "
                  f"{fmt(delai_max):>10} {sum(r['fa_nominal'] for r in resultats):>11} "
                  f"{fmt(sum(r['degrade_s'] for r in avec_panne)):>19}")
    duree = sum(evaluer_vol(df, seuils(vols, n, 2), 1)["duree_nominal_s"] for n, df in vols.items())
    print(f"\nDurée nominale évaluée (cercle, hors 10 premières s) : {duree:.0f} s sur {len(vols)} vols.")


if __name__ == "__main__":
    if len(sys.argv) not in (2, 4):
        sys.exit(__doc__)
    vols = charger(sys.argv[1])
    if len(sys.argv) == 4:
        detail(vols, float(sys.argv[2]), int(sys.argv[3]))
    else:
        balayage(vols)
