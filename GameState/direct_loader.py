"""
Direct module loader - loads Python modules directly from file system
when the standard import system fails
"""
import os
import sys
import types
import inspect
import importlib.util
import chess

def load_module_from_file(filepath, module_name=None):
    """
    Load a Python module directly from a file path without relying on Python's import system
    """
    if not os.path.exists(filepath):
        raise ImportError(f"File {filepath} does not exist")
        
    if module_name is None:
        # Generate a module name from the file name
        module_name = os.path.splitext(os.path.basename(filepath))[0]
    
    print(f"Direct loading: {module_name} from {filepath}")
    
    try:
        # Method 1: Using importlib (modern approach)
        spec = importlib.util.spec_from_file_location(module_name, filepath)
        if spec is None:
            raise ImportError(f"Failed to create spec for {filepath}")
            
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    except Exception as e:
        print(f"Error loading module via importlib: {e}")
        
        # Method 2: Fallback to older imp module
        try:
            module = types.ModuleType(module_name)
            with open(filepath, 'r') as file:
                exec(compile(file.read(), filepath, 'exec'), module.__dict__)
            return module
        except Exception as e2:
            print(f"Error loading module via direct execution: {e2}")
            raise ImportError(f"Could not load module from {filepath}: {e}, {e2}")

def load_drawbacks_directly(drawbacks_dir):
    """
    Load all drawback modules directly from files
    """
    drawbacks = {}
    
    if not os.path.exists(drawbacks_dir):
        print(f"Drawbacks directory not found: {drawbacks_dir}")
        return drawbacks
        
    print(f"Loading drawbacks directly from: {drawbacks_dir}")
    
    # Load each Python file in the drawbacks directory
    for filename in os.listdir(drawbacks_dir):
        if filename.endswith(".py") and filename != "__init__.py":
            try:
                drawback_name = filename[:-3]  # remove '.py'
                filepath = os.path.join(drawbacks_dir, filename)
                
                # Load the module directly
                module = load_module_from_file(filepath, f"drawback_{drawback_name}")
                
                # Check for drawback info
                if hasattr(module, 'DRAWBACK_INFO'):
                    drawbacks[drawback_name] = module.DRAWBACK_INFO.copy()
                    
                    # Add direct function references
                    func_name = module.DRAWBACK_INFO.get('check_move')
                    if func_name and hasattr(module, func_name):
                        check_function = getattr(module, func_name)
                        drawbacks[drawback_name]['check_function'] = check_function
                        print(f"Added direct function reference for {drawback_name}: {func_name}")
                        
                    # Add loss condition function if it exists
                    loss_func_name = module.DRAWBACK_INFO.get('loss_condition')
                    if loss_func_name and hasattr(module, loss_func_name):
                        loss_function = getattr(module, loss_func_name)
                        drawbacks[drawback_name]['loss_function'] = loss_function
                        print(f"Added loss function for {drawback_name}: {loss_func_name}")
                        
                    print(f"Successfully loaded drawback module: {drawback_name}")
                else:
                    # Try to load with expected function name
                    expected_func_name = f"check_{drawback_name}"
                    if hasattr(module, expected_func_name):
                        # Create default info
                        drawbacks[drawback_name] = {
                            "description": drawback_name.replace('_', ' ').title(),
                            "check_move": expected_func_name,
                            "supported": True,
                            "check_function": getattr(module, expected_func_name)
                        }
                        print(f"Created default info for {drawback_name}")
                    else:
                        print(f"No DRAWBACK_INFO or expected function in {filename}")
                        
            except Exception as e:
                print(f"Error loading {filename}: {e}")
                import traceback
                traceback.print_exc()
    
    return drawbacks

# Simple module preloading for common drawbacks
def create_built_in_function(drawback_name):
    """Create a built-in function for a drawback"""
    if drawback_name == "forward_march":
        def check_forward_march(board, move, color):
            from_rank = chess.square_rank(move.from_square)
            to_rank = chess.square_rank(move.to_square)
            
            # For white, can't decrease rank (moving down)
            if color == chess.WHITE and to_rank < from_rank:
                return False
                
            # For black, can't increase rank (moving down from their perspective)
            if color == chess.BLACK and to_rank > from_rank:
                return False
                
            return True
        return check_forward_march
        
    elif drawback_name == "covering_fire":
        def check_covering_fire(board, move, color):
            # If it's not a capture, allow the move
            if not board.is_capture(move):
                return True
                
            # For captures, check if another piece can also capture the target
            target_square = move.to_square
            attacking_count = 0
            
            # Count how many pieces of the player's color attack the target square
            for square in chess.SQUARES:
                piece = board.piece_at(square)
                
                # Check if this square contains a piece of the player's color
                if piece and piece.color == color:
                    # Create a move from this square to the target square
                    if square != move.from_square:  # Skip the piece that's making the actual move
                        # Check if this move would be a valid capture
                        try:
                            potential_move = chess.Move(square, target_square)
                            if board.is_pseudo_legal(potential_move) and potential_move != move:
                                attacking_count += 1
                                # If we have at least one other attacker, the move is allowed
                                if attacking_count >= 1:
                                    return True
                        except Exception:
                            # Skip invalid moves
                            continue
            
            # If we didn't find at least one other attacker, the move is not allowed
            return False
        return check_covering_fire
    
    # Add more built-in functions as needed
    return None
