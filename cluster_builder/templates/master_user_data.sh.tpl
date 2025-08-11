#!/bin/bash
set -euo pipefail

LOG_FILE="/var/log/k3s_server_install.log"
exec > >(tee -a "$LOG_FILE") 2>&1
echo "=== K3s Server Install Script Started at $(date) ==="

# Function to log messages with timestamp
log_message() {
    echo "$(date) - $1"
}

# Check if K3s server is already running
if systemctl is-active --quiet k3s; then
    log_message "K3s is already running. Skipping installation."
else
    log_message "K3s is not running. Proceeding with installation..."


# Use the provided public IP
log_message "Using provided public IP: ${public_ip}"

# Templated installation based on HA configuration
if [[ "${ha}" == "true" ]]; then
    log_message "Installing in HA mode using cluster-init..."
    curl -sfL https://get.k3s.io | INSTALL_K3S_EXEC="--cluster-init --node-external-ip=${public_ip} --flannel-backend=wireguard-native --flannel-external-ip" K3S_TOKEN="${k3s_token}" sh -s - server
    if [[ $? -ne 0 ]]; then
        log_message "ERROR: Failed to install K3s in HA mode."
        exit 1
    fi
else
    log_message "Installing in single-server mode..."
    curl -sfL https://get.k3s.io | INSTALL_K3S_EXEC="--node-external-ip=${public_ip} --flannel-backend=wireguard-native --flannel-external-ip" K3S_TOKEN="${k3s_token}" sh -s - server
    if [[ $? -ne 0 ]]; then
        log_message "ERROR: Failed to install K3s in single-server mode."
        exit 1
    fi
fi

log_message "K3s installation completed successfully."
fi

log_message "=== Script completed at $(date) ==="
