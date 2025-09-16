#!/bin/bash
set -euo pipefail

LOG_FILE="/var/log/k3s_server_install.log"
exec > >(tee -a "$LOG_FILE") 2>&1
echo "=== K3s HA Server Install Script Started at $(date) ==="

# Function to log messages with timestamp
log_message() {
    echo "$(date) - $1"
}

# Check if K3s server is already running
if systemctl is-active --quiet k3s; then
    log_message "K3s is already running. Skipping installation."
    exit 0
fi

# Install K3s HA server and join the cluster
log_message "Installing K3s HA Server and joining the cluster..."
if ! curl -sfL https://get.k3s.io | K3S_TOKEN="${k3s_token}" sh -s - server \
    --server "https://${master_ip}:6443" \
    --node-external-ip="${public_ip}" \
    --node-name="${resource_name}" \
    --flannel-backend=wireguard-native \
    --flannel-external-ip; then
    log_message "ERROR: K3s server installation failed!"
    exit 1
else
    log_message "K3s server installation succeeded."
fi

log_message "=== Script completed at $(date) ==="
