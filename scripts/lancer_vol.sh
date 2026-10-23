#!/bin/bash
# Lance un vol SITL automatique : démarre le SITL, exécute vol_auto.py, arrête le SITL.
# Usage : scripts/lancer_vol.sh <scénario> [vitesse direction turbulence] [--injection T] [--amplitude A]
#         [--detecteur] [--trainee] [--bascule T] [--reponse R] [--bruit R] [--vibration [gyro|acc]] [--flux_optique]
# Scénarios : nominal, gps60, gps30, biais10, biais05, magneto, jam, et avec --amplitude : biais,
# derive, gyro, bruit_gyro, bloque, leurre, leurre_rampe.
# Vent optionnel : vitesse (m/s), direction d'où il vient (degrés), turbulence (m/s).
# Toutes les options sont transmises à vol_auto.py (voir son en-tête).
# Le log .BIN est écrit dans ~/drone/ardupilot/logs/ ; le journal du vol dans data/.
SCENARIO="$1"
shift
VENT=("$@")
# Nom des journaux : scénario suivi des options, espaces et tirets remplacés par « _ »
NOM="$(echo "$SCENARIO $*" | sed -e 's/--//g' -e 's/ /_/g')"
DEPOT="$(cd "$(dirname "$0")/.." && pwd)"
ARDUPILOT="${ARDUPILOT:-$HOME/drone/ardupilot}"
HORODATAGE="$(date '+%Y%m%d-%H%M%S')"

# Capteurs pris en compte seulement au démarrage : chargés par un fichier de paramètres
PARAMS=()
for option in "$@"; do
    if [ "$option" = "--flux_optique" ]; then
        PARAMS=(--add-param-file "$DEPOT/scripts/flux_optique.parm")
    fi
done

cd "$ARDUPILOT" || exit 1
echo "Dernier log avant le vol : $(cat logs/LASTLOG.TXT)"
./Tools/autotest/sim_vehicle.py -v ArduCopter -w -N --no-mavproxy "${PARAMS[@]}" > "$DEPOT/data/sitl_${NOM}_${HORODATAGE}.out" 2>&1 &
SV=$!
"$DEPOT/.venv/bin/python" -I "$DEPOT/scripts/vol_auto.py" "$SCENARIO" "${VENT[@]}" 2>&1 | tee "$DEPOT/data/journal_${NOM}_${HORODATAGE}.txt"
RC=${PIPESTATUS[0]}
sleep 3
pkill -f "build/sitl/bin/arducopter"
kill "$SV" 2>/dev/null
wait 2>/dev/null
echo "Code de sortie du vol : $RC"
echo "Dernier log après le vol : $(cat logs/LASTLOG.TXT)"
exit "$RC"
