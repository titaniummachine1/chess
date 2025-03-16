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
import random

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
        self.original_start_time = None
        self.depth = 0
        self.time_limit = 0
        self.last_best_move = None  # Track the last best move for comparison
        self.current_best_move = None  # Current best move
        self.board = None  # Added to store the board
        
        # Persistent search data between moves
        self.transposition_table = {}  # Preserve TT between moves
        self.killer_moves = None  # Preserve killer moves between moves
        self.history_heuristic = {}  # Preserve history heuristic between moves
        self.principal_variation = []  # Store the principal variation
        
        self.partial_result = None  # Partial result from search (best move so far)
        
    def reset(self):
        """Reset the engine state completely but preserve search knowledge"""
        self.current_progress = "Idle"
        self.current_result = None
        self.start_time = None
        self.original_start_time = None
        self.depth = 0
        self.time_limit = 0
        self.last_best_move = None
        self.current_best_move = None
        self.board = None
        
        # Note: We do NOT reset transposition_table, killer_moves, history_heuristic, or principal_variation
        # This allows search knowledge to persist between moves
        
        self.partial_result = None
        
    def clear_search_knowledge(self):
        """Clear all accumulated search knowledge (use sparingly)"""
        self.transposition_table = {}
        self.killer_moves = None
        self.history_heuristic = {}
        self.principal_variation = []

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
    
    print(f"Starting engine search at depth {depth}, time limit {time_limit}s")
    print(f"Board position: {board.fen()}")
    print(f"Turn: {'White' if board.turn == chess.WHITE else 'Black'}")
    
    # Get the active drawback for the current player
    active_drawback = None
    if hasattr(board, 'get_active_drawback'):
        active_drawback = board.get_active_drawback(board.turn)
        print(f"Active drawback for current player: {active_drawback}")
    
    # Create a board copy for thread safety
    board_copy = board.copy()
    
    # Add a flag to indicate we're in a search - critical for drawback checks
    if hasattr(board_copy, '_in_search'):
        board_copy._in_search = True
    
    # Get the preserved search data from the engine state
    global engine_state
    preserved_data = {
        'transposition_table': engine_state.transposition_table,
        'killer_moves': engine_state.killer_moves,
        'history_heuristic': engine_state.history_heuristic,
        'principal_variation': engine_state.principal_variation
    }
    
    try:
        # List all legal moves before starting search
        legal_moves = list(board_copy.legal_moves)
        print(f"Legal moves count: {len(legal_moves)}")
        if len(legal_moves) > 0:
            print(f"Sample legal moves: {[move.uci() for move in legal_moves[:5]]}")
        else:
            print("WARNING: No legal moves available!")
            return None
        
        # Call the engine to get best move
        # When smart_time_management is True, the search will extend time when a new best move is found
        # and terminate early if the best move remains stable
        result = select_best_move(board_copy, depth, time_limit, {}, smart_time_management, preserved_data=preserved_data)
    
        # If the engine returned updated search data, store it for future searches
        if hasattr(result, 'tt') and result.tt:
            engine_state.transposition_table = result.tt
        if hasattr(result, 'killers') and result.killers:
            engine_state.killer_moves = result.killers
        if hasattr(result, 'history') and result.history:
            engine_state.history_heuristic = result.history
        if hasattr(result, 'pv') and result.pv:
            engine_state.principal_variation = result.pv
        
        if result.move:
            print(f"Search completed successfully, selected move: {result.move.uci()}, score: {result.score}")
            engine_state.current_best_move = result.move
            return result.move
        else:
            print("WARNING: Search completed but no move was found!")
    except Exception as e:
        print(f"ERROR in engine search: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        
    # If we get here, either the search failed or no move was found
    # Try to select a good fallback move
    
    print("Attempting to find fallback move...")
    
    # Try to select a legal move as fallback
    if board_copy.legal_moves:
        legal_moves = list(board_copy.legal_moves)
        
        # First look for king captures (instant win)
        for move in legal_moves:
            target_piece = board_copy.piece_at(move.to_square)
            if target_piece and target_piece.piece_type == chess.KING:
                print("Fallback selected immediate king capture")
                return move
                
        # For atomic bomb, find threatened pieces adjacent to king
        if active_drawback == "atomic_bomb":
            # Find our king
            king_square = None
            for square in chess.SQUARES:
                piece = board_copy.piece_at(square)
                if piece and piece.piece_type == chess.KING and piece.color == board_copy.turn:
                    king_square = square
                    break
                    
            if king_square:
                # Find adjacent squares
                adjacent_squares = []
                king_file, king_rank = chess.square_file(king_square), chess.square_rank(king_square)
                for file_offset in [-1, 0, 1]:
                    for rank_offset in [-1, 0, 1]:
                        if file_offset == 0 and rank_offset == 0:
                            continue  # Skip the king's own square
                        
                        target_file = king_file + file_offset
                        target_rank = king_rank + rank_offset
                        
                        # Skip off-board squares
                        if not (0 <= target_file < 8 and 0 <= target_rank < 8):
                            continue
                        
                        adjacent_squares.append(chess.square(target_file, target_rank))
                        
                # Find any moves that protect threatened pieces next to king
                for move in legal_moves:
                    # Moving pieces away from danger
                    if move.from_square in adjacent_squares:
                        # A piece next to the king is moving
                        print(f"Fallback selected move that gets a piece away from the king: {move.uci()}")
                        return move
        
        # As a last resort, select a random legal move
        fallback_move = random.choice(legal_moves)
        print(f"Fallback selected random move: {fallback_move.uci()}")
        return fallback_move
        
    return None

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
    engine_state.original_start_time = engine_state.start_time  # Save original start time
    engine_state.depth = depth
    engine_state.time_limit = time_limit
    engine_state.last_best_move = None
    engine_state.current_best_move = None
    engine_state.board = board
    
    # CRITICAL: First check for immediate wins before doing any search
    # 1. Look for direct king captures - absolute highest priority
    for move in board.legal_moves:
        target = board.piece_at(move.to_square)
        if target and target.piece_type == chess.KING:
            elapsed = 0.1  # Minimal time since this is instant
            engine_state.current_result = {
                'move': move.uci(),
                'score': 30000,  # Much higher than normal evaluation
                'time': elapsed,
                'depth': depth,
                'note': 'immediate_king_capture'
            }
            engine_state.current_progress = f"Found immediate king capture: {move.uci()}"
            return  # Exit immediately - no need to search
            
    # 2. For atomic bomb drawback, check if we can cause a loss by capturing a piece adjacent to opponent's king
    opponent_color = not board.turn
    if hasattr(board, 'get_active_drawback'):
        active_drawback = board.get_active_drawback(opponent_color)
        if active_drawback == "atomic_bomb":
            # Find opponent's king
            opponent_king_square = None
            for square in chess.SQUARES:
                piece = board.piece_at(square)
                if piece and piece.piece_type == chess.KING and piece.color == opponent_color:
                    opponent_king_square = square
                    break
                    
            if opponent_king_square:
                # Check each adjacent square for opponent pieces we can capture
                king_file, king_rank = chess.square_file(opponent_king_square), chess.square_rank(opponent_king_square)
                for file_offset in [-1, 0, 1]:
                    for rank_offset in [-1, 0, 1]:
                        if file_offset == 0 and rank_offset == 0:
                            continue  # Skip the king itself
                        
                        target_file = king_file + file_offset
                        target_rank = king_rank + rank_offset
                        
                        # Skip off-board squares
                        if not (0 <= target_file < 8 and 0 <= target_rank < 8):
                            continue
                            
                        target_square = chess.square(target_file, target_rank)
                        # Check if there's an opponent's piece here that we can capture
                        target_piece = board.piece_at(target_square)
                        if target_piece and target_piece.color == opponent_color:
                            # Look for a move that captures this piece
                            for move in board.legal_moves:
                                if move.to_square == target_square and board.is_capture(move):
                                    elapsed = 0.1  # Again, minimal time
                                    engine_state.current_result = {
                                        'move': move.uci(),
                                        'score': 29000,  # Very high score
                                        'time': elapsed,
                                        'depth': depth,
                                        'note': 'atomic_bomb_win'
                                    }
                                    engine_state.current_progress = f"Found atomic bomb win: {move.uci()}"
                                    return  # Exit immediately - this is a winning move
    
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
        
    # Initialize search state
    engine_state.start_time = time.time()
    engine_state.original_start_time = engine_state.start_time  # Save original start time
    engine_state.depth = depth
    engine_state.time_limit = time_limit
    engine_state.board = board
    engine_state.current_result = None
    engine_state.last_best_move = None
    engine_state.partial_result = None
    engine_state.current_progress = f"Starting search at depth {depth}..."
        
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
        print(f"Error starting search: {e}")
        engine_state.current_progress = f"Failed to start search: {str(e)}"
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
    
    # Check if there's a partial result available from drawback_Bot
    try:
        from AI.drawback_Bot import current_best_move, current_best_score
        
        # See if we have a current best move
        if current_best_move is not None:
            # If we have a move, check if it's different from the last one we saw
            move_str = current_best_move.uci() if current_best_move else None
            
            if move_str and move_str != engine_state.last_best_move:
                print(f"New best move found in search: {move_str}, resetting search timer")
                
                # New best move found, update our tracking and reset the timer
                engine_state.last_best_move = move_str
                engine_state.start_time = time.time()  # Reset the timer!
                
                # Save as partial result to ensure we don't lose it on timeout
                engine_state.partial_result = {
                    'move': move_str,
                    'time': time.time() - engine_state.original_start_time if engine_state.original_start_time else 0,
                    'depth': engine_state.depth,
                    'partial': True
                }
                return None  # Return None to indicate search is still in progress
    except (ImportError, AttributeError):
        # If we can't access the current best move, just continue
        pass
        
    # If search has exceeded time limit, force termination
    if (engine_state.current_search and 
        engine_state.start_time and 
        engine_state.time_limit > 0 and
        time.time() - engine_state.start_time >= engine_state.time_limit):
        
        # Before forcing termination, check if there are any obvious winning moves
        # This helps avoid overlooking critical moves due to timeouts
        if engine_state.board is not None:
            winning_move = find_immediate_win(engine_state.board)
            if winning_move:
                print(f"Found immediate winning move before timeout: {winning_move.uci()}")
                elapsed = time.time() - engine_state.start_time
                return {
                    'move': winning_move.uci(),
                    'time': elapsed,
                    'depth': engine_state.depth,
                    'note': 'immediate_win'
                }
        
        # Try to get the current best move from the search before cancelling
        try:
            from AI.drawback_Bot import current_best_move
            
            if current_best_move is not None:
                move_str = current_best_move.uci() if current_best_move else None
                if move_str:
                    print(f"Using best move found before timeout: {move_str}")
                    elapsed = time.time() - engine_state.start_time
                    
                    # Try to cancel the search
                    if not engine_state.current_search.done():
                        engine_state.current_search.cancel()
                        
                    # Reset the engine state
                    engine_state.reset()
                    
                    return {
                        'move': move_str,
                        'time': elapsed,
                        'depth': engine_state.depth,
                        'note': 'timeout_best_move'
                    }
        except (ImportError, AttributeError):
            # If we can't access the current best move, continue with timeout
            pass
            
        # Check if we have a partial result saved
        if engine_state.partial_result and 'move' in engine_state.partial_result:
            print(f"Using partial result from search: {engine_state.partial_result['move']}")
            partial_result = engine_state.partial_result
            
            # Try to cancel the search
            if not engine_state.current_search.done():
                engine_state.current_search.cancel()
                
            # Reset the engine state
            engine_state.reset()
            
            # Add elapsed time to result
            partial_result['time'] = time.time() - engine_state.original_start_time if engine_state.original_start_time else 0
            partial_result['note'] = 'partial_result_on_timeout'
            
            return partial_result
        
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
    
    # Clear all search knowledge when resetting between different players
    # This is critical to avoid perspective inconsistencies
    engine_state.clear_search_knowledge()
    
    # Give a short moment for task cleanup
    time.sleep(0.1) 