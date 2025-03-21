#!/bin/bash
%{ if ha }
curl -sfL https://get.k3s.io | K3S_TOKEN=${k3s_token} sh -s - server --cluster-init
%{ else }
curl -sfL https://get.k3s.io | K3S_TOKEN=${k3s_token} sh -s - server
%{ endif }
