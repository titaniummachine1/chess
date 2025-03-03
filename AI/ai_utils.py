"""
Utility functions and common constants for the AI modules.
This module helps prevent circular imports.
"""

import random
import chess

# Centralized constants
MATE_LOWER = 10000
MATE_UPPER = 20000
MAX_DEPTH = 20

# Book move bonus
BOOK_MOVE_BONUS = 60  # Value for random book move
BOOK_MOVE_BONUS_REGULAR = 35  # Value for other book moves

# Random move selection functions
def select_random_from_list(moves):
    """Select a random move from a list"""
    if not moves:
        return None
    return random.choice(moves)

def select_random_element(collection):
    """Select a random element from any collection"""
    if not collection:
        return None
    return random.choice(list(collection))

def get_king_capture_move(board):
    """Find a move that captures the opponent's king if available"""
    for move in board.legal_moves:
        target = board.piece_at(move.to_square)
        if target and target.piece_type == chess.KING:
            return move
    return None
