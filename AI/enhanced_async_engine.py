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
from AI.engine_core import select_best_move, analyze_position, check_drawback_loss_conditions, EngineResult
from GameState.movegen import DrawbackBoard

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
        # Don't reset the executor here - we'll reuse it
        self.current_progress = "Idle"
        self.current_result = None
        self.start_time = None
        self.depth = 0
        self.time_limit = 0

# Create a singleton instance
engine_state = AsyncEngineState()

def run_search(board, depth, time_limit=5):
    """
    Run the engine search in a separate thread
    
    Args:
        board: Chess board position
        depth: Search depth
        time_limit: Time limit in seconds (used exactly as provided)
        
    Returns:
        Best move found by the engine
    """
    # Validate inputs
    assert board is not None, "Board cannot be None"
    assert depth > 0, f"Search depth must be positive, got {depth}"
    assert time_limit > 0, f"Time limit must be positive, got {time_limit}"
    
    start_time = time.time()
    print(f"Search started at depth {depth}, time limit {time_limit}s")
    
    # Always use a copy of the board for thread safety
    board_copy = board.copy()
    
    # Check for win conditions immediately
    # 1. Direct king capture (checkmate in standard chess)
    for move in board_copy.legal_moves:
        target = board_copy.piece_at(move.to_square)
        if target and target.piece_type == chess.KING:
            print(f"Found immediate win (king capture): {move}")
            return move
            
    # 2. Check for specific drawback win conditions
    has_loss, losing_color, reason = check_drawback_loss_conditions(board_copy)
    if has_loss and losing_color != board_copy.turn:
        print(f"Found drawback win condition: {reason}")
        # Look for the move that triggers this win
        # Since this is complex, let the engine figure it out
    
    # Verify legal moves available
    position_stats = analyze_position(board_copy)
    legal_moves = position_stats.legal_moves
    
    if not legal_moves:
        print("No legal moves available - game should be over")
        return None
    
    # Use the exact time limit as provided, without adjustments
    print(f"Using exact time limit: {time_limit}s")
    
    # Call the unified engine to get best move
    result = select_best_move(board_copy, depth, time_limit)
    
    # Log search statistics
    elapsed = time.time() - start_time
    print(f"Search completed in {elapsed:.2f}s, found move: {result.move}")
    
    # Ensure minimum thinking time for visual feedback
    min_think_time = 0.5  # At least 0.5 second of "thinking"
    if elapsed < min_think_time:
        time.sleep(min_think_time - elapsed)
    
    return result.move

async def async_search(board, depth, time_limit=5):
    """
    Run the chess engine search asynchronously
    
    Args:
        board: Chess board position
        depth: Search depth 
        time_limit: Time limit in seconds
    """
    global engine_state
    engine_state.current_progress = f"Analyzing position at depth {depth}..."
    engine_state.start_time = time.time()
    engine_state.depth = depth
    engine_state.time_limit = time_limit
    
    try:
        # Make a copy of the board for thread safety
        board_copy = board.copy()
        
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            engine_state.search_executor,
            partial(run_search, board_copy, depth, time_limit)
        )
        
        engine_state.current_result = result
        
        if result:
            engine_state.current_progress = "Analysis complete"
        else:
            engine_state.current_progress = "No move found"
    except Exception as e:
        print(f"ASYNC SEARCH ERROR: {str(e)}")
        traceback.print_exc()
        engine_state.current_progress = f"Search error: {str(e)}"
        engine_state.current_result = None

def start_search(board, depth, time_limit=5):
    """
    Start a new asynchronous search task
    
    Args:
        board: Chess board position
        depth: Search depth
        time_limit: Time limit in seconds
    """
    global engine_state
    
    # Cancel any existing search first
    if engine_state.current_search and not engine_state.current_search.done():
        engine_state.current_search.cancel()
        print("Cancelled existing search")
        
    # Make sure we have an event loop
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
    # Start the new search task
    engine_state.current_search = asyncio.create_task(async_search(board, depth, time_limit))
    engine_state.current_progress = f"Thinking at depth {depth} for {time_limit}s..."
    engine_state.start_time = time.time()
    print(f"[DEBUG] Search task started successfully with time limit {time_limit}s")

def get_progress():
    """Get the current progress message"""
    global engine_state
    
    # Calculate elapsed time if search is in progress
    if engine_state.start_time and engine_state.current_progress != "Idle" and engine_state.current_progress != "Analysis complete":
        elapsed = time.time() - engine_state.start_time
        if elapsed > 0.5:  # Only show time after half a second
            return f"{engine_state.current_progress} ({elapsed:.1f}s)"
    
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
        
    # If search is still running but has been going for at least the time limit,
    # check if we can extract a partial result from the engine
    if (engine_state.current_search and 
        engine_state.start_time and 
        engine_state.time_limit > 0 and
        time.time() - engine_state.start_time >= engine_state.time_limit):
        
        # Search has exceeded time limit but hasn't been properly completed
        print(f"Search time limit reached but no result available. Forcing termination.")
        
        # Try to cancel the search
        if not engine_state.current_search.done():
            engine_state.current_search.cancel()
            
        # In this case, we need to find a valid move some other way
        # For now, we'll return None and let the calling code handle it with fallback logic
        return None
        
    # Otherwise, search is still running or hasn't been started
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
        print("Active search task cancelled")
    
    # Reset all state variables
    engine_state.reset()
    
    # Give a short moment for task cleanup
    time.sleep(0.1)
    print("Search state reset") 