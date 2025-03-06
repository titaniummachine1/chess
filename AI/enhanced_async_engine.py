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

def run_search(board, depth, time_limit=5, smart_time_management=False):
    """
    Run the engine search in a separate thread
    
    Args:
        board: Chess board position
        depth: Search depth (passed directly to AI)
        time_limit: Time limit in seconds (used exactly as provided)
        smart_time_management: If True, terminate early if best move is stable
        
    Returns:
        Best move found by the engine
    """
    # Validate inputs
    assert board is not None, "Board cannot be None"
    assert depth > 0, f"Search depth must be positive, got {depth}"
    assert time_limit > 0, f"Time limit must be positive, got {time_limit}"
    
    start_time = time.time()
    print(f"Search started at depth {depth}, time limit {time_limit}s")
    if smart_time_management:
        print("Using smart time management: will stop early if best move is stable")
    
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
    
    # Find book moves to guide search, but NEVER play them directly
    book_move_bonuses = {}
    found_book_move = None
    
    try:
        from AI.book_handler import BookMoveSelector
        book_selector = BookMoveSelector()
        book_move_result = book_selector.get_weighted_book_move(board_copy)
        
        if book_move_result and book_move_result[0]:
            book_move = book_move_result[0]
            found_book_move = book_move  # Save for potential tiebreaker
            book_info = book_move_result[1]
            
            # Get the book move bonuses - these are stored with Move objects as keys
            raw_bonuses = book_info.get("book_move_bonuses", {})
            
            # Convert to a dictionary with UCI strings as keys for safer comparison
            for move, bonus in raw_bonuses.items():
                if isinstance(move, chess.Move):
                    book_move_bonuses[move.uci()] = bonus
                else:
                    book_move_bonuses[str(move)] = bonus
                    
            if book_move in legal_moves:
                print(f"Found book move: {book_move} (will use to guide search)")
    except Exception as e:
        print(f"Book move selection failed: {e}")
    
    # Pass the exact time limit and depth to the engine without further adjustments
    # Let the DrawbackBot handle iterative deepening internally
    print(f"Using exact time limit: {time_limit}s")
    
    # Call the engine to get best move
    result = select_best_move(board_copy, depth, time_limit, book_move_bonuses, smart_time_management)
    
    # Log search statistics
    elapsed = time.time() - start_time
    print(f"Search completed in {elapsed:.2f}s, found move: {result.move}")
    
    # In case of a fairly even evaluation and we found a book move, consider using it
    if result.move and found_book_move and abs(result.score) < 20:
        # If search result is very close to neutral, use book move as tiebreaker
        if found_book_move in legal_moves:
            print(f"Evaluation close to neutral, using book move as tiebreaker: {found_book_move}")
            return found_book_move
    
    # Return the search result, normally never use book moves directly
    return result.move

async def async_search(board, depth, time_limit=5, smart_time_management=False):
    """
    Run the chess engine search asynchronously
    
    Args:
        board: Chess board position
        depth: Search depth 
        time_limit: Time limit in seconds
        smart_time_management: If True, terminate early if best move is stable
    """
    global engine_state
    engine_state.current_progress = f"Analyzing position at depth {depth}..."
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
            engine_state.current_progress = f"Analyzing position... (Elapsed: {elapsed:.1f}s)"
            await asyncio.sleep(0.1)
            
        # Get the result when done
        best_move = future.result()
        elapsed = time.time() - engine_state.start_time
        
        # Store result
        engine_state.current_result = {
            'move': best_move.uci() if best_move else None,
            'time': elapsed,
            'nodes': 0,  # We don't have access to node count here
            'depth': depth
        }
        
        engine_state.current_progress = f"Search complete in {elapsed:.2f}s"
        print(f"Search is complete, retrieving result...")
        
    except Exception as e:
        print(f"Error in async search: {e}")
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
        smart_time_management: If True, terminate early if best move is stable
        
    Returns:
        True if search started successfully, False otherwise
    """
    global engine_state
    
    # Don't start a new search if one is in progress
    if engine_state.current_search and not engine_state.current_search.done():
        print("Search already in progress, please wait or reset")
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
            # No loop running, create one
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
        # Create and set the search task
        engine_state.current_search = asyncio.create_task(search_task())
        print(f"[DEBUG] Search task started successfully with time limit {time_limit}s")
        return True
    except Exception as e:
        print(f"Failed to start search: {e}")
        return False

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