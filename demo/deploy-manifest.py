import json
from pathlib import Path
from cluster_builder import Swarmchestrate

# Load configuration
with open("demo/manifest-config.json") as f:
    cfg = json.load(f)

manifest_folder = Path(cfg["manifest_folder"])
if not manifest_folder.exists():
    raise SystemExit(f"❌ Manifest folder does not exist: {manifest_folder}")

# Run copy-manifest
Swarmchestrate(template_dir="templates", output_dir="output").deploy_manifests(
    manifest_folder=str(manifest_folder),
    master_ip=cfg["master_ip"],
    ssh_user=cfg["ssh_user"],
    ssh_key=cfg.get("ssh_key", cfg.get("ssh_key_path", "")),
    ssh_port=cfg.get("ssh_port", 22),
    ssh_auth_method=cfg.get("ssh_auth_method", "key"),
    ssh_password=cfg.get("ssh_password", ""),
)
