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

def quiescence_search(bot, board, alpha, beta, maximizing_player, start_time=None, time_limit=None, depth=0):
    """
    Quiescence search to avoid horizon effect.
    Only searches captures and checks to reach a quiet position.
    
    Args:
        bot: The DrawbackBot instance
        board: Current board position
        alpha: Alpha value for pruning
        beta: Beta value for pruning
        maximizing_player: Whether current player is maximizing
        start_time: Start time of search for time management
        time_limit: Time limit in seconds
        depth: Current depth within quiescence search
        
    Returns:
        Best score for the position
    """
    # Check for timeout if time management is enabled
    if start_time and time_limit and time.time() - start_time > time_limit:
        raise TimeoutError("Search timed out")
    
    # Increment node count
    bot.nodes += 1
    
    # Base case - evaluate current position
    stand_pat = bot.evaluate_position(board)
    
    # Immediate return if we're at a good position
    if maximizing_player:
        if stand_pat >= beta:
            return stand_pat
        if stand_pat > alpha:
            alpha = stand_pat
    else:
        if stand_pat <= alpha:
            return stand_pat
        if stand_pat < beta:
            beta = stand_pat
    
    # Maximum quiescence depth to avoid excessive searching
    if depth >= 4:
        return stand_pat
    
    # Check for immediate terminal state - the check is lightweight here
    if board.is_check():
        # Only generate legal moves to handle check
        moves = list(board.legal_moves)
        if not moves:  # Checkmate
            return -MATE_UPPER if maximizing_player else MATE_UPPER
    else:
        # Only consider captures and promotions for quiescence
        moves = [move for move in board.legal_moves if board.is_capture(move) or move.promotion]
        
        # If no captures, just return the stand_pat evaluation
        if not moves:
            return stand_pat
    
    # Score moves for better ordering
    scored_moves = []
    for move in moves:
        score = 0
        
        # Score captures by MVV-LVA
        if board.is_capture(move):
            victim = board.piece_at(move.to_square)
            aggressor = board.piece_at(move.from_square)
            
            if victim and aggressor:
                victim_value = get_piece_value(victim)
                aggressor_value = get_piece_value(aggressor)
                
                # MVV-LVA scoring: victim value - attacker value / 10
                score = victim_value * 10 - aggressor_value
                
                # Bonus for capturing with less valuable piece
                if victim_value > aggressor_value:
                    score += 100
        
        # Score promotions
        if move.promotion:
            promotion_values = {
                chess.QUEEN: 900,
                chess.ROOK: 500,
                chess.BISHOP: 330,
                chess.KNIGHT: 320
            }
            score += promotion_values.get(move.promotion, 0)
            
        scored_moves.append((score, move))
        
    # Sort moves by score (highest first)
    scored_moves.sort(key=lambda x: x[0], reverse=True)
    
    # Search through moves
    for _, move in scored_moves:
        board.push(move)
        
        # Recursively search with negated parameters
        value = -quiescence_search(bot, board, -beta, -alpha, not maximizing_player, start_time, time_limit, depth + 1)
        
        board.pop()
        
        # Update alpha/beta
        if maximizing_player:
            if value >= beta:
                return beta
            if value > alpha:
                alpha = value
        else:
            if value <= alpha:
                return alpha
            if value < beta:
                beta = value
    
    # Return best score
    return alpha if maximizing_player else beta

def negamax(bot, board, depth, alpha, beta, maximizing_player, is_root=False, start_time=None, time_limit=None):
    """
    Negamax search with alpha-beta pruning.
    
    Args:
        bot: The DrawbackBot instance
        board: Current board position
        depth: Remaining search depth
        alpha: Alpha value for pruning
        beta: Beta value for pruning
        maximizing_player: Whether current player is maximizing
        is_root: Whether this is the root node of the search
        start_time: Start time of search for time management
        time_limit: Time limit in seconds
        
    Returns:
        Best score for the position
    """
    # Check for timeout if time management is enabled
    if start_time and time_limit and time.time() - start_time > time_limit:
        raise TimeoutError("Search timed out")
    
    # Generate a key for the current position
    key = bot.get_position_key(board)
    original_alpha = alpha
    tt_move = None
    
    # Check transposition table
    if key in bot.tt and bot.tt[key].depth >= depth:
        entry = bot.tt[key]
        tt_move = entry.move  # Save TT move regardless of cutoff
        
        # Use TT entry based on node type
        if entry.flag == 'EXACT':
            return entry.value
        elif entry.flag == 'LOWER' and entry.value > alpha:
            alpha = entry.value
        elif entry.flag == 'UPPER' and entry.value < beta:
            beta = entry.value
            
        if alpha >= beta:
            return entry.value
    
    # Check for immediate terminal states - avoid expensive checks at deeper nodes
    if depth == 0 or bot.check_terminal_state(board):
        # Use quiescence search to avoid horizon effect
        return quiescence_search(bot, board, alpha, beta, maximizing_player, start_time, time_limit)
    
    # Increment node count
    bot.nodes += 1
    
    # Generate and order legal moves
    legal_moves = list(board.legal_moves)
    
    # If there are no legal moves, evaluate the position
    if not legal_moves:
        # Special case for atomic bomb drawback (or similar variant)
        # Don't assume stalemate/checkmate applies, just evaluate the current position
        if hasattr(board, 'get_active_drawback') and board.get_active_drawback(board.turn):
            eval_score = bot.evaluate_position(board)
            # Negate for negamax perspective
            return -eval_score if not maximizing_player else eval_score
        # Normal rules - no legal moves means stalemate or checkmate
        elif board.is_check():
            # Checkmate - return a score based on depth to prefer quicker mates
            return -(MATE_UPPER - depth) if maximizing_player else (MATE_UPPER - depth)
        else:
            # Stalemate - return draw score
            return 0
    
    # Score and order moves for better pruning
    scored_moves = score_moves(bot, board, legal_moves, depth, maximizing_player)
    
    # Keep track of best move for this position
    best_move = None
    best_score = float('-inf')
    
    # Flag for PV node (true if at least one move raises alpha)
    is_pv_node = False
    
    # Search through all legal moves
    for score, move in scored_moves:
        # Make the move
        board.push(move)
        
        # Recursively search with negated parameters
        if is_pv_node:
            # Try PVS (Principal Variation Search) for non-first moves
            # First do a null window search to see if this move is better than our best so far
            value = -negamax(bot, board, depth - 1, -alpha - 1, -alpha, not maximizing_player, False, start_time, time_limit)
            # If the move looks promising, do a full window search
            if alpha < value < beta:
                value = -negamax(bot, board, depth - 1, -beta, -alpha, not maximizing_player, False, start_time, time_limit)
        else:
            # Do a full window search for the first move
            value = -negamax(bot, board, depth - 1, -beta, -alpha, not maximizing_player, False, start_time, time_limit)
            
        # Unmake the move
        board.pop()
        
        # Check if this move is better than our best so far
        if value > best_score:
            best_score = value
            best_move = move
            
            # Update alpha if this move is better
            if value > alpha:
                alpha = value
                is_pv_node = True
            
            # Prune if alpha >= beta
            if alpha >= beta:
                # Store killer moves (good quiet moves that caused cutoffs)
                if not board.is_capture(move):
                    # Store UCI string to avoid move object issues
                    if depth < len(bot.killers):
                        if isinstance(move, chess.Move):
                            move_uci = move.uci()
                        else:
                            move_uci = str(move)
                            
                        if move_uci != bot.killers[depth][0]:
                            bot.killers[depth][1] = bot.killers[depth][0]
                            bot.killers[depth][0] = move_uci
                
                # Update history heuristic for quiet moves
                if not board.is_capture(move):
                    bot.history[(move.from_square, move.to_square)] = bot.history.get((move.from_square, move.to_square), 0) + depth * depth
                
                break
    
    # If search was exhaustive or this is the root node, store best move in TT
    if best_move is not None:
        # Determine TT entry flag
        if best_score <= original_alpha:
            flag = 'UPPER'
        elif best_score >= beta:
            flag = 'LOWER'
        else:
            flag = 'EXACT'
        
        # Convert best_move to string to avoid reference issues
        best_move_uci = best_move.uci() if isinstance(best_move, chess.Move) else str(best_move)
        
        # Update transposition table with best move
        bot.tt[key] = Entry(
            value=best_score,
            depth=depth,
            flag=flag,
            move=best_move_uci
        )
        
        # For root node, update bot.current_best_move
        if is_root:
            if hasattr(bot, 'principal_variation'):
                # Extract PV for this move
                pv = []
                board.push(best_move)
                pv_key = bot.get_position_key(board)
                pv.append(best_move_uci)
                
                # Try to extract principal variation from TT
                current_depth = depth - 1
                while current_depth > 0 and pv_key in bot.tt and bot.tt[pv_key].move:
                    next_move_uci = bot.tt[pv_key].move
                    # Convert UCI string to Move object
                    next_move = None
                    for legal in board.legal_moves:
                        if legal.uci() == next_move_uci:
                            next_move = legal
                            break
                            
                    if next_move:
                        board.push(next_move)
                        pv.append(next_move_uci)
                        pv_key = bot.get_position_key(board)
                        current_depth -= 1
                    else:
                        break
                
                # Restore board position
                for _ in range(len(pv)):
                    board.pop()
                    
                # Store PV
                bot.principal_variation = pv
    
    # If no moves were searched (e.g., due to timeout), return a default evaluation
    if best_move is None:
        return bot.evaluate_position(board) * (1 if maximizing_player else -1)
    
    # Handle specially the case where a player has no legal moves
    if best_score == float('-inf'):
        # This means all moves led to a worse position
        # We should still return the least bad option
        return -MATE_UPPER + 100  # Return a very bad but not terminal score
    
    return best_score

def minimax(bot, board, depth, alpha, beta, maximizing_player, can_enter_quiescence=True, start_time=None, time_limit=None):
    """
    Minimax search with alpha-beta pruning optimized for proper move evaluation.
    
    Parameters:
        bot: The DrawbackBot instance
        board: The current board position
        depth: Remaining search depth
        alpha: Alpha bound
        beta: Beta bound
        maximizing_player: True if current player is maximizing (White), False if minimizing (Black)
        can_enter_quiescence: Whether to allow quiescence search
        start_time: Start time of the search
        time_limit: Time limit for the search
        
    Returns:
        Position score from current player's perspective
    """
    bot.nodes += 1
    
    # Check for timeout
    if start_time and time_limit and time.time() - start_time >= time_limit * 0.95:
        raise TimeoutError("Search time limit exceeded")
    
    # Win/loss condition checks
    if hasattr(board, 'is_variant_win') and board.is_variant_win():
        return MATE_UPPER - bot.nodes - depth if maximizing_player else -MATE_UPPER + bot.nodes + depth
    
    if hasattr(board, 'is_variant_loss') and board.is_variant_loss():
        return -MATE_UPPER + bot.nodes + depth if maximizing_player else MATE_UPPER - bot.nodes - depth
    
    # Base case: reached leaf node
    if depth <= 0:
        if can_enter_quiescence:
            q_score = quiescence_search(bot, board, alpha, beta, maximizing_player, start_time, time_limit)
            return q_score
        else:
            eval_score = bot.evaluate_position(board)
            # For Black (minimizing player), we don't negate here as evaluation already considers perspective
            return eval_score
    
    # Generate position key for transposition table
    key = bot.get_position_key(board)
    
    # Check transposition table
    if key in bot.tt:
        tt_entry = bot.tt[key]
        
        if tt_entry.depth >= depth:
            if tt_entry.flag == 'exact':
                return tt_entry.value
            if tt_entry.flag == 'lower' and tt_entry.value > alpha:
                alpha = tt_entry.value
            if tt_entry.flag == 'upper' and tt_entry.value < beta:
                beta = tt_entry.value
            
            if alpha >= beta:
                return tt_entry.value
    
    # Get legal moves
    legal_moves = list(board.legal_moves)
    
    # No legal moves is a draw
    if not legal_moves:
        return 0  # Draw score
    
    # Score and order moves to improve alpha-beta pruning efficiency
    scored_moves = score_moves(bot, board, legal_moves, depth, maximizing_player)
    
    # Initialize variables to store best move
    best_score = -MATE_UPPER if maximizing_player else MATE_UPPER
    best_move = None
    
    # Search through moves
    for _, move in scored_moves:
        try:
            board.push(move)
            
            # Recursive minimax call with switched player perspective
            score = minimax(bot, board, depth - 1, alpha, beta, not maximizing_player, 
                           can_enter_quiescence, start_time, time_limit)
            
            board.pop()
            
            # Update best score and move
            if maximizing_player:
                if score > best_score:
                    best_score = score
                    best_move = move
                alpha = max(alpha, best_score)
            else:
                if score < best_score:
                    best_score = score
                    best_move = move
                beta = min(beta, best_score)
                
            # Alpha-beta pruning
            if beta <= alpha:
                break
                
        except Exception as e:
            if board.move_stack and board.move_stack[-1] == move:
                board.pop()
            # Skip problematic moves
            continue
    
    # Store result in transposition table
    if best_move:
        flag = 'exact'
        if maximizing_player:
            if best_score <= alpha:
                flag = 'upper'
            elif best_score >= beta:
                flag = 'lower'
        else:
            if best_score <= alpha:
                flag = 'lower'
            elif best_score >= beta:
                flag = 'upper'
                
        bot.tt[key] = Entry(best_score, depth, flag, best_move)
        
        # Update killer moves if it's a good quiet move
        if not board.is_capture(best_move) and best_score >= beta:
            bot.killers[depth][1] = bot.killers[depth][0]
            bot.killers[depth][0] = best_move.uci()
            
        # Update history heuristic
        if not board.is_capture(best_move):
            bot.history[(best_move.from_square, best_move.to_square)] = bot.history.get((best_move.from_square, best_move.to_square), 0) + depth * depth
    
    return best_score

def score_moves(bot, board, legal_moves, depth, maximizing_player):
    """
    Score and order moves to improve alpha-beta pruning efficiency.
    Prioritizes captures, especially high-value captures.
    
    Args:
        bot: The DrawbackBot instance
        board: Current board position
        legal_moves: List of legal moves
        depth: Current search depth
        maximizing_player: Whether current player is maximizing
        
    Returns:
        List of (score, move) tuples sorted by score (highest first)
    """
    scored_moves = []
    
    # Get transposition table move for this position
    tt_move_uci = None
    key = bot.get_position_key(board)
    if key in bot.tt and bot.tt[key].move:
        tt_move_uci = bot.tt[key].move
        
    # Get killer moves for current depth
    killer_move_ucis = []
    if hasattr(bot, 'killers') and depth < len(bot.killers):
        for killer in bot.killers[depth]:
            if killer is not None:
                if isinstance(killer, chess.Move):
                    killer_move_ucis.append(killer.uci())
                else:
                    killer_move_ucis.append(killer)

    # Get player's color and active drawback
    current_color = board.turn
    active_drawback = None
    if hasattr(board, 'get_active_drawback'):
        active_drawback = board.get_active_drawback(current_color)
        
    # Special handling for capturing opponent's king - always highest priority
    for move in legal_moves:
        target_piece = board.piece_at(move.to_square)
        if target_piece and target_piece.piece_type == chess.KING:
            # Immediate win - should be processed before all other moves
            return [(100000000, move)]  # Return immediately - no need to check other moves
    
    # SPECIAL HANDLING FOR ATOMIC BOMB: Find king and adjacent pieces
    king_square = None
    adjacent_squares = []
    
    # Check for atomic bomb drawback
    has_atomic_bomb = active_drawback == "atomic_bomb"
    
    # If we have atomic bomb drawback, find king and adjacent squares
    if has_atomic_bomb:
        # Find our king
        for square in chess.SQUARES:
            piece = board.piece_at(square)
            if piece and piece.piece_type == chess.KING and piece.color == current_color:
                king_square = square
                break
        
        # Get adjacent squares
        if king_square is not None:
            king_file, king_rank = chess.square_file(king_square), chess.square_rank(king_square)
            for file_offset in [-1, 0, 1]:
                for rank_offset in [-1, 0, 1]:
                    if file_offset == 0 and rank_offset == 0:
                        continue  # Skip the king's own square
                    
                    target_file = king_file + file_offset
                    target_rank = king_rank + rank_offset
                    
                    # Skip off-board squares
                    if not (0 <= target_file < 8 and 0 <= target_rank < 8):
                        continue
                    
                    adjacent_squares.append(chess.square(target_file, target_rank))
    
    # Also check if OPPONENT has atomic bomb, opening tactical opportunities
    opponent_has_atomic_bomb = False
    opponent_king_square = None
    opponent_adjacent_squares = []
    
    if hasattr(board, 'get_active_drawback'):
        opponent_color = not current_color
        opponent_drawback = board.get_active_drawback(opponent_color)
        opponent_has_atomic_bomb = opponent_drawback == "atomic_bomb"
        
        if opponent_has_atomic_bomb:
            # Find opponent's king
            for square in chess.SQUARES:
                piece = board.piece_at(square)
                if piece and piece.piece_type == chess.KING and piece.color == opponent_color:
                    opponent_king_square = square
                    break
                    
            # Get adjacent squares to opponent's king
            if opponent_king_square is not None:
                king_file, king_rank = chess.square_file(opponent_king_square), chess.square_rank(opponent_king_square)
                for file_offset in [-1, 0, 1]:
                    for rank_offset in [-1, 0, 1]:
                        if file_offset == 0 and rank_offset == 0:
                            continue  # Skip the king itself
                        
                        target_file = king_file + file_offset
                        target_rank = king_rank + rank_offset
                        
                        # Skip off-board squares
                        if not (0 <= target_file < 8 and 0 <= target_rank < 8):
                            continue
                        
                        opponent_adjacent_squares.append(chess.square(target_file, target_rank))
    
    # Score each move
    for move in legal_moves:
        move_uci = move.uci()
        score = 0
        
        # HIGHEST PRIORITY: King safety
        # Check if the current move prevents a direct king capture on the next move
        king_square = None
        for square in chess.SQUARES:
            piece = board.piece_at(square)
            if piece and piece.piece_type == chess.KING and piece.color == current_color:
                king_square = square
                break
                
        if king_square:
            # See if our king is currently under attack
            attackers = list(board.attackers(not current_color, king_square))
            if attackers:
                # King is under attack - any move that gets it out of danger is highest priority
                board.push(move)
                # After our move, is king still under attack?
                king_still_attacked = False
                for square in chess.SQUARES:
                    piece = board.piece_at(square)
                    if piece and piece.piece_type == chess.KING and piece.color == current_color:
                        king_attackers = list(board.attackers(not current_color, square))
                        if king_attackers:
                            king_still_attacked = True
                        break
                board.pop()
                
                if not king_still_attacked:
                    # This move saves our king from capture!
                    score = 500000000  # Absolute highest priority
        
        # 1. Transposition table moves (high priority)
        if tt_move_uci and move_uci == tt_move_uci:
            score = max(score, 10000000)
            
        # 2. Captures by MVV-LVA (Most Valuable Victim - Least Valuable Attacker)
        if board.is_capture(move):
            victim = board.piece_at(move.to_square)
            aggressor = board.piece_at(move.from_square)
            
            if victim and aggressor:
                victim_value = get_piece_value(victim)
                aggressor_value = get_piece_value(aggressor)
                
                # MVV-LVA scoring formula: 1000000 + 10 * victim - attacker
                # This ensures all captures are ranked higher than non-captures
                capture_score = 1000000 + victim_value * 10 - aggressor_value
                
                # Extra bonus for capturing with less valuable piece
                if victim_value > aggressor_value:
                    capture_score += 100000
                    
                # Extra bonus for promotion captures
                if move.promotion:
                    capture_score += 200000
                    
                # SPECIAL CASE - Attacking piece next to king with atomic bomb
                if opponent_has_atomic_bomb and move.to_square in opponent_adjacent_squares:
                    capture_score = 90000000  # Tactical opportunity - instant win if opponent has atomic bomb
                
                score = max(score, capture_score)
                    
        # 3. Killer moves (good quiet moves that caused cutoffs)
        elif move_uci in killer_move_ucis:
            killer_score = 900000 - 100000 * killer_move_ucis.index(move_uci)
            score = max(score, killer_score)
        
        # 4. History heuristic (learning from past quiet moves)
        else:
            history_score = bot.history.get((move.from_square, move.to_square), 0)
            
            # Check for promoting moves
            if move.promotion:
                promotion_values = {
                    chess.QUEEN: 500000,
                    chess.ROOK: 400000,
                    chess.BISHOP: 350000, 
                    chess.KNIGHT: 300000
                }
                history_score += promotion_values.get(move.promotion, 0)
                
            score = max(score, history_score)

        # ATOMIC BOMB SPECIAL HANDLING
        if has_atomic_bomb:
            atomic_score = 0
            
            # Avoiding danger in atomic bomb - our pieces shouldn't be next to our king
            if move.from_square in adjacent_squares:
                # Moving a piece away from king is good in atomic bomb
                atomic_score += 800000
                
            # Test if this move defends a piece adjacent to our king
            if move.from_square in adjacent_squares or move.to_square in adjacent_squares:
                # Test if this move makes adjacent pieces safe
                board.push(move)
                all_safe = True
                
                # Check if any adjacent pieces can be captured after our move
                for adj_square in adjacent_squares:
                    piece = board.piece_at(adj_square)
                    if piece and piece.color == current_color:
                        attackers = board.attackers(not current_color, adj_square)
                        if attackers:
                            all_safe = False
                            break
                
                board.pop()
                
                # Big bonus if this move makes all adjacent pieces safe
                if all_safe:
                    atomic_score += 5000000
                    
            score = max(score, atomic_score)
        
        scored_moves.append((score, move))
    
    # Sort by score (highest first)
    scored_moves.sort(key=lambda x: x[0], reverse=True)
    return scored_moves

def get_piece_value(piece):
    """
    Get the value of a chess piece.
    
    Args:
        piece: A chess.Piece object
        
    Returns:
        The value of the piece in centipawns
    """
    # Set standard piece values
    values = {
        chess.PAWN: 100,
        chess.KNIGHT: 320,
        chess.BISHOP: 330,
        chess.ROOK: 500,
        chess.QUEEN: 900,
        chess.KING: 20000  # King is most valuable
    }
    
    return values.get(piece.piece_type, 0) 