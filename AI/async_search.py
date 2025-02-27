import threading
import time
import copy
from AI.search import negamax, score_move
import chess

# Global variables to track AI state
ai_thinking = False
ai_current_depth = 0
ai_best_move = None
ai_progress = ""

def iterative_deepening_search(board, max_depth, time_limit=5.0):
    """
    Performs iterative deepening search starting from depth 1 up to max_depth.
    Uses a time limit to ensure the AI doesn't take too long.
    Returns the best move found within the time limit.
    """
    global ai_thinking, ai_current_depth, ai_best_move, ai_progress
    
    ai_thinking = True
    ai_best_move = None
    start_time = time.time()
    
    # Start with all legal moves
    moves = list(board.legal_moves)
    if not moves:
        ai_thinking = False
        return None
    
    # Check for immediate king captures
    for move in moves:
        captured_piece = board.piece_at(move.to_square)
        if captured_piece and captured_piece.piece_type == chess.KING:
            ai_best_move = move
            ai_progress = f"Found king capture!"
            ai_thinking = False
            return move
    
    # Sort moves for better pruning using basic heuristic
    moves.sort(key=lambda mv: score_move(board, mv), reverse=True)
    
    # Start iterative deepening
    for depth in range(1, max_depth + 1):
        if time.time() - start_time > time_limit:
            # Time limit reached, return the best move from previous depth
            break
        
        ai_current_depth = depth
        ai_progress = f"Searching at depth {depth}..."
        
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
            if time.time() - start_time > time_limit:
                break
        
        if best_move:
            ai_best_move = best_move
            ai_progress = f"Depth {depth}: {best_move}, score {best_score}"
    
    # Search completed
    ai_thinking = False
    return ai_best_move

def async_best_move(board, max_depth):
    """
    Start the AI search in a separate thread and return immediately.
    The result will be stored in ai_best_move when the search completes.
    """
    global ai_thinking, ai_current_depth, ai_best_move, ai_progress
    
    # If AI is already thinking, don't start another search
    if ai_thinking:
        return None
    
    # Reset state
    ai_thinking = True
    ai_current_depth = 0
    ai_best_move = None
    ai_progress = "Starting search..."
    
    # Start the search in a separate thread
    thread = threading.Thread(
        target=iterative_deepening_search,
        args=(copy.deepcopy(board), max_depth),
        daemon=True
    )
    thread.start()
    
    # Return immediately, the result will be stored in ai_best_move
    return None

def is_thinking():
    """Returns whether the AI is currently thinking."""
    return ai_thinking

def get_current_depth():
    """Returns the current search depth."""
    return ai_current_depth

def get_best_move():
    """Returns the best move found so far."""
    return ai_best_move

def get_progress():
    """Returns a string describing the current search progress."""
    return ai_progress
