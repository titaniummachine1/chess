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

def select_best_move(board, depth=3, time_limit=1.0, book_move_bonuses=None):
    """
    Enhanced unified function to select the best move in the current position.
    Abstracts the engine complexity and provides cleaner interface.
    
    Args:
        board: Chess board position
        depth: Search depth
        time_limit: Time limit in seconds
        book_move_bonuses: Dictionary of bonuses for book moves
        
    Returns:
        EngineResult object with move, score, principal variation and stats
    """
    assert board is not None, "Board cannot be None"
    
    start_time = time.time()
    
    # Always work with a copy of the board for thread safety
    board_copy = board.copy()
    
    # First check for immediate win conditions
    # 1. Direct king capture
    for move in board_copy.legal_moves:
        target = board_copy.piece_at(move.to_square)
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
        
        # If we have book move bonuses, pass them to the engine
        if book_move_bonuses:
            engine.book_move_bonuses = book_move_bonuses
            
        # Start with iterative deepening from lower depths
        best_move = None
        best_score = -9999
        
        # Always search at least depth 1
        for current_depth in range(1, min(depth, 10) + 1):
            # Check if we've used more than 80% of our time budget
            elapsed = time.time() - start_time
            time_remaining = max_time - elapsed
            
            # Ensure we have at least 0.1s left for the search
            if time_remaining < 0.1:
                print(f"Breaking search at depth {current_depth-1} due to time constraint")
                break
                
            # Do a limited depth search
            try:
                score, move = engine.search(board_copy, current_depth, time_limit=time_remaining)
                
                # If we found a move, save it as our best so far
                if move:
                    best_move = move
                    best_score = score
                    
                    # Early exit if we found a winning move
                    if score > 9000:  # Near mate score
                        print(f"Found winning move at depth {current_depth}")
                        break
                        
                # Check time after each depth
                elapsed = time.time() - start_time
                if elapsed > max_time * 0.8:
                    print(f"Time limit approaching, stopping at depth {current_depth}")
                    break
            except Exception as e:
                print(f"Error at depth {current_depth}: {e}")
                # Continue with the best move found so far
                break
                
        # Check if we found a move
        if best_move:
            elapsed = time.time() - start_time
            print(f"Search completed at max depth {current_depth} in {elapsed:.2f}s")
            return EngineResult(
                move=best_move,
                score=best_score,
                pv=[best_move.uci()],
                nodes=engine.nodes,
                time=elapsed
            )
    except Exception as e:
        print(f"Error using DrawbackBot: {str(e)}")
        import traceback
        traceback.print_exc()
    
    # If we reach here, all above methods failed - use fallback
    # Just pick the first available legal move
    legal_moves = list(board_copy.legal_moves)
    if legal_moves:
        # If we have book moves, try to use one with the highest bonus
        if book_move_bonuses:
            best_book_move = None
            best_bonus = -1
            for move in legal_moves:
                if move in book_move_bonuses and book_move_bonuses[move] > best_bonus:
                    best_book_move = move
                    best_bonus = book_move_bonuses[move]
            
            if best_book_move:
                elapsed = time.time() - start_time
                print(f"Using best book move as fallback: {best_book_move.uci()}")
                return EngineResult(
                    move=best_book_move,
                    score=best_bonus,
                    pv=[best_book_move.uci()],
                    nodes=1,
                    time=elapsed
                )
        
        # Otherwise use first legal move
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