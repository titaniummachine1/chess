import asyncio
import time
import chess
from AI.search import best_move as search_best_move

# Global state for async search
_thinking = False
_best_move = None
_current_depth = 0
_target_depth = 0
_search_complete = False
_start_time = 0

def is_thinking():
    return _thinking

def is_search_complete():
    return _search_complete

def get_best_move():
    return _best_move

def get_progress():
    elapsed = time.time() - _start_time if _thinking else 0
    return f"Depth: {_current_depth}/{_target_depth} Time: {elapsed:.1f}s" if _thinking else "Not searching"

def reset_ai_state():
    global _thinking, _best_move, _current_depth, _target_depth, _search_complete, _start_time
    _thinking = False
    _best_move = None
    _current_depth = 0
    _target_depth = 0
    _search_complete = False
    _start_time = 0
    print("AI state reset")

async def process_search(board, depth):
    global _thinking, _best_move, _current_depth, _target_depth, _search_complete
    _thinking = True
    _target_depth = depth
    while _current_depth < _target_depth:
        await asyncio.sleep(0)  # yield control so UI stays responsive
        try:
            move = search_best_move(board.copy(), _current_depth + 1)
        except Exception as e:
            print(f"Error at depth {_current_depth+1}: {e}")
            break
        if not move:
            print("No move found at depth", _current_depth + 1)
            break
        _best_move = move
        _current_depth += 1
        print(f"Completed depth {_current_depth}, best move: {move}")
    _search_complete = True
    _thinking = False
    print("Search complete at depth", _current_depth)

def async_best_move(board, depth):
    """Starts an asynchronous search using asyncio.
       Returns immediately while the search task runs.
    """
    global _start_time
    if _thinking:
        print("Search already in progress")
        return False
    reset_ai_state()
    _start_time = time.time()
    # Schedule the search task
    asyncio.create_task(process_search(board, depth))
    print(f"Started search to depth {depth}")
    return True

