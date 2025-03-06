"""
Chess search utilities for Drawback Chess AI.
Contains the core negamax and quiescence search algorithms extracted from DrawbackBot.
"""
import chess
import time
from collections import namedtuple
from AI.piece_square_table import PIECE_VALUES
from AI.ai_utils import MATE_LOWER, MATE_UPPER, MAX_DEPTH

# Define an entry for the transposition table
class Entry:
    """
    Entry in the transposition table
    
    Attributes:
        value: The score for this position
        depth: The depth of the search that produced this score
        flag: The type of node ('exact', 'lower', 'upper')
        move: The best move found for this position
    """
    def __init__(self, value, depth, flag, move=None):
        self.value = value
        self.depth = depth
        self.flag = flag  # 'exact', 'lower', or 'upper'
        self.move = move

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
    Negamax search with alpha-beta pruning. 
    Optimized for Drawback Chess which has some unique rules.
    
    Parameters:
        bot: The DrawbackBot instance
        board: The current board position
        depth: Remaining search depth
        alpha: Alpha bound
        beta: Beta bound
        allow_null: Whether to allow null-move pruning
        can_enter_quiescence: Whether to use quiescence search at depth 0
        start_time: Starting time of the search
        time_limit: Time limit in seconds
        
    Returns:
        The evaluated score for the position
    """
    # Store original alpha value for transposition table flag
    alpha_orig = alpha
    
    # Check time limit if provided
    if start_time and time_limit and time.time() - start_time > time_limit:
        raise TimeoutError("Search time limit reached")
        
    # Get position key for transposition table lookup
    key = board.zobrist_hash() if hasattr(board, 'zobrist_hash') else str(board.fen())
    
    # Lookup position in transposition table
    if key in bot.tt:
        tt_entry = bot.tt[key]
        if tt_entry.depth >= depth:
            if tt_entry.flag == 'exact':
                return tt_entry.value
            elif tt_entry.flag == 'lower' and tt_entry.value > alpha:
                alpha = tt_entry.value
            elif tt_entry.flag == 'upper' and tt_entry.value < beta:
                beta = tt_entry.value
                
            if alpha >= beta:
                return tt_entry.value
    
    # Increment node counter
    bot.nodes += 1
    
    # Base case: reached leaf node
    if depth <= 0:
        if can_enter_quiescence:
            return quiescence_search(bot, board, alpha, beta)
        else:
            return bot.evaluate_position(board)

    # Check for terminal conditions
    if not any(True for _ in board.legal_moves):
        # This is a draw in standard chess, but in Drawback Chess could be a win or loss
        if board.is_variant_loss():
            return -MATE_UPPER + bot.nodes
        return 0  # Draw
    
    # Generate and score moves
    moves = list(board.legal_moves)
    
    # No legal moves - it's a draw/stalemate
    if not moves:
        return 0  # Draw score
    
    # Score and sort moves for better pruning
    scored_moves = []
    for move in moves:
        score = move_value(bot, board, move, key)
        scored_moves.append((score, move))
    
    # Sort by score (highest first)
    scored_moves.sort(reverse=True)
    
    # Initialize variables for storing the best move
    best_value = -MATE_UPPER
    best_move = None
    
    # Search through moves
    for i, (score, move) in enumerate(scored_moves):
        # Try the move
        board.push(move)
        
        # Recursive search
        try:
            # Full-depth search for first move, reduced depth for others
            if i == 0:
                value = -negamax(bot, board, depth - 1, -beta, -alpha, allow_null, can_enter_quiescence, start_time, time_limit)
            else:
                # Late move reduction - search with reduced depth first
                if depth >= 3 and i >= 3 and not board.is_capture(move) and not move.promotion:
                    # Reduced depth search
                    value = -negamax(bot, board, depth - 2, -alpha - 1, -alpha, False, can_enter_quiescence, start_time, time_limit)
                    # Re-search if promising
                    if value > alpha:
                        value = -negamax(bot, board, depth - 1, -beta, -alpha, allow_null, can_enter_quiescence, start_time, time_limit)
                else:
                    value = -negamax(bot, board, depth - 1, -beta, -alpha, allow_null, can_enter_quiescence, start_time, time_limit)
                    
            board.pop()
            
            # Update best value
            if value > best_value:
                best_value = value
                best_move = move
                
                # Update alpha
                if value > alpha:
                    alpha = value
                    
                    # Store move in transposition table
                    bot.tt[key] = Entry(value, depth, 'exact', move)
                    
                    # Beta cutoff
                    if alpha >= beta:
                        # Store killer move
                        if not board.is_capture(move):
                            bot.killers[depth][1] = bot.killers[depth][0]
                            bot.killers[depth][0] = move
                            
                        # Store move ordering info
                        if not board.is_capture(move):
                            bot.history[(move.from_square, move.to_square)] = depth * depth
                            
                        # Store in transposition table
                        bot.tt[key] = Entry(value, depth, 'lower', move)
                        return value
        except TimeoutError:
            board.pop()
            # Return best move found so far
            if best_move:
                bot.tt[key] = Entry(best_value, depth, 'exact', best_move)
            raise
        except Exception as e:
            board.pop()
            # Just continue with next move
            continue
            
    # If no move improved alpha, store the position as an upper bound
    if best_move is None and len(scored_moves) > 0:
        best_move = scored_moves[0][1]  # Use the highest scored move as fallback
        
    # Store best move in transposition table with appropriate flag
    if best_value <= alpha_orig:
        bot.tt[key] = Entry(best_value, depth, 'upper', best_move)
    else:
        bot.tt[key] = Entry(best_value, depth, 'exact', best_move)
    
    return best_value 

def move_value(bot, board, move, key):
    """
    Score a move for move ordering in negamax search
    
    Parameters:
        bot: The bot instance containing history and killer move tables
        board: The current chess board
        move: The move to score
        key: The position hash key
        
    Returns:
        A numeric score for the move (higher is better)
    """
    # Check if this is a TT move (highest priority)
    if key in bot.tt and bot.tt[key].move == move:
        return 10000000
    
    # Killer moves (good non-captures found during search)
    if move in bot.killers[bot.depth]:
        return 9000000
    
    # Captures are sorted by MVV-LVA (Most Valuable Victim - Least Valuable Attacker)
    if board.is_capture(move):
        victim = board.piece_at(move.to_square)
        aggressor = board.piece_at(move.from_square)
        
        if victim and aggressor:
            victim_symbol = victim.symbol().upper()
            aggressor_symbol = aggressor.symbol().upper()
            
            # Get piece values
            victim_value = PIECE_VALUES.get(victim_symbol, (100, 0))[0]
            aggressor_value = PIECE_VALUES.get(aggressor_symbol, (100, 0))[0]
            
            # King captures are highest priority
            if victim.piece_type == chess.KING:
                return 9500000
                
            # MVV-LVA formula: victim value - attacker value / 10
            # This prioritizes capturing valuable pieces with less valuable attackers
            return 8000000 + (victim_value * 100 - aggressor_value)
    
    # Promotions are high priority
    if move.promotion:
        promotion_value = {
            chess.QUEEN: 800,
            chess.ROOK: 500,
            chess.BISHOP: 320,
            chess.KNIGHT: 300
        }
        return 7000000 + promotion_value.get(move.promotion, 0)
    
    # History heuristic for quiet moves
    history_score = bot.history.get((move.from_square, move.to_square), 0)
    
    # Book moves
    book_bonus = 0
    if hasattr(bot, 'book_move_bonuses') and bot.book_move_bonuses and move in bot.book_move_bonuses:
        book_bonus = bot.book_move_bonuses[move] * 10000  # Scale up book bonus
    
    # Center control for pawns
    center_bonus = 0
    if board.piece_at(move.from_square) and board.piece_at(move.from_square).piece_type == chess.PAWN:
        to_file, to_rank = chess.square_file(move.to_square), chess.square_rank(move.to_square)
        # Center files (c, d, e, f)
        if 2 <= to_file <= 5:
            # Center ranks (3, 4, 5, 6) - higher for advanced ranks
            center_bonus = (to_rank - 1) * 10 if board.turn == chess.WHITE else (8 - to_rank) * 10
    
    return history_score + book_bonus + center_bonus 