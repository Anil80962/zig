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

# ---- on-screen keyboard (on demand) ----
# A small local helper starts the wvkbd keyboard only while a text field is
# focused (driven by the osk-ext browser extension) and hides it afterwards, so
# the keyboard is off the screen the rest of the time. The page runs MAXIMIZED
# (not fullscreen) so the keyboard can appear over its lower part.
if command -v wvkbd-mobintl >/dev/null 2>&1 && command -v python3 >/dev/null 2>&1; then
    pgrep -f 'osk-daemon[.]py' >/dev/null || \
        python3 "$HOME/aquagen-kiosk/osk-daemon.py" >/tmp/osk-daemon.log 2>&1 &
    OSK_EXT="$HOME/aquagen-kiosk/osk-ext"
fi

# ---- clean up any stale "Chrome didn't shut down correctly" flag ----
PROFILE="$HOME/.config/chromium/Default/Preferences"
if [ -f "$PROFILE" ]; then
    sed -i 's/"exit_type":"Crashed"/"exit_type":"Normal"/'         "$PROFILE" 2>/dev/null || true
    sed -i 's/"exited_cleanly":false/"exited_cleanly":true/'       "$PROFILE" 2>/dev/null || true
fi

# ---- Chromium flags ----
# --app (no tabs/URL bar) + --start-maximized so the window fills the screen but
# is NOT true-fullscreen — that lets the wvkbd keyboard appear over its lower
# part when needed. Native Wayland (so wvkbd can inject keystrokes), but NOT
# --enable-wayland-ime, so the built-in squeekboard does not also pop up.
FLAGS=(
    "--app=$URL"
    --user-data-dir="$HOME/.config/aquagen-chrome"
    --start-maximized
    --noerrdialogs
    --disable-infobars
    --disable-session-crashed-bubble
    --disable-features=Translate,TranslateUI,OverlayScrollbar
    --check-for-update-interval=31536000
    --overscroll-history-navigation=0
    --autoplay-policy=no-user-gesture-required
    --touch-events=enabled
)
if [ "$IS_WAYLAND" = "1" ]; then
    FLAGS+=( --ozone-platform=wayland )
fi
if [ -n "${OSK_EXT:-}" ] && [ -d "$OSK_EXT" ]; then
    FLAGS+=( --load-extension="$OSK_EXT" --disable-extensions-except="$OSK_EXT" )
fi

exec "$CHROME" "${FLAGS[@]}"
