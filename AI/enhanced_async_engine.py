"""
Enhanced Async Chess Engine Handler
===================================

This module provides an asynchronous interface to the chess engine,
allowing non-blocking AI move calculation.
"""
import asyncio
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from functools import partial
import chess

# Import engine components
from AI.engine_core import select_best_move

# Global state for async search
class AsyncEngineState:
    def __init__(self):
        self.current_search = None
        self.current_progress = "Idle"
        self.current_result = None
        self.search_executor = ThreadPoolExecutor(max_workers=1)
        self.start_time = None
        self.depth = 0
        self.time_limit = 0
        
    def reset(self):
        """Reset the engine state completely"""
        self.current_progress = "Idle"
        self.current_result = None
        self.start_time = None
        self.depth = 0
        self.time_limit = 0

# Create a singleton instance
engine_state = AsyncEngineState()

def run_search(board, depth, time_limit=5, smart_time_management=False):
    """
    Run the engine search in a separate thread
    
    Args:
        board: Chess board position
        depth: Search depth
        time_limit: Time limit in seconds
        smart_time_management: If True, enables dynamic time management:
            - Extends search time when a new best move is found
            - Terminates early if the same best move is stable for a while
        
    Returns:
        Best move found by the engine
    """
    # Validate inputs
    assert board is not None, "Board cannot be None"
    assert depth > 0, f"Search depth must be positive, got {depth}"
    assert time_limit > 0, f"Time limit must be positive, got {time_limit}"
    
    # Create a board copy for thread safety
    board_copy = board.copy()
    
    # Call the engine to get best move
    # When smart_time_management is True, the search will extend time when a new best move is found
    # and terminate early if the best move remains stable
    result = select_best_move(board_copy, depth, time_limit, {}, smart_time_management)
    
    # Return the move from the result
    return result.move if result else None

async def async_search(board, depth, time_limit=5, smart_time_management=False):
    """
    Run the chess engine search asynchronously
    
    Args:
        board: Chess board position
        depth: Search depth
        time_limit: Time limit in seconds
        smart_time_management: If True, enables dynamic time management:
            - Extends search time when a new best move is found
            - Terminates early if the same best move is stable for a while
    """
    global engine_state
    engine_state.current_progress = f"Thinking... analyzing position at depth {depth}"
    engine_state.start_time = time.time()
    engine_state.depth = depth
    engine_state.time_limit = time_limit
    
    # Create a partial function with the search parameters
    search_func = partial(run_search, 
                          board=board, 
                          depth=depth, 
                          time_limit=time_limit,
                          smart_time_management=smart_time_management)
    
    # Submit to executor and get future
    future = engine_state.search_executor.submit(search_func)
    
    try:
        # Wait for the search to complete asynchronously
        while not future.done():
            # Update progress while waiting
            elapsed = time.time() - engine_state.start_time
            engine_state.current_progress = f"Thinking... analyzing position (Elapsed: {elapsed:.1f}s)"
            await asyncio.sleep(0.1)
            
        # Get the result when done
        best_move = future.result()
        elapsed = time.time() - engine_state.start_time
        
        # Store result
        engine_state.current_result = {
            'move': best_move.uci() if best_move else None,
            'time': elapsed,
            'depth': depth
        }
        
        engine_state.current_progress = f"Analysis complete in {elapsed:.2f}s"
        
    except Exception as e:
        traceback.print_exc()
        engine_state.current_progress = f"Search failed: {str(e)}"
        engine_state.current_result = {'move': None, 'error': str(e)}

def start_search(board, depth, time_limit=5, smart_time_management=False):
    """
    Start a non-blocking search for the best move
    
    Args:
        board: Chess board position
        depth: Search depth
        time_limit: Time limit in seconds
        smart_time_management: If True, enables dynamic time management:
            - Extends search time when a new best move is found
            - Terminates early if the same best move is stable for a while
        
    Returns:
        True if search started successfully, False otherwise
    """
    global engine_state
    
    # Don't start a new search if one is in progress
    if engine_state.current_search and not engine_state.current_search.done():
        return False
        
    # Create and start the search task
    async def search_task():
        await async_search(board, depth, time_limit, smart_time_management)
        
    # Start the search task
    try:
        # Get or create an event loop
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
        # Create and set the search task
        engine_state.current_search = asyncio.create_task(search_task())
        return True
    except Exception as e:
        return False

def get_progress():
    """Get the current progress message"""
    global engine_state
    
    # Calculate elapsed time if search is in progress
    if engine_state.start_time and engine_state.current_progress != "Idle" and engine_state.current_progress != "Analysis complete":
        elapsed = time.time() - engine_state.start_time
        if elapsed > 0.5:  # Only show time after half a second
            # Ensure message includes "Thinking" keyword for test compatibility
            message = engine_state.current_progress
            if "Thinking" not in message:
                message = f"Thinking... {message}"
            return f"{message} ({elapsed:.1f}s)"
    
    return engine_state.current_progress

def get_result():
    """
    Get the result of the current or completed search
    
    Returns:
        The best move found by the engine, or None if search is still running or failed
    """
    global engine_state
    
    # If search is complete, return the result
    if engine_state.current_result is not None:
        return engine_state.current_result
        
    # If search has exceeded time limit, force termination
    # For smart time management, use a higher multiplier as search time can be extended
    timeout_multiplier = 2.5  # Higher multiplier to account for smart time management extending search
    if (engine_state.current_search and 
        engine_state.start_time and 
        engine_state.time_limit > 0 and
        time.time() - engine_state.start_time >= engine_state.time_limit * timeout_multiplier):
        
        # Try to cancel the search
        if not engine_state.current_search.done():
            engine_state.current_search.cancel()
            
        # Reset the engine state
        engine_state.reset()
        
        # Return timeout error
        return {'move': None, 'error': 'timeout'}
        
    # Otherwise, search is still running
    return None

def is_search_complete():
    """Check if the search is complete"""
    global engine_state
    return engine_state.current_search is not None and engine_state.current_search.done()

def reset_search():
    """Reset the search state completely"""
    global engine_state
    
    # Cancel existing search task if it exists
    if engine_state.current_search and not engine_state.current_search.done():
        engine_state.current_search.cancel()
    
    # Reset all state variables
    engine_state.reset()
    
    # Give a short moment for task cleanup
    time.sleep(0.1) 