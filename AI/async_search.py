import threading
import time
import copy
import chess
from AI.search import negamax, score_move

# Global variables to track AI state
ai_thinking = False
ai_search_complete = False
ai_current_depth = 0
ai_completed_depth = 0  # Track the highest completed depth
ai_target_depth = 0
ai_best_move = None
ai_progress = ""
ai_board_position = None
ai_start_time = None
ai_min_think_time = 0.8

def iterative_deepening_search(board, max_depth, time_limit=5.0):
    """
    Performs iterative deepening search starting from depth 1 up to max_depth.
    Uses a time limit to ensure the AI doesn't take too long.
    Returns the best move found within the time limit.
    """
    global ai_thinking, ai_search_complete, ai_current_depth, ai_completed_depth
    global ai_target_depth, ai_best_move, ai_progress, ai_board_position, ai_start_time
    
    ai_thinking = True
    ai_search_complete = False
    ai_best_move = None
    ai_board_position = board.fen()
    ai_start_time = time.time()
    
    # Start with all legal moves
    moves = list(board.legal_moves)
    if not moves:
        ai_thinking = False
        ai_progress = "No legal moves"
        return None
    
    # Check for immediate king captures
    for move in moves:
        captured_piece = board.piece_at(move.to_square)
        if captured_piece and captured_piece.piece_type == chess.KING:
            ai_best_move = move
            ai_progress = f"Found king capture"
            ai_completed_depth = 1  # Set completed depth
            # Even with king capture, enforce minimum think time
            ensure_min_think_time()
            ai_search_complete = True
            ai_thinking = False
            return move
    
    # Sort moves for better pruning using basic heuristic
    moves.sort(key=lambda mv: score_move(board, mv), reverse=True)
    
    # Start iterative deepening
    for depth in range(1, max_depth + 1):
        if time.time() - ai_start_time > time_limit:
            # Time limit reached, return the best move from previous depth
            break
        
        ai_current_depth = depth
        ai_progress = f"Searching..."
        
        alpha = -float('inf')
        beta = float('inf')
        best_score = -float('inf')
        best_move = None
        
        for move in moves:
            # Make a copy of the board to avoid modifying the original
            new_board = board.copy()
            new_board.push(move)
            
            # Search deeper
            score = -negamax(new_board, depth - 1, -beta, -alpha)
            
            if score > best_score:
                best_score = score
                best_move = move
                alpha = max(alpha, score)
            
            # Check if time limit is exceeded during search
            if time.time() - ai_start_time > time_limit:
                break
        
        if best_move:
            ai_best_move = best_move
            ai_completed_depth = depth  # Update the completed depth
            ai_progress = f"Found move"
            
            # Mark as complete when we reach the target depth
            if depth >= ai_target_depth:
                # Still enforce minimum think time
                ensure_min_think_time()
                ai_search_complete = True
    
    # Search completed or timed out
    ai_search_complete = True
    ai_thinking = False
    return ai_best_move

def ensure_min_think_time():
    """Ensure AI thinks for at least the minimum time to avoid instant moves"""
    global ai_start_time, ai_min_think_time
    
    elapsed = time.time() - ai_start_time
    if elapsed < ai_min_think_time:
        time.sleep(ai_min_think_time - elapsed)

def async_best_move(board, max_depth):
    """
    Start the AI search in a separate thread and return immediately.
    The result will be stored in ai_best_move when the search completes.
    """
    global ai_thinking, ai_search_complete, ai_current_depth, ai_completed_depth
    global ai_target_depth, ai_best_move, ai_progress, ai_board_position
    
    # If AI is already thinking, don't start another search
    if ai_thinking:
        return None
    
    # Reset state
    ai_thinking = True
    ai_search_complete = False
    ai_current_depth = 0
    ai_completed_depth = 0
    ai_target_depth = max_depth
    ai_best_move = None
    ai_progress = "Starting search..."
    ai_board_position = board.fen()
    
    # Create a deep copy of the board to avoid any shared state issues
    board_copy = board.copy()
    
    # Start the search in a separate thread
    thread = threading.Thread(
        target=iterative_deepening_search,
        args=(board_copy, max_depth),
        daemon=True
    )
    thread.start()
    
    # Return immediately, the result will be stored in ai_best_move
    return None

def is_thinking():
    """Returns whether the AI is currently thinking."""
    return ai_thinking

def is_search_complete():
    """Returns whether the AI search has completed to the desired depth."""
    return ai_search_complete

def get_current_depth():
    """Returns the current search depth."""
    return ai_current_depth

def get_completed_depth():
    """Returns the highest completed search depth."""
    return ai_completed_depth

def get_target_depth():
    """Returns the target search depth."""
    return ai_target_depth

def get_best_move():
    """Returns the best move found so far."""
    return ai_best_move

def get_progress():
    """Returns a string describing the current search progress."""
    global ai_start_time, ai_completed_depth, ai_target_depth
    elapsed_time = 0 if ai_start_time is None else time.time() - ai_start_time
    return f"Depth {ai_completed_depth}/{ai_target_depth} ({elapsed_time:.1f}s)"

def get_board_position():
    """Returns the FEN of the position being evaluated."""
    return ai_board_position
