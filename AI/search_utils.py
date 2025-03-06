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
        move: The best move found for this position (stored as UCI string)
    """
    def __init__(self, value, depth, flag, move=None):
        self.value = value
        self.depth = depth
        self.flag = flag  # 'exact', 'lower', or 'upper'
        # Store move as UCI string if it's a Move object
        if move is not None and hasattr(move, 'uci'):
            self.move = move.uci()
        else:
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
    
    # Sort moves by score in descending order - avoid comparing Move objects directly
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
        except Exception as e:
            # If move causes an error, pop it and continue
            if board.move_stack and board.move_stack[-1] == move:
                board.pop()
            print(f"Error in quiescence search: {str(e)}")
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
    # Only check time limit at the beginning of a search path
    # This avoids excessive checking that slows down the search
    if start_time is not None and time_limit is not None:
        # At root node (depth >= 5), check time every node
        # At deeper nodes, check less frequently to improve performance
        if depth >= 5 or bot.nodes % (1000 * (1 + max(0, 5 - depth))) == 0:
            elapsed = time.time() - start_time
            if elapsed >= time_limit * 0.95:  # Allow using 95% of time limit
                raise TimeoutError("Search time limit reached")
        
    # Store original alpha value for transposition table flag
    alpha_orig = alpha
    
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
            # When losing, return a score that's worse the closer we are to the root
            # This incentivizes the engine to find variations that delay mate
            return -MATE_UPPER + bot.nodes + depth
        return 0  # Draw

    # Define a helper function to detect atomic bomb loss for consistent evaluation
    def is_atomic_bomb_loss(board, color):
        if not hasattr(board, 'get_active_drawback') or not hasattr(board, '_last_capture_square'):
            return False
        
        # Only check if atomic bomb is active
        active_drawback = board.get_active_drawback(color)
        if active_drawback != "atomic_bomb":
            return False
            
        # Only check if a capture happened
        if not board._last_capture_square:
            return False
            
        # Find the king
        king_square = None
        for square, piece in board.piece_map().items():
            if piece and piece.piece_type == chess.KING and piece.color == color:
                king_square = square
                break
                
        if not king_square:
            return False
            
        # Check if the capture is adjacent to the king
        capture_square = board._last_capture_square
        king_file, king_rank = chess.square_file(king_square), chess.square_rank(king_square)
        capture_file = chess.square_file(capture_square)
        capture_rank = chess.square_rank(capture_square)
        
        # If they're adjacent (within 1 square in any direction)
        if abs(king_file - capture_file) <= 1 and abs(king_rank - capture_rank) <= 1:
            if king_square != capture_square:  # Not the king itself
                return True
                
        return False

    # Check for immediate loss by drawback win conditions
    if hasattr(board, 'check_drawback_win'):
        active_drawback = board.get_active_drawback(board.turn) if hasattr(board, 'get_active_drawback') else None
        
        if active_drawback:
            # Check if current position is already a loss due to drawback
            is_loss = False
            
            # Check specifically for atomic bomb loss
            if active_drawback == "atomic_bomb":
                is_loss = is_atomic_bomb_loss(board, board.turn)
            
            # If not an atomic bomb loss, try other drawback loss functions
            if not is_loss:
                try:
                    from GameState.drawback_manager import get_drawback_loss_function
                    loss_function = get_drawback_loss_function(active_drawback)
                    if loss_function and loss_function(board, board.turn):
                        is_loss = True
                except Exception:
                    pass
                
            # If it's a loss, return a very negative score
            # Add depth to prefer longer paths to inevitable loss
            if is_loss:
                return -MATE_UPPER + bot.nodes + depth
    
    # Generate legal moves
    legal_moves = list(board.legal_moves)
    
    # No legal moves - it's a draw/stalemate
    if not legal_moves:
        return 0  # Draw score
    
    # Get the current killer moves for this depth (as UCI strings)
    killer_move_ucis = []
    if hasattr(bot, 'killers') and hasattr(bot, 'depth') and bot.depth < len(bot.killers):
        for killer in bot.killers[bot.depth]:
            if killer is not None:
                if isinstance(killer, chess.Move):
                    killer_move_ucis.append(killer.uci())
                else:
                    killer_move_ucis.append(killer)
    
    # Get transposition table move if available (as UCI)
    tt_move_uci = None
    if key in bot.tt and bot.tt[key].move:
        tt_move_uci = bot.tt[key].move  # Already stored as UCI
    
    # Get principal variation move if available
    pv_move_uci = None
    if hasattr(bot, 'principal_variation') and bot.principal_variation:
        # The current position is fen, but PV move is from the original position
        # Need to get the first move of the PV that matches this position
        for move in legal_moves:
            if move.uci() in bot.principal_variation:
                pv_move_uci = move.uci()
                break
    
    # Score moves without any direct comparisons of Move objects
    scored_moves = []
    
    for move in legal_moves:
        # Calculate a score for move ordering
        score = 0
        move_uci = move.uci()
        
        # Absolute highest priority for principal variation moves
        if pv_move_uci and move_uci == pv_move_uci:
            score = 50000000
            
        # Check for immediate variant win moves (highest priority)
        board.push(move)
        is_variant_win = board.is_variant_win() if hasattr(board, 'is_variant_win') else False
        
        # Check for drawback-specific winning moves
        is_drawback_win = False
        is_no_legal_moves = False
        
        if hasattr(board, 'get_active_drawback') and hasattr(board, 'check_drawback_win'):
            active_drawback = board.get_active_drawback(not board.turn)  # Check opponent's drawback
            if active_drawback:
                # For move ordering, use the board's drawback win check
                is_drawback_win = board.check_drawback_win(not board.turn, active_drawback)
                
                # Check if opponent has any legal moves with their drawback
                if not is_drawback_win:
                    has_moves = any(True for _ in board.legal_moves)
                    if not has_moves:
                        is_no_legal_moves = True
                        
                # For atomic bomb, check specifically if this capture is adjacent to opponent's king
                if active_drawback == "atomic_bomb" and board.is_capture(move):
                    # Set the last capture square for atomic bomb check
                    old_capture_square = board._last_capture_square if hasattr(board, '_last_capture_square') else None
                    if hasattr(board, '_last_capture_square'):
                        board._last_capture_square = move.to_square
                    
                    # Use the same function for consistency
                    if is_atomic_bomb_loss(board, not board.turn):
                        is_drawback_win = True
                        score = 30000000  # Even higher priority than other wins
                    
                    # Restore the last capture square
                    if hasattr(board, '_last_capture_square'):
                        board._last_capture_square = old_capture_square
        
        board.pop()
        
        if is_variant_win or is_drawback_win:
            # Absolute highest priority: variant win
            score = 30000000
        elif is_no_legal_moves:
            # High priority: opponent has no legal moves
            score = 20000000
        # Very high priority for transposition table moves
        elif tt_move_uci and move_uci == tt_move_uci:
            score = 10000000
        # High priority for killer moves (good quiet moves found during search)
        elif move_uci in killer_move_ucis:
            score = 9000000 - killer_move_ucis.index(move_uci) * 100000
        # Captures are sorted by MVV-LVA
        elif board.is_capture(move):
            victim = board.piece_at(move.to_square)
            aggressor = board.piece_at(move.from_square)
            
            if victim and aggressor:
                victim_symbol = victim.symbol().upper()
                aggressor_symbol = aggressor.symbol().upper()
                
                # Get piece values
                victim_value = PIECE_VALUES.get(victim_symbol, (100, 0))[0]
                aggressor_value = PIECE_VALUES.get(aggressor_symbol, (100, 0))[0]
                
                # King captures are highest priority after variant wins
                if victim.piece_type == chess.KING:
                    score = 15000000
                else:
                    # MVV-LVA formula: victim value - attacker value / 10
                    score = 8000000 + (victim_value * 100 - aggressor_value)
        # Promotions are high priority
        elif move.promotion:
            promotion_value = {
                chess.QUEEN: 800,
                chess.ROOK: 500,
                chess.BISHOP: 320,
                chess.KNIGHT: 300
            }
            score = 7000000 + promotion_value.get(move.promotion, 0)
        # Check-giving moves have medium-high priority
        elif board.gives_check(move):
            score = 6500000
        # History heuristic for quiet moves
        else:
            history_score = bot.history.get((move.from_square, move.to_square), 0)
            score = history_score
            
        # Book moves - small bonus to guide search, not enough to dominate
        if hasattr(bot, 'book_move_bonuses') and bot.book_move_bonuses:
            if move_uci in bot.book_move_bonuses:
                # Apply the bonus directly
                score += bot.book_move_bonuses[move_uci] * 50
        
        # Add the scored move to our list
        scored_moves.append((score, move))
    
    # Sort by score (highest first) using key function to avoid direct Move comparisons
    scored_moves.sort(key=lambda x: x[0], reverse=True)
    
    # Initialize variables for storing the best move
    best_value = -MATE_UPPER
    best_move = None
    
    # Search through moves
    for i, (score, move) in enumerate(scored_moves):
        # At regular intervals, check if we're out of time
        if start_time and time_limit and i > 0 and i % 5 == 0:
            elapsed = time.time() - start_time
            if elapsed >= time_limit * 0.95:
                if best_move:
                    bot.tt[key] = Entry(best_value, depth, 'exact', best_move)
                raise TimeoutError("Search time limit exceeded")
                
        # Try the move
        board.push(move)
        
        # Set the search flag to true if the board supports it
        # This helps optimize drawback checks during search
        if hasattr(board, '_in_search'):
            old_search_flag = board._in_search
            board._in_search = False  # Set to FALSE to force drawback checks during search for accurate evaluation
        else:
            old_search_flag = None
        
        # Simulate the _last_capture_square tracking that the real board has
        if hasattr(board, '_last_capture_square') and board.is_capture(move):
            old_capture_square = board._last_capture_square
            board._last_capture_square = move.to_square
        else:
            old_capture_square = None
        
        # Check for immediate win due to drawback
        win_by_drawback = False
        if hasattr(board, 'get_active_drawback'):
            opponent_color = not board.turn
            active_drawback = board.get_active_drawback(opponent_color)
            
            # For atomic bomb, use our consistent check function
            if active_drawback == "atomic_bomb":
                win_by_drawback = is_atomic_bomb_loss(board, opponent_color)
            # For other drawbacks, use the loss function
            elif active_drawback and hasattr(board, 'check_drawback_win'):
                try:
                    from GameState.drawback_manager import get_drawback_loss_function
                    loss_function = get_drawback_loss_function(active_drawback)
                    if loss_function and loss_function(board, opponent_color):
                        win_by_drawback = True
                except Exception:
                    pass
            
        # If this move leads to a win by drawback, return a winning score
        # Subtract depth to prefer shorter paths to checkmate
        if win_by_drawback:
            if old_search_flag is not None:
                board._in_search = old_search_flag
            if old_capture_square is not None and hasattr(board, '_last_capture_square'):
                board._last_capture_square = old_capture_square
            board.pop()
            return MATE_UPPER - bot.nodes - depth
        
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
            
            # Restore search flag
            if old_search_flag is not None:
                board._in_search = old_search_flag
                
            # Restore capture square tracking
            if old_capture_square is not None and hasattr(board, '_last_capture_square'):
                board._last_capture_square = old_capture_square
                
            board.pop()
            
            # Update best value
            if value > best_value:
                best_value = value
                best_move = move
                
                # Update alpha
                if value > alpha:
                    alpha = value
                    
                    # Store move in transposition table (Entry class will convert to UCI)
                    bot.tt[key] = Entry(value, depth, 'exact', move)
                    
                    # Beta cutoff
                    if alpha >= beta:
                        # Store killer move as UCI string, not Move object
                        if not board.is_capture(move):
                            if hasattr(bot, 'killers') and hasattr(bot, 'depth') and bot.depth < len(bot.killers):
                                # Make sure we're using proper array indices
                                if len(bot.killers[bot.depth]) > 1:
                                    # Store the UCI string, not the move object
                                    move_uci = move.uci()
                                    bot.killers[bot.depth][1] = bot.killers[bot.depth][0]
                                    bot.killers[bot.depth][0] = move_uci
                            
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
            print(f"Error in search: {str(e)}")
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