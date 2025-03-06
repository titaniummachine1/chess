"""
Drawback Manager - handles loading and managing drawback rules

The Drawback Manager loads all drawback modules from the 'drawbacks' directory
and provides functions to access them. Each drawback has:

1. A 'check_move' function that determines if a move is legal
2. An optional 'loss_condition' function that can trigger a variant loss

Drawbacks are loaded dynamically at runtime and stored in the DRAWBACKS dictionary.
"""
import importlib
import os
import sys
import chess
import inspect
import traceback
from typing import Dict, Any, Callable, Optional, Union, List

# Dictionary to store dynamically loaded drawbacks
DRAWBACKS: Dict[str, Dict[str, Any]] = {}

def validate_drawback_info(info: Dict[str, Any], name: str) -> None:
    """
    Validate that the drawback info has all required fields
    
    Each drawback must define a DRAWBACK_INFO dictionary with:
    - name: Display name of the drawback
    - description: Text description of what it does
    - check_move: Name of the function that checks move legality
    - supported: Boolean flag indicating if it's fully implemented
    - loss_condition: (Optional) Name of function that checks for loss
    """
    assert isinstance(info, dict), f"DRAWBACK_INFO for {name} must be a dictionary"
    assert "description" in info, f"DRAWBACK_INFO for {name} must have a description"
    assert "check_move" in info, f"DRAWBACK_INFO for {name} must have a check_move function name"
    assert "supported" in info, f"DRAWBACK_INFO for {name} must have a supported flag"
    assert isinstance(info["description"], str), f"Description for {name} must be a string"
    assert isinstance(info["check_move"], str), f"Check move function name for {name} must be a string"
    assert isinstance(info["supported"], bool), f"Supported flag for {name} must be a boolean"

def load_drawbacks() -> None:
    """
    Dynamically loads all drawbacks from the 'Drawbacks' directory.
    Each drawback module defines specific game rule modifications.
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    drawbacks_dir = os.path.join(current_dir, "Drawbacks")
    
    assert os.path.isdir(current_dir), f"Invalid current directory: {current_dir}"
    
    # Make sure project root is in path
    project_root = os.path.dirname(current_dir)
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
        print(f"Added {project_root} to sys.path")
    
    if not os.path.exists(drawbacks_dir):
        print(f"Warning: Drawbacks directory not found at: {drawbacks_dir}")
        ensure_drawbacks_package()  # Create the directory
        return
    
    print(f"Loading drawbacks from: {drawbacks_dir}")
    print(f"Current sys.path: {sys.path}")
    
    # Import and load each Python file in the 'Drawbacks' directory
    for filename in [f for f in os.listdir(drawbacks_dir) if f.endswith(".py") and f != "__init__.py"]:
        drawback_name = filename[:-3]  # remove '.py'
        filepath = os.path.join(drawbacks_dir, filename)
        
        try:
            print(f"Loading directly from file: {filepath}")
            
            # Create a clean module namespace
            import types
            module = types.ModuleType(drawback_name)
            
            # Add chess to the module's namespace
            module.chess = chess
            
            # Execute the file in the module's namespace
            with open(filepath, 'rb') as f:
                code = compile(f.read(), filepath, 'exec')
                exec(code, module.__dict__)
            
            # Check and process the loaded module
            if hasattr(module, "DRAWBACK_INFO"):
                info = module.DRAWBACK_INFO
                validate_drawback_info(info, drawback_name)
                
                # Clone the info to avoid external modification
                DRAWBACKS[drawback_name] = info.copy()
                
                # Store direct references to functions
                func_name = info.get("check_move")
                if func_name and hasattr(module, func_name):
                    check_function = getattr(module, func_name)
                    DRAWBACKS[drawback_name]["check_function"] = check_function
                
                loss_func_name = info.get("loss_condition")
                if loss_func_name and hasattr(module, loss_func_name):
                    DRAWBACKS[drawback_name]["loss_function"] = getattr(module, loss_func_name)
                    
                print(f"Successfully loaded drawback: {drawback_name}")
            else:
                print(f"Warning: Drawback '{drawback_name}' is missing 'DRAWBACK_INFO'")
                
        except Exception as e:
            print(f"Error loading drawback file '{filename}': {e}")
            traceback.print_exc()

def set_default_params() -> None:
    """Set default parameters for configurable drawbacks"""
    for name, config in [
        ("just_passing_through", {"rank": 3}),
        ("blinded_by_the_sun", {"sun_square": chess.E4})
    ]:
        if name in DRAWBACKS and "params" not in DRAWBACKS[name]:
            DRAWBACKS[name]["params"] = config

def get_drawback_function(drawback_name: str) -> Optional[Callable]:
    """
    Get the check_move function for a drawback
    
    The check_move function determines if a move is legal according to the drawback.
    It should return True if the move is ILLEGAL, False if the move is legal.
    
    Args:
        drawback_name: Name of the drawback
        
    Returns:
        The check_move function or None if not found
    """
    if drawback_name not in DRAWBACKS:
        return None
        
    return DRAWBACKS[drawback_name].get("check_function")
    
def get_drawback_loss_function(drawback_name: str) -> Optional[Callable]:
    """
    Get the loss_condition function for a drawback
    
    The loss_condition function determines if a player has lost due to the drawback.
    It should return True if the loss condition is met, False otherwise.
    
    Args:
        drawback_name: Name of the drawback
        
    Returns:
        The loss_condition function or None if not found
    """
    if drawback_name not in DRAWBACKS:
        return None
        
    return DRAWBACKS[drawback_name].get("loss_function")
    
def get_drawback_info(drawback_name: str) -> Optional[Dict[str, Any]]:
    """
    Get information about a drawback
    
    Args:
        drawback_name: Name of the drawback
        
    Returns:
        Dictionary with drawback information or None if not found
    """
    return DRAWBACKS.get(drawback_name)

def get_drawback_params(drawback_name: str) -> Optional[Dict[str, Any]]:
    """Get the configurable parameters for a drawback"""
    drawback = DRAWBACKS.get(drawback_name, {})
    if drawback.get("configurable"):
        return {
            "config_type": drawback.get("config_type", ""),
            "config_name": drawback.get("config_name", "Parameter"),
            "current_value": drawback.get("params", {})
        }
    return None

def update_drawback_params(drawback_name: str, new_params: Dict[str, Any]) -> bool:
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

def ensure_drawbacks_package() -> None:
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
            raise IOError(f"Failed to create Drawbacks directory: {e}")
            
    # Create __init__.py if it doesn't exist
    if not os.path.exists(init_path):
        try:
            with open(init_path, 'w') as f:
                f.write('"""Drawbacks package - contains all rule variations for Drawback Chess."""\n')
                f.write('# List of available drawbacks\navailable_drawbacks = []\n')
            print(f"Created __init__.py in Drawbacks directory")
        except Exception as e:
            raise IOError(f"Failed to create __init__.py: {e}")
            
    # Create parent package __init__.py if it doesn't exist
    parent_init_path = os.path.join(current_dir, "__init__.py")
    if not os.path.exists(parent_init_path):
        try:
            with open(parent_init_path, 'w') as f:
                f.write('"""GameState package - contains game logic for Drawback Chess."""\n')
            print(f"Created __init__.py in GameState directory")
        except Exception as e:
            raise IOError(f"Failed to create GameState __init__.py: {e}")
            
    # Create root package __init__.py
    root_init_path = os.path.join(os.path.dirname(current_dir), "__init__.py")
    if not os.path.exists(root_init_path):
        try:
            with open(root_init_path, 'w') as f:
                f.write('"""Drawback Chess - Root package."""\n')
            print(f"Created __init__.py in root directory")
        except Exception as e:
            raise IOError(f"Failed to create root __init__.py: {e}")

# Initialize everything on module import
ensure_drawbacks_package()
load_drawbacks()
set_default_params()