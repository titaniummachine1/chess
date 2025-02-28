import time
import chess
from AI.search import best_move as search_best_move

# Global state for synchronous search
_best_move = None
_target_depth = 0
_search_complete = False
_start_time = 0

def get_best_move():
    return _best_move

def get_progress():
    elapsed = time.time() - _start_time if _start_time else 0
    return f"Depth: {_target_depth} completed, Time: {elapsed:.1f}s"

def reset_ai_state():
    global _best_move, _target_depth, _search_complete, _start_time
    _best_move = None
    _target_depth = 0
    _search_complete = False
    _start_time = 0

def sync_best_move(board, depth):
    """
    Synchronous iterative deepening search that blocks execution.
    """
    global _best_move, _target_depth, _search_complete, _start_time
    reset_ai_state()
    _target_depth = depth
    _start_time = time.time()
    for current in range(1, depth + 1):
        move = search_best_move(board.copy(), current)
        _best_move = move
    _search_complete = True
    return _best_move

def is_search_complete():
    return _search_complete

