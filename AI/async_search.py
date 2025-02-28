"""
This module now simply wraps the synchronous search from AI/search.py.
It replaces the previous asynchronous implementation.
"""

def sync_best_move(board, depth):
    from AI.search import best_move as search_best_move_function
    return search_best_move_function(board, depth)

def reset_ai_state():
    # No persistent state is used in the synchronous search.
    pass

def get_best_move():
    # The synchronous search returns the move immediately.
    return None

def get_progress():
    return ""

def is_search_complete():
    # Synchronous search always completes immediately.
    return True
