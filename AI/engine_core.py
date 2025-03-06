"""
Engine Core Module - Unified interface for chess engine components
==================================================================

This module provides a simplified interface to the chess engine components,
reducing duplication and making the code more maintainable.
"""
import time
import chess
from collections import namedtuple

# Import engine components
from AI.drawback_sunfish import best_move as sunfish_best_move
from AI.ai_utils import get_king_capture_move, MATE_LOWER, MATE_UPPER, MAX_DEPTH
from AI.book_handler import BookMoveSelector
from AI.evaluation import evaluate_position

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
    
    # Try to get a book move
    book_move, _ = book_selector.get_weighted_book_move(board)
    if book_move:
        return EngineResult(
            move=book_move,
            score=100,  # Arbitrary positive score for book moves
            pv=[book_move],
            nodes=0,
            time=time.time() - start_time
        )
    
    # Fall back to engine search
    move = sunfish_best_move(board, depth, time_limit)
    
    # Calculate elapsed time
    elapsed = time.time() - start_time
    
    # Ensure we have a move, even if engine failed
    if not move and len(list(board.legal_moves)) > 0:
        # Fallback to random move
        stats = analyze_position(board)
        move = stats.legal_moves[0] if stats.legal_moves else None
    
    return EngineResult(
        move=move,
        score=0,  # We don't have the score from sunfish here
        pv=[move] if move else [],
        nodes=0,  # We don't have node count
        time=elapsed
    )

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