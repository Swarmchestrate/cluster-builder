#!/bin/bash
set -euo pipefail

LOG_FILE="/var/log/k3s_agent_install.log"
exec > >(tee -a "$LOG_FILE") 2>&1
echo "=== K3s Agent Install Script Started at $(date) ==="

# Function to log messages with timestamp
log_message() {
    echo "$(date) - $1"
}

# Use the provided public IP
log_message "Using provided public IP: ${public_ip}"

# Check if K3s agent is already running
if systemctl is-active --quiet k3s-agent; then
    log_message "K3s agent is already running. Skipping installation."
else
    log_message "K3s agent is not running. Proceeding with installation..."

    export K3S_URL="https://${master_ip}:6443"
    export K3S_TOKEN="${k3s_token}"

    # Install the K3s agent and join the cluster
    if ! curl -sfL https://get.k3s.io | sh -s - agent --node-external-ip="${public_ip}" --node-name="${resource_name}"; then
        log_message "ERROR: K3s agent installation failed!"
        exit 1
    else
        log_message "K3s agent installation succeeded."
    fi
fi

log_message "=== Script completed at $(date) ==="
