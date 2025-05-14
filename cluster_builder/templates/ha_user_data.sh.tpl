#!/bin/bash
set -euo pipefail

LOG_FILE="/var/log/k3s_server_install.log"
exec > >(tee -a "$LOG_FILE") 2>&1
echo "=== K3s HA Server Install Script Started at $(date) ==="

# Check if K3s server is already running
if systemctl is-active --quiet k3s; then
    echo "$(date) - K3s is already running. Skipping installation."
    exit 0
fi

# Install K3s HA server and join the cluster
echo "$(date) - Installing K3s HA Server and joining the cluster..."
if ! curl -sfL https://get.k3s.io | K3S_TOKEN="${k3s_token}" sh -s - server \
    --server "https://${master_ip}:6443" \
    --node-external-ip="${external_ip}" \
    --flannel-backend=wireguard-native \
    --flannel-external-ip; then
    echo "$(date) - K3s server installation failed!"
    exit 1
else
    echo "$(date) - K3s server installation succeeded."
fi

echo "=== Script completed at $(date) ==="
