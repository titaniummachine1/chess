"""
Drawback manager - handles loading and managing drawback rules
"""
import importlib
import os
import sys
import chess
import inspect
import traceback

# Dictionary to store dynamically loaded drawbacks
DRAWBACKS = {}

def load_drawbacks():
    """
    Dynamically loads all drawbacks from the 'Drawbacks' directory.
    Each drawback module defines specific game rule modifications.
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    drawbacks_dir = os.path.join(current_dir, "Drawbacks")
    
    # Make sure project root is in path
    project_root = os.path.dirname(current_dir)
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
        print(f"Added {project_root} to sys.path")
    
    if not os.path.exists(drawbacks_dir):
        print(f"Warning: Drawbacks directory not found at: {drawbacks_dir}")
        ensure_drawbacks_package()  # Try to create the directory
        ensure_basic_drawbacks()    # Create basic drawback files
        return

    # Try using the direct loader instead of standard imports
    try:
        from GameState.direct_loader import load_drawbacks_directly
        global DRAWBACKS
        direct_drawbacks = load_drawbacks_directly(drawbacks_dir)
        if direct_drawbacks:
            print(f"Successfully loaded {len(direct_drawbacks)} drawbacks directly")
            DRAWBACKS.update(direct_drawbacks)
            return
    except ImportError as e:
        print(f"Direct loader not available: {e}")
    except Exception as e:
        print(f"Error using direct loader: {e}")
        traceback.print_exc()
    
    # Fallback to standard import system if direct loader fails
    print("Attempting standard import method...")
    
    # Print current path for debugging
    print(f"Loading drawbacks from: {drawbacks_dir}")
    print(f"Current sys.path: {sys.path}")
    
    # Load each Python file in the 'Drawbacks' directory (except __init__.py)
    try:
        for filename in os.listdir(drawbacks_dir):
            if filename.endswith(".py") and filename != "__init__.py":
                drawback_name = filename[:-3]  # remove '.py'
                # Try direct file import instead of module import
                try:
                    filepath = os.path.join(drawbacks_dir, filename)
                    print(f"Loading directly from file: {filepath}")
                    
                    # Create a clean module namespace
                    import types
                    module = types.ModuleType(drawback_name)
                    
                    # Add chess to the module's namespace
                    module.chess = chess
                    
                    # Execute the file in the module's namespace
                    with open(filepath, 'rb') as f:
                        exec(compile(f.read(), filepath, 'exec'), module.__dict__)
                    
                    # Now process the loaded module like before
                    if hasattr(module, "DRAWBACK_INFO"):
                        DRAWBACKS[drawback_name] = module.DRAWBACK_INFO.copy()
                        # Store reference to the actual check function 
                        func_name = module.DRAWBACK_INFO.get("check_move")
                        if func_name and hasattr(module, func_name):
                            check_function = getattr(module, func_name)
                            DRAWBACKS[drawback_name]["check_function"] = check_function
                        
                        # Also handle loss condition functions
                        loss_func_name = module.DRAWBACK_INFO.get("loss_condition")
                        if loss_func_name and hasattr(module, loss_func_name):
                            DRAWBACKS[drawback_name]["loss_function"] = getattr(module, loss_func_name)
                            
                        print(f"Successfully loaded drawback: {drawback_name}")
                    else:
                        print(f"Warning: Drawback '{drawback_name}' is missing 'DRAWBACK_INFO'")
                        
                except Exception as e:
                    print(f"Error loading drawback file '{filename}': {e}")
                    traceback.print_exc()
    except Exception as e:
        print(f"Error accessing drawbacks directory: {e}")
        traceback.print_exc()

# Add default values for drawbacks with configurable parameters
def set_default_params():
    """Set default parameters for configurable drawbacks"""
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
        "supported": True,
        "loss_condition": "check_explosion_loss"
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
def use_builtin_if_empty():
    global DRAWBACKS  # Moved global declaration to the top of function
    if not DRAWBACKS:
        print("Using built-in drawback definitions instead of dynamically loaded ones")
        DRAWBACKS = BUILTIN_DRAWBACKS.copy()
        
        # Create and add built-in function implementations
        try:
            from GameState.direct_loader import create_built_in_function
            for name in DRAWBACKS:
                func = create_built_in_function(name)
                if func:
                    func_name = DRAWBACKS[name].get("check_move")
                    if func_name:
                        print(f"Adding built-in function for {name}: {func_name}")
                        DRAWBACKS[name]["check_function"] = func
        except ImportError:
            print("Built-in function generator not available")
        except Exception as e:
            print(f"Error creating built-in functions: {e}")
            traceback.print_exc()

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
    
    # First check if we have direct function reference (new method)
    if "check_function" in drawback:
        return drawback["check_function"]

    # Fallback method for compatibility
    func_name = drawback.get("check_move")
    if not func_name:
        return None
        
    # Try a direct implementation based on the drawback name
    if func_name == "check_forward_march":
        def forward_march_impl(board, move, color):
            from_rank = chess.square_rank(move.from_square)
            to_rank = chess.square_rank(move.to_square)
            if color == chess.WHITE and to_rank < from_rank:
                return False
            if color == chess.BLACK and to_rank > from_rank:
                return False
            return True
        return forward_march_impl
        
    elif func_name == "check_knight_moves":
        def knight_moves_impl(board, move, color):
            piece = board.piece_at(move.from_square)
            if piece and piece.piece_type == chess.KNIGHT:
                return False
            return True
        return knight_moves_impl
    
    # ... add more implementations as needed ...
        
    # Fall back to old import method
    try:
        module_name = f"GameState.Drawbacks.{drawback_name}"
        module = importlib.import_module(module_name)
        
        # Get function
        check_function = getattr(module, func_name)
        return check_function
    except (ImportError, AttributeError) as e:
        print(f"Error getting drawback function '{func_name}' from {drawback_name}: {e}")
        
        # Last-resort fallback
        filepath = os.path.join(os.path.dirname(__file__), "Drawbacks", f"{drawback_name}.py")
        if os.path.exists(filepath):
            try:
                # Try to load the function directly from the file
                print(f"Attempting direct file load for {drawback_name} from {filepath}")
                
                # Create a module namespace
                import types
                module = types.ModuleType(drawback_name)
                module.chess = chess
                
                # Execute the file
                with open(filepath, 'rb') as f:
                    exec(compile(f.read(), filepath, 'exec'), module.__dict__)
                
                if hasattr(module, func_name):
                    check_function = getattr(module, func_name)
                    # Cache the function for next time
                    drawback["check_function"] = check_function
                    return check_function
            except Exception as direct_err:
                print(f"Direct file load failed: {direct_err}")
    
    return None

def get_drawback_loss_function(drawback_name):
    """Get the loss condition function for a drawback directly"""
    if not drawback_name or drawback_name not in DRAWBACKS:
        return None
        
    drawback = DRAWBACKS[drawback_name]
    
    # First check if we have direct function reference (new method)
    if "loss_function" in drawback:
        return drawback["loss_function"]
        
    # Fall back to old import method
    func_name = drawback.get("loss_condition")
    if not func_name:
        return None
        
    # Try to import the module
    try:
        module_name = f"GameState.Drawbacks.{drawback_name}"
        module = importlib.import_module(module_name)
        
        # Get function
        loss_function = getattr(module, func_name)
        return loss_function
    except (ImportError, AttributeError) as e:
        print(f"Error getting loss function '{func_name}' from {drawback_name}: {e}")
        return None

def ensure_drawbacks_package():
    """Ensure the Drawbacks directory has an __init__.py file"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    drawbacks_dir = os.path.join(current_dir, "Drawbacks")
    init_path = os.path.join(drawbacks_dir, "__init__.py")
    
    # Create directory if it doesn't exist
    if not os.path.exists(drawbacks_dir):
        try:
            os.makedirs(drawbacks_dir)
            print(f"Created Drawbacks directory at {drawbacks_dir}")
        except Exception as e:
            print(f"Error creating Drawbacks directory: {e}")
            return False
            
    # Create __init__.py if it doesn't exist
    if not os.path.exists(init_path):
        try:
            with open(init_path, 'w') as f:
                f.write('"""Drawbacks package - contains all rule variations for Drawback Chess."""\n')
                f.write('# List of available drawbacks\navailable_drawbacks = []\n')
            print(f"Created __init__.py in Drawbacks directory")
        except Exception as e:
            print(f"Error creating __init__.py: {e}")
            return False
            
    # Create parent package __init__.py if it doesn't exist
    parent_init_path = os.path.join(current_dir, "__init__.py")
    if not os.path.exists(parent_init_path):
        try:
            with open(parent_init_path, 'w') as f:
                f.write('"""GameState package - contains game logic for Drawback Chess."""\n')
            print(f"Created __init__.py in GameState directory")
        except Exception as e:
            print(f"Error creating GameState __init__.py: {e}")
            
    # Create root package __init__.py
    root_init_path = os.path.join(os.path.dirname(current_dir), "__init__.py")
    if not os.path.exists(root_init_path):
        try:
            with open(root_init_path, 'w') as f:
                f.write('"""Drawback Chess - Root package."""\n')
            print(f"Created __init__.py in root directory")
        except Exception as e:
            print(f"Error creating root __init__.py: {e}")
            
    return True

def ensure_basic_drawbacks():
    """Create basic drawback modules if they don't exist"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    drawbacks_dir = os.path.join(current_dir, "Drawbacks")
    
    # Make sure directory exists
    if not os.path.exists(drawbacks_dir):
        try:
            os.makedirs(drawbacks_dir)
        except Exception as e:
            print(f"Error creating drawbacks directory: {e}")
            return
            
    # Create empty __init__.py file if it doesn't exist
    init_file = os.path.join(drawbacks_dir, "__init__.py")
    if not os.path.exists(init_file):
        try:
            with open(init_file, 'w') as f:
                f.write('"""Drawbacks package - contains all rule variations for Drawback Chess."""\n')
                f.write('# List of available drawbacks\navailable_drawbacks = []\n')
        except Exception as e:
            print(f"Error creating __init__.py: {e}")
    
    # Basic drawback definitions to create if missing
    basic_drawbacks = {
        "forward_march": {
            "code": """
import chess

DRAWBACK_INFO = {
    "description": "Can't move backwards",
    "check_move": "check_forward_march",
    "supported": True
}

def check_forward_march(board, move, color):
    \"\"\"Check if a move follows the forward march rule\"\"\"
    
    from_rank = chess.square_rank(move.from_square)
    to_rank = chess.square_rank(move.to_square)
    
    # For white, can't decrease rank (moving down)
    if color == chess.WHITE and to_rank < from_rank:
        return False
        
    # For black, can't increase rank (moving down from their perspective)
    if color == chess.BLACK and to_rank > from_rank:
        return False
        
    return True
"""
        }
    }
    
    # Create minimal drawback files
    for drawback_name, details in basic_drawbacks.items():
        file_path = os.path.join(drawbacks_dir, f"{drawback_name}.py")
        
        if not os.path.exists(file_path):
            try:
                with open(file_path, 'w') as f:
                    f.write(details["code"])
                print(f"Created basic drawback: {drawback_name}")
            except Exception as e:
                print(f"Error creating {drawback_name} file: {e}")

# Initialize everything
ensure_drawbacks_package()
load_drawbacks()
use_builtin_if_empty()
set_default_params()