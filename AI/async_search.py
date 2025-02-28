import asyncio
import sys
from concurrent.futures import ThreadPoolExecutor
from AI.search import best_move, Searcher
from GameState.movegen import DrawbackBoard

# Global state for async search
current_search = None
current_progress = "Thinking..."
current_result = None
executor = ThreadPoolExecutor(max_workers=1)

async def async_search(board, depth):
    """Run the chess engine search asynchronously"""
    global current_progress, current_result, executor
    
    current_progress = "Starting search..."
    print("Search started at depth", depth)
    
    try:
        # Create a new searcher instance for this search
        searcher = Searcher()
        # Run the search in the thread pool
        current_result = await asyncio.get_event_loop().run_in_executor(
            executor, 
            lambda: searcher.search(board, depth)
        )
        print(f"Search completed, found move: {current_result}")
        current_progress = "Search complete"
    except Exception as e:
        print(f"Search error: {e}")
        current_progress = "Search error"
        current_result = None
    finally:
        print("Search task finished")

def start_search(board, depth):
    """Start a new async search"""
    global current_search, current_progress
    
    # Cancel any existing search
    if current_search and not current_search.done():
        current_search.cancel()
        print("Cancelled existing search")
    
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    # Start new search task
    current_search = asyncio.create_task(async_search(board, depth))
    current_progress = "Search started..."
    print(f"Created new search task at depth {depth}")

def get_progress():
    """Get the current search progress"""
    global current_progress
    return current_progress

def get_result():
    """Get the current search result if available"""
    global current_result
    return current_result

def is_search_complete():
    """Check if the current search is complete"""
    return current_search is not None and current_search.done()

def reset_search():
    """Reset the search state"""
    global current_search, current_progress, current_result
    current_search = None
    current_progress = ""
    current_result = None
