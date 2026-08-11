# AquaGen Kiosk — Raspberry Pi 4 + 7" display

Boots the Pi straight into `https://web.aquagen.co.in/login` fullscreen.

## Quick install (on the Pi)

Copy this `aquagen-kiosk` folder to the Pi (USB stick, `scp`, or git), then:

```bash
cd ~/aquagen-kiosk
bash install.sh
sudo reboot
```

After reboot the dashboard opens fullscreen automatically. That's it.

## What it does
- Installs Chromium + `unclutter` (hides the mouse) + `curl`
- Waits for the network/site before launching (survives boot before Wi-Fi is up)
- Runs Chromium in `--kiosk` mode (no toolbar, no tabs, no address bar)
- Disables screen blanking so the display never sleeps
- Auto-detects Wayland (Pi OS Bookworm) vs X11 (Bullseye) and sets up autostart accordingly

## 7" display resolution
Most 7" panels are **1024×600** or **800×480**. If the image is stretched or has black
borders, set the mode in `/boot/firmware/config.txt`, e.g. for 1024×600:

```
hdmi_group=2
hdmi_mode=87
hdmi_cvt=1024 600 60 6 0 0 0
hdmi_drive=2
```
(For the official 7" DSI touchscreen you don't need any of this — it's auto-detected.)

## Everyday controls
- **Exit kiosk:** plug a keyboard, press `Ctrl+Alt+F2` for a console, or `Alt+F4`.
- **Change the URL:** edit the `URL=` line at the top of `~/aquagen-kiosk/kiosk.sh`, then reboot.
- **Screen still blanks?** `sudo raspi-config` → Display → Screen Blanking → Off.
- **Restart the kiosk without rebooting:** `pkill chromium; ~/aquagen-kiosk/kiosk.sh &`

## Files
| File | Purpose |
|------|---------|
| `kiosk.sh` | Launches Chromium in kiosk mode (edit `URL` here) |
| `install.sh` | Installs packages + sets up autostart |
| `README.md` | This file |
