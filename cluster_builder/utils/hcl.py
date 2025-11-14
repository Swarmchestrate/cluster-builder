import json
import os
import hcl2
from lark import Tree, Token
import logging
import re

logger = logging.getLogger("cluster_builder")
def add_backend_config(backend_tf_path, conn_str, schema_name):
    """
    Adds a PostgreSQL backend configuration to a Terraform file.
    - `backend_tf_path`: path to backend.tf for this configuration
    - `conn_str`: PostgreSQL connection string
    - `schema_name`: Schema name for Terraform state
    """
    # Check if the backend configuration already exists
    if os.path.exists(backend_tf_path):
        with open(backend_tf_path) as f:
            if 'backend "pg"' in f.read():
                logger.debug("⚠️ Backend config already exists, skipping: %s", backend_tf_path)
                return

    # Build the backend configuration block
    lines = [
        "terraform {",
        '  backend "pg" {',
        f'    conn_str = "{conn_str}"',
        f'    schema_name = "{schema_name}"',
        "  }",
        "}",
    ]

    # Write to backend.tf
    os.makedirs(os.path.dirname(backend_tf_path), exist_ok=True)
    with open(
        backend_tf_path, "w"
    ) as f:  # Use "w" instead of "a" to create/overwrite the file
        f.write("\n".join(lines) + "\n")

    logger.debug("✅ Added PostgreSQL backend config to %s", backend_tf_path)


def add_module_block(main_tf_path, module_name, config):
    """
    Appends a new module block to main.tf for this RA+cluster.
    - `main_tf_path`: path to `main.tf` for this RA+cluster
    - `module_name`: e.g. "master_xyz123"
    - `config`: dict of configuration and module-specific variables
    """
    # Check if the module already exists
    if os.path.exists(main_tf_path):
        with open(main_tf_path) as f:
            if f'module "{module_name}"' in f.read():
                logger.warning("⚠️ Module '%s' already exists, skipping in %s", module_name, main_tf_path)
                return

    # Build the module block
    lines = [f'module "{module_name}" {{', f'  source = "{config["module_source"]}"']
    for k, v in config.items():
        if k == "module_source":
            continue  # Skip the module source since it's already handled
        if isinstance(v, bool):
            v_str = "true" if v else "false"
        elif isinstance(v, (int, float)):
            v_str = str(v)
        elif isinstance(v, (list, dict)):
            v_str = json.dumps(v)
        elif v is None:
            continue
        else:
            v_str = f'"{v}"'
        lines.append(f"  {k} = {v_str}")
    lines.append("}")

    # Write to main.tf
    with open(main_tf_path, "a") as f:
        f.write("\n\n" + "\n".join(lines) + "\n")

    logger.debug("✅ Added module '%s' to %s", module_name, main_tf_path)


def is_target_module_block(tree: Tree, module_name: str) -> bool:
    """
    Check if the tree is a module block with the specified name.
    """
    logger.debug(f"Checking tree with data: {tree.data}, children count: {len(tree.children)}")
    logger.debug(f"Children types and values: {[ (type(c), getattr(c, 'value', None)) for c in tree.children ]}")

    if tree.data != "block":
        logger.debug(f"Rejected: tree.data is '{tree.data}', expected 'block'")
        return False

    # Need at least 3 children: identifier, name, body
    if len(tree.children) < 3:
        logger.debug(f"Rejected: tree has less than 3 children ({len(tree.children)})")
        return False

    # First child should be an identifier tree
    first_child = tree.children[0]
    if not isinstance(first_child, Tree) or first_child.data != "identifier":
        logger.debug(f"Rejected: first child is not an identifier Tree (found {type(first_child)} with data '{getattr(first_child, 'data', None)}')")
        return False

    # First child should have a NAME token with 'module'
    if len(first_child.children) == 0 or not isinstance(first_child.children[0], Token):
        logger.debug("Rejected: first child has no Token children")
        return False

    first_value = first_child.children[0].value
    if first_value != "module":
        logger.debug(f"Rejected: first child token value '{first_value}' is not 'module'")
        return False

    # Second child: could be a Token or Tree with Token child for module name
    second_child = tree.children[1]

    if not isinstance(second_child, Token) or second_child.value != f'"{module_name}"':
        logger.debug(f"Second child check failed: type={type(second_child)}, value={getattr(second_child, 'value', None)} expected=\"{module_name}\"")
        return False

    logger.debug(f"Module block matched for module name '{module_name}'")
    return True

def simple_remove_module(tree, module_name, removed=False):
    """
    A simpler function to remove module blocks that maintains the exact Tree structure
    that the write function expects.
    """
    # Don't remove the root node
    if tree.data == "start":
        # Process only the body of the start rule
        body_node = tree.children[0]

        if isinstance(body_node, Tree) and body_node.data == "body":
            # Debug: Log body node children
            logger.debug("Body Node Children: %s", body_node.children)

            # Create new children list for the body node
            new_body_children = []
            skip_next = False

            # Process body children (these should be blocks and new_line_or_comment nodes)
            for i, child in enumerate(body_node.children):
                if skip_next:
                    skip_next = False
                    continue

                # If this is a block node, check if it's our target
                if (
                    isinstance(child, Tree)
                    and child.data == "block"
                    and is_target_module_block(child, module_name)
                ):
                    removed = True
                    print(f"Module {module_name} found and removed.")  # Debug log

                    # Check if the next node is a new_line_or_comment, and skip it as well
                    if i + 1 < len(body_node.children):
                        next_child = body_node.children[i + 1]
                        if (
                            isinstance(next_child, Tree)
                            and next_child.data == "new_line_or_comment"
                        ):
                            skip_next = True
                else:
                    new_body_children.append(child)

            # Replace body children with filtered list
            new_body = Tree(body_node.data, new_body_children)
            return Tree(tree.data, [new_body]), removed

    # No changes made
    return tree, removed


def remove_module_block(main_tf_path, module_name: str):
    """
    Removes a module block by name from main.tf for this cluster.
    """
    if not os.path.exists(main_tf_path):
        logger.warning("⚠️ No main.tf found at %s", main_tf_path)
        return

    try:
        with open(main_tf_path, "r") as f:
            tree = hcl2.parse(f)
            # Debug: Log the parsed tree structure
            logger.debug("Parsed Tree: %s", tree)
    except Exception as e:
        logger.error("❌ Failed to parse HCL in %s: %s", main_tf_path, e, exc_info=True)
        return

    # Process tree to remove target module block
    new_tree, removed = simple_remove_module(tree, module_name)

    # If no modules were removed
    if not removed:
        logger.warning("⚠️ No module named '%s' found in %s", module_name, main_tf_path)
        return
    
    # Debug: Log the final tree structure after removal
    logger.debug("Final Tree after module removal: %s", new_tree)

    try:
        # Reconstruct HCL
        new_source = hcl2.writes(new_tree)

        # Write back to file
        with open(main_tf_path, "w") as f:
            f.write(new_source)

        logger.debug("🗑️ Removed module '%s' from %s", module_name, main_tf_path)
    except Exception as e:
        logger.error("❌ Failed to reconstruct HCL in %s: %s", main_tf_path, e, exc_info=True)
        # Print more detailed error information
        import traceback

        traceback.print_exc()


def extract_template_variables(template_path):
    """
    Extract variables from a Terraform template file using hcl2.

    Args:
        template_path: Path to the Terraform template file

    Returns:
        Dictionary of variable names to their complete configuration

    Raises:
        ValueError: If the template cannot be parsed or variables cannot be extracted
    """
    try:
        with open(template_path, "r") as f:
            parsed = hcl2.load(f)

        variables = {}

        # Extract variables from the list of variable blocks
        if "variable" in parsed:
            for var_block in parsed["variable"]:
                # Each var_block is a dict with a single key (the variable name)
                for var_name, var_config in var_block.items():
                    variables[var_name] = var_config

        return variables

    except FileNotFoundError:
        logger.warning(f"⚠️ Template file not found: {template_path}")
        return {}

    except Exception as e:
        error_msg = f"Failed to extract variables from {template_path}: {e}"
        logger.error(f"❌ {error_msg}")
        raise ValueError(error_msg)

def add_output_blocks(outputs_tf_path, module_name, output_names):
    existing_text = ""
    
    # Read existing content if the file exists
    if os.path.exists(outputs_tf_path):
        with open(outputs_tf_path, "r") as f:
            existing_text = f.read()

    lines_to_add = []
    updated_lines = []

    # Check and add output blocks
    for output_name in output_names:
        output_block = f'output "{output_name}" {{\n  value = module.{module_name}.{output_name}\n}}'.strip()

        if f'output "{output_name}"' in existing_text:
            # Check if the output block already exists in the file
            logger.debug(f"⚠️ Output '{output_name}' already exists in {outputs_tf_path}. Checking if it needs an update.")
            
            # Only update if the value is None in the current output
            if output_name in ["worker_ip", "ha_ip"] and "None" in existing_text:
                updated_lines.append(output_block)
            elif output_block not in existing_text:
                # If it's there but not the same, we need to update it
                updated_lines.append(output_block)
            else:
                logger.debug(f"Output '{output_name}' is already correctly defined in {outputs_tf_path}.")
            continue
        else:
            # If the output doesn't exist, add it
            lines_to_add.append(output_block)

    # Remove old output blocks before adding or updating new ones
    if lines_to_add or updated_lines:
        # Remove old output definitions for those outputs that will be replaced
        for output_name in output_names:
            existing_text = re.sub(
                f'output "{output_name}".*?}}', '', existing_text, flags=re.DOTALL
            )

        # Combine all new output blocks and updates to add
        final_output = "\n\n".join(lines_to_add + updated_lines)

        # Append new or updated blocks
        with open(outputs_tf_path, "w") as f:
            f.write(existing_text.strip() + "\n\n" + final_output + "\n")

        logger.debug(f"✅ Added/updated outputs for module '{module_name}'")
    else:
        logger.debug(f"⚠️ No new outputs to add or update in {outputs_tf_path}.")