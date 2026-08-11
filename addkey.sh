#!/usr/bin/env bash
# Installs the operator's SSH public key so the kiosk can be set up remotely.
set -e
install -d -m 700 ~/.ssh
KEY='ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIDrWKE3S5piwGIbUmtxMilOO3hsa8gM3nPXhcQh+E97M Anil Fluxgen@LAPTOP-0GV8D282'
grep -qF "$KEY" ~/.ssh/authorized_keys 2>/dev/null || printf '%s\n' "$KEY" >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
chmod 755 ~
echo "KEY INSTALLED for $(whoami)@$(hostname)"
ssh-keygen -lf ~/.ssh/authorized_keys | tail -1
