"""Chargement d'un journal DJI décodé (CSV de dji-log-parser).

Usage : python scripts/charger_vol.py data/decode/vol_<date>_<heure>.csv

Ce que fait charger() :
- temps : `t_s` = secondes depuis le décollage, à partir de `OSD.flyTime` (horloge du drone,
  pas de 0,1 s). `CUSTOM.dateTime` (UTC) ne sert qu'à l'heure absolue `t_utc` : il est
  irrégulier d'un échantillon à l'autre (0,1 à 0,4 s) mais ne dérive pas (≤ 0,1 s sur un vol),
  et quelques lignes valent 1970 ou une date aberrante (2042 sur le vol du 2026-10-01 15:00) :
  elles sont mises à NaT ;
- position : `est_m`, `nord_m` par rapport au point de décollage (approximation locale plane,
  suffisante sur quelques centaines de mètres) ; NaN tant que le GPS donne (0, 0) ;
- confidentialité : les coordonnées absolues (OSD, HOME) et les numéros de série sont retirés
  du tableau rendu. Rien en aval ne peut donc les publier.
"""

import sys

import numpy as np
import pandas as pd

RAYON_TERRE_M = 6_371_000.0

COLONNES_RETIREES = [
    "OSD.latitude", "OSD.longitude", "HOME.latitude", "HOME.longitude",
    "RECOVER.aircraftSerial", "RECOVER.cameraSerial", "RECOVER.rcSerial",
    "RECOVER.batterySerial", "DETAILS.aircraftSerial", "DETAILS.cameraSerial",
    "DETAILS.rcSerial",
]


def heure_utc(colonne):
    """Heure UTC de chaque ligne ; NaT si avant 2000 ou à plus d'un jour de la médiane."""
    t = pd.to_datetime(colonne, utc=True, format="ISO8601")
    t = t.where(t.dt.year > 2000)
    return t.where((t - t.median()).abs() < pd.Timedelta("1D"))


def charger(chemin):
    d = pd.read_csv(chemin, low_memory=False)
    d["t_utc"] = heure_utc(d["CUSTOM.dateTime"])

    en_vol = ~d["OSD.isOnGround"].astype(bool)
    if not en_vol.any():
        raise ValueError(f"{chemin} : le drone ne quitte jamais le sol")
    i_decollage = en_vol.idxmax()
    d["t_s"] = (d["OSD.flyTime"] - d.loc[i_decollage, "OSD.flyTime"]).round(1)

    fix = (d["OSD.latitude"] != 0) & (d["OSD.longitude"] != 0)
    lat = d["OSD.latitude"].where(fix)
    lon = d["OSD.longitude"].where(fix)
    # origine : dernière position valide au décollage, sinon la première après
    avant = lat.loc[:i_decollage].last_valid_index()
    i0 = avant if avant is not None else lat.first_valid_index()
    if i0 is None:
        d["nord_m"] = np.nan
        d["est_m"] = np.nan
    else:
        lat0, lon0 = np.radians(lat[i0]), np.radians(lon[i0])
        d["nord_m"] = (np.radians(lat) - lat0) * RAYON_TERRE_M
        d["est_m"] = (np.radians(lon) - lon0) * RAYON_TERRE_M * np.cos(lat0)

    return d.drop(columns=[c for c in COLONNES_RETIREES if c in d.columns])


def resumer(d):
    vol = d[~d["OSD.isOnGround"].astype(bool)]
    t_utc = d["t_utc"].dropna()
    dist = np.hypot(vol["est_m"], vol["nord_m"])
    v_h = np.hypot(vol["OSD.xSpeed"], vol["OSD.ySpeed"])
    print(f"échantillons          : {len(d)} ({len(vol)} en vol)")
    print(f"début (UTC)           : {t_utc.iloc[0]:%Y-%m-%d %H:%M:%S}")
    print(f"durée depuis décollage: {d['t_s'].iloc[-1]:.1f} s")
    print(f"hauteur max           : {vol['OSD.height'].max():.1f} m")
    print(f"distance max au départ: {dist.max():.0f} m")
    print(f"vitesse horiz. max    : {v_h.max():.1f} m/s")
    print(f"satellites min en vol : {vol['OSD.gpsNum'].min()}")
    print(f"batterie              : {d['BATTERY.chargeLevel'].iloc[0]} → "
          f"{d['BATTERY.chargeLevel'].iloc[-1]} %")
    print(f"états de vol          : {d['OSD.flycState'].value_counts().to_dict()}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__.splitlines()[2])
    resumer(charger(sys.argv[1]))
