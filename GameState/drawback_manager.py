import importlib
import os

DRAWBACKS = {}  # Stores all loaded drawbacks dynamically


def load_drawbacks():
    """
    Loads all drawbacks dynamically from the 'drawbacks' directory.
    Each drawback is a separate Python module defining its rules.
    """
    drawbacks_dir = os.path.join(os.path.dirname(__file__), "drawbacks")
    if not os.path.exists(drawbacks_dir):
        print("Warning: Drawbacks directory not found!")
        return

    for filename in os.listdir(drawbacks_dir):
        if filename.endswith(".py") and filename != "__init__.py":
            drawback_name = filename[:-3]  # Remove '.py' extension
            try:
                module = importlib.import_module(f"GameState.drawbacks.{drawback_name}")
                if hasattr(module, "drawback_info"):
                    DRAWBACKS[drawback_name] = module.drawback_info
                else:
                    print(f"Warning: Drawback '{drawback_name}' is missing 'drawback_info'.")
            except Exception as e:
                print(f"Error loading drawback '{drawback_name}': {e}")


def get_drawback_info(drawback_name):
    """
    Retrieves drawback rules for a given drawback name.
    :param drawback_name: Name of the drawback to fetch.
    :return: Drawback rule dictionary or an empty dict if not found.
    """
    return DRAWBACKS.get(drawback_name, {})


# Load drawbacks when the module is first imported
load_drawbacks()
