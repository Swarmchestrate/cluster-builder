import os
import re
import tempfile
import hcl2
import logging
from cluster_builder.utils.hcl import (
    add_backend_config,
    add_module_block,
    add_output_blocks,
    remove_module_block,
    sanitize_module_name,
)
# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def test_add_backend_config_creates_file():
    logger.debug("Starting test_add_backend_config_creates_file...")
    # Arrange
    with tempfile.TemporaryDirectory() as temp_dir:
        backend_tf_path = os.path.join(temp_dir, "backend.tf")
        conn_str = "postgres://user:password@localhost:5432/dbname"
        schema_name = "test_schema"

        # Act
        add_backend_config(backend_tf_path, conn_str, schema_name)

        # Assert
        assert os.path.exists(backend_tf_path), "backend.tf file was not created"
        with open(backend_tf_path, "r") as f:
            parsed = hcl2.load(f)
            assert "terraform" in parsed, "Terraform block not found"
            assert "backend" in parsed["terraform"][0], "Backend block not found"
            assert "pg" in parsed["terraform"][0]["backend"][0], (
                "Backend type 'pg' not found"
            )
            assert parsed["terraform"][0]["backend"][0]["pg"]["conn_str"] == conn_str, (
                "Connection string not found or incorrect"
            )
            assert (
                parsed["terraform"][0]["backend"][0]["pg"]["schema_name"] == schema_name
            ), "Schema name not found or incorrect"


def test_add_backend_config_skips_existing_file():
    logger.debug("Starting test_add_backend_config_skips_existing_file...")
    # Arrange
    with tempfile.TemporaryDirectory() as temp_dir:
        backend_tf_path = os.path.join(temp_dir, "backend.tf")
        conn_str = "***localhost:5432/dbname"
        schema_name = "test_schema"

        # Create an existing backend.tf file
        with open(backend_tf_path, "w") as f:
            f.write('backend "pg" { conn_str = "existing" schema_name = "existing" }')

        # Act
        add_backend_config(backend_tf_path, conn_str, schema_name)

        # Assert
        with open(backend_tf_path, "r") as f:
            content = f.read()
            logger.debug("Backend TF content: %s", content)
            assert 'conn_str = "existing"' in content, "Existing content was overwritten"
            assert 'schema_name = "existing"' in content, "Existing content was overwritten"

def test_remove_module_block_removes_existing_module():
    logger.info("Starting test_remove_module_block_removes_existing_module...")
    # Arrange
    with tempfile.TemporaryDirectory() as temp_dir:
        main_tf_path = os.path.join(temp_dir, "main.tf")
        module_name = "test_module1"
        content = f"""
        module "{module_name}" {{
            source = "some/source"
            param1 = "value1"
        }}
        """
        with open(main_tf_path, "w") as f:
            f.write(content)
        logger.info("Initial main.tf content:\n%r", content)

        # Act
        logger.info("Calling remove_module_block with file=%s and module_name=%s", main_tf_path, module_name)
        remove_module_block(main_tf_path, module_name)

        # Assert
        with open(main_tf_path, "r") as f:
            remaining_content = f.read()
            logger.info("Remaining content after removal: %s", remaining_content)
        
        logger.info("Remaining content after removal:\n%r", remaining_content)

        # Debug check: does it still contain module name?
        if module_name in remaining_content:
            logger.warning("Module name %r still found in file content!", module_name)
        else:
            logger.debug("Module name %r not found in file after removal.", module_name)

        # Assert
        assert module_name not in remaining_content, "Module block was not removed"


def test_remove_module_block_no_matching_module():
    logger.debug("Starting test_remove_module_block_no_matching_module...")
    # Arrange
    with tempfile.TemporaryDirectory() as temp_dir:
        main_tf_path = os.path.join(temp_dir, "main.tf")
        module_name = "non_existent_module"
        content = """\
module "existing_module" {
    source = "some/source"
    param1 = "value1"
}
"""
        with open(main_tf_path, "w") as f:
            f.write(content)

        # Act
        remove_module_block(main_tf_path, module_name)

        # Assert
        with open(main_tf_path, "r") as f:
            remaining_content = f.read()
            assert "existing_module" in remaining_content, (
                "Existing module block was incorrectly removed"
            )


def test_remove_module_block_handles_missing_file():
    # Arrange
    with tempfile.TemporaryDirectory() as temp_dir:
        main_tf_path = os.path.join(temp_dir, "non_existent_main.tf")
        module_name = "test_module"

        # Act & Assert
        try:
            remove_module_block(main_tf_path, module_name)
        except Exception as e:
            assert False, f"Exception was raised: {e}"


def test_remove_module_block_handles_invalid_hcl():
    # Arrange
    with tempfile.TemporaryDirectory() as temp_dir:
        main_tf_path = os.path.join(temp_dir, "main.tf")
        module_name = "test_module"
        invalid_content = """
        module "test_module" {
            source = "some/source"
            param1 = "value1"
        """  # Missing closing brace
        with open(main_tf_path, "w") as f:
            f.write(invalid_content)

        # Act & Assert
        try:
            remove_module_block(main_tf_path, module_name)
        except Exception as e:
            assert False, f"Exception was raised: {e}"


def test_add_module_block_creates_module():
    # Arrange
    with tempfile.TemporaryDirectory() as temp_dir:
        main_tf_path = os.path.join(temp_dir, "main.tf")
        module_name = "test_module"
        config = {
            "module_source": "some/source",
            "param1": "value1",
            "param2": 42,
            "param3": True,
        }

        # Act
        add_module_block(main_tf_path, module_name, config)

        # Assert
        assert os.path.exists(main_tf_path), "main.tf file was not created"
        with open(main_tf_path, "r") as f:
            parsed = hcl2.load(f)
            assert "module" in parsed, "Module block not found"
            assert module_name in parsed["module"][0], (
                f"Module '{module_name}' not found"
            )
            module_block = parsed["module"][0][module_name]
            assert module_block["source"] == config["module_source"], (
                "Module source was not added or incorrect"
            )
            assert module_block["param1"] == "value1", (
                "String parameter was not added or incorrect"
            )
            assert module_block["param2"] == 42, (
                "Integer parameter was not added or incorrect"
            )
            assert module_block["param3"] is True, (
                "Boolean parameter was not added or incorrect"
            )


def test_add_module_block_skips_existing_module():
    # Arrange
    with tempfile.TemporaryDirectory() as temp_dir:
        main_tf_path = os.path.join(temp_dir, "main.tf")
        module_name = "test_module"
        existing_content = f"""
        module "{module_name}" {{
            source = "existing/source"
        }}
        """
        with open(main_tf_path, "w") as f:
            f.write(existing_content)

        config = {
            "module_source": "some/source",
            "param1": "value1",
        }

        # Act
        add_module_block(main_tf_path, module_name, config)

        # Assert
        with open(main_tf_path, "r") as f:
            content = f.read()
            assert 'source = "existing/source"' in content, (
                "Existing module block was overwritten"
            )
            assert 'param1 = "value1"' not in content, (
                "New parameters were incorrectly added to existing module"
            )


def test_add_module_block_appends_to_existing_file():
    # Arrange
    with tempfile.TemporaryDirectory() as temp_dir:
        main_tf_path = os.path.join(temp_dir, "main.tf")
        existing_content = """
        module "existing_module" {
            source = "existing/source"
        }
        """
        with open(main_tf_path, "w") as f:
            f.write(existing_content)

        module_name = "new_module"
        config = {
            "module_source": "new/source",
            "param1": "value1",
        }

        # Act
        add_module_block(main_tf_path, module_name, config)

        # Assert
        with open(main_tf_path, "r") as f:
            content = f.read()
            assert 'module "existing_module"' in content, (
                "Existing module block was removed"
            )
            assert f'module "{module_name}"' in content, (
                "New module block was not added"
            )
            assert 'source = "new/source"' in content, "New module source was not added"


def test_sanitize_module_name_replaces_invalid_characters():
    module_name = "aws-test-cp1"
    sanitized = sanitize_module_name(module_name)

    assert sanitized == "aws_test_cp1"
    assert "-" not in sanitized
    assert re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", sanitized)


def test_add_module_block_with_hyphenated_name():
    with tempfile.TemporaryDirectory() as temp_dir:
        main_tf_path = os.path.join(temp_dir, "main.tf")
        module_name = "aws-test-cp1"
        config = {
            "module_source": "some/source",
            "param1": "value1",
        }

        add_module_block(main_tf_path, module_name, config)

        with open(main_tf_path, "r") as f:
            content = f.read()

        assert 'module "aws_test_cp1"' in content
        assert 'module "aws-test-cp1"' not in content
        assert 'param1 = "value1"' in content


def test_add_module_block_migrates_legacy_hyphenated_label():
    with tempfile.TemporaryDirectory() as temp_dir:
        main_tf_path = os.path.join(temp_dir, "main.tf")
        module_name = "aws-test-cp1"
        legacy_content = f"""
module \"{module_name}\" {{
    source = \"some/source\"
    resource_name = \"{module_name}\"
}}
"""
        with open(main_tf_path, "w") as f:
            f.write(legacy_content)

        config = {
            "module_source": "some/source",
            "resource_name": module_name,
            "cloud": "aws",
            "k3s_role": "master",
            "ssh_user": "ubuntu",
            "ssh_key": "path/to/key",
            "ami": "ami-123",
        }

        add_module_block(main_tf_path, module_name, config)

        with open(main_tf_path, "r") as f:
            content = f.read()

        assert 'module "aws_test_cp1"' in content
        assert 'module "aws-test-cp1"' not in content

def test_add_output_blocks_uses_sanitized_module_name():
    with tempfile.TemporaryDirectory() as temp_dir:
        outputs_tf_path = os.path.join(temp_dir, "outputs.tf")
        module_name = "aws-test-cp1"
        output_names = ["cluster_name", "master_ip"]

        add_output_blocks(outputs_tf_path, module_name, output_names)

        with open(outputs_tf_path, "r") as f:
            content = f.read()

        assert 'value = module.aws_test_cp1.cluster_name' in content
        assert 'value = module.aws_test_cp1.master_ip' in content
        assert 'value = module["aws-test-cp1"].cluster_name' not in content


def test_add_output_blocks_supports_different_module_labels():
    with tempfile.TemporaryDirectory() as temp_dir:
        outputs_tf_path = os.path.join(temp_dir, "outputs.tf")

        add_output_blocks(outputs_tf_path, "aws-test-cp1", ["cluster_name"])
        add_output_blocks(outputs_tf_path, "sztaki-test2", ["cluster_name"])

        with open(outputs_tf_path, "r") as f:
            content = f.read()

        assert 'value = module.aws_test_cp1.cluster_name' in content
        assert 'value = module.sztaki_test2.cluster_name' in content
