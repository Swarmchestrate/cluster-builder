#!/usr/bin/env bash
set -euo pipefail

# Install OpenTofu (required by cluster_builder to run apply/destroy)
if ! command -v tofu >/dev/null 2>&1; then
  curl -fsSL --proto '=https' --tlsv1.2 https://get.opentofu.org/install-opentofu.sh -o /tmp/install-opentofu.sh
  chmod +x /tmp/install-opentofu.sh
  sudo /tmp/install-opentofu.sh --install-method standalone
  rm -f /tmp/install-opentofu.sh
fi

# Install SSH client (needed to reach K3s nodes), skip if already present
# apt-get update may fail on unrelated third-party repos in the base image, so don't hard-fail on it
if ! command -v ssh >/dev/null 2>&1; then
  sudo apt-get update -y || true
  sudo apt-get install -y openssh-client
fi

# Install the project in editable mode with its dependencies
pip install -e .
