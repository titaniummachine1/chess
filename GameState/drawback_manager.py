import importlib
import os
import drawbacks

DRAWBACKS = {}

def load_drawbacks():
    """Dynamically import all drawback modules in the 'drawbacks' directory."""
    global DRAWBACKS
    drawback_folder = os.path.dirname(drawbacks.__file__)

    for file in os.listdir(drawback_folder):
        if file.endswith(".py") and file != "__init__.py":
            module_name = f"drawbacks.{file[:-3]}"  # Convert filename to module import path
            module = importlib.import_module(module_name)
            DRAWBACKS[file[:-3]] = module.DRAWBACK_INFO

def get_drawback_info(drawback_name):
    """Retrieve drawback details by name."""
    return DRAWBACKS.get(drawback_name, {"legal_moves": lambda board, move: True, "loss_condition": None})

# Load drawbacks on startup
load_drawbacks()
