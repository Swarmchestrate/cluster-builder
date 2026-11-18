import pytest

from cluster_builder.config.cluster import ClusterConfig
from cluster_builder.swarmchestrate import Swarmchestrate


class TemplateManagerStub:
    def get_module_source_path(self, cloud):
        return f"../templates/{cloud}"


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
