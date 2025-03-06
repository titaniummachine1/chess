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

def select_best_move(board, depth, time_limit, book_move_bonuses=None, smart_time_management=False):
    """
    Unified function to select the best move for a position
    
    Args:
        board: Chess board position
        depth: Maximum search depth
        time_limit: Time limit in seconds
        book_move_bonuses: Dictionary of book moves with bonus values
        smart_time_management: If True, terminate early if best move is stable
        
    Returns:
        EngineResult containing move, score, and search statistics
    """
    # Check for immediate win conditions
    # 1. Direct king capture
    for move in board.legal_moves:
        target = board.piece_at(move.to_square)
        if target and target.piece_type == chess.KING:
            # Found immediate win!
            return EngineResult(
                move=move,
                score=9900,
                pv=[move.uci()],
                nodes=1,
                time=0.01
            )
    
    # Set up time management
    start_time = time.time()
    max_time = min(time_limit, 30.0)  # Cap at 30 seconds to prevent hangs
    
    # Use the DrawbackBot if available
    try:
        from AI.drawback_Bot import DrawbackBot
        engine = DrawbackBot()
        
        # If we have book move bonuses, pass them to the engine, but with reduced importance
        if book_move_bonuses:
            # Convert the UCI strings to a proper format for the engine
            # This ensures we avoid any direct Move object comparisons
            uci_bonuses = {}
            
            for move_uci, bonus in book_move_bonuses.items():
                # Reduce the bonus to ensure it only guides search but doesn't dominate
                reduced_bonus = min(float(bonus) * 0.2, 10)  # Cap at 10 centipawns
                uci_bonuses[move_uci] = reduced_bonus
                
            engine.book_move_bonuses = uci_bonuses
            print(f"Using {len(uci_bonuses)} book moves to guide search (with reduced importance)")
        
        # Let the DrawbackBot handle the search with its own iterative deepening
        # This avoids nested iterative deepening loops
        score, best_move = engine.search(board, depth, time_limit=max_time, use_smart_time_management=smart_time_management)
        
        elapsed = time.time() - start_time
        
        # Check if we found a move
        if best_move:
            return EngineResult(
                move=best_move,
                score=score,
                pv=[best_move.uci()],
                nodes=engine.nodes,
                time=elapsed
            )
    except Exception as e:
        print(f"Error using DrawbackBot: {str(e)}")
        import traceback
        traceback.print_exc()
    
    # If we reach here, all above methods failed - use fallback legal move
    legal_moves = list(board.legal_moves)
    if legal_moves:
        fallback_move = legal_moves[0]
        elapsed = time.time() - start_time
        print(f"Using fallback move: {fallback_move.uci()}")
        return EngineResult(
            move=fallback_move,
            score=0,
            pv=[fallback_move.uci()],
            nodes=1,
            time=elapsed
        )
        
    # No legal moves available
    return EngineResult(move=None, score=-9999, pv=[], nodes=0, time=0)

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