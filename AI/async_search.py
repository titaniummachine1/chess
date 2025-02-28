import asyncio
import time
import chess
from AI.search import best_move as search_best_move

# New global state
_search_task = None
_best_move = None
_target_depth = 0
_search_complete = False
_start_time = 0

def is_thinking():
    return _search_task is not None and not _search_task.done()

def is_search_complete():
    return _search_complete

def get_best_move():
    return _best_move

def get_progress():
    elapsed = time.time() - _start_time if _start_time else 0
    return f"Depth: {_target_depth} in progress, Time: {elapsed:.1f}s" if is_thinking() else "Not searching"

def reset_ai_state():
    global _search_task, _best_move, _target_depth, _search_complete, _start_time
    _search_task = None
    _best_move = None
    _target_depth = 0
    _search_complete = False
    _start_time = 0
    print("AI state reset")

async def iterative_search(board, depth):
    global _best_move, _target_depth, _search_complete, _start_time
    _target_depth = depth
    _start_time = time.time()
    # Iterative deepening: try increasing depths from 1 to depth.
    for current in range(1, depth + 1):
        # Yield to keep UI responsive.
        await asyncio.sleep(0)
        try:
            move = search_best_move(board.copy(), current)
            print(f"Completed depth {current}, best move: {move}")
            _best_move = move
        except Exception as e:
            print(f"Error at depth {current}: {e}")
            break
    _search_complete = True
    print("Search complete at target depth", depth)

def async_best_move(board, depth):
    """
    Launches an asynchronous iterative deepening search using asyncio.
    Returns True if a new search is started.
    """
    global _search_task
    if is_thinking():
        print("Search already in progress")
        return False
    reset_ai_state()
    _search_task = asyncio.get_event_loop().create_task(iterative_search(board, depth))
    print(f"Started search to depth {depth}")
    return True

