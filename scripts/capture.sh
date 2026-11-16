#!/bin/bash
# Capture raw app screenshots from an iOS simulator or Android emulator.
# Uses only xcrun simctl and adb. No MCP server needed.
#
#   capture.sh ios     --device <udid|name> --bundle <bundle.id> --out <dir> \
#                      [--app <path/to/App.app>] [--arg-name -screenshots] \
#                      [--wait 4] state1 [state2 ...]
#   capture.sh android --package <pkg> --activity <.MainActivity> --out <dir> \
#                      [--serial <emulator-5554>] [--apk <path.apk>] \
#                      [--extra-name shot] [--wait 4] state1 [state2 ...]
#
# Each "state" is passed to the app at launch (iOS: "<arg-name> <state>" launch
# arguments; Android: "--es <extra-name> <state>" intent extra) and saved as
# <out>/<state>.png. The app needs a debug-only hook that reads it and shows
# that screen with sample data. See SKILL.md, "Sample data".
# Pass the single state "current" to capture whatever is on screen right now
# without relaunching the app.
set -euo pipefail

usage() { sed -n '2,17p' "$0" | sed 's/^# \{0,1\}//'; exit 1; }
[ $# -ge 1 ] || usage
platform=$1; shift

device="" bundle="" app="" out="" package="" activity="" serial="" apk=""
arg_name="-screenshots" extra_name="shot" wait_s=4
states=()
while [ $# -gt 0 ]; do
  case "$1" in
    --device) device=$2; shift 2 ;;
    --bundle) bundle=$2; shift 2 ;;
    --app) app=$2; shift 2 ;;
    --out) out=$2; shift 2 ;;
    --package) package=$2; shift 2 ;;
    --activity) activity=$2; shift 2 ;;
    --serial) serial=$2; shift 2 ;;
    --apk) apk=$2; shift 2 ;;
    --arg-name) arg_name=$2; shift 2 ;;
    --extra-name) extra_name=$2; shift 2 ;;
    --wait) wait_s=$2; shift 2 ;;
    -h|--help) usage ;;
    *) states+=("$1"); shift ;;
  esac
done
[ -n "$out" ] || { echo "error: --out is required" >&2; exit 1; }
[ ${#states[@]} -gt 0 ] || { echo "error: give at least one state name" >&2; exit 1; }
mkdir -p "$out"

size_of() { sips -g pixelWidth -g pixelHeight "$1" 2>/dev/null | awk '/pixel/{printf "%s%s", s, $2; s="x"}'; }

case "$platform" in
  ios)
    [ -n "$device" ] && [ -n "$bundle" ] || { echo "error: ios needs --device and --bundle" >&2; exit 1; }
    xcrun simctl boot "$device" 2>/dev/null || true
    xcrun simctl bootstatus "$device" >/dev/null
    # Clean status bar: 9:41, full battery, full signal.
    xcrun simctl status_bar "$device" override --time "9:41" --batteryState charged \
      --batteryLevel 100 --cellularBars 4 --wifiBars 3 2>/dev/null || true
    [ -z "$app" ] || xcrun simctl install "$device" "$app"
    for s in "${states[@]}"; do
      if [ "$s" != "current" ]; then
        xcrun simctl terminate "$device" "$bundle" 2>/dev/null || true
        xcrun simctl launch "$device" "$bundle" "$arg_name" "$s" >/dev/null
        sleep "$wait_s"
      fi
      xcrun simctl io "$device" screenshot --type=png "$out/$s.png" >/dev/null 2>&1
      echo "ios $s -> $out/$s.png ($(size_of "$out/$s.png"))"
    done
    xcrun simctl status_bar "$device" clear 2>/dev/null || true
    ;;
  android)
    [ -n "$package" ] && [ -n "$activity" ] || { echo "error: android needs --package and --activity" >&2; exit 1; }
    ADB=${ADB:-$(command -v adb || echo "$HOME/Library/Android/sdk/platform-tools/adb")}
    adb_() { if [ -n "$serial" ]; then "$ADB" -s "$serial" "$@"; else "$ADB" "$@"; fi; }
    adb_ wait-for-device
    [ -z "$apk" ] || adb_ install -r "$apk" >/dev/null
    # Clean status bar via SystemUI demo mode.
    adb_ shell settings put global sysui_demo_allowed 1
    demo() { adb_ shell am broadcast -a com.android.systemui.demo -e command "$@" >/dev/null; }
    demo enter
    demo clock -e hhmm 0941
    demo battery -e level 100 -e plugged false
    demo network -e wifi show -e level 4 -e fully true
    demo network -e mobile show -e level 4 -e datatype none -e fully true
    demo notifications -e visible false
    for s in "${states[@]}"; do
      if [ "$s" != "current" ]; then
        adb_ shell am force-stop "$package"
        adb_ shell am start -n "$package/$activity" --es "$extra_name" "$s" >/dev/null
        sleep "$wait_s"
      fi
      adb_ exec-out screencap -p > "$out/$s.png"
      echo "android $s -> $out/$s.png ($(size_of "$out/$s.png"))"
    done
    demo exit
    ;;
  *) usage ;;
esac
