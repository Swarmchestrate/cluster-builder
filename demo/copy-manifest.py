import json
from pathlib import Path
from cluster_builder import Swarmchestrate

# Load configuration
with open("demo/manifest-config.json") as f:
    cfg = json.load(f)

manifest_folder = Path(cfg["manifest_folder"])
manifest_folder.exists() or exit(f"❌ Manifest folder does not exist: {manifest_folder}")

# Run copy-manifest
Swarmchestrate(template_dir="templates", output_dir="output").run_copy_manifests_tf(
    manifest_folder=str(manifest_folder),
    master_ip=cfg["master_ip"],
    ssh_key_path=cfg["ssh_key_path"],
    ssh_user=cfg["ssh_user"]
)
