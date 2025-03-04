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
    try:
        start_time = time.time()
        print(f"Search started at depth {depth}, time limit {time_limit}s")
        
        # Always use a copy of the board for thread safety
        board_copy = board.copy()
        
        # First check for king captures - this is done directly here to avoid imports
        king_capture = get_king_capture_move(board_copy)
        if king_capture:
            print("Found king capture (checkmate)!")
            return king_capture
        
        # Import engine only when needed to avoid circular imports
        try:
            # Force a small delay to prevent instant moves
            min_think_time = 1.0  # At least 1 second of "thinking"
            from AI.drawback_sunfish import best_move as engine_best_move
            
            # Call the actual engine search with the time limit
            move = engine_best_move(board_copy, depth, time_limit)
            
            elapsed = time.time() - start_time
            # Ensure minimum thinking time for visual feedback
            if elapsed < min_think_time:
                time.sleep(min_think_time - elapsed)
                elapsed = time.time() - start_time
                
            print(f"Search completed in {elapsed:.2f}s, found move: {move}")
            
            return move
        except Exception as engine_error:
            print(f"Engine error: {engine_error}")
            traceback.print_exc()
            
    except Exception as e:
        print(f"ENGINE SEARCH ERROR: {e}")
        traceback.print_exc()
        
    # Emergency fallback - pick a random legal move
    try:
        legal_moves = list(board.legal_moves)
        if legal_moves:
            move = random.choice(legal_moves)
            print(f"EMERGENCY: Using random fallback move: {move}")
            return move
    except Exception as fallback_error:
        print(f"Critical fallback error: {fallback_error}")
    return None

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
    Ensures any canceled searches don't affect future results.
    """
    global current_search, current_progress, current_result
    
    # Cancel existing search task if it exists
    if current_search and not current_search.done():
        try:
            current_search.cancel()
            print("Active search task cancelled")
        except Exception as e:
            print(f"Error cancelling search: {e}")
    
    # Reset all state variables
    current_search = None
    current_progress = "Idle"
    current_result = None
    
    # Give a short moment for task cleanup
    time.sleep(0.1)
    
    print("Search state fully reset")
