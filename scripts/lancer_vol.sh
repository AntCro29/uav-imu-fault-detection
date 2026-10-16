#!/bin/bash
# Lance un vol SITL automatique : démarre le SITL, exécute vol_auto.py, arrête le SITL.
# Usage : scripts/lancer_vol.sh <nominal|gps60|gps30|biais10|biais05|magneto>
# Le log .BIN est écrit dans ~/drone/ardupilot/logs/ ; le journal du vol dans data/.
SCENARIO="$1"
DEPOT="$(cd "$(dirname "$0")/.." && pwd)"
ARDUPILOT="${ARDUPILOT:-$HOME/drone/ardupilot}"
HORODATAGE="$(date '+%Y%m%d-%H%M%S')"

cd "$ARDUPILOT" || exit 1
echo "Dernier log avant le vol : $(cat logs/LASTLOG.TXT)"
./Tools/autotest/sim_vehicle.py -v ArduCopter -w -N --no-mavproxy > "$DEPOT/data/sitl_${SCENARIO}_${HORODATAGE}.out" 2>&1 &
SV=$!
"$DEPOT/.venv/bin/python" -I "$DEPOT/scripts/vol_auto.py" "$SCENARIO" 2>&1 | tee "$DEPOT/data/journal_${SCENARIO}_${HORODATAGE}.txt"
RC=${PIPESTATUS[0]}
sleep 3
pkill -f "build/sitl/bin/arducopter"
kill "$SV" 2>/dev/null
wait 2>/dev/null
echo "Code de sortie du vol : $RC"
echo "Dernier log après le vol : $(cat logs/LASTLOG.TXT)"
exit "$RC"
