
---
```markdown
# Edge Device Requirements for Swarmchestrate

To integrate edge devices as part of your K3s cluster, ensure that the following **ports** are open on each edge device to enable communication within nodes:

## Inbound Rules:

| Port Range| Protocol| Purpose                                                     |
|-----------|---------|-------------------------------------------------------------|
| 2379-2380 | TCP     | Internal servers communication for embedded etcd            |
| 6443      | TCP     | K3s API server communication                                |
| 8472      | UDP     | Flannel VXLAN (network overlay)                             |
| 10250     | TCP     | Kubelet metrics and communication                           |
| 51820     | UDP     | WireGuard IPv4 (for encrypted networking)                   |
| 51821     | UDP     | WireGuard IPv6 (for encrypted networking)                   |
| 5001      | TCP     | Embedded registry (Spegel)                                  |
| 22        | TCP     | SSH access for provisioning and management                  |
| 80        | TCP     | HTTP communication for web access                           |
| 443       | TCP     | HTTPS communication for secure access                       |
| 53        | UDP     | DNS (CoreDNS) for internal service discovery                |
| 5432      | TCP     | PostgreSQL database access                                  |

---

## Outbound Rule:

| Port Range| Protocol | Purpose                                                |
|-----------|----------|--------------------------------------------------------|
| all       | all      | Allow all outbound traffic for the system's operations |

---

## Edge Device Assumptions:
- The firewall rules are assumed to be open for the required ports on the edge device.
- You can authenticate using either an SSH key pair or an SSH password.
  - If you use SSH keys, specify the `ssh_private_key` path.
  - If you use a password, specify `ssh_password` instead.

---