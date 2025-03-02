import asyncio
import sys
from concurrent.futures import ThreadPoolExecutor
from GameState.movegen import DrawbackBoard

# Global state for async search
current_search = None
current_progress = "Thinking..."
current_result = None
executor = ThreadPoolExecutor(max_workers=1)

async def async_search(board, depth):
    """Run the chess engine search asynchronously."""
    global current_progress, current_result
    current_progress = "Starting search..."
    print("Search started at depth", depth)
    try:
        # Create a new searcher instance for this search

        # Use the running loop to schedule the blocking search in the executor
        loop = asyncio.get_running_loop()
        current_result = await loop.run_in_executor(
            executor,

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
    """Start a new async search using asyncio.create_task."""
    global current_search, current_progress
    # Cancel any existing search if it's still running.
    if current_search and not current_search.done():
        current_search.cancel()
        print("Cancelled existing search")
    # Use the current running loop (or create one if necessary)
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    # Schedule a new asynchronous search task.
    current_search = asyncio.create_task(async_search(board, depth))
    current_progress = "Search started..."
    print(f"Created new search task at depth {depth}")

def get_progress():
    """Return the current search progress string."""
    return current_progress

def get_result():
    """Return the search result if available."""
    return current_result

def is_search_complete():
    """Return True if the current search task is done."""
    return current_search is not None and current_search.done()

def reset_search():
    """Reset the search state."""
    global current_search, current_progress, current_result
    current_search = None
    current_progress = ""
    current_result = None
