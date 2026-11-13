"""Analyse des essais de la campagne 1, critères de docs/plan_essai.md (figés avant les vols).

Usage : python scripts/analyser_essais.py <dossier_carnet> <date AAAA-MM-JJ> <journal.csv> [...]

- carnet : un JSON par ligne (export de la page de terrain) ; l'heure est l'heure locale ;
- décalage local → UTC : DECALAGE_UTC (UTC−5, heure du site en novembre) ;
- chaque essai est rattaché au journal dont l'intervalle d'heures UTC contient l'heure notée.

Positions : position *estimée* par le drone (journal), pas la position réelle.
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from charger_vol import charger

DECALAGE_UTC = pd.Timedelta(hours=5)
NEUTRE = 1024
BUTEES = (364, 1684)
MANCHES = ["RC.aileron", "RC.elevator", "RC.throttle", "RC.rudder"]
SAT_MIN = 10
DUREE_PALIER = pd.Timedelta(seconds=60)


def charger_carnet(dossier, date):
    lignes = [json.loads(p.read_text()) for p in Path(dossier).glob("*.json")]
    c = pd.DataFrame(lignes)
    heure = c["heure"].where(c["heure"].str.count(":") == 2, c["heure"] + ":00")
    c["t_utc"] = pd.to_datetime(date + " " + heure).dt.tz_localize("UTC") + DECALAGE_UTC
    return c.sort_values("t_utc").reset_index(drop=True)


def journal_de(journaux, t, dernier_commence=False):
    """Journal qui contient l'heure t ; avec dernier_commence, le dernier journal commencé
    avant t (FE-04 : la ligne du carnet peut être notée après la pose)."""
    for nom, d in journaux:
        if d["t_utc"].min() <= t <= d["t_utc"].max():
            return nom, d
    if dernier_commence:
        avant = [(nom, d) for nom, d in journaux if d["t_utc"].min() <= t]
        if avant:
            return max(avant, key=lambda j: j[1]["t_utc"].min())
    return None, None


def validite(f, vision_interdite):
    """Liste des conditions de validité non remplies sur la fenêtre f."""
    pb = []
    if f["OSD.gpsNum"].min() < SAT_MIN:
        pb.append(f"satellites min {f['OSD.gpsNum'].min()}")
    if (f["OSD.flycState"] != "GPSAtti").any():
        pb.append(f"mode {sorted(set(f['OSD.flycState']))}")
    if vision_interdite and f["OSD.isVisionUsed"].astype(bool).any():
        pb.append("vision utilisée")
    return pb


def palier(d, t0, seuil_h, seuil_v, vision_interdite):
    f = d[(d["t_utc"] >= t0) & (d["t_utc"] < t0 + DUREE_PALIER)]
    pb = validite(f, vision_interdite)
    for m in MANCHES:
        n = int((f[m] != NEUTRE).sum())
        if n:
            pb.append(f"{m} hors neutre sur {n} échantillons ({sorted(set(f[m]) - {NEUTRE})})")
    if f["t_utc"].max() - f["t_utc"].min() < DUREE_PALIER - pd.Timedelta(seconds=1):
        pb.append(f"fenêtre incomplète ({len(f)} échantillons)")
    ecart_h = np.hypot(f["nord_m"] - f["nord_m"].mean(), f["est_m"] - f["est_m"].mean())
    ecart_v = (f["OSD.height"] - f["OSD.height"].mean()).abs()
    p95_h, p95_v = ecart_h.quantile(0.95), ecart_v.quantile(0.95)
    return {
        "n": len(f),
        "hauteur_moy_m": round(f["OSD.height"].mean(), 1),
        "vps_moy_m": round(f["OSD.vpsHeight"].mean(), 1),
        "p95_h_m": round(p95_h, 2), "max_h_m": round(ecart_h.max(), 2),
        "p95_v_m": round(p95_v, 2), "max_v_m": round(ecart_v.max(), 2),
        "vision_%": round(100 * f["OSD.isVisionUsed"].astype(bool).mean()),
        "sat_min": int(f["OSD.gpsNum"].min()),
        "h_ok": p95_h <= seuil_h, "v_ok": p95_v <= seuil_v,
        "valide": not pb, "problemes": "; ".join(pb),
    }


def phases_butee(d, manche):
    """Groupes d'échantillons consécutifs où la manche est en butée (364 ou 1684)."""
    en_butee = d[manche].isin(BUTEES)
    groupe = (en_butee != en_butee.shift()).cumsum()
    phases = []
    for _, f in d[en_butee].groupby(groupe[en_butee]):
        if f[manche].nunique() == 1:
            phases.append(f)
    return phases


def fe02(d):
    lignes = []
    for f in phases_butee(d, "RC.throttle"):
        sens = "montée" if f["RC.throttle"].iloc[0] == 1684 else "descente"
        vz = f["OSD.zSpeed"].abs().max()
        lignes.append({
            "début (local)": (f["t_utc"].iloc[0] - DECALAGE_UTC).strftime("%H:%M:%S"),
            "sens": sens, "durée_s": round(len(f) / 10, 1),
            "h_début_m": f["OSD.height"].iloc[0], "h_fin_m": f["OSD.height"].iloc[-1],
            "vz_max_m_s": vz, "dans_4,5-5,5": 4.5 <= vz <= 5.5,
            "atterrissage": bool(f["OSD.isOnGround"].astype(bool).any()
                                 or (f["OSD.flycState"] != "GPSAtti").any()),
            "problemes": "; ".join(validite(f, False)),
        })
    return pd.DataFrame(lignes)


def fe05(d):
    lignes = []
    for f in phases_butee(d, "RC.elevator"):
        v = np.hypot(f["OSD.xSpeed"], f["OSD.ySpeed"])
        cap = np.degrees(np.arctan2(f["OSD.ySpeed"], f["OSD.xSpeed"])) % 360
        lignes.append({
            "début (local)": (f["t_utc"].iloc[0] - DECALAGE_UTC).strftime("%H:%M:%S"),
            "manche": int(f["RC.elevator"].iloc[0]), "durée_s": round(len(f) / 10, 1),
            "v_max_m_s": round(v.max(), 1),
            "route_à_v_max_deg": round(cap[v.idxmax()]),
            "tangage_max_deg": round(f["OSD.pitch"].abs().max(), 1),
            "roulis_max_deg": round(f["OSD.roll"].abs().max(), 1),
            "problemes": "; ".join(validite(f, False)),
        })
    return pd.DataFrame(lignes)


def fe04(d):
    """Écart entre le point de décollage et le point de pose, d'après le journal."""
    sol = d[d["OSD.isOnGround"].astype(bool)]
    fin = sol[sol.index > d[~d["OSD.isOnGround"].astype(bool)].index[0]]
    fin = fin if len(fin) else d.tail(1)
    return {
        "pose_journal_m": round(float(np.hypot(fin["nord_m"].iloc[-1], fin["est_m"].iloc[-1])), 2),
        "gohome": bool((d["OSD.flycState"] == "GoHome").any()),
        "etats": " → ".join(pd.unique(d["OSD.flycState"])),
    }


def main(dossier_carnet, date, chemins):
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 30)
    journaux = [(Path(c).stem, charger(c)) for c in chemins]
    carnet = charger_carnet(dossier_carnet, date)

    print("== Rattachement carnet → journal")
    for _, e in carnet.iterrows():
        nom, _ = journal_de(journaux, e["t_utc"])
        print(f"{e['heure']:>8}  vol {e['vol']} {e['batterie']}  {e['essai']:<16} "
              f"vent {e['vent']} m/s  mesure {e['mesure'] or '-':>5}  → {nom}")

    for essai, seuils, vision_interdite in (("FE-01", (1.5, 0.5), True),
                                            ("FE-03", (0.3, 0.1), False)):
        print(f"\n== {essai} (critère : 95 % à moins de {seuils[0]} m en horizontal, "
              f"{seuils[1]} m en vertical, de la position moyenne du palier)")
        lignes = []
        for _, e in carnet[carnet["essai"].str.startswith(essai)].iterrows():
            _, d = journal_de(journaux, e["t_utc"])
            lignes.append({"palier": e["essai"], "début": e["heure"],
                           **palier(d, e["t_utc"], *seuils, vision_interdite)})
        print(pd.DataFrame(lignes).to_string(index=False))

    print("\n== FE-02 (critère : vz max entre 4,5 et 5,5 m/s, montée et descente)")
    e = carnet[carnet["essai"].str.startswith("FE-02")].iloc[0]
    nom, d = journal_de(journaux, e["t_utc"])
    print(f"journal {nom}")
    print(fe02(d).to_string(index=False))

    print("\n== FE-04 (critère : pose à 1,5 m au plus du repère, mesuré au ruban)")
    for _, e in carnet[carnet["essai"].str.startswith("FE-04")].iterrows():
        nom, d = journal_de(journaux, e["t_utc"], dernier_commence=True)
        print(f"{e['essai']}  ruban {e['mesure']} m  journal {nom}  {fe04(d)}")

    print("\n== FE-05 (critère : moyenne aller / retour de la vitesse max à ±10 % de 12 m/s ;"
          " inclinaison max comparée à 35°)")
    e = carnet[carnet["essai"].str.startswith("FE-05")].iloc[0]
    nom, d = journal_de(journaux, e["t_utc"])
    print(f"journal {nom}")
    print(fe05(d).to_string(index=False))


if __name__ == "__main__":
    if len(sys.argv) < 4:
        sys.exit(__doc__.splitlines()[2])
    main(sys.argv[1], sys.argv[2], sys.argv[3:])
