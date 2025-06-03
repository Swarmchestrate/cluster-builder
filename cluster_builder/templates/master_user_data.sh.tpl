#!/bin/bash
set -euo pipefail

LOG_FILE="/var/log/k3s_server_install.log"
exec > >(tee -a "$LOG_FILE") 2>&1
echo "=== K3s Server Install Script Started at $(date) ==="

# Check if K3s server is already running
if systemctl is-active --quiet k3s; then
    echo "$(date) - K3s is already running. Skipping installation."
    exit 0
fi

# Use external IP passed from Terraform
external_ip="${external_ip}"
echo "Using external IP provided: ${external_ip}"

# Templated installation based on HA configuration
%{ if ha != null && ha }
echo "$(date) - Installing in HA mode using cluster-init..."
curl -sfL https://get.k3s.io | INSTALL_K3S_EXEC="--cluster-init --node-external-ip=${external_ip} --flannel-backend=wireguard-native --flannel-external-ip" K3S_TOKEN="${k3s_token}" sh -s - server
%{ else }
echo "$(date) - Installing in single-server mode..."
curl -sfL https://get.k3s.io | INSTALL_K3S_EXEC="--node-external-ip=${external_ip} --flannel-backend=wireguard-native --flannel-external-ip" K3S_TOKEN="${k3s_token}" sh -s - server
%{ endif }

echo "=== Script completed at $(date) ==="
