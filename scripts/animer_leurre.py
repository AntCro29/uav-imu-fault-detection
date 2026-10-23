"""Animation de démonstration : deux vols R3 face au même leurre GPS, sans et avec flux optique.

Usage : python animer_leurre.py <log_sans.BIN> <log_avec.BIN> <sortie.mp4> [t_debut t_fin]
        (t en s depuis l'entrée en CIRCLE ; par défaut 115 à 265)

Chaque panneau montre, vu de dessus : la trajectoire vraie du simulateur (SIM), la position
donnée par le GPS (GPS, instance 0, décalée par le leurre) et la position estimée par le cœur EKF
principal (XKF1 du cœur indiqué par les messages « EKF3 primary changed », celui sur lequel le
drone pilote). Après « EKF3 IMUn stopped aiding » du cœur principal, XKF1 contient la position GPS
brute signalée invalide (AP_NavEKF3_Outputs.cpp:234-242) : l'estimée n'est alors plus tracée.
En bas : distance entre l'estimée et la vérité. Vidéo accélérée 4 fois (ffmpeg nécessaire).
"""
import contextlib
import io
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.animation import FFMpegWriter
from pymavlink import mavutil

import erreur_navigation as en

ACCELERATION = 4
IPS = 25                           # images par seconde de la vidéo
TRAINEE_S = 30                     # longueur des traces GPS et estimée
VERITE, GPS, ESTIMEE, ZONE = "#222222", "#e08a1e", "#2a78d6", "#2a78d6"
SANS, AVEC = "#d6452a", "#2a78d6"


def charger(chemin):
    """Séries vérité / GPS / estimée (m, repère de l'origine EKF) et événements, t depuis CIRCLE."""
    origine, sim, _, _, textes, debut_fin, bascules, modes, tc, _, _ = en.lire(chemin)
    with contextlib.redirect_stdout(io.StringIO()):     # analyser() affiche son rapport
        _, centre, _ = en.analyser(chemin)
    sim = np.array(sim)
    vn, ve = en.en_metres(sim[:, 1], sim[:, 2], origine)
    m = mavutil.mavlink_connection(chemin)
    coeurs, gps, flux = {0: [], 1: []}, [], False
    while (msg := m.recv_match(type=["XKF1", "GPS", "PARM"])) is not None:
        if msg.get_type() == "PARM":
            flux = flux or (msg.Name == "SIM_FLOW_ENABLE" and msg.Value == 1)
        elif msg.get_type() == "XKF1":
            coeurs[msg.C].append((msg.TimeUS / 1e6 - tc, msg.PN, msg.PE))
        elif msg.I == 0:
            gps.append((msg.TimeUS / 1e6 - tc, msg.Lat, msg.Lng))
    gps = np.array(gps)
    gn, ge = en.en_metres(gps[:, 1], gps[:, 2], origine)
    # Cœur principal et validité de chaque cœur au cours du temps (mêmes règles que erreur_navigation.py)
    principal, invalide = en.coeur_principal([(t - tc, x) for t, x in textes])
    return {"t_v": sim[:, 0] - tc, "vn": vn, "ve": ve, "t_g": gps[:, 0], "gn": gn, "ge": ge,
            "coeurs": {c: np.array(v) for c, v in coeurs.items()}, "principal": principal,
            "invalide": invalide, "centre": centre, "textes": [(t - tc, x) for t, x in textes],
            "panne": [(t - tc, debut) for t, debut in debut_fin],
            "bascules": [(t - tc, sans_gps) for t, sans_gps in bascules],
            "modes": [(t - tc, mode) for t, mode in modes], "flux": flux}


def estimee(d, temps):
    """Position estimée du cœur principal à chaque instant, NaN si ce cœur ne navigue plus."""
    n, e = np.full(len(temps), np.nan), np.full(len(temps), np.nan)
    for i, t in enumerate(temps):
        c = en.dernier(d["principal"], t, 0)
        if en.dernier(d["invalide"][c], t, False):
            continue
        k = d["coeurs"][c]
        n[i] = np.interp(t, k[:, 0], k[:, 1])
        e[i] = np.interp(t, k[:, 0], k[:, 2])
    return n, e


def etat(d, t, navigation):
    """Phrase d'état affichée au-dessus du panneau."""
    mode = en.dernier(d["modes"], t, 7)
    if mode == 9:
        return "Dernier recours : atterrissage sur place (LAND)"
    if mode == 6:
        return "Retour au départ (RTL)"
    c = en.dernier(d["principal"], t, 0)
    if en.dernier(d["invalide"][c], t, False):
        return "EKF : position perdue, le drone ne sait plus où il est"
    sans_gps = en.dernier(d["bascules"], t, False)
    leurre = en.dernier(d["panne"], t, False)
    if sans_gps and leurre:
        return f"R3 : GPS écarté, navigation {navigation}"
    if sans_gps:
        return f"Leurre retiré, R3 vérifie le GPS avant de le reprendre ({navigation})"
    if leurre:
        return "Leurre GPS : position décalée de 100 m"
    if any(not s for ts, s in d["bascules"] if ts <= t):
        return "R3 : GPS repris, mission poursuivie"
    return "Vol nominal, cercle de surveillance"


def main():
    if len(sys.argv) not in (4, 6):
        sys.exit(__doc__)
    t0, t1 = (115.0, 265.0) if len(sys.argv) == 4 else (float(sys.argv[4]), float(sys.argv[5]))
    vols = [(charger(sys.argv[1]), "Sans flux optique", "à l'estime (centrale inertielle)", SANS),
            (charger(sys.argv[2]), "Avec flux optique", "au flux optique", AVEC)]
    temps = np.arange(t0, t1, ACCELERATION / IPS)

    fig = plt.figure(figsize=(12.8, 7.2), dpi=100)
    grille = fig.add_gridspec(2, 2, height_ratios=[3.2, 1], hspace=0.32, wspace=0.18,
                              left=0.06, right=0.98, top=0.86, bottom=0.08)
    fig.suptitle("Leurre GPS de 100 m sous vibration des moteurs, vent 6 m/s : réponse R3 sans et avec "
                 "flux optique\n(simulation ArduPilot SITL, vols 250 et 262, vidéo accélérée ×4)",
                 fontsize=12)
    horloge = fig.text(0.5, 0.895, "", ha="center", fontsize=10, color="#555555")
    courbe = fig.add_subplot(grille[1, :])
    courbe.set_xlim(t0, t1)
    courbe.set_xlabel("temps depuis l'entrée en cercle (s)", fontsize=9)
    courbe.set_ylabel("erreur de l'estimée (m)", fontsize=9)
    courbe.grid(True, color="#e6e6e6", lw=0.6)
    courbe.tick_params(labelsize=8)
    curseur = courbe.axvline(t0, color="#888888", lw=1)

    elements = []
    for i, (d, titre, navigation, couleur) in enumerate(vols):
        a = fig.add_subplot(grille[0, i])
        n_est, e_est = estimee(d, temps)
        n_v, e_v = np.interp(temps, d["t_v"], d["vn"]), np.interp(temps, d["t_v"], d["ve"])
        n_g, e_g = np.interp(temps, d["t_g"], d["gn"]), np.interp(temps, d["t_g"], d["ge"])
        erreur = np.hypot(n_est - n_v, e_est - e_v)
        trace_err, = courbe.plot([], [], color=couleur, lw=1.6, label=titre.lower())
        # Échelle fixe pour toute la vidéo, englobant vérité, GPS, estimée et la zone
        xs = np.concatenate([e_v, e_g, e_est[~np.isnan(e_est)], [d["centre"][1] - 60, d["centre"][1] + 60]])
        ys = np.concatenate([n_v, n_g, n_est[~np.isnan(n_est)], [d["centre"][0] - 60, d["centre"][0] + 60]])
        # Limites élargies à la forme du panneau : même échelle en x et en y sans que matplotlib
        # ne les recalcule (aspect « equal » avec des limites fixes)
        boite = a.get_position()
        forme = (boite.width * fig.get_figwidth()) / (boite.height * fig.get_figheight())
        x0, x1, y0, y1 = xs.min() - 15, xs.max() + 15, ys.min() - 15, ys.max() + 15
        largeur, hauteur = max(x1 - x0, (y1 - y0) * forme), max(y1 - y0, (x1 - x0) / forme)
        a.set_xlim((x0 + x1 - largeur) / 2, (x0 + x1 + largeur) / 2)
        a.set_ylim((y0 + y1 - hauteur) / 2, (y0 + y1 + hauteur) / 2)
        a.add_patch(plt.Circle((d["centre"][1], d["centre"][0]), en.ZONE_M, fill=False, color=ZONE,
                               ls=":", lw=1.2))
        a.grid(True, color="#eeeeee", lw=0.6)
        a.tick_params(labelsize=8)
        a.set_xlabel("est (m)", fontsize=8)
        a.set_ylabel("nord (m)", fontsize=8)
        a.set_title(titre, fontsize=11, color=couleur, fontweight="bold", pad=22)
        texte_etat = a.text(0.5, 1.015, "", transform=a.transAxes, ha="center", fontsize=9.5)
        texte_chiffres = a.text(0.02, 0.02, "", transform=a.transAxes, fontsize=8.5, va="bottom",
                                bbox=dict(boxstyle="round", fc="white", ec="#cccccc", alpha=0.9))
        tv, = a.plot([], [], color=VERITE, lw=1.2, label="position vraie")
        tg, = a.plot([], [], ".", color=GPS, ms=2.5, label="position GPS (leurrée)")
        te, = a.plot([], [], color=ESTIMEE, lw=1.2, ls="--", label="position estimée par le drone")
        pv, = a.plot([], [], "o", color=VERITE, ms=7)
        pg, = a.plot([], [], "s", color=GPS, ms=6)
        pe, = a.plot([], [], "^", color=ESTIMEE, ms=7)
        if i == 0:
            a.plot([], [], ":", color=ZONE, label="zone surveillée (60 m)")
            a.legend(fontsize=7.5, loc="upper left")
        elements.append(dict(d=d, navigation=navigation, n_v=n_v, e_v=e_v, n_g=n_g, e_g=e_g,
                             n_est=n_est, e_est=e_est, erreur=erreur, tv=tv, tg=tg, te=te, pv=pv,
                             pg=pg, pe=pe, etat=texte_etat, chiffres=texte_chiffres, err=trace_err))
    # Échelle fixée d'avance : la courbe se construit au fil de la vidéo
    courbe.set_ylim(0, 1.05 * max(np.nanmax(el["erreur"]) for el in elements))
    courbe.legend(fontsize=8, loc="upper left")

    ecrivain = FFMpegWriter(fps=IPS, bitrate=4000)
    with ecrivain.saving(fig, sys.argv[3], dpi=100):
        for k, t in enumerate(temps):
            debut = max(0, k - int(TRAINEE_S * IPS / ACCELERATION))
            for el in elements:
                el["tv"].set_data(el["e_v"][:k + 1], el["n_v"][:k + 1])
                el["tg"].set_data(el["e_g"][debut:k + 1], el["n_g"][debut:k + 1])
                el["te"].set_data(el["e_est"][debut:k + 1], el["n_est"][debut:k + 1])
                el["pv"].set_data([el["e_v"][k]], [el["n_v"][k]])
                el["pg"].set_data([el["e_g"][k]], [el["n_g"][k]])
                el["pe"].set_data([el["e_est"][k]], [el["n_est"][k]])
                el["err"].set_data(temps[:k + 1], el["erreur"][:k + 1])
                el["etat"].set_text(etat(el["d"], t, el["navigation"]))
                distance = np.hypot(el["n_v"][k] - el["d"]["centre"][0], el["e_v"][k] - el["d"]["centre"][1])
                err = "—" if np.isnan(el["erreur"][k]) else f"{el['erreur'][k]:.0f} m"
                el["chiffres"].set_text(f"erreur de l'estimée : {err}\ndistance vraie au centre : {distance:.0f} m")
            curseur.set_xdata([t, t])
            horloge.set_text(f"t = {t:5.1f} s")
            ecrivain.grab_frame()
    print(f"{sys.argv[3]} : {len(temps)} images, {len(temps) / IPS:.1f} s")


if __name__ == "__main__":
    main()
