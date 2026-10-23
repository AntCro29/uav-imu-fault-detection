"""Montage de démonstration : enregistrement d'écran de QGroundControl à côté de la vérité du même vol.

Usage : python animer_qgc.py <log.BIN> <enregistrement.mov> <decalage_s> <sortie.mp4> [t_debut t_fin]
        decalage_s : instant de l'enregistrement (s) moins le temps de cercle (s), mesuré sur un
        changement de mode visible dans QGC (vol 269 : CIRCLE à 35,7 s d'enregistrement, contrôlé
        sur le RTL à 0,1 s près) ; t en s depuis l'entrée en CIRCLE (par défaut 115 à 245).

À gauche, QGC affiche la position estimée par le drone ; à droite, la vérité du simulateur, la
position GPS et l'estimée du cœur principal (fonctions d'animer_leurre.py). Matplotlib dessine
l'image en laissant la zone de gauche vide, ffmpeg y incruste l'enregistrement accéléré ×4.
"""
import os
import subprocess
import sys
import tempfile

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.animation import FFMpegWriter

import erreur_navigation as en
from animer_leurre import ACCELERATION, ESTIMEE, GPS, IPS, TRAINEE_S, VERITE, ZONE, charger, estimee, etat

LARGEUR, HAUTEUR = 1920, 1080
# Zone de QGC dans l'enregistrement plein écran (3420 × 2214) : bandeau de mode, messages et carte,
# sans la barre d'outils de capture de macOS en bas
RECADRAGE = (2672, 1897, 0, 67)            # largeur, hauteur, x, y
QGC = (20, 150, 1100, 781)                 # x, y (depuis le haut), largeur, hauteur dans la vidéo


def cadre(x, y, l, h):
    """Rectangle en pixels (origine en haut à gauche) vers les fractions de figure de matplotlib."""
    return [x / LARGEUR, 1 - (y + h) / HAUTEUR, l / LARGEUR, h / HAUTEUR]


def main():
    if len(sys.argv) not in (5, 7):
        sys.exit(__doc__)
    log, enregistrement, decalage, sortie = sys.argv[1], sys.argv[2], float(sys.argv[3]), sys.argv[4]
    t0, t1 = (115.0, 245.0) if len(sys.argv) == 5 else (float(sys.argv[5]), float(sys.argv[6]))
    d = charger(log)
    vol = int(os.path.basename(log)[:8]) - 14
    navigation = "au flux optique" if d["flux"] else "à l'estime (centrale inertielle)"
    temps = np.arange(t0, t1, ACCELERATION / IPS)
    n_est, e_est = estimee(d, temps)
    n_v, e_v = np.interp(temps, d["t_v"], d["vn"]), np.interp(temps, d["t_v"], d["ve"])
    n_g, e_g = np.interp(temps, d["t_g"], d["gn"]), np.interp(temps, d["t_g"], d["ge"])
    erreur = np.hypot(n_est - n_v, e_est - e_v)

    fig = plt.figure(figsize=(LARGEUR / 100, HAUTEUR / 100), dpi=100)
    fig.text(0.5, 0.965, f"Vol {vol} : leurre GPS de 100 m, vibration des moteurs, vent 6 m/s, "
             f"{'flux optique' if d['flux'] else 'sans flux optique'} et réponse R3",
             ha="center", va="center", fontsize=17)
    horloge = fig.text(0.5, 0.93, "", ha="center", va="center", fontsize=11, color="#666666")
    x, y, l, h = QGC
    fig.text((x + l / 2) / LARGEUR, 1 - (y - 18) / HAUTEUR, "Ce que voit l'opérateur : QGroundControl "
             "(position estimée par le drone)", ha="center", fontsize=12, fontweight="bold")
    fond = fig.add_axes(cadre(*QGC))          # recouvert par l'enregistrement
    fond.set_xticks([]); fond.set_yticks([])

    carte = fig.add_axes(cadre(1190, 150, 710, 560))
    fig.text((1190 + 355) / LARGEUR, 1 - (150 - 40) / HAUTEUR, "Ce qui se passe vraiment (vérité du simulateur)",
             ha="center", fontsize=12, fontweight="bold")
    texte_etat = carte.text(0.5, 1.015, "", transform=carte.transAxes, ha="center", fontsize=11)
    xs = np.concatenate([e_v, e_g, e_est[~np.isnan(e_est)], [d["centre"][1] - 60, d["centre"][1] + 60]])
    ys = np.concatenate([n_v, n_g, n_est[~np.isnan(n_est)], [d["centre"][0] - 60, d["centre"][0] + 60]])
    forme = 710 / 560
    x0, x1, y0, y1 = xs.min() - 15, xs.max() + 15, ys.min() - 15, ys.max() + 15
    largeur, hauteur = max(x1 - x0, (y1 - y0) * forme), max(y1 - y0, (x1 - x0) / forme)
    carte.set_xlim((x0 + x1 - largeur) / 2, (x0 + x1 + largeur) / 2)
    carte.set_ylim((y0 + y1 - hauteur) / 2, (y0 + y1 + hauteur) / 2)
    carte.add_patch(plt.Circle((d["centre"][1], d["centre"][0]), en.ZONE_M, fill=False, color=ZONE, ls=":", lw=1.2))
    carte.grid(True, color="#eeeeee", lw=0.6)
    carte.tick_params(labelsize=9)
    carte.set_xlabel("est (m)", fontsize=9)
    carte.set_ylabel("nord (m)", fontsize=9)
    tv, = carte.plot([], [], color=VERITE, lw=1.2, label="position vraie")
    tg, = carte.plot([], [], ".", color=GPS, ms=3, label="position GPS (leurrée)")
    te, = carte.plot([], [], color=ESTIMEE, lw=1.2, ls="--", label="position estimée par le drone")
    pv, = carte.plot([], [], "o", color=VERITE, ms=8)
    pg, = carte.plot([], [], "s", color=GPS, ms=7)
    pe, = carte.plot([], [], "^", color=ESTIMEE, ms=8)
    carte.plot([], [], ":", color=ZONE, label="zone surveillée (60 m)")
    carte.legend(fontsize=9, loc="upper left")
    chiffres = carte.text(0.02, 0.02, "", transform=carte.transAxes, fontsize=10, va="bottom",
                          bbox=dict(boxstyle="round", fc="white", ec="#cccccc", alpha=0.9))

    courbe = fig.add_axes(cadre(1190, 775, 710, 156))
    courbe.set_xlim(t0, t1)
    courbe.set_ylim(0, max(25.0, 1.1 * np.nanmax(erreur)))
    courbe.set_xlabel("temps depuis l'entrée en cercle (s)", fontsize=9)
    courbe.set_ylabel("erreur de l'estimée (m)", fontsize=9)
    courbe.grid(True, color="#e6e6e6", lw=0.6)
    courbe.tick_params(labelsize=8)
    trace_err, = courbe.plot([], [], color=ESTIMEE, lw=1.6)
    curseur = courbe.axvline(t0, color="#888888", lw=1)
    fig.text(0.5, 0.06, "Le leurre décale le GPS de 100 m. R3 l'écarte en moins d'une seconde, le drone continue "
             "sa mission au flux optique,\npuis reprend le GPS une fois le leurre retiré. La station sol ne voit "
             "pas le leurre : seulement une alerte « EKF3 lane switch ».", ha="center", va="center", fontsize=13)

    with tempfile.TemporaryDirectory() as dossier:
        animation = os.path.join(dossier, "animation.mp4")
        ecrivain = FFMpegWriter(fps=IPS, bitrate=6000)
        with ecrivain.saving(fig, animation, dpi=100):
            for k, t in enumerate(temps):
                debut = max(0, k - int(TRAINEE_S * IPS / ACCELERATION))
                tv.set_data(e_v[:k + 1], n_v[:k + 1])
                tg.set_data(e_g[debut:k + 1], n_g[debut:k + 1])
                te.set_data(e_est[debut:k + 1], n_est[debut:k + 1])
                pv.set_data([e_v[k]], [n_v[k]])
                pg.set_data([e_g[k]], [n_g[k]])
                pe.set_data([e_est[k]], [n_est[k]])
                trace_err.set_data(temps[:k + 1], erreur[:k + 1])
                curseur.set_xdata([t, t])
                texte_etat.set_text(etat(d, t, navigation))
                err = "—" if np.isnan(erreur[k]) else f"{erreur[k]:.0f} m"
                distance = np.hypot(n_v[k] - d["centre"][0], e_v[k] - d["centre"][1])
                chiffres.set_text(f"erreur de l'estimée : {err}\ndistance vraie au centre : {distance:.0f} m")
                horloge.set_text(f"simulation ArduPilot SITL, vidéo accélérée ×4 · t = {t:5.1f} s depuis l'entrée en cercle")
                ecrivain.grab_frame()
        # Incrustation de QGC : même instant de départ, même accélération, même cadence
        l_r, h_r, x_r, y_r = RECADRAGE
        filtre = (f"[1:v]setpts=(PTS-STARTPTS)/{ACCELERATION},fps={IPS},crop={l_r}:{h_r}:{x_r}:{y_r},"
                  f"scale={l}:{h}[q];[0:v][q]overlay={x}:{y}:shortest=1")
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", animation,
                        "-ss", f"{t0 + decalage:.2f}", "-t", f"{t1 - t0:.2f}", "-i", enregistrement,
                        "-filter_complex", filtre, "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                        "-crf", "20", sortie], check=True)
    print(f"{sortie} : {len(temps)} images, {len(temps) / IPS:.1f} s")


if __name__ == "__main__":
    main()
