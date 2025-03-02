"""
Unified async handler for chess engines - streamlined version
"""
import asyncio
import time
import threading
import traceback
from concurrent.futures import ThreadPoolExecutor
import random
import chess
from AI.drawback_sunfish import best_move as engine_best_move

# Global state for async search
current_search = None
current_progress = "Idle"
current_result = None
search_executor = ThreadPoolExecutor(max_workers=1)

def run_search(board, depth, time_limit=5):
    """Run the engine search in a separate thread"""
    try:
        start_time = time.time()
        print(f"Starting engine search at depth {depth}, time limit {time_limit}s")
        
        # Always use a copy of the board for thread safety
        board_copy = board.copy()
        
        # Call the actual engine search with the time limit
        move = engine_best_move(board_copy, depth, time_limit)
        
        # Log results
        elapsed = time.time() - start_time
        print(f"Search completed in {elapsed:.2f}s")
        
        # Validate the returned move
        if move and move not in board.legal_moves:
            print(f"WARNING: Engine returned illegal move: {move}")
            # Find a fallback move
            legal_moves = list(board.legal_moves)
            if legal_moves:
                move = random.choice(legal_moves)
                print(f"Using random legal move instead: {move}")
            else:
                move = None
                
        return move
    except Exception as e:
        print(f"Engine search error: {e}")
        
        # Last resort - try to find any legal move
        try:
            legal_moves = list(board.legal_moves)
            if legal_moves:
                move = random.choice(legal_moves)
                print(f"Using emergency fallback move: {move}")
                return move
        except:
            pass
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
        print(f"Search error: {str(e)}")
        current_progress = f"Search error: {str(e)}"
        current_result = None

def start_search(board, depth, time_limit=5):
    """Start a new async search task"""
    global current_search, current_progress
    
    if current_search and not current_search.done():
        current_search.cancel()
        print("Cancelled existing search")
        
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
    current_search = asyncio.create_task(async_search(board, depth, time_limit))
    current_progress = f"Thinking at depth {depth}, {time_limit}s limit..."

def get_progress():
    """Get the current search progress description"""
    return current_progress

def get_result():
    """Get the completed search result"""
    return current_result

def is_search_complete():
    """Check if the current search is complete"""
    return current_search is not None and current_search.done()

def reset_search():
    """Reset the search state"""
    global current_search, current_progress, current_result
    current_search = None
    current_progress = "Idle"
    current_result = None
