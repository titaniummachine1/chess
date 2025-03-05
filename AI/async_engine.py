"""
Unified async handler for chess engines - combines functionality from all async modules and opening book
"""
import asyncio
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
import random
import chess
from AI.ai_utils import get_king_capture_move

# Global state for async search
current_search = None
current_progress = "Idle"
current_result = None
search_executor = ThreadPoolExecutor(max_workers=1)

# Update the run_search function to give the engine more time
def run_search(board, depth, time_limit=5):
    """Run the engine search in a separate thread"""
    assert board is not None, "Board cannot be None"
    assert depth > 0, f"Search depth must be positive, got {depth}"
    assert time_limit > 0, f"Time limit must be positive, got {time_limit}"
    
    start_time = time.time()
    print(f"Search started at depth {depth}, time limit {time_limit}s")
    
    # Always use a copy of the board for thread safety
    board_copy = board.copy()
    
    # Verify legal moves using direct approach
    from GameState.movegen import DrawbackBoard
    if isinstance(board_copy, DrawbackBoard):
        pseudo_moves = list(super(DrawbackBoard, board_copy).generate_pseudo_legal_moves())
        legal_moves = []
        for move in pseudo_moves:
            if not board_copy._is_drawback_illegal(move, board_copy.turn):
                legal_moves.append(move)
        print(f"Legal moves verified: {len(legal_moves)}")
    else:
        # Regular board
        legal_moves = list(board_copy.legal_moves)
        
    assert len(legal_moves) > 0, "No legal moves available in position"
    
    # Check for king captures - this is an immediate win
    king_capture = get_king_capture_move(board_copy)
    if king_capture:
        print("Found king capture (checkmate)!")
        return king_capture
    
    # Import engine only when needed to avoid circular imports
    from AI.drawback_sunfish import best_move as engine_best_move
    
    # Call the actual engine search with the time limit
    move = engine_best_move(board_copy, depth, time_limit)
    assert move is None or move in legal_moves, f"Engine returned illegal move: {move}"
    
    elapsed = time.time() - start_time
    # Ensure minimum thinking time for visual feedback
    min_think_time = 1.0  # At least 1 second of "thinking"
    if elapsed < min_think_time:
        time.sleep(min_think_time - elapsed)
        elapsed = time.time() - start_time
        
    print(f"Search completed in {elapsed:.2f}s, found move: {move}")
    return move

async def async_search(board, depth, time_limit=5):
    """Run the chess engine search asynchronously"""
    global current_progress, current_result
    current_progress = f"Searching at depth {depth}..."
    
    try:
        # Make a copy of the board for thread safety
        board_copy = board.copy()
        
        loop = asyncio.get_running_loop()
        current_result = await loop.run_in_executor(
            search_executor,
            lambda: run_search(board_copy, depth, time_limit)
        )
        
        if current_result:
            current_progress = "Search complete"
        else:
            current_progress = "No move found"
    except Exception as e:
        print(f"ASYNC SEARCH ERROR: {str(e)}")
        current_progress = f"Search error: {str(e)}"
        current_result = None

def start_search(board, depth, time_limit=5):
    """Start a new async search task"""
    global current_search, current_progress
    
    # Cancel any existing search first
    if current_search and not current_search.done():
        current_search.cancel()
        print("Cancelled existing search")
        
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
    current_search = asyncio.create_task(async_search(board, depth, time_limit))
    current_progress = f"Thinking at depth {depth} for {time_limit}s..."  # Update progress message
    print(f"[DEBUG] Search task started successfully with time limit {time_limit}s")

# Other simple functions remain the same
def get_progress():
    return current_progress

def get_result():
    return current_result

def is_search_complete():
    return current_search is not None and current_search.done()

def reset_search():
    """
    Reset the search state completely.
    """
    global current_search, current_progress, current_result
    
    # Cancel existing search task if it exists
    if current_search and not current_search.done():
        current_search.cancel()
        print("Active search task cancelled")
    
    # Reset all state variables
    current_search = None
    current_progress = "Idle"
    current_result = None
    
    # Give a short moment for task cleanup
    time.sleep(0.1)
    
    # Clear any pending tasks in the thread pool
    global search_executor
    search_executor.shutdown(wait=False)
    search_executor = ThreadPoolExecutor(max_workers=1)
    
    print("Search state fully reset")
