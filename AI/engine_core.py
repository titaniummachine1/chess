"""
Engine Core Module - Unified interface for chess engine components
==================================================================

This module provides a simplified interface to the chess engine components,
reducing duplication and making the code more maintainable.
"""
import time
import chess
from collections import namedtuple
import random

# Import engine components
from AI.drawback_Bot import best_move as bot_best_move
from AI.ai_utils import get_king_capture_move, MATE_LOWER, MATE_UPPER, MAX_DEPTH
from AI.book_handler import BookMoveSelector
from AI.evaluation import evaluate_position
from GameState.drawback_manager import get_drawback_loss_function

# Cache structures
EngineResult = namedtuple('EngineResult', 'move score pv nodes time')
PositionStats = namedtuple('PositionStats', 'legal_moves captures checks advancement_moves')

# Global instances
book_selector = BookMoveSelector()

def analyze_position(board, include_stats=False):
    """
    Analyze a position to get basic statistics and legal moves.
    This is a utility function that can be used by both the UI and engine.
    
    Args:
        board: Chess board position
        include_stats: Whether to include detailed statistics
        
    Returns:
        A PositionStats object with move counts and categories
    """
    # Always use a copy of the board for thread safety
    board_copy = board.copy()
    
    # Get all legal moves
    legal_moves = list(board_copy.legal_moves)
    
    # Only compute detailed stats if requested (to save time)
    if include_stats:
        # Categorize moves
        captures = []
        checks = []
        advancement_moves = []
        
        for move in legal_moves:
            # Track captures
            if board_copy.is_capture(move):
                captures.append(move)
                
            # See if move gives check
            board_copy.push(move)
            if board_copy.is_check():
                checks.append(move)
            
            # Consider pawn advancement and piece development as advancement moves
            piece = board_copy.piece_at(move.from_square)
            if piece and piece.piece_type == chess.PAWN:
                # Pawn moving forward is advancement
                if (piece.color == chess.WHITE and chess.square_rank(move.to_square) > chess.square_rank(move.from_square)) or \
                   (piece.color == chess.BLACK and chess.square_rank(move.to_square) < chess.square_rank(move.from_square)):
                    advancement_moves.append(move)
            
            board_copy.pop()
    else:
        captures = []
        checks = []
        advancement_moves = []
    
    return PositionStats(
        legal_moves=legal_moves,
        captures=captures,
        checks=checks, 
        advancement_moves=advancement_moves
    )

def check_drawback_loss_conditions(board):
    """
    Check if the current position has a loss condition based on active drawbacks.
    
    Args:
        board: DrawbackBoard position
        
    Returns:
        tuple: (has_loss, losing_color, reason) where:
            - has_loss: True if a loss condition is detected
            - losing_color: The color that lost (None if no loss)
            - reason: A string describing the loss reason (None if no loss)
    """
    # Check both colors for potential loss conditions
    for color in [chess.WHITE, chess.BLACK]:
        # Get the active drawback for this color
        drawback = board.get_active_drawback(color)
        if not drawback:
            continue
            
        # Get the loss condition function for this drawback
        loss_func = get_drawback_loss_function(drawback)
        if not loss_func:
            continue
            
        # Check if the loss condition is met
        try:
            if loss_func(board, color):
                return (True, color, f"{drawback} loss condition triggered")
        except Exception as e:
            print(f"Error checking loss condition for {drawback}: {e}")
    
    # No loss conditions detected
    return (False, None, None)

def select_best_move(board, depth=3, time_limit=1.0):
    """
    Select the best move using the engine and book.
    This is the main entry point for the AI system.
    
    Args:
        board: Chess board position
        depth: Search depth
        time_limit: Time limit in seconds
        
    Returns:
        An EngineResult object with the selected move and stats
    """
    start_time = time.time()
    
    # Mark board as being in search context to skip slow checks during search
    board._in_search = True
    
    try:
        # Always check for direct king captures first (unique to Drawback Chess)
        king_capture = get_king_capture_move(board)
        if king_capture:
            return EngineResult(
                move=king_capture,
                score=MATE_UPPER,
                pv=[king_capture],
                nodes=1,
                time=time.time() - start_time
            )
        
        # Extract book move bonuses from the info
        book_move, book_info = book_selector.get_weighted_book_move(board)
        book_move_bonuses = book_info.get("book_move_bonuses", {})
        special_move = book_info.get("special_move", None)
        all_book_moves = book_info.get("all_book_moves", [])
        
        # Apply book move bonuses during search, but let the AI choose the final move
        if book_move_bonuses:
            # There are book moves, but we'll let the search make the final decision
            print(f"Found {len(book_move_bonuses)} legal book moves for this position")
            if special_move:
                print(f"Special book move: {special_move} (gets 30cp bonus)")
                
            # Run the search with book move information
            # We let the search make the decision rather than returning the book move directly
            move = bot_best_move(board, depth, time_limit, book_move_bonuses)
            
            # Calculate elapsed time
            elapsed = time.time() - start_time
            
            # Ensure we have a move, even if engine failed
            if not move and len(list(board.legal_moves)) > 0:
                # Fallback to the suggested book move if available
                if book_move and book_move in board.legal_moves:
                    move = book_move
                    print(f"Search failed, using suggested book move: {move}")
                else:
                    # Fallback to first legal move (better than random for determinism)
                    stats = analyze_position(board)
                    move = stats.legal_moves[0] if stats.legal_moves else None
                    print(f"Search failed, using first legal move: {move}")
            
            return EngineResult(
                move=move,
                score=0,  # We don't have the score from the engine here
                pv=[move] if move else [],
                nodes=0,  # We don't have node count
                time=elapsed
            )
        else:
            # No book moves, run normal search
            move = bot_best_move(board, depth, time_limit)
            
            # Calculate elapsed time
            elapsed = time.time() - start_time
            
            # Ensure we have a move, even if engine failed
            if not move and len(list(board.legal_moves)) > 0:
                # Fallback to first legal move (better than random for determinism)
                stats = analyze_position(board)
                move = stats.legal_moves[0] if stats.legal_moves else None
            
            return EngineResult(
                move=move,
                score=0,  # We don't have the score from the engine here
                pv=[move] if move else [],
                nodes=0,  # We don't have node count
                time=elapsed
            )
    finally:
        # Always clear the search flag when done
        board._in_search = False

def evaluate_current_position(board, include_drawback_effects=True):
    """
    Evaluate the current position statically.
    This can be used for UI feedback and debugging.
    
    Args:
        board: Chess board position
        include_drawback_effects: Whether to consider drawback effects
        
    Returns:
        A numeric score from white's perspective
    """
    if include_drawback_effects:
        return evaluate_position(board)
    else:
        # Use standard evaluation without drawback considerations
        from AI.evaluation import evaluate_position_standard
        return evaluate_position_standard(board) 