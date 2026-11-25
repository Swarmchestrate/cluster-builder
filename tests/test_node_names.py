import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from cluster_builder.config.cluster import ClusterConfig
from cluster_builder.swarmchestrate import Swarmchestrate


class TemplateManagerStub:
    def get_module_source_path(self, cloud):
        return f"../templates/{cloud}"


@pytest.mark.skipif(shutil.which("tofu") is None, reason="OpenTofu is not installed")
@pytest.mark.parametrize("cloud", ["aws", "openstack", "edge"])
@pytest.mark.parametrize(
    "node_labels", [[], ["environment=production", "region=eu-west-1"]]
)
def test_node_configs_include_resource_name_label(tmp_path, node_labels, cloud):
    template = (
        Path(__file__).resolve().parents[1]
        / f"cluster_builder/templates/{cloud}/main.tf"
    ).read_text()
    labels_local = re.search(r"^  node_labels_yaml = .+$", template, re.MULTILINE)
    configs = re.findall(
        r"^  config = (<<-EOT\n.*?^  EOT)", template, re.MULTILINE | re.DOTALL
    )
    assert labels_local is not None
    assert len(configs) == 4
    config_locals = "\n".join(
        f"  config_{index} = {config}" for index, config in enumerate(configs)
    )
    (tmp_path / "main.tf").write_text(
        'variable "node_labels" { type = list(string) }\n'
        'variable "resource_name" { type = string }\n'
        'variable "cluster_name" { type = string }\n'
        f"locals {{\n{labels_local.group()}\n{config_locals}\n}}\n"
    )
    result = subprocess.run(
        [
            "tofu",
            "console",
            "-no-color",
            f"-var=node_labels={json.dumps(node_labels)}",
            "-var=resource_name=worker-node-01",
            "-var=cluster_name=test-cluster",
        ],
        input="jsonencode([for config in [local.config_0, local.config_1, local.config_2, local.config_3] : yamldecode(config)])\n",
        text=True,
        capture_output=True,
        cwd=tmp_path,
        check=True,
    )
    rendered_configs = json.loads(json.loads(result.stdout))
    for config in rendered_configs:
        assert config["node-name"] == "worker-node-01"
        assert config["node-label"] == [
            *node_labels,
            "labels.swarmchestrate.eu/ms_id=worker-node-01",
        ]


def test_prepare_normalizes_underscores_in_resource_name(tmp_path):
    cluster_config = ClusterConfig(TemplateManagerStub(), str(tmp_path))

    _, prepared_config = cluster_config.prepare(
        {
            "cloud": "aws",
            "k3s_role": "worker",
            "cluster_name": "test_cluster",
            "resource_name": "worker_node_01",
            "k3s_token": "test-token",
        }
    )

    assert prepared_config["resource_name"] == "worker-node-01"


def test_prepare_still_rejects_resource_names_invalid_after_normalization(tmp_path):
    cluster_config = ClusterConfig(TemplateManagerStub(), str(tmp_path))

    with pytest.raises(ValueError, match="RFC 1123 compliant"):
        cluster_config.prepare(
            {
                "cloud": "aws",
                "k3s_role": "worker",
                "cluster_name": "test_cluster",
                "resource_name": "_worker_node_01",
                "k3s_token": "test-token",
            }
        )


@pytest.mark.parametrize("resource_name", ["worker_node_01", "worker-node-01"])
def test_remove_node_uses_sanitized_module_name(tmp_path, monkeypatch, resource_name):
    orchestrator = Swarmchestrate.__new__(Swarmchestrate)
    monkeypatch.setattr(
        orchestrator, "get_cluster_output_dir", lambda cluster_name: str(tmp_path)
    )
    (tmp_path / "main.tf").touch()

    commands = []
    removed_modules = []
    monkeypatch.setattr(
        "cluster_builder.swarmchestrate.CommandExecutor.run_command",
        lambda command, **kwargs: commands.append(command),
    )
    monkeypatch.setattr(
        "cluster_builder.swarmchestrate.hcl.remove_module_block",
        lambda path, module_name: removed_modules.append(module_name),
    )

    orchestrator.remove_node("test_cluster", resource_name)

    assert ["tofu", "workspace", "select", "worker_node_01"] in commands
    assert ["tofu", "workspace", "delete", "-force", "worker_node_01"] in commands
    assert removed_modules == ["worker_node_01"]
