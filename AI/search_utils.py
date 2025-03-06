"""
Chess search utilities for Drawback Chess AI.
Contains the core negamax and quiescence search algorithms extracted from DrawbackBot.
"""
import chess
import time
from collections import namedtuple
from AI.piece_square_table import PIECE_VALUES
from AI.ai_utils import MATE_LOWER, MATE_UPPER, MAX_DEPTH

# Transposition table entry
Entry = namedtuple('Entry', 'lower upper move')

def quiescence_search(bot, board, alpha, beta, depth=0, max_depth=5):
    """
    Enhanced quiescence search that handles both captures and potential win conditions.
    Extends search dynamically when promising win patterns are detected.
    
    Args:
        bot: The DrawbackBot instance with evaluation methods
        board: Current position
        alpha: Alpha bound
        beta: Beta bound
        depth: Current depth
        max_depth: Maximum quiescence depth
        
    Returns:
        Position score
    """
    bot.nodes += 1
    
    # Early return if maximum depth reached to prevent excessive recursion
    if depth >= max_depth:
        return bot.evaluate_position(board)
        
    # Stand pat score - evaluate current position
    stand_pat = bot.evaluate_position(board)
    
    # Beta cutoff check
    if stand_pat >= beta:
        return beta
        
    # Adjust alpha if standing pat is better
    alpha = max(alpha, stand_pat)
    
    # Get tactical moves sorted by MVV/LVA (Most Valuable Victim/Least Valuable Attacker)
    tactical_moves = []
    for move in board.legal_moves:
        # Only include captures and promotions in quiescence search
        if board.is_capture(move) or move.promotion:
            # Score the move for sorting
            score = 0
            
            # Handle capture moves
            if board.is_capture(move):
                victim = board.piece_at(move.to_square)
                aggressor = board.piece_at(move.from_square)
                
                if victim and aggressor:
                    victim_symbol = victim.symbol().upper()
                    aggressor_symbol = aggressor.symbol().upper()
                    victim_value = PIECE_VALUES.get(victim_symbol, (0, 0))[0]
                    aggressor_value = PIECE_VALUES.get(aggressor_symbol, (0, 0))[0]
                    
                    # MVV-LVA scoring: 10 * victim value - attacker value
                    score = 10 * victim_value - aggressor_value
                    
                    # Bonus for capturing with less valuable piece
                    if victim_value > aggressor_value:
                        score += 50
                        
            # Handle promotion moves
            if move.promotion:
                score += 900  # Queen promotion value
                
            tactical_moves.append((score, move))
    
    # Sort moves by score in descending order
    tactical_moves.sort(reverse=True)
    
    # Search tactical moves
    for _, move in tactical_moves:
        try:
            # Skip bad captures in late quiescence unless they threaten something important
            if depth > 0 and board.is_capture(move):
                victim = board.piece_at(move.to_square)
                aggressor = board.piece_at(move.from_square)
                
                # Always check king captures
                if not (victim and victim.piece_type == chess.KING):
                    if victim and aggressor:
                        victim_symbol = victim.symbol().upper()
                        aggressor_symbol = aggressor.symbol().upper()
                        victim_value = PIECE_VALUES.get(victim_symbol, (0, 0))[0]
                        aggressor_value = PIECE_VALUES.get(aggressor_symbol, (0, 0))[0]
                    
                        # Skip "bad" captures in deep quiescence unless they threaten something
                        # More conservative approach - skip only very clearly bad captures
                        if victim_value < aggressor_value * 0.8 and depth >= 2:
                            continue
                            
            board.push(move)
            score = -quiescence_search(bot, board, -beta, -alpha, depth + 1, max_depth)
            board.pop()
            
            if score >= beta:
                return beta
            if score > alpha:
                alpha = score
        except Exception:
            # If move causes an error, pop it and continue
            if board.move_stack and board.move_stack[-1] == move:
                board.pop()
            continue  # Skip problematic moves
    
    return alpha

def negamax(bot, board, depth, alpha, beta, allow_null=True, can_enter_quiescence=True, start_time=None, time_limit=None):
    """
    Enhanced negamax search algorithm optimized for Drawback Chess.
    Includes null move pruning, killer moves, history heuristics and transposition tables.
    
    Args:
        bot: The DrawbackBot instance with evaluation methods
        board: Current position
        depth: Search depth
        alpha: Alpha bound
        beta: Beta bound
        allow_null: Whether null move pruning is allowed
        can_enter_quiescence: Whether search can enter quiescence at leaf nodes
        start_time: Optional start time for time limit checking
        time_limit: Optional time limit in seconds
        
    Returns:
        Position score
    """
    # Time limit check at the beginning of each call
    if start_time and time_limit and time.time() - start_time > time_limit:
        # Signal time limit reached by returning the current alpha
        return alpha
        
    # Check for direct win opportunity (king capture in Drawback Chess)
    for move in board.legal_moves:
        target = board.piece_at(move.to_square)
        if target and target.piece_type == chess.KING:
            return MATE_UPPER - 1
    
    # Direct draw detection
    # In Drawback Chess, a draw might still be a win due to special rules, 
    # so we check for variant loss
    if not any(True for _ in board.legal_moves):
        if board.is_variant_loss():
            return -MATE_UPPER
        return 0  # Draw
    
    # Transposition table lookup
    key = board.zobrist_hash() if hasattr(board, 'zobrist_hash') else str(board.fen())
    if key in bot.tt and bot.tt[key].lower <= bot.tt[key].upper:
        if bot.tt[key].lower >= beta:
            return bot.tt[key].lower
        if bot.tt[key].upper <= alpha:
            return bot.tt[key].upper
        alpha = max(alpha, bot.tt[key].lower)
        beta = min(beta, bot.tt[key].upper)

    # Leaf node
    if depth <= 0:
        if can_enter_quiescence:
            score = quiescence_search(bot, board, alpha, beta)
        else:
            score = bot.evaluate_position(board)
        return score

    # Null move pruning
    if allow_null and depth >= 3 and not board.is_check():
        # Don't use null move if the side to move is in danger of capture threat
        king_square = None
        for sq, piece in board.piece_map().items():
            if piece and piece.piece_type == chess.KING and piece.color == board.turn:
                king_square = sq
                break
        
        can_use_null = True
        if king_square:
            # If in Drawback Chess we have pieces that threaten the king, don't use null move
            attackers = board.attackers(not board.turn, king_square)
            if attackers:
                can_use_null = False
                
        if can_use_null:
            R = 3 if depth >= 5 else 2  # Dynamic null move reduction
            board.push(chess.Move.null())
            null_score = -negamax(bot, board, depth - 1 - R, -beta, -beta + 1, False, False)
            board.pop()
            
            if null_score >= beta:
                return beta
    
    # Get killer moves for the current ply
    killer1, killer2 = bot.killers[depth]
    
    # Move scoring for move ordering
    def move_value(move):
        """Score a move for move ordering"""
        # Assign a score to each move for sorting
        if move == killer1:
            return 900000
        if move == killer2:
            return 800000
            
        # Use history table for non-captures
        if not board.is_capture(move):
            from_to = (move.from_square, move.to_square)
            return bot.history.get(from_to, 0) 
            
        # Score captures
        target = board.piece_at(move.to_square)
        attacker = board.piece_at(move.from_square)
        
        if target and attacker:
            # MVV-LVA (Most Valuable Victim - Least Valuable Attacker)
            target_symbol = target.symbol().upper()
            attacker_symbol = attacker.symbol().upper()
            target_value = PIECE_VALUES.get(target_symbol, (0, 0))[0]
            attacker_value = PIECE_VALUES.get(attacker_symbol, (0, 0))[0]
            
            # King captures get highest priority
            if target.piece_type == chess.KING:
                return 1000000
                
            # Use MVV-LVA formula: 10 * victim value - attacker value
            # This prioritizes capturing valuable pieces with less valuable attackers
            return 10 * target_value - attacker_value + 500000
            
        return 0  # Default case
    
    # Get all legal moves and score them for move ordering
    moves = list(board.legal_moves)
    moves.sort(key=move_value, reverse=True)
    
    # Initialize bounds
    best_value = -MATE_UPPER
    best_move = None
    
    # Iterate through moves
    for move in moves:
        bot.nodes += 1
        
        # Check time limit periodically (every 1000 nodes)
        if start_time and time_limit and bot.nodes % 1000 == 0:
            if time.time() - start_time > time_limit:
                return alpha  # Return current best score
        
        try:
            # Apply book move bonuses if available
            book_bonus = 0
            if hasattr(bot, 'book_move_bonuses') and bot.book_move_bonuses:
                if move in bot.book_move_bonuses:
                    book_bonus = bot.book_move_bonuses[move] / 100.0  # Convert centipawns to pawn units
            
            board.push(move)
            # Reduced depth search for history pruning
            if best_value > -MATE_LOWER and depth >= 3 and not board.is_capture(move) and move != killer1 and move != killer2:
                score = -negamax(bot, board, depth - 2, -beta, -alpha, allow_null, can_enter_quiescence)
                if score <= alpha:
                    board.pop()
                    continue
            
            # Full depth search    
            score = -negamax(bot, board, depth - 1, -beta, -alpha, allow_null, can_enter_quiescence)
            
            # Add book bonus AFTER search
            if book_bonus > 0:
                score += book_bonus
                
            board.pop()
            
            # Beta cutoff
            if score >= beta:
                # Update history scores
                if not board.is_capture(move):
                    from_to = (move.from_square, move.to_square)
                    if from_to in bot.history:
                        bot.history[from_to] += depth * depth
                    else:
                        bot.history[from_to] = depth * depth
                    
                    # Update killer moves
                    if move != killer1:
                        bot.killers[depth] = (move, killer1)
                
                # Update transposition table (lower bound)
                bot.tt[key] = Entry(score, MATE_UPPER, move)
                return beta
            
            # Alpha improvement
            if score > best_value:
                best_value = score
                best_move = move
                
                if score > alpha:
                    alpha = score
        except Exception:
            board.pop()
            continue
        
    # No legal moves - this should be caught earlier but just in case
    if best_value == -MATE_UPPER:
        # Check if this is a checkmate or stalemate
        return 0  # Draw - should be updated if drawbacks change this
        
    # Update transposition table
    if best_move:
        # We have a PV-node or a cut-node
        if best_value <= alpha:
            # All-node (upper bound)
            bot.tt[key] = Entry(-MATE_UPPER, best_value, None)
        else:
            # PV-node (exact)
            bot.tt[key] = Entry(best_value, best_value, best_move)
    
    return best_value 