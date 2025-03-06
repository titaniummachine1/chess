"""
Drawbacks package - contains all drawback rule implementations.

A drawback is a rule restriction that applies to one player.
Each drawback has:
1. A check_move function that validates if a move is legal
2. An optional loss_condition function that can trigger a loss

Drawback developers: use this file as a reference for the API.
"""

# Standard drawback template for reference below.
# Copy and modify this template when creating new drawbacks.
"""
import chess

DRAWBACK_INFO = {
    "name": "Example Drawback",
    "description": "Example description of what this drawback does",
    "check_move": "check_example_drawback",   # Name of the move checking function below
    "loss_condition": "check_example_loss",   # Optional loss condition function
    "supported": True                         # Set to True when fully implemented
}

def check_example_drawback(board, move, color):
    """
    Check if a move is legal according to this drawback.
    Return True if the move is ILLEGAL, False if it's legal.
    
    Args:
        board: The current board state (DrawbackBoard)
        move: The chess.Move to check
        color: The color making the move (chess.WHITE or chess.BLACK)
    """
    # Implement your move validation logic here
    return False  # Default: move is legal

def check_example_loss(board, color):
    """
    Check if the player has lost due to this drawback's special condition.
    Return True if the loss condition is met, False otherwise.
    
    Args:
        board: The current board state (DrawbackBoard)
        color: The color to check for loss (chess.WHITE or chess.BLACK)
    """
    # Implement your loss condition logic here
    return False  # Default: no loss
"""

# This file makes the drawbacks directory a proper Python package
