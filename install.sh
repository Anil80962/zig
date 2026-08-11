#!/usr/bin/env bash
# One-shot installer for the AquaGen kiosk.
# Run this ON THE RASPBERRY PI:   bash install.sh
set -e

USER_NAME="$(whoami)"
HOME_DIR="$HOME"
SRC_DIR="$(cd "$(dirname "$0")" && pwd)"
KIOSK="$HOME_DIR/aquagen-kiosk/kiosk.sh"

echo "==> Installing packages (chromium, unclutter, curl)"
sudo apt-get update
sudo apt-get install -y chromium-browser unclutter curl || \
    sudo apt-get install -y chromium unclutter curl

echo "==> Copying kiosk script to $KIOSK"
mkdir -p "$HOME_DIR/aquagen-kiosk"
cp "$SRC_DIR/kiosk.sh" "$KIOSK"
chmod +x "$KIOSK"

SESSION="${XDG_SESSION_TYPE:-unknown}"
echo "==> Detected session type: $SESSION"

if [ -d "$HOME_DIR/.config/labwc" ] || [ "$SESSION" = "wayland" ]; then
    # --- Bookworm default: Wayland + labwc ---
    echo "==> Configuring labwc autostart (Wayland)"
    mkdir -p "$HOME_DIR/.config/labwc"
    AUTO="$HOME_DIR/.config/labwc/autostart"
    grep -q "aquagen-kiosk/kiosk.sh" "$AUTO" 2>/dev/null || \
        echo "$KIOSK &" >> "$AUTO"
    # keep the screen awake under wayland/labwc
    echo "==> (Wayland) disable screen blanking via ~/.config/labwc/rc..."
    echo "    If the screen still blanks, run: sudo raspi-config -> Display -> Screen Blanking -> Off"
else
    # --- Bullseye / X11 desktop autostart ---
    echo "==> Configuring XDG autostart (X11/LXDE)"
    mkdir -p "$HOME_DIR/.config/autostart"
    cat > "$HOME_DIR/.config/autostart/aquagen-kiosk.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=AquaGen Kiosk
Exec=$KIOSK
X-GNOME-Autostart-enabled=true
EOF
fi

echo ""
echo "==> Done. Reboot to launch the kiosk:   sudo reboot"
echo "    To exit kiosk later: plug in a keyboard and press Ctrl+Alt+F2 (or Alt+F4)."
