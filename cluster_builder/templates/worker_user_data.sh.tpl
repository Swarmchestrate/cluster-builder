#!/bin/bash
set -euo pipefail

LOG_FILE="/var/log/k3s_agent_install.log"
exec > >(tee -a "$LOG_FILE") 2>&1
echo "=== K3s Agent Install Script Started at $(date) ==="

# Use the provided external IP
echo "Using provided external IP: ${external_ip}"

# Check if K3s agent is already running
if systemctl is-active --quiet k3s-agent; then
    echo "$(date) - K3s agent is already running. Skipping installation."
else
    echo "$(date) - K3s agent is not running. Proceeding with installation..."

    export K3S_URL="https://${master_ip}:6443"
    export K3S_TOKEN="${k3s_token}"

    # Install the K3s agent and join the cluster
    if ! curl -sfL https://get.k3s.io | sh -s - agent --node-external-ip="${external_ip}"; then
        echo "$(date) - K3s agent installation failed!"
        exit 1
    else
        echo "$(date) - K3s agent installation succeeded."
    fi
fi

echo "=== Script completed at $(date) ==="
