"""
Utility script to check all drawbacks for common issues and diagnose parameter problems
"""
import os
import sys
import importlib
import inspect
import chess
from GameState.movegen import DrawbackBoard
from GameState.drawback_manager import DRAWBACKS, get_drawback_function

def print_function_signature(func):
    """Print the signature of a function"""
    sig = inspect.signature(func)
    print(f"Function: {func.__name__}")
    print(f"Signature: {sig}")
    print(f"Parameter names: {list(sig.parameters.keys())}")
    print()

def check_drawback(drawback_name):
    """Test a single drawback to ensure it works correctly"""
    print(f"\nChecking drawback: {drawback_name}")
    
    # Create a test board with the drawback
    board = DrawbackBoard()
    board.set_white_drawback(drawback_name)
    
    # Get the drawback function
    check_function = get_drawback_function(drawback_name)
    if not check_function:
        print(f"ERROR: No check function found for drawback {drawback_name}")
        return False
        
    # Print function signature to check parameter order
    print_function_signature(check_function)
    
    # Get initial legal moves count
    initial_legal_count = len(list(board.legal_moves))
    print(f"Initial position has {initial_legal_count} legal moves")
    
    if initial_legal_count == 0:
        print(f"ERROR: Drawback {drawback_name} prevents all legal moves in the initial position")
        return False
    
    # Check a few standard moves against the drawback
    test_moves = [
        chess.Move.from_uci("e2e4"),  # e4 - standard pawn move
        chess.Move.from_uci("g1f3"),  # Nf3 - knight move
    ]
    
    for move in test_moves:
        try:
            # Try both parameter orders to diagnose issues
            try:
                is_illegal = check_function(board, move, chess.WHITE)
                print(f"Move {move.uci()} is {'illegal' if is_illegal else 'legal'} according to {drawback_name}")
                print(f"Parameter order (board, move, color) works correctly")
            except TypeError as e:
                print(f"Error with (board, move, color) order: {e}")
                try:
                    is_illegal = check_function(board, chess.WHITE, move)
                    print(f"Move {move.uci()} is {'illegal' if is_illegal else 'legal'} according to {drawback_name}")
                    print(f"Parameter order (board, color, move) works correctly")
                except TypeError as e2:
                    print(f"Error with (board, color, move) order: {e2}")
                    print(f"FAILED: Function does not accept either parameter order")
                    return False
        except Exception as e:
            print(f"ERROR: Exception while checking move {move.uci()}: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    print(f"Drawback {drawback_name} appears to be working correctly")
    return True

def check_all_drawbacks():
    """Check all loaded drawbacks"""
    print("Checking all drawbacks...")
    
    results = {}
    for name in DRAWBACKS:
        results[name] = check_drawback(name)
        
    print("\n--- SUMMARY ---")
    for name, success in results.items():
        print(f"{name}: {'✓ OK' if success else '✗ FAILED'}")
    
    failed = [name for name, success in results.items() if not success]
    if failed:
        print(f"\nFailed drawbacks: {', '.join(failed)}")
        print("\nRun the following command to validate each failed drawback:")
        for name in failed:
            print(f"python check_drawbacks.py {name}")
    else:
        print("\nAll drawbacks passed basic checks")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Check specific drawback
        check_drawback(sys.argv[1])
    else:
        check_all_drawbacks()
