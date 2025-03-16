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
from GameState.drawbacks.atomic_bomb import check_explosion_loss

# Cache structures
EngineResult = namedtuple('EngineResult', 'move score pv nodes time tt killers history')
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
    Check if the current position triggers a loss condition for drawbacks
    
    Args:
        board: Chess board position
        
    Returns:
        tuple: (has_loss, losing_color, reason)
    """
    # Check each player's active drawback
    for color in [chess.WHITE, chess.BLACK]:
        active_drawback = board.get_active_drawback(color) if hasattr(board, 'get_active_drawback') else None
        
        if active_drawback:
            try:
                # Get the loss condition function for this drawback
                loss_function = get_drawback_loss_function(active_drawback)
                
                if loss_function:
                    print(f"CHECKING LOSS CONDITION for {active_drawback} drawback (player {'White' if color == chess.WHITE else 'Black'})")
                    has_lost, reason = loss_function(board, color)
                    
                    if has_lost:
                        print(f"LOSS DETECTED: {active_drawback} loss condition triggered for {'White' if color == chess.WHITE else 'Black'}")
                        if reason:
                            print(f"Reason: {reason}")
                        return True, color, reason
                        
            except Exception as e:
                print(f"ERROR checking loss condition for {active_drawback}: {e}")
                import traceback
                traceback.print_exc()
                
    # Special case for atomic bomb - additional verification
    for color in [chess.WHITE, chess.BLACK]:
        active_drawback = board.get_active_drawback(color) if hasattr(board, 'get_active_drawback') else None
        
        if active_drawback == "atomic_bomb":
            try:
                # Check for atomic bomb specifically
                from GameState.drawbacks.atomic_bomb import check_explosion_loss
                print(f"ATOMIC BOMB LOSS CHECK: Checking if last capture was adjacent to {color} king")
                has_lost, reason = check_explosion_loss(board, color)
                
                if has_lost:
                    print(f"ATOMIC BOMB CONFIRMED: The last capture was adjacent to the {color} king")
                    return True, color, reason
                    
            except Exception as e:
                print(f"ERROR in atomic bomb check: {e}")
                import traceback
                traceback.print_exc()
    
    # No loss conditions triggered
    return False, None, None

def select_best_move(board, depth, time_limit, book_move_bonuses=None, smart_time_management=False, preserved_data=None):
    """
    Unified function to select the best move for a position
    
    Args:
        board: Chess board position
        depth: Maximum search depth
        time_limit: Time limit in seconds
        book_move_bonuses: Dictionary of book moves with bonus values
        smart_time_management: If True, terminate early if best move is stable
        preserved_data: Dictionary of preserved search data from previous searches
        
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
                score=MATE_UPPER,
                pv=[move.uci()],
                nodes=1,
                time=0.01,
                tt={},
                killers=[[None, None]],
                history={}
            )
    
    # Set up time management
    start_time = time.time()
    max_time = min(time_limit, 30.0)  # Cap at 30 seconds to prevent hangs
    
    # Use the DrawbackBot if available
    try:
        from AI.drawback_Bot import DrawbackBot
        engine = DrawbackBot()
        
        # Apply preserved search data if available
        if preserved_data:
            if 'transposition_table' in preserved_data and preserved_data['transposition_table']:
                engine.tt = preserved_data['transposition_table']
            if 'killer_moves' in preserved_data and preserved_data['killer_moves']:
                engine.killers = preserved_data['killer_moves']
            if 'history_heuristic' in preserved_data and preserved_data['history_heuristic']:
                engine.history = preserved_data['history_heuristic']
        
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
            # Get the principal variation if available
            principal_variation = []
            if hasattr(engine, 'principal_variation') and engine.principal_variation:
                principal_variation = engine.principal_variation
            elif best_move:
                principal_variation = [best_move.uci()]
            
            # Create result with preserved search data
            return EngineResult(
                move=best_move,
                score=score,
                pv=principal_variation,
                nodes=engine.nodes,
                time=elapsed,
                tt=engine.tt,
                killers=engine.killers,
                history=engine.history
            )
        else:
            # Try to find any legal move as a fallback
            king_capture_move = get_king_capture_move(board)
            if king_capture_move:
                return EngineResult(
                    move=king_capture_move, 
                    score=MATE_UPPER,
                    pv=[king_capture_move.uci()],
                    nodes=1,
                    time=elapsed,
                    tt=engine.tt,
                    killers=engine.killers,
                    history=engine.history
                )
                
            # Last resort: pick a random legal move
            legal_moves = list(board.legal_moves)
            if legal_moves:
                random_move = random.choice(legal_moves)
                return EngineResult(
                    move=random_move,
                    score=0,
                    pv=[random_move.uci()],
                    nodes=1,
                    time=elapsed,
                    tt=engine.tt,
                    killers=engine.killers,
                    history=engine.history
                )
    except ImportError:
        # Use fallback method if DrawbackBot is not available
        best_move = bot_best_move(board, depth, time_limit, book_move_bonuses)
        elapsed = time.time() - start_time
        return EngineResult(
            move=best_move,
            score=0,
            pv=[best_move.uci()] if best_move else [],
            nodes=0,
            time=elapsed,
            tt={},
            killers=[[None, None]],
            history={}
        )
    except Exception as e:
        # If any error occurs, return a minimal result
        print(f"Error in select_best_move: {e}")
        import traceback
        traceback.print_exc()
        
        # Try to at least return a legal move
        legal_moves = list(board.legal_moves)
        if legal_moves:
            fallback_move = legal_moves[0]
            return EngineResult(
                move=fallback_move,
                score=0,
                pv=[fallback_move.uci()],
                nodes=0,
                time=time.time() - start_time,
                tt={},
                killers=[[None, None]],
                history={}
            )
        
    # Should never reach here, but provide a null result just in case
    return EngineResult(
        move=None, 
        score=0, 
        pv=[], 
        nodes=0, 
        time=0, 
        tt={}, 
        killers=[[None, None]], 
        history={}
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

def find_immediate_win(board):
    """
    Checks for any immediate winning moves on the board
    
    Args:
        board: Current position
        
    Returns:
        A winning move if found, otherwise None
    """
    # Check each legal move for a direct win
    for move in board.legal_moves:
        # 1. Check for king capture (immediate win in Drawback Chess)
        target = board.piece_at(move.to_square)
        if target and target.piece_type == chess.KING:
            return move
            
        # 2. Check for atomic bomb win (capture adjacent to opponent's king)
        if board.is_capture(move):
            # Check if opponent has atomic bomb drawback
            opponent_color = not board.turn
            if hasattr(board, 'get_active_drawback'):
                active_drawback = board.get_active_drawback(opponent_color)
                if active_drawback == "atomic_bomb":
                    # Find opponent's king
                    king_square = None
                    for square, piece in board.piece_map().items():
                        if piece and piece.piece_type == chess.KING and piece.color == opponent_color:
                            king_square = square
                            break
                            
                    if king_square is not None:
                        # Check if capture is adjacent to king
                        capture_square = move.to_square
                        king_file, king_rank = chess.square_file(king_square), chess.square_rank(king_square)
                        capture_file = chess.square_file(capture_square)
                        capture_rank = chess.square_rank(capture_square)
                        
                        # If they're adjacent (within 1 square in any direction)
                        if abs(king_file - capture_file) <= 1 and abs(king_rank - capture_rank) <= 1:
                            if king_square != capture_square:  # Not the king itself
                                return move
    
    # 3. Try any drawback-specific logic for other drawbacks
    if hasattr(board, 'get_active_drawback'):
        opponent_color = not board.turn
        active_drawback = board.get_active_drawback(opponent_color)
        
        if active_drawback:
            # We could add special logic for other drawbacks here
            pass
            
    return None 