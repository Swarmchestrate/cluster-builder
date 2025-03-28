import os
import hcl2
from lark import Tree, Token


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
                print("⚠️  Backend configuration already exists — skipping.")
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

    print(f"✅ Added PostgreSQL backend configuration to {backend_tf_path}")


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
                print(f"⚠️  Module '{module_name}' already exists — skipping.")
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
        elif v is None:
            continue
        else:
            v_str = f'"{v}"'
        lines.append(f"  {k} = {v_str}")
    lines.append("}")

    # Write to main.tf
    with open(main_tf_path, "a") as f:
        f.write("\n\n" + "\n".join(lines) + "\n")

    print(f"✅ Added module '{module_name}' to {main_tf_path}")


def is_target_module_block(tree: Tree, module_name: str) -> bool:
    """
    Check if the tree is a module block with the specified name.
    """
    if tree.data != "block":
        return False

    # Need at least 3 children: identifier, name, body
    if len(tree.children) < 3:
        return False

    # First child should be an identifier tree
    first_child = tree.children[0]
    if not isinstance(first_child, Tree) or first_child.data != "identifier":
        return False

    # First child should have a NAME token with 'module'
    if len(first_child.children) == 0 or not isinstance(first_child.children[0], Token):
        return False

    if first_child.children[0].value != "module":
        return False

    # Second child should be a STRING_LIT token with module name
    second_child = tree.children[1]
    if not isinstance(second_child, Token) or second_child.value != f'"{module_name}"':
        return False

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
        print(f"⚠️  No main.tf found at {main_tf_path}")
        return

    try:
        with open(main_tf_path, "r") as f:
            tree = hcl2.parse(f)
    except Exception as e:
        print(f"❌ Failed to parse HCL: {e}")
        return

    # Process tree to remove target module block
    new_tree, removed = simple_remove_module(tree, module_name)

    # If no modules were removed
    if not removed:
        print(f"⚠️  No module named '{module_name}' found in {main_tf_path}")
        return

    try:
        # Reconstruct HCL
        new_source = hcl2.writes(new_tree)

        # Write back to file
        with open(main_tf_path, "w") as f:
            f.write(new_source)

        print(f"🗑️  Removed module '{module_name}' from {main_tf_path}")
    except Exception as e:
        print(f"❌ Failed to reconstruct HCL: {e}")
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
        print(f"Warning: Template file not found: {template_path}")
        return {}

    except Exception as e:
        error_msg = f"Failed to extract variables from {template_path}: {e}"
        print(f"Error: {error_msg}")
        raise ValueError(error_msg)
