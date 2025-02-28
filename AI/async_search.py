"""
This module now simply wraps the synchronous best_move function from AI/search.py.
It removes all asynchronous code so that the move is computed immediately.
"""

import sys
from AI.search import best_move  # Blocking search function from your search module
from GameState.movegen import DrawbackBoard

def get_initial_board():
    # Initialize a new board using your custom DrawbackBoard
    board = DrawbackBoard()
    board.reset()
    return board

def sync_best_move(board, depth):
    from AI.search import best_move
    return best_move(board, depth)

def reset_ai_state():
    pass

def get_best_move():
    return None

def get_progress():
    return ""

def is_search_complete():
    return True

if __name__ == '__main__':
    board = get_initial_board()
    best_move_result = sync_best_move(board, 5)
    print("bestmove", best_move_result)
    sys.stdout.flush()
