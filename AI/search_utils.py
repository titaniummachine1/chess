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
    
    # Check for direct win opportunity (king capture in Drawback Chess)
    opponent_king_square = None
    for sq, piece in board.piece_map().items():
        if piece.piece_type == chess.KING and piece.color != board.turn:
            opponent_king_square = sq
            break
            
    if opponent_king_square:
        for move in board.legal_moves:
            if move.to_square == opponent_king_square:
                # Found immediate win (king capture)!
                return MATE_UPPER - depth
    
    # Check for draws and stalemates (no legal moves)
    if not any(True for _ in board.legal_moves):
        # This is a draw in standard chess, but in Drawback Chess could be a win or loss
        if board.is_variant_loss():
            return -MATE_UPPER + depth
        return 0  # Draw
    
    # Check for drawback-specific win conditions
    if opponent_king_square:
        # Get opponent's drawback
        opponent_color = not board.turn
        opponent_drawback = board.get_active_drawback(opponent_color)
        
        # Check for Atomic Bomb win condition
        if opponent_drawback == "atomic_bomb":
            king_file, king_rank = chess.square_file(opponent_king_square), chess.square_rank(opponent_king_square)
            
            # Look for captures adjacent to opponent's king
            for move in board.legal_moves:
                if board.is_capture(move):
                    to_file, to_rank = chess.square_file(move.to_square), chess.square_rank(move.to_square)
                    if abs(to_file - king_file) <= 1 and abs(to_rank - king_rank) <= 1:
                        # Found atomic bomb win!
                        return MATE_UPPER - depth - 1
    
    # Static evaluation
    stand_pat = bot.evaluate_position(board)
    
    # Stand pat cutoff
    if stand_pat >= beta:
        return beta
    if alpha < stand_pat:
        alpha = stand_pat
        
    # Maximum normal depth check
    if depth >= max_depth:
        # Even at max depth, if the stand_pat score is high, look a bit deeper
        # for potential win conditions to avoid horizon effect
        if stand_pat < MATE_LOWER and stand_pat > 500:
            # Only extend depth for promising positions
            pass
        else:
            return alpha
    
    # Generate tactical moves (captures and threats)
    tactical_moves = []
    
    # First, add captures with MVV-LVA scoring
    for move in board.legal_moves:
        score = 0
        is_tactical = False
        
        # Score captures
        if board.is_capture(move):
            is_tactical = True
            target = board.piece_at(move.to_square)
            attacker = board.piece_at(move.from_square)
            if target and attacker:
                target_symbol = target.symbol().upper()
                attacker_symbol = attacker.symbol().upper()
                target_value = PIECE_VALUES.get(target_symbol, (0, 0))[0]
                attacker_value = PIECE_VALUES.get(attacker_symbol, (0, 0))[0]
                score = target_value - attacker_value/10
                
                # King capture is the highest priority
                if target.piece_type == chess.KING:
                    score = 10000  # Huge score for king captures
        
        # Check for attacking moves - look deeper at these
        if not is_tactical:
            board_copy = board.copy()
            try:
                board_copy.push(move)
                # In Drawback Chess, we need to check for actual threats, not just checks
                # Look for moves that threaten the opponent's king
                king_in_danger = False
                for king_sq, piece in board_copy.piece_map().items():
                    if piece and piece.piece_type == chess.KING and piece.color != board.turn:
                        attackers = board_copy.attackers(board.turn, king_sq)
                        if attackers:
                            king_in_danger = True
                            is_tactical = True
                            score = 300  # High score for king threats
                            break
                            
                # Also consider moves that put our pieces in a position to attack the king
                if not king_in_danger and opponent_king_square:
                    # Find pieces that are getting into attack position
                    moved_piece = board.piece_at(move.from_square)
                    if moved_piece:
                        king_file, king_rank = chess.square_file(opponent_king_square), chess.square_rank(opponent_king_square)
                        to_file, to_rank = chess.square_file(move.to_square), chess.square_rank(move.to_square)
                        
                        # Pieces moving closer to enemy king
                        king_distance = abs(to_file - king_file) + abs(to_rank - king_rank)
                        if king_distance <= 2:  # Close to king
                            is_tactical = True
                            score = 50  # Lower priority but still worth checking
            except Exception:
                continue  # Skip problematic moves
        
        # Add tactical moves to our search list
        if is_tactical:
            tactical_moves.append((score, move))
    
    # Sort moves: captures by score, threats after
    tactical_moves.sort(key=lambda x: x[0], reverse=True)
    
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
                        if victim_value < aggressor_value * 0.9 and depth >= 1:
                            continue
                            
            board.push(move)
            score = -quiescence_search(bot, board, -beta, -alpha, depth + 1, max_depth)
            board.pop()
            
            if score >= beta:
                return beta
            if score > alpha:
                alpha = score
        except Exception:
            continue  # Skip problematic moves
    
    return alpha

def negamax(bot, board, depth, alpha, beta, allow_null=True, can_enter_quiescence=True):
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
        
    Returns:
        Position score
    """
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