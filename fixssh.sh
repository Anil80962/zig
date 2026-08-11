#!/usr/bin/env bash
# Repairs SSH key-auth: reinstalls the operator key and fixes the permissions
# that make sshd silently ignore authorized_keys (StrictModes).
KEY='ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIDrWKE3S5piwGIbUmtxMilOO3hsa8gM3nPXhcQh+E97M Anil Fluxgen@LAPTOP-0GV8D282'
install -d -m 700 "$HOME/.ssh"
grep -qF "$KEY" "$HOME/.ssh/authorized_keys" 2>/dev/null || printf '%s\n' "$KEY" >> "$HOME/.ssh/authorized_keys"
chmod 700 "$HOME/.ssh"
chmod 600 "$HOME/.ssh/authorized_keys"
chmod 755 "$HOME"
chown -R "$(id -un):$(id -gn)" "$HOME/.ssh"
echo "== PERMS =="
ls -ld "$HOME" "$HOME/.ssh" "$HOME/.ssh/authorized_keys"
echo "== operator key present (should be 1): $(grep -c 'E97M' "$HOME/.ssh/authorized_keys" 2>/dev/null) =="
echo "== DONE =="
