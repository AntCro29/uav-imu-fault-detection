"""Compare la trace du détecteur en vol (vol_auto.py --detecteur) à l'analyse après coup du même vol.

Usage : python scripts/comparer_en_ligne.py <trace.csv> <dossier_jeu_donnees> <log> [fichier.joblib]
La trace est data/en_ligne_<date>.csv ; le CSV du log doit avoir été construit avant avec
construire_jeu_donnees.py. Détecteur : data/detecteur_en_ligne.joblib par défaut (celui du vol).
Vérifie la chaîne MAVLink, que le rejeu des CSV (detecteur_en_ligne.py rejouer) ne voit pas :
  - débit : intervalle entre deux EKF_STATUS_REPORT (10 Hz demandés) ;
  - horloge : la trace est datée par vol_auto.py, le log par le simulateur ; on cherche le
    décalage d'échantillons qui fait coïncider le plus de valeurs (SV, SP, SM) ;
  - valeurs : EKF_STATUS_REPORT vient du cœur principal, XKF4 du cœur 0 ;
  - alarmes : délai après injection et fausses alarmes (mêmes définitions que detecteur_seuil.mesurer).
Critère fixé avant les vols : mêmes pannes détectées, délais à ± 0,3 s, aucune fausse alarme.
"""
import os
import sys
import joblib
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import detecteur_seuil as ds
import detecteur_adaptatif as da
import detecteur_ml as ml
import detecteur_en_ligne as enligne

DEPOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DECALAGE_MAX = 30       # échantillons (3 s) explorés de part et d'autre
TOLERANCE_S = 0.3


def meilleur_decalage(trace, cercle):
    """Décalage d (trace[i] ↔ cercle[i + d]) qui maximise la part de triplets SV, SP, SM égaux."""
    a = trace[ds.CANAUX].to_numpy()
    b = cercle[ds.CANAUX].to_numpy()
    meilleur = (None, -1.0)
    for d in range(-DECALAGE_MAX, DECALAGE_MAX + 1):
        i0, j0 = max(0, -d), max(0, d)
        n = min(len(a) - i0, len(b) - j0)
        if n <= 0:
            continue
        part = np.mean(np.all(np.isclose(a[i0:i0 + n], b[j0:j0 + n]), axis=1))
        if part > meilleur[1]:
            meilleur = (d, part)
    return meilleur


def fronts(t, alarme, debut, fin):
    """Instants de début d'alarme compris entre debut et fin."""
    f = alarme & ~alarme.shift(1, fill_value=False)
    return t[f & (t >= debut) & (t < fin)].to_numpy()


def delai(t, alarme, t_inj):
    """Délai de la première alarme active après l'injection (0 si déjà active), None si aucune."""
    apres = alarme[t >= t_inj]
    return t[apres.idxmax()] - t_inj if apres.any() else None


def comparer(chemin_trace, dossier, log, fichier):
    p = joblib.load(fichier)
    trace = pd.read_csv(chemin_trace)
    for nm in enligne.NOMS:
        trace[nm] = trace[nm].astype(str).isin(["1", "True"])   # vol_auto.py écrit 0 / 1
    df = ds.charger(dossier)[log]
    cercle = ml.cercle_de(df)

    dt = np.diff(trace.t_cercle_s.to_numpy())
    print(f"Trace : {len(trace)} échantillons sur {trace.t_cercle_s.iloc[-1] - trace.t_cercle_s.iloc[0]:.1f} s ; "
          f"log : {len(cercle)} échantillons XKF4 en cercle")
    print(f"Débit : intervalle médian {np.median(dt) * 1000:.0f} ms, {np.mean((dt > 0.08) & (dt < 0.12)) * 100:.1f} % "
          f"entre 80 et 120 ms, plus long trou {dt.max() * 1000:.0f} ms")

    d, part = meilleur_decalage(trace, cercle)
    i0, j0 = max(0, -d), max(0, d)
    n = min(len(trace) - i0, len(cercle) - j0)
    ta = trace.iloc[i0:i0 + n].reset_index(drop=True)
    cb = cercle.iloc[j0:j0 + n].reset_index(drop=True)
    decalage_s = float(np.median(ta.t_cercle_s - cb.t_cercle_s))
    print(f"Alignement : décalage de {d} échantillon(s), horloge de la trace en avance de {decalage_s:+.2f} s "
          f"sur le log ; {part * 100:.1f} % des triplets SV, SP, SM identiques")
    for c in ds.CANAUX:
        ecart = (ta[c] - cb[c]).abs()
        print(f"  {c} : {np.mean(np.isclose(ta[c], cb[c])) * 100:.1f} % identiques, écart max {ecart.max():.2f}")

    # Alarmes après coup, et alarmes en vol ramenées à l'horloge du log
    apres = enligne.alarmes_apres_coup(df, p)
    t_log = cercle.t_cercle_s
    t_vol = trace.t_cercle_s - decalage_s
    panne = cercle.etiquette == "panne"
    t_inj = t_log[panne].iloc[0] if panne.any() else np.inf
    print(f"\n{'détecteur':<17} {'délai en vol':>13} {'délai après coup':>17} {'FA en vol':>10} {'FA après coup':>14}  critère")
    ok_total = True
    for nm in enligne.NOMS:
        series = ((t_vol, trace[nm]), (t_log, apres[nm]))
        delais = [delai(t, al, t_inj) for t, al in series]
        fa = [len(fronts(t, al, ds.DEBUT_CALIBRATION, t_inj)) for t, al in series]
        if np.isfinite(t_inj):
            meme = (delais[0] is None) == (delais[1] is None)
            ok = meme and (delais[0] is None or abs(delais[0] - delais[1]) <= TOLERANCE_S) and fa[0] == 0
        else:
            ok = fa[0] == 0
        ok_total &= ok
        txt = ["—" if not np.isfinite(t_inj) else ("manqué" if x is None else f"{x:.1f} s") for x in delais]
        print(f"{nm:<17} {txt[0]:>13} {txt[1]:>17} {fa[0]:>10} {fa[1]:>14}  {'OK' if ok else 'NON'}")
    print(f"\nCritère {'respecté' if ok_total else 'NON respecté'} pour le log {log} ({da.nom_panne(df)})")
    return ok_total


if __name__ == "__main__":
    if len(sys.argv) not in (4, 5):
        sys.exit(__doc__)
    fichier = sys.argv[4] if len(sys.argv) == 5 else os.path.join(DEPOT, "data", "detecteur_en_ligne.joblib")
    sys.exit(0 if comparer(sys.argv[1], sys.argv[2], int(sys.argv[3]), fichier) else 1)
