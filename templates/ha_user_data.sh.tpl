#!/bin/bash
curl -sfL https://get.k3s.io | K3S_TOKEN=${k3s_token} sh -s - server --server https://${master_ip}:6443
