import json

OUTPUT_FILE = "demo/lead_RA_outputs.json"

def write_outputs(cluster_name, master_ip, k3s_token, node_name):
    data = {
        "cluster_name": cluster_name,
        "master_ip": master_ip,
        "k3s_token": k3s_token,
        "node_name": node_name
    }
    with open(OUTPUT_FILE, "w") as f:
        json.dump(data, f, indent=2)

def read_outputs():
    with open(OUTPUT_FILE, "r") as f:
        return json.load(f)