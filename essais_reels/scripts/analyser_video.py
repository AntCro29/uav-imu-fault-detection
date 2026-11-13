"""Dérive réelle en stationnaire (FE-01, FE-03), mesurée sur la vidéo de la caméra pointée
vers le bas, comparée à la position estimée du journal.

Usage : python scripts/analyser_video.py [--tol-angle DEG] <video.MP4> <journal.csv>
                     <distance_chaises_m> <hauteur_m> <début palier HH:MM:SS (local)> [...]

Méthode :
- images extraites par ffmpeg à 10 i/s, réduites en 1920 × 1080 ; chaque chaise est repérée par
  sa couleur (rouge, bleue) : centre des taches de cette couleur à moins de RAYON_M de la plus
  grande tache ;
- échelle (m/pixel) = distance mesurée entre les chaises / distance en pixels (médiane du palier) ;
- le drone se déplace à l'opposé de l'image : déplacement du drone = −déplacement du milieu des
  chaises × échelle ; rotation vers nord / est avec le cap du journal (haut de l'image = avant du
  drone) ;
- hauteur : la distance en pixels entre chaises varie comme 1 / hauteur ; variation de hauteur
  = hauteur × (d_moy / d − 1), avec la hauteur du journal au-dessus du point de décollage
  (les chaises sont posées au même niveau) ;
- images écartées si la distance entre chaises s'écarte de plus de 2 % de sa médiane glissante
  (chaise mal repérée, souvent pendant un déplacement) ;
- chaise déplacée par le vent (ligne entre chaises tournée de plus de 0,5°) : image gardée pour la
  dérive horizontale mesurée sur la chaise bleue seule, écartée pour le milieu des chaises et la
  hauteur. Tolérance 0,5° par défaut (FE-01, 20 m : angle stable à ±0,1° hors déplacement) ;
  à 2 m (FE-03), perspective et distorsion font varier l'angle apparent lentement de ±1° quand
  les chaises se déplacent dans l'image, sans saut : tolérance de 3° (--tol-angle 3) ;
- heure de l'image = creation_time de la vidéo + temps dans la vidéo + recalage ; le recalage est
  le décalage (±20 s) qui superpose le mieux la trajectoire vidéo et la trajectoire du journal sur
  toute la vidéo, déplacements entre paliers compris (creation_time s'est révélé en retard
  d'environ 10 s sur FE-01).

Limites : distorsion de l'objectif ignorée (déplacements faibles près du centre) ; caméra supposée
verticale (nacelle en butée à −90°).
"""

import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import ndimage

from analyser_essais import DECALAGE_UTC, DUREE_PALIER
from charger_vol import charger

LARGEUR, HAUTEUR_IMG = 1920, 1080
IPS = 10
RAYON_M = 0.6
TOL_DISTANCE = 0.02
TOL_ANGLE_DEG = 0.5
RECALAGE_MAX_S = 20


def masques(im):
    r, g, b = im[..., 0], im[..., 1], im[..., 2]
    rouge = (r > 130) & (r - g > 70) & (r - b > 40)
    bleu = (b > 130) & (b - r > 70) & (b - g > 10)
    return rouge, bleu


def centre(masque, rayon_px):
    lab, n = ndimage.label(masque)
    if n == 0:
        return np.nan, np.nan, 0
    idx = np.arange(1, n + 1)
    tailles = ndimage.sum(masque, lab, idx)
    centres = np.array(ndimage.center_of_mass(masque, lab, idx))
    k = np.argmax(tailles)
    garde = np.hypot(*(centres - centres[k]).T) < rayon_px
    cy, cx = np.average(centres[garde], axis=0, weights=tailles[garde])
    return cx, cy, int(tailles[garde].sum())


def suivre(video, cache, distance_m):
    if cache.exists():
        return pd.read_csv(cache)
    cmd = ["ffmpeg", "-v", "error", "-i", str(video), "-vf",
           f"fps={IPS},scale={LARGEUR}:{HAUTEUR_IMG}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    taille = LARGEUR * HAUTEUR_IMG * 3
    lignes, i, d_prec = [], 0, None
    while True:
        raw = proc.stdout.read(taille)
        if len(raw) < taille:
            break
        im = np.frombuffer(raw, np.uint8).reshape(HAUTEUR_IMG, LARGEUR, 3).astype(np.int16)
        rouge, bleu = masques(im)
        if d_prec is None:      # première image : plus grandes taches seules, pour l'échelle
            xr, yr, _ = centre(rouge, 1)
            xb, yb, _ = centre(bleu, 1)
            d_prec = np.hypot(xr - xb, yr - yb)
        rayon_px = RAYON_M / distance_m * d_prec
        xr, yr, nr = centre(rouge, rayon_px)
        xb, yb, nb = centre(bleu, rayon_px)
        lignes.append({"t_video_s": i / IPS, "xr": xr, "yr": yr, "nr": nr,
                       "xb": xb, "yb": yb, "nb": nb})
        d = np.hypot(xr - xb, yr - yb)
        if np.isfinite(d):
            d_prec = d
        i += 1
    proc.wait()
    t = pd.DataFrame(lignes)
    t.to_csv(cache, index=False)
    return t


def heure_debut(video):
    sortie = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format_tags=creation_time",
                             "-of", "default=nw=1:nk=1", str(video)],
                            capture_output=True, text=True).stdout.strip()
    return pd.Timestamp(sortie)


def filtrer(t):
    """Écarte les images où une chaise est mal repérée : distance entre chaises à plus de
    TOL_DISTANCE de sa médiane glissante (2 s)."""
    d = np.hypot(t.xr - t.xb, t.yr - t.yb)
    ok = (d / d.rolling(21, center=True, min_periods=1).median() - 1).abs() < TOL_DISTANCE
    return t[ok].copy()


def chaises_en_place(t, tol_angle_deg):
    """Faux quand la ligne entre les chaises tourne de plus de tol_angle_deg par rapport à sa
    médiane sur la vidéo : une chaise a bougé (vent)."""
    angle = np.degrees(np.arctan2(t.yr - t.yb, t.xr - t.xb))
    return (angle - angle.median()).abs() < tol_angle_deg


def deplacement_video(t, echelle, cap_deg, bleue_seule=False):
    """Déplacement du drone (nord, est, m) d'après la vidéo, à une constante près ; repère :
    milieu des deux chaises, ou chaise bleue seule."""
    if bleue_seule:
        mx, my = t.xb, t.yb
    else:
        mx, my = (t.xr + t.xb) / 2, (t.yr + t.yb) / 2
    droite = -mx * echelle                      # l'image glisse à l'opposé du drone
    avant = my * echelle                        # image qui descend = drone qui avance
    psi = np.radians(cap_deg)
    return (avant * np.cos(psi) - droite * np.sin(psi)).values, \
           (avant * np.sin(psi) + droite * np.cos(psi)).values


def recaler(t, tj, nj, ej, echelle, cap_deg):
    """Décalage (s) à ajouter au temps vidéo pour coller au journal : écart quadratique minimal
    entre trajectoires centrées, cherché à ±RECALAGE_MAX_S, sur toute la vidéo."""
    n, e = deplacement_video(t, echelle, cap_deg)
    meilleur = None
    for dec in np.arange(-RECALAGE_MAX_S, RECALAGE_MAX_S + 0.01, 0.1):
        tv = t.t_video_s.values + dec
        rn, re = np.interp(tv, tj, nj), np.interp(tv, tj, ej)
        rms = np.sqrt(np.mean((n - n.mean() - rn + rn.mean()) ** 2
                              + (e - e.mean() - re + re.mean()) ** 2))
        if meilleur is None or rms < meilleur[1]:
            meilleur = (round(dec, 1), rms, np.corrcoef(n, rn)[0, 1], np.corrcoef(e, re)[0, 1])
    return meilleur


def analyser(video, journal, distance_m, hauteur_m, debuts, tol_angle_deg=TOL_ANGLE_DEG):
    cache = Path(journal).parent / f"suivi_{Path(video).stem}.csv"
    brut = suivre(video, cache, distance_m)
    t = filtrer(brut)
    t["en_place"] = chaises_en_place(t, tol_angle_deg)
    t0 = heure_debut(video)

    d = charger(journal)
    d = d[d.t_utc.notna()]
    tj = (d.t_utc - t0).dt.total_seconds().values
    o = np.argsort(tj, kind="stable")
    tj, nj, ej = tj[o], d.nord_m.values[o], d.est_m.values[o]
    hj, yaw = d["OSD.height"].values[o], d["OSD.yaw"].values[o]

    p = t[t.en_place]
    d_px = np.hypot(p.xr - p.xb, p.yr - p.yb)
    echelle = distance_m / d_px.median()
    cap = np.mean(yaw[(tj >= 0) & (tj <= t.t_video_s.max())])
    dec, rms, cn, ce = recaler(p, tj, nj, ej, echelle, cap)
    print(f"{Path(video).name} : {len(t)} images gardées sur {len(brut)} "
          f"(chaise déplacée sur {int((~t.en_place).sum())}), "
          f"échelle {1000 * echelle:.2f} mm/px, cap {cap:.1f}°, recalage {dec:+.1f} s "
          f"(corrélation nord {cn:.2f}, est {ce:.2f}, écart rms {rms:.2f} m)")

    resultats = []
    for h in debuts:
        debut = (pd.Timestamp(f"{t0:%Y-%m-%d} {h}", tz="UTC") + DECALAGE_UTC - t0).total_seconds()
        tv = t.t_video_s + dec
        w = t[(tv >= debut) & (tv < debut + DUREE_PALIER.total_seconds())]
        if len(w) < 100:
            resultats.append({"palier": h, "images": len(w)})
            continue
        nb, eb = deplacement_video(w, echelle, cap, bleue_seule=True)
        bleue = np.hypot(nb - nb.mean(), eb - eb.mean())
        w = w[w.en_place]
        tw = w.t_video_s.values + dec
        nv, ev = deplacement_video(w, echelle, cap)
        nv, ev = nv - nv.mean(), ev - ev.mean()
        rn, re = np.interp(tw, tj, nj), np.interp(tw, tj, ej)
        rn, re = rn - rn.mean(), re - re.mean()
        dp = np.hypot(w.xr - w.xb, w.yr - w.yb).values
        dz = hauteur_m * (dp.mean() / dp - 1)
        ecart_h = np.hypot(nv, ev)
        resultats.append({
            "palier": h, "couverture_s": round(len(bleue) / IPS, 1),
            "deux_chaises_s": round(len(w) / IPS, 1),
            "p95_h_bleue_m": round(np.quantile(bleue, 0.95), 2),
            "p95_h_vidéo_m": round(np.quantile(ecart_h, 0.95), 2),
            "max_h_vidéo_m": round(ecart_h.max(), 2),
            "p95_h_journal_m": round(np.quantile(np.hypot(rn, re), 0.95), 2),
            "p95_écart_vidéo-journal_m": round(np.quantile(np.hypot(nv - rn, ev - re), 0.95), 2),
            "corr_nord": round(np.corrcoef(nv, rn)[0, 1], 2),
            "corr_est": round(np.corrcoef(ev, re)[0, 1], 2),
            "p95_v_vidéo_m": round(np.quantile(np.abs(dz - dz.mean()), 0.95), 3),
            "max_v_vidéo_m": round(np.abs(dz - dz.mean()).max(), 3),
        })
    return pd.DataFrame(resultats)


if __name__ == "__main__":
    args = sys.argv[1:]
    tol = TOL_ANGLE_DEG
    if args[:1] == ["--tol-angle"]:
        tol, args = float(args[1]), args[2:]
    if len(args) < 5:
        sys.exit(__doc__.splitlines()[3])
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 30)
    print(analyser(args[0], args[1], float(args[2]), float(args[3]), args[4:],
                   tol).to_string(index=False))
