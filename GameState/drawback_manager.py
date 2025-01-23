import importlib
import os
import sys

# Dictionary to store dynamically loaded drawbacks
DRAWBACKS = {}

def load_drawbacks():
    """
    Dynamically loads all drawbacks from the 'drawbacks' directory.
    Each drawback module defines specific game rule modifications.
    """
    drawbacks_dir = os.path.join(os.path.dirname(__file__), "drawbacks")

    if not os.path.exists(drawbacks_dir):
        print("Warning: Drawbacks directory not found!")
        return

    # Ensure the drawbacks directory is a valid Python module path
    if drawbacks_dir not in sys.path:
        sys.path.append(drawbacks_dir)

    # Load each Python file in the drawbacks directory (except __init__.py)
    for filename in os.listdir(drawbacks_dir):
        if filename.endswith(".py") and filename != "__init__.py":
            drawback_name = filename[:-3]  # Remove '.py' extension
            module_path = f"GameState.drawbacks.{drawback_name}"

            try:
                module = importlib.import_module(module_path)
                
                if hasattr(module, "DRAWBACK_INFO"):
                    DRAWBACKS[drawback_name] = module.DRAWBACK_INFO
                    print(f"Loaded drawback: {drawback_name}")
                else:
                    print(f"Warning: Drawback '{drawback_name}' is missing 'DRAWBACK_INFO'.")

            except Exception as e:
                print(f"Error loading drawback '{drawback_name}': {e}")


def get_drawback_info(drawback_name):
    """
    Retrieves the drawback rules based on the given drawback name.
    :param drawback_name: Name of the drawback to fetch.
    :return: Dictionary containing the drawback details or an empty dict if not found.
    """
    return DRAWBACKS.get(drawback_name, {})


# Automatically load drawbacks when the module is first imported
load_drawbacks()
