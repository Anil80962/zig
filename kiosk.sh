#!/usr/bin/env bash
# AquaGen kiosk launcher — opens the dashboard fullscreen on the 7" display,
# with an on-screen keyboard for typing the username/password on a touchscreen.
# Works on Raspberry Pi OS Bookworm/Trixie (Wayland/labwc) and Bullseye (X11/LXDE).

set -u

URL="https://web.aquagen.co.in/login"

# ---- pick the chromium binary (name differs across OS versions) ----
if command -v chromium-browser >/dev/null 2>&1; then
    CHROME="chromium-browser"
elif command -v chromium >/dev/null 2>&1; then
    CHROME="chromium"
else
    echo "[kiosk] Chromium not installed. Run: sudo apt install -y chromium-browser" >&2
    exit 1
fi

# ---- detect Wayland (labwc) vs X11 ----
if [ -n "${WAYLAND_DISPLAY:-}" ] || [ "${XDG_SESSION_TYPE:-}" = "wayland" ]; then
    IS_WAYLAND=1
else
    IS_WAYLAND=0
fi

# ---- wait for the network + site to be reachable (max ~2 min) ----
for i in $(seq 1 60); do
    if curl -sSf --max-time 4 -o /dev/null "$URL"; then
        break
    fi
    echo "[kiosk] waiting for $URL ... ($i)"
    sleep 2
done

# ---- disable screen blanking / power saving ----
export DISPLAY="${DISPLAY:-:0}"
if [ "$IS_WAYLAND" = "0" ]; then
    xset s off      2>/dev/null || true
    xset s noblank  2>/dev/null || true
    xset -dpms      2>/dev/null || true
fi

# ---- hide the mouse cursor when idle (if unclutter is installed) ----
if command -v unclutter >/dev/null 2>&1; then
    unclutter -idle 0.5 -root >/dev/null 2>&1 &
fi

# ---- on-screen keyboard ----
# squeekboard is the Pi's built-in OSK; it draws ABOVE the fullscreen page and
# auto-shows when a text field is focused (Chromium runs native-Wayland + IME).
if command -v squeekboard >/dev/null 2>&1; then
    pgrep -x squeekboard >/dev/null || squeekboard >/dev/null 2>&1 &
fi

# ---- WiFi manager ----
# Local page (127.0.0.1:8088) opened by the WiFi icon on the dashboard, so the
# WiFi can be changed from the kiosk without a desktop.
if command -v python3 >/dev/null 2>&1; then
    pgrep -f 'wifi-manager[.]py' >/dev/null || \
        python3 "$HOME/aquagen-kiosk/wifi-manager.py" >/tmp/wifi-manager.log 2>&1 &
fi

# ---- clean up any stale "Chrome didn't shut down correctly" flag ----
PROFILE="$HOME/.config/chromium/Default/Preferences"
if [ -f "$PROFILE" ]; then
    sed -i 's/"exit_type":"Crashed"/"exit_type":"Normal"/'         "$PROFILE" 2>/dev/null || true
    sed -i 's/"exited_cleanly":false/"exited_cleanly":true/'       "$PROFILE" 2>/dev/null || true
fi

# ---- Chromium flags ----
# Fullscreen kiosk + native Wayland + IME so squeekboard auto-shows over the
# page on field focus.
FLAGS=(
    --kiosk
    --user-data-dir="$HOME/.config/aquagen-chrome"
    --no-first-run
    --noerrdialogs
    --disable-infobars
    --disable-session-crashed-bubble
    --disable-features=Translate,TranslateUI,OverlayScrollbar
    --check-for-update-interval=31536000
    --overscroll-history-navigation=0
    --autoplay-policy=no-user-gesture-required
    --touch-events=enabled
    --force-device-scale-factor=0.8
    --start-fullscreen
)
if [ "$IS_WAYLAND" = "1" ]; then
    FLAGS+=( --ozone-platform=wayland --enable-wayland-ime )
fi
# Kiosk tweaks: thin scrollbars + scrollable side menu (runs after page load).
TWEAKS="$HOME/aquagen-kiosk/kiosk-tweaks"
if [ -d "$TWEAKS" ]; then
    FLAGS+=( --load-extension="$TWEAKS" --disable-extensions-except="$TWEAKS" )
fi

exec "$CHROME" "${FLAGS[@]}" "$URL"
