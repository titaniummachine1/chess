"""
Async wrapper for the chess engine - allows non-blocking search
"""
import asyncio
import chess
import time
import threading
import traceback
from concurrent.futures import ThreadPoolExecutor
from AI.drawback_sunfish import DrawbackSunfish  # Proper import

# Global state for async search
current_search = None
current_progress = "Idle"
current_result = None
search_executor = ThreadPoolExecutor(max_workers=1)

# Constants for evaluation
CHECKMATE_SCORE = 10000
DRAW_SCORE = 0

def evaluate_position(board, drawbacks=None):
    """
    Evaluate the current position from the perspective of the current player
    Returns a score where positive is better for the current player
    """
    # Check for game over states
    if board.is_checkmate():
        return -CHECKMATE_SCORE  # Losing
    
    if board.is_stalemate() or board.is_insufficient_material() or board.is_fifty_moves() or board.is_repetition():
        return DRAW_SCORE  # Draw
    
    # Basic material evaluation
    piece_values = {
        chess.PAWN: 100,
        chess.KNIGHT: 320,
        chess.BISHOP: 330,
        chess.ROOK: 500,
        chess.QUEEN: 900,
        chess.KING: 0  # King's value is implied in checkmate
    }
    
    score = 0
    
    # Material count
    for piece_type in piece_values:
        score += len(board.pieces(piece_type, board.turn)) * piece_values[piece_type]
        score -= len(board.pieces(piece_type, not board.turn)) * piece_values[piece_type]
    
    return score

def get_ordered_moves(board, drawbacks=None):
    """Get moves in a good order for alpha-beta pruning efficiency"""
    return list(board.legal_moves)

def run_search(board, depth):
    """Run the engine search in a separate thread with detailed logging"""
    try:
        start_time = time.time()
        print(f"Search started at depth {depth}")
        
        # Always use a copy of the board
        board_copy = board.copy()
        
        # Create search engine instance and run actual search
        engine = DrawbackSunfish()
        best_move = engine.search(board_copy, depth, time_limit=5)
        
        # Simple completion info without excessive debug output
        elapsed = time.time() - start_time
        print(f"Search completed, found move: {best_move}")
        
        return best_move
    except Exception as e:
        print(f"Search error: {e}")
        print(traceback.format_exc())  # Print full stack trace
        return None

async def async_search(board, depth):
    """Run the chess engine search asynchronously"""
    global current_progress, current_result
    current_progress = f"Searching at depth {depth}..."
    print(f"Search started at depth {depth}")
    
    try:
        # Make a copy of the board for thread safety
        board_copy = board.copy()
        
        loop = asyncio.get_running_loop()
        current_result = await loop.run_in_executor(
            search_executor,
            lambda: run_search(board_copy, depth)
        )
        
        if current_result:
            print(f"Search completed, found move: {current_result}")
            current_progress = "Search complete"
        else:
            print("Search completed but no move was found")
            current_progress = "No move found"
            
    except Exception as e:
        print(f"Search error: {e}")
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
