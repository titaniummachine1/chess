import threading
import time
import chess
from AI.search import best_move as search_best_move

# Global variables to track search state
_thinking = False
_best_move = None
_completed_depth = 0
_target_depth = 0
_search_complete = False
_start_time = 0
_lock = threading.Lock()

def is_thinking():
    """Returns True if the AI is currently calculating a move."""
    with _lock:
        return _thinking

def is_search_complete():
    """Returns True if the search has completed to the target depth."""
    with _lock:
        return _search_complete

def get_best_move():
    """Returns the best move found so far."""
    with _lock:
        return _best_move

def get_completed_depth():
    """Returns the depth to which search has been completed."""
    with _lock:
        return _completed_depth

def get_target_depth():
    """Returns the target depth for the current search."""
    with _lock:
        return _target_depth

def get_progress():
    """Returns a string indicating search progress."""
    with _lock:
        elapsed = time.time() - _start_time if _thinking else 0
        depth_info = f"Depth: {_completed_depth}/{_target_depth}" if _thinking else "Not searching"
        time_info = f"Time: {elapsed:.1f}s" if _thinking else ""
        return f"{depth_info} {time_info}"

def reset_ai_state():
    """Resets all AI search state variables."""
    global _thinking, _best_move, _completed_depth, _target_depth, _search_complete, _start_time
    with _lock:
        _thinking = False
        _best_move = None
        _completed_depth = 0
        _target_depth = 0
        _search_complete = False
        _start_time = 0
    print("AI search state reset")

def _search_thread(board, max_depth):
    """Background thread function to perform iterative deepening search."""
    global _thinking, _best_move, _completed_depth, _target_depth, _search_complete, _start_time

    try:
        # Safety check to avoid searching on completed game
        if board.is_variant_end():
            with _lock:
                _thinking = False
                _search_complete = True
            print("Game already ended - search canceled")
            return

        # Start with depth 1 and iteratively increase
        for depth in range(1, max_depth + 1):
            # Check if search has been canceled
            if not is_thinking():
                print(f"Search canceled at depth {depth}")
                return

            # Perform search at current depth
            start = time.time()
            move = search_best_move(board.copy(), depth)
            end = time.time()

            if move:
                with _lock:
                    _best_move = move
                    _completed_depth = depth
                print(f"Depth {depth} completed in {end-start:.2f}s - Best: {move}")

        # Search completed to target depth
        with _lock:
            _search_complete = True
            _thinking = False
        print(f"Search completed to target depth {max_depth}")

    except Exception as e:
        print(f"Error in search thread: {e}")
        with _lock:
            _thinking = False

def async_best_move(board, depth):
    """
    Start an asynchronous search for the best move.
    Returns immediately while search continues in background.
    """
    global _thinking, _best_move, _completed_depth, _target_depth, _search_complete, _start_time

    # Don't start a new search if one is already in progress
    if is_thinking():
        print("Search already in progress - ignoring new request")
        return False

    # Reset search state
    reset_ai_state()
    
    with _lock:
        _thinking = True
        _target_depth = depth
        _start_time = time.time()
    
    # Start search in a background thread
    thread = threading.Thread(target=_search_thread, args=(board.copy(), depth))
    thread.daemon = True  # Thread will be terminated when main program exits
    thread.start()
    
    print(f"Started async search to depth {depth}")
    return True

def wait_for_ai():
    """Wait until the AI completes its search."""
    while is_thinking():
        time.sleep(0.1)  # Short sleep to prevent CPU hogging
    return get_best_move()
