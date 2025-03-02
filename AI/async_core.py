"""
Async wrapper for the chess engine - allows non-blocking search
"""
import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor
from AI.core_engine import ChessEngine

# Global state for async search
current_search = None
current_progress = "Idle"
current_result = None
search_executor = ThreadPoolExecutor(max_workers=1)

def run_search(board, depth):
    """Run the engine search in a separate thread"""
    try:
        engine = ChessEngine()
        move = engine.search(board, depth)
        return move
    except Exception as e:
        print(f"Search error: {e}")
        return None

async def async_search(board, depth):
    """Run the chess engine search asynchronously"""
    global current_progress, current_result
    current_progress = f"Searching at depth {depth}..."
    print(f"Search started at depth {depth}")
    
    try:
        loop = asyncio.get_running_loop()
        current_result = await loop.run_in_executor(
            search_executor,
            lambda: run_search(board, depth)
        )
        
        print(f"Search completed, found move: {current_result}")
        current_progress = "Search complete"
    except Exception as e:
        print(f"Async search error: {e}")
        current_progress = f"Search error: {str(e)}"
        current_result = None
    finally:
        print("Search task finished")

def start_search(board, depth):
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
        
    current_search = asyncio.create_task(async_search(board, depth))
    current_progress = f"Search started at depth {depth}..."
    print(f"Created new search task at depth {depth}")

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
