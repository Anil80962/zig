#!/usr/bin/env bash
# One-time: allow user zig to run nmcli without a password, so the WiFi manager
# page can change WiFi networks. Run with: sudo bash setup-wifi-sudo.sh
set -e
echo 'zig ALL=(ALL) NOPASSWD: /usr/bin/nmcli' > /etc/sudoers.d/zig-nmcli
chmod 440 /etc/sudoers.d/zig-nmcli
echo "Done — WiFi 'Connect' is now enabled. You can return to the kiosk."
