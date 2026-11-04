"""Archive des logs ArduPilot sous un numéro de vol qui ne revient jamais (appelé par lancer_vol.sh).

Usage :
  python scripts/archiver_log.py verifier <dossier_logs>
      Avant un vol : refuse (code 1) si le log qu'ArduPilot va écrire existe déjà sans copie
      identique dans l'archive. ArduPilot ne garde que 500 numéros (LOG_MAX_FILES ≤ 500,
      AP_Logger.cpp:198-205) et repart à 1 en écrasant l'ancien fichier (AP_Logger_File.cpp:805-806).
  python scripts/archiver_log.py archiver <dossier_logs> <dernier_log_avant> <journal>
      Après un vol : si ArduPilot a écrit un nouveau log, le copie en vols/vol_NNNN.BIN (vol = dernier
      vol de l'index + 1), vérifie la copie octet par octet et ajoute une ligne à docs/index_vols.csv
      et à la copie de l'index dans l'archive.
Archive : ~/drone/archive_logs (ou la variable ARCHIVE_LOGS) ; index construit le 2026-11-04 pour les
vols 1 à 492 (docs/vols.md).
"""
import csv
import datetime as dt
import filecmp
import os
import shutil
import sys

DEPOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX = os.path.join(DEPOT, "docs", "index_vols.csv")
ARCHIVE = os.environ.get("ARCHIVE_LOGS", os.path.expanduser("~/drone/archive_logs"))
MAX_LOGS = 500   # LOG_MAX_FILES par défaut, remis par sim_vehicle.py -w


def dernier_log(dossier):
    with open(os.path.join(dossier, "LASTLOG.TXT")) as f:
        return int(f.read().strip())


def lire_index():
    with open(INDEX, newline="") as f:
        return list(csv.DictReader(f))


def archive(chemin, lignes):
    """Vrai si le fichier a une copie identique dans l'archive (même numéro de log ArduPilot)."""
    n = int(os.path.basename(chemin)[:8])
    taille = os.path.getsize(chemin)
    for r in lignes:
        copie = os.path.join(ARCHIVE, r["fichier_archive"])
        if (int(r["log_ardupilot"]) == n and os.path.exists(copie) and os.path.getsize(copie) == taille
                and filecmp.cmp(chemin, copie, shallow=False)):
            return True
    return False


def verifier(dossier):
    if not os.path.isdir(os.path.join(ARCHIVE, "vols")):
        sys.exit(f"Archive introuvable : {ARCHIVE}/vols")
    prochain = dernier_log(dossier) + 1
    if prochain > MAX_LOGS:
        prochain = 1
    chemin = os.path.join(dossier, f"{prochain:08d}.BIN")
    if os.path.exists(chemin) and not archive(chemin, lire_index()):
        sys.exit(f"Le prochain log ({chemin}) écraserait un fichier absent de l'archive : vol refusé")
    print(f"Prochain log : {prochain:08d}.BIN (aucun fichier non archivé écrasé)")


def archiver(dossier, avant, journal):
    n = dernier_log(dossier)
    if n == avant:
        print("Aucun nouveau log : rien à archiver")
        return
    lignes = lire_index()
    vol = max(int(r["vol"]) for r in lignes if r["vol"]) + 1
    source = os.path.join(dossier, f"{n:08d}.BIN")
    fichier = f"vols/vol_{vol:04d}.BIN"
    copie = os.path.join(ARCHIVE, fichier)
    if os.path.exists(copie):
        sys.exit(f"{copie} existe déjà")
    shutil.copy2(source, copie)
    if not filecmp.cmp(source, copie, shallow=False):
        sys.exit(f"Copie de {source} différente de l'original")
    st = os.stat(source)
    ligne = {"vol": vol, "log_ardupilot": n,
             "fin_ecriture": dt.datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
             "taille_octets": st.st_size, "fichier_archive": fichier, "journal": os.path.basename(journal),
             "remarque": ""}
    for chemin in (INDEX, os.path.join(ARCHIVE, "index_vols.csv")):
        with open(chemin, "a", newline="") as f:
            csv.DictWriter(f, fieldnames=list(ligne)).writerow(ligne)
    print(f"Log {n:08d}.BIN archivé : vol {vol} → {copie}")


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "verifier":
        verifier(sys.argv[2])
    elif len(sys.argv) == 5 and sys.argv[1] == "archiver":
        archiver(sys.argv[2], int(sys.argv[3]), sys.argv[4])
    else:
        sys.exit(__doc__)
