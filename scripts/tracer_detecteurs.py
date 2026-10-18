"""Trace un vol avec ce que voient les quatre détecteurs : innovations, seuils, score ML et alarmes.

Usage : python scripts/tracer_detecteurs.py <dossier_jeu_donnees> <dernier_log_calibration> <log> <image.png> [titre]
Mêmes réglages que comparer_detecteurs.py : seuil fixe (2 × max nominal) calibré et Isolation
Forest entraîné sur les logs ≤ dernier_log_calibration. Panneaux : SV, SP, SM avec le seuil fixe
et le seuil adaptatif (k = 6) ; score d'anomalie de l'Isolation Forest et son seuil ; alarmes
des quatre détecteurs (fixe, adaptatif, Isolation Forest, ML + adaptatif). Zone rose : panne.
Exemple (figure du README, dérive de 0,5 m/s², vol 104) :
    python scripts/tracer_detecteurs.py data/jeu_test 49 118 docs/figures/test_derive_vol104.png
"""
import os
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import detecteur_seuil as ds
import detecteur_adaptatif as da
import detecteur_ml as ml
import comparer_detecteurs as cd

COUL = {"fixe": "#2a78d6", "adaptatif": "#eb6834", "isolation forest": "#1baf7a", "ML + adaptatif": "#eda100"}
ENCRE, GRILLE, ZONE_PANNE = "#333333", "#e6e6e6", "#f3d6d6"


def seuil_adaptatif(x, k=da.K):
    """Même boucle que da.alarme_canal, en gardant la valeur du seuil à chaque instant."""
    n = len(x)
    actif, seuil = np.zeros(n, dtype=bool), np.full(n, np.nan)
    compte, fige = 0, None
    for i in range(n):
        if fige is not None:
            s = fige
        elif i >= da.FENETRE + da.RETARD:
            w = x[i - da.RETARD - da.FENETRE:i - da.RETARD]
            s = max(da.PLANCHER, w.mean() + k * w.std())
        else:
            s = None
        if s is not None:
            seuil[i] = s
        compte = compte + 1 if s is not None and x[i] > s else 0
        actif[i] = compte >= da.PERSISTANCE
        if actif[i] and fige is None:
            fige = s
        elif not actif[i] and compte == 0:
            fige = None
    return seuil, pd.Series(actif)


def tracer(df, seuil_fixe, modele, seuil_ml, sortie, titre):
    c = ml.cercle_de(df)
    t = c.t_cercle_s
    gps = ds.persistant(c.gps_fix.fillna(0) < ds.FIX_3D, cd.PERSISTANCE)
    al_fixe = [ds.persistant(c[k] > seuil_fixe[k], cd.PERSISTANCE) for k in ds.CANAUX]
    sa, al_ad = {}, []
    for k in ds.CANAUX:
        sa[k], a = seuil_adaptatif(c[k].to_numpy())
        assert a.equals(da.alarme_canal(c[k].to_numpy(), da.K)), "seuil adaptatif non reproduit"
        al_ad.append(a)
    score = ml.scores(modele, c)
    alarmes = {"fixe": pd.concat(al_fixe + [gps], axis=1).any(axis=1),
               "adaptatif": pd.concat(al_ad + [gps], axis=1).any(axis=1),
               "isolation forest": ds.persistant(score > seuil_ml, ml.PERSISTANCE) | gps}
    alarmes["ML + adaptatif"] = alarmes["isolation forest"] | alarmes["adaptatif"]

    panne = c.etiquette == "panne"
    fig, ax = plt.subplots(5, 1, figsize=(12, 11), sharex=True,
                           gridspec_kw={"height_ratios": [1, 1, 1, 1, 0.8]})
    for a in ax:
        if panne.any():
            a.axvspan(t[panne].iloc[0], t[panne].iloc[-1], color=ZONE_PANNE, lw=0, zorder=0)
        a.grid(True, color=GRILLE, lw=0.6)
        a.set_axisbelow(True)
        for s in ("top", "right"):
            a.spines[s].set_visible(False)
    for a, k in zip(ax[:3], ds.CANAUX):
        a.plot(t, c[k], color=ENCRE, lw=1.0, label=f"{k} (innovation)")
        a.axhline(seuil_fixe[k], color=COUL["fixe"], lw=2, ls="--", label=f"seuil fixe {seuil_fixe[k]:.2f}")
        a.plot(t, sa[k], color=COUL["adaptatif"], lw=2, label="seuil adaptatif (k = 6)")
        a.set_ylim(0, min(max(np.nanmax(c[k]) * 1.1, seuil_fixe[k] * 1.3, 0.05), 1.2))
        a.set_ylabel(k)
        a.legend(loc="upper left", fontsize=8, frameon=False, ncol=3)
    ax[3].plot(t, score, color=COUL["isolation forest"], lw=1.2, label="score d'anomalie")
    ax[3].axhline(seuil_ml, color=ENCRE, lw=1.5, ls="--", label=f"seuil {seuil_ml:.3f}")
    ax[3].set_ylim(np.nanmin(score) - 0.02, max(np.nanmax(score), seuil_ml) + 0.08)
    ax[3].set_ylabel("score ML")
    ax[3].legend(loc="upper left", fontsize=8, frameon=False, ncol=2)
    noms = list(alarmes)
    for i, nm in enumerate(noms):
        y = len(noms) - 1 - i
        ax[4].fill_between(t, y - 0.35, y + 0.35, where=alarmes[nm].to_numpy(), color=COUL[nm],
                           lw=0, step="mid")
    ax[4].set_yticks(range(len(noms)))
    ax[4].set_yticklabels(noms[::-1])
    ax[4].set_ylim(-0.6, len(noms) - 0.4)
    ax[4].set_ylabel("alarme")
    ax[4].set_xlabel("temps depuis l'entrée en cercle (s)  —  zone rose : panne")
    fig.suptitle(titre, fontsize=12, x=0.01, ha="left")
    fig.tight_layout()
    fig.savefig(sortie, dpi=110)
    plt.close(fig)


if __name__ == "__main__":
    if len(sys.argv) not in (5, 6):
        sys.exit(__doc__)
    vols = ds.charger(sys.argv[1])
    dernier, log, sortie = int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
    calib = [n for n in vols if n <= dernier]
    nominal = pd.concat([ds.lignes_calibration(vols[n]) for n in calib])
    seuil_fixe = {c: cd.FACTEUR * nominal[c].max() for c in ds.CANAUX}
    modele, seuil_ml, _ = ml.entrainer(vols, calib)
    titre = sys.argv[5] if len(sys.argv) == 6 else f"Log {log} : {da.nom_panne(vols[log])}"
    tracer(vols[log], seuil_fixe, modele, seuil_ml, sortie, titre)
    print(sortie)
