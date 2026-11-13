"""EX-U05 : chaque vol produit un journal complet et décodable (critère de docs/exigences.md).

Usage : python scripts/verifier_journal.py <journal.csv> [...]

Sur l'intervalle décollage → première confirmation d'atterrissage :
- aucun pas de `OSD.flyTime` supérieur à 0,2 s (un échantillon isolé manquant toléré) ;
- attitude, vitesses, position et batterie présentes sur tous les échantillons ;
- le journal atteint la confirmation d'atterrissage.
"""

import sys
from pathlib import Path

import pandas as pd

from charger_vol import charger

PAS_MAX_S = 0.2
COLONNES = ["OSD.pitch", "OSD.roll", "OSD.yaw", "OSD.xSpeed", "OSD.ySpeed", "OSD.zSpeed",
            "nord_m", "est_m", "OSD.height", "BATTERY.chargeLevel"]


def verifier(chemin):
    d = charger(chemin)
    en_vol = ~d["OSD.isOnGround"].astype(bool)
    i0 = en_vol.idxmax()
    atterri = d.index[(d["OSD.flycState"] == "ConfirmLanding") & (d.index > i0)]
    i1 = atterri[0] if len(atterri) else d.index[-1]
    s = d.loc[i0:i1]
    pas = s["OSD.flyTime"].diff().dropna()
    manquants = [c for c in COLONNES if s[c].isna().any()]
    ok = len(atterri) > 0 and (pas <= PAS_MAX_S + 1e-9).all() and not manquants
    return {
        "journal": Path(chemin).stem, "durée_s": round(s["t_s"].iloc[-1], 1),
        "pas_max_s": round(pas.max(), 1), "trous": int((pas > PAS_MAX_S + 1e-9).sum()),
        "confirmation_atterrissage": len(atterri) > 0,
        "colonnes_incomplètes": ", ".join(manquants), "conforme": ok,
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__.splitlines()[2])
    pd.set_option("display.width", 200)
    r = pd.DataFrame([verifier(c) for c in sys.argv[1:]])
    print(r.to_string(index=False))
    print(f"\nconformes : {r['conforme'].sum()} / {len(r)}")
