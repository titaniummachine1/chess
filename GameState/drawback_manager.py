import importlib
import os
import sys
import chess

# Dictionary to store dynamically loaded drawbacks
DRAWBACKS = {}

def load_drawbacks():
    """
    Dynamically loads all drawbacks from the 'drawbacks' directory.
    Each drawback module defines specific game rule modifications.
    """
    current_dir = os.path.dirname(__file__)
    drawbacks_dir = os.path.join(current_dir, "drawbacks")

    if not os.path.exists(drawbacks_dir):
        print(f"Warning: Drawbacks directory not found at: {drawbacks_dir}")
        return

    # Ensure the parent directory is in sys.path to import 'drawbacks' package
    parent_dir = os.path.dirname(current_dir)
    if (parent_dir not in sys.path):
        sys.path.append(parent_dir)

    # Load each Python file in the 'drawbacks' directory (except __init__.py)
    try:
        for filename in os.listdir(drawbacks_dir):
            if filename.endswith(".py") and filename != "__init__.py":
                drawback_name = filename[:-3]  # remove '.py'
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
                    import traceback
                    traceback.print_exc()
    except Exception as e:
        print(f"Error accessing drawbacks directory: {e}")
        import traceback
        traceback.print_exc()

# Add default values for our drawbacks with configurable parameters
if "just_passing_through" in DRAWBACKS:
    if "params" not in DRAWBACKS["just_passing_through"]:
        DRAWBACKS["just_passing_through"]["params"] = {"rank": 3}

if "blinded_by_the_sun" in DRAWBACKS:
    if "params" not in DRAWBACKS["blinded_by_the_sun"]:
        DRAWBACKS["blinded_by_the_sun"]["params"] = {"sun_square": chess.E4}

# Backup builtin drawbacks in case dynamic loading fails
BUILTIN_DRAWBACKS = {
    "no_knight_moves": {
        "description": "Your knights can't move",
        "check_move": "check_knight_moves",
        "supported": True
    },
    "no_bishop_captures": {
        "description": "Your bishops can't capture",
        "check_move": "check_bishop_captures",
        "supported": True
    },
    "no_knight_captures": {
        "description": "Your knights can't capture", 
        "check_move": "check_knight_captures",
        "supported": True,
        "alt_name": "Horse Tranquilizer"  # Add alternate name for UI display
    },
    "punching_down": {
        "description": "Your pieces can't capture pieces worth more than them",
        "check_move": "check_punching_down",
        "supported": True
    },
    "professional_courtesy": {
        "description": "You can't capture non-pawn pieces with pieces of the same type",
        "check_move": "check_professional_courtesy",
        "supported": True
    },
    "just_passing_through": {
        "description": "You can't capture on a specific rank",
        "check_move": "check_just_passing_through",
        "supported": True,
        "params": {"rank": 3},  # Configurable rank (0-7)
        "configurable": True,
        "config_type": "rank",
        "config_name": "Restricted Rank"
    },
    "forward_march": {
        "description": "Can't move backwards",
        "check_move": "check_forward_march",
        "supported": True
    },
    "get_down_mr_president": {
        "description": "You can't move your king when in check",
        "check_move": "check_get_down_mr_president",
        "supported": True
    },
    "vegan": {
        "description": "You can't capture knights",
        "check_move": "check_vegan",
        "supported": True
    },
    "chivalry": {
        "description": "You can only capture rooks and queens with knights",
        "check_move": "check_chivalry",
        "supported": True
    },
    "blinded_by_the_sun": {
        "description": "You can't end your turn attacking a specific square",
        "check_move": "check_blinded_by_the_sun",
        "supported": True,
        "params": {"sun_square": chess.E4},  # Configurable sun square
        "configurable": True,
        "config_type": "square",
        "config_name": "Sun Square"
    },
    "leaps_and_bounds": {
        "description": "You can't move a piece adjacent to where it was",
        "check_move": "check_leaps_and_bounds",
        "supported": True
    },
    "friendly_fire": {
        "description": "Can only move to squares defended by your other pieces",
        "check_move": "check_friendly_fire",
        "supported": True
    },
    "covering_fire": {
        "description": "You can only capture a piece if you could capture it two different ways",
        "check_move": "check_covering_fire",
        "supported": True
    },
    "atomic_bomb": {
        "description": "If your opponent captures a piece adjacent to your king, you lose",
        "check_move": "check_atomic_bomb",
        "supported": True
    },
    "closed_book": {
        "description": "You lose if you ever start your turn while there's an open file",
        "check_move": "check_closed_book", 
        "supported": True
    },
    "true_gentleman": {
        "description": "You can't capture queens",
        "check_move": "check_true_gentleman",
        "supported": True
    },
    "pack_mentality": {
        "description": "Your pieces must move to squares adjacent to another one of your pieces",
        "check_move": "check_pack_mentality",
        "supported": True
    }
}

# If no drawbacks were loaded, use the builtin ones
if not DRAWBACKS:
    print("Using built-in drawback definitions instead of dynamically loaded ones")
    DRAWBACKS = BUILTIN_DRAWBACKS

def get_drawback_info(drawback_name):
    """
    Retrieves the drawback rules based on the given drawback name.
    """
    return DRAWBACKS.get(drawback_name, {})

def get_drawback_params(drawback_name):
    """Get the configurable parameters for a drawback"""
    drawback = DRAWBACKS.get(drawback_name, {})
    if drawback.get("configurable"):
        return {
            "config_type": drawback.get("config_type", ""),
            "config_name": drawback.get("config_name", "Parameter"),
            "current_value": drawback.get("params", {})
        }
    return None

def update_drawback_params(drawback_name, new_params):
    """Update the parameters for a configurable drawback"""
    if drawback_name in DRAWBACKS and DRAWBACKS[drawback_name].get("configurable"):
        # Make a copy of the current params
        current_params = DRAWBACKS[drawback_name].get("params", {}).copy()
        # Update with new params
        current_params.update(new_params)
        # Store back in the drawback
        DRAWBACKS[drawback_name]["params"] = current_params
        return True
    return False

def get_drawback_function(drawback_name):
    """Get the check function for a drawback directly"""
    if not drawback_name or drawback_name not in DRAWBACKS:
        return None
        
    drawback = DRAWBACKS[drawback_name]
    if not drawback.get("supported", False):
        return None
        
    # Get function name
    func_name = drawback.get("check_move")
    if not func_name:
        return None
        
    # Try to import the module
    try:
        module_name = f"GameState.drawbacks.{drawback_name}"
        module = __import__(module_name, fromlist=[''])
        
        # Get function
        check_function = getattr(module, func_name)
        return check_function
    except (ImportError, AttributeError) as e:
        print(f"Error getting drawback function '{func_name}' from {drawback_name}: {e}")
        return None

# Attempt to load drawbacks when this module is imported
load_drawbacks()
