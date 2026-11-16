#!/bin/bash
# OPTIONAL: render 3D device frames with Rotato, one transparent PNG per raw capture.
# compose.js uses these when a set has "framedDir"; without them it draws a plain
# frame in code, so nothing depends on this script.
#
#   rotato_frame.sh --check
#   rotato_frame.sh --device "iPhone 17 Pro Max" --raw <rawDir> --out <framedDir>
#
# Exit codes: 0 ok, 3 Rotato not installed or not reachable (use the plain frames).
# Rotato's CLI ships inside the app. It talks to the running app over a socket, so
# it must run outside a sandbox, and the first call may launch Rotato.
set -uo pipefail

ROTATO=${ROTATO:-/Applications/Rotato.app/Contents/Resources/rotato}

available() {
  [ -x "$ROTATO" ] || return 1
  "$ROTATO" --version >/dev/null 2>&1
}

if [ "${1:-}" = "--check" ]; then
  if available; then echo "rotato: available ($("$ROTATO" --version | head -1))"; exit 0; fi
  echo "rotato: not available; compose.js will draw plain frames"; exit 3
fi

device="" raw="" out=""
while [ $# -gt 0 ]; do
  case "$1" in
    --device) device=$2; shift 2 ;;
    --raw) raw=$2; shift 2 ;;
    --out) out=$2; shift 2 ;;
    *) echo "unknown option: $1" >&2; exit 1 ;;
  esac
done
[ -n "$device" ] && [ -n "$raw" ] && [ -n "$out" ] || { sed -n '2,8p' "$0" | sed 's/^# \{0,1\}//'; exit 1; }
available || { echo "rotato: not available; skip this step and let compose.js draw plain frames" >&2; exit 3; }

mkdir -p "$out"
out=$(cd "$out" && pwd)
plan="$out/plan.json"
# Transparent background, tall canvas, no screen reflections: a clean cut-out.
cat > "$plan" <<'EOF'
{"version":1,"duration":1,"operations":[{"type":"scene.configure","background":"transparent","screen_reflections":false,"canvas_aspect_ratio":{"width":2400,"height":4200}}]}
EOF

fail=0
for f in "$raw"/*.png; do
  [ -e "$f" ] || { echo "no PNG captures in $raw" >&2; exit 1; }
  name=$(basename "$f" .png)
  proj="$out/$name.rotato"
  rm -rf "$proj"
  if "$ROTATO" create "$proj" --device "$device" --screen-media "$f" --timeout 300 >/dev/null 2>&1 &&
     "$ROTATO" frame "$proj" --plan "$plan" --time 0 --output "$out/$name.png" --timeout 300 >/dev/null 2>&1 &&
     [ -s "$out/$name.png" ]; then
    echo "framed $name -> $out/$name.png"
  else
    echo "rotato failed for $name (is \"$device\" in Rotato's device catalog?)" >&2
    fail=1
  fi
done
[ $fail -eq 0 ] || exit 3
