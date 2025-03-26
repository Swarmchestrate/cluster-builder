import os
import tempfile
import hcl2
from cluster_builder.utils.hcl import (
    add_backend_config,
    add_module_block,
    remove_module_block,
)


def test_add_backend_config_creates_file():
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
    # Arrange
    with tempfile.TemporaryDirectory() as temp_dir:
        backend_tf_path = os.path.join(temp_dir, "backend.tf")
        conn_str = "postgres://user:password@localhost:5432/dbname"
        schema_name = "test_schema"

        # Create an existing backend.tf file
        with open(backend_tf_path, "w") as f:
            f.write('backend "pg" { conn_str = "existing" schema_name = "existing" }')

        # Act
        add_backend_config(backend_tf_path, conn_str, schema_name)

        # Assert
        with open(backend_tf_path, "r") as f:
            parsed = hcl2.parse(f)
            print(parsed)
            f.seek(0)
            content = f.read()
            assert 'conn_str = "existing"' in content, (
                "Existing content was overwritten"
            )
            assert 'schema_name = "existing"' in content, (
                "Existing content was overwritten"
            )


def test_remove_module_block_removes_existing_module():
    # Arrange
    with tempfile.TemporaryDirectory() as temp_dir:
        main_tf_path = os.path.join(temp_dir, "main.tf")
        module_name = "test_module"
        content = f"""
        module "{module_name}" {{
            source = "some/source"
            param1 = "value1"
        }}
        """
        with open(main_tf_path, "w") as f:
            f.write(content)

        # Act
        remove_module_block(main_tf_path, module_name)

        # Assert
        with open(main_tf_path, "r") as f:
            remaining_content = f.read()
            assert module_name not in remaining_content, "Module block was not removed"


def test_remove_module_block_no_matching_module():
    # Arrange
    with tempfile.TemporaryDirectory() as temp_dir:
        main_tf_path = os.path.join(temp_dir, "main.tf")
        module_name = "non_existent_module"
        content = """
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
            assert 'param1 = "value1"' in content, "New module parameter was not added"
