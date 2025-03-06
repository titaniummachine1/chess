"""
Drawback Sunfish - A chess engine inspired by Sunfish but adapted for Drawback Chess.
Uses the DrawbackBoard move generation and existing piece square tables.
Core engine logic with minimal dependencies.
"""
import chess
import time
import random
from collections import namedtuple
from GameState.movegen import DrawbackBoard
from AI.evaluation import evaluate_position as eval_position
from AI.piece_square_table import PIECE_VALUES
# Safe imports to avoid circular references
try:
    from AI.book_parser import is_book_position
except ImportError:
    # Define a fallback function if module not available
    def is_book_position(board):
        return False

from AI.ai_utils import MATE_LOWER, MATE_UPPER, MAX_DEPTH, BOOK_MOVE_BONUS, BOOK_MOVE_BONUS_REGULAR

# Transposition table entry
Entry = namedtuple('Entry', 'lower upper move')

class DrawbackSunfish:
    """Chess engine inspired by Sunfish but using DrawbackBoard for move generation"""
    
    def __init__(self):
        self.nodes = 0
        self.tt = {}  # Transposition table
        self.history = {}  # Move history heuristic
        self.killers = [[None, None] for _ in range(MAX_DEPTH + 1)]  # Killer moves
        self.eval_cache = {}  # Cache for position evaluations
        
    def evaluate_position(self, board, drawbacks=None):
        """Enhanced evaluation function that considers drawbacks"""
        # Check if the position is a variant loss due to drawbacks
        if board.is_variant_loss():
            return -MATE_UPPER  # Return worst possible score
            
        # Get active drawback for current side
        active_drawback = board.get_active_drawback(board.turn)
        if active_drawback:
            # Count legal moves - heavily penalize positions with few moves
            legal_count = len(list(board.legal_moves))
            if legal_count == 0:
                return -MATE_UPPER  # No legal moves is a loss
            mobility_bonus = min(100, legal_count * 5)  # Encourage positions with more legal moves
        else:
            mobility_bonus = 0
            
        # Use regular evaluation + mobility bonus
        regular_eval = eval_position(board, drawbacks)
        return regular_eval + mobility_bonus
        
    def quiescence(self, board, alpha, beta, depth=0, max_depth=5):
        """
        Enhanced quiescence search that handles both captures and potential checkmates.
        Extends search dynamically when promising checkmate patterns are detected.
        """
        self.nodes += 1
        
        # Check for direct checkmate opportunity (king capture in Drawback Chess)
        opponent_king_square = None
        for sq, piece in board.piece_map().items():
            if piece.piece_type == chess.KING and piece.color != board.turn:
                opponent_king_square = sq
                break
                
        if opponent_king_square:
            for move in board.legal_moves:
                if move.to_square == opponent_king_square:
                    # Found checkmate (king capture)!
                    return MATE_UPPER - depth
        
        # Check for draws and stalemates (no legal moves)
        if not any(True for _ in board.legal_moves):
            # This is a draw in standard chess, but in Drawback Chess could be a win or loss
            if board.is_variant_loss():
                return -MATE_UPPER + depth
            return 0  # Draw
        
        # Static evaluation
        stand_pat = self.evaluate_position(board)
        
        # Stand pat cutoff
        if stand_pat >= beta:
            return beta
        if alpha < stand_pat:
            alpha = stand_pat
            
        # Maximum normal depth check
        if depth >= max_depth:
            # Even at max depth, if the stand_pat score is high, look a bit deeper
            # for potential checkmates to avoid horizon effect on winning positions
            if stand_pat < MATE_LOWER and stand_pat > 500:
                # Only extend depth for promising positions
                pass
            else:
                return alpha
        
        # Generate tactical moves (captures and checks)
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
            
            # Check for checks - look deeper at these
            if not is_tactical:
                board_copy = board.copy()
                try:
                    board_copy.push(move)
                    # In standard chess we'd check is_check(), but in Drawback Chess
                    # we need to check manually for pieces attacking the king
                    king_square = None
                    for sq, piece in board_copy.piece_map().items():
                        if piece.piece_type == chess.KING and piece.color == board.turn:
                            king_square = sq
                            break
                    
                    # If the move gives check, it's a tactical move worth exploring
                    if king_square:
                        attackers = board_copy.attackers(not board.turn, king_square)
                        if attackers:
                            is_tactical = True
                            score = 10  # Base score for checks
                except Exception:
                    continue  # Skip problematic moves
            
            # Add tactical moves to our search list
            if is_tactical:
                tactical_moves.append((score, move))
        
        # Sort moves: captures by score, checks after
        tactical_moves.sort(key=lambda x: x[0], reverse=True)
        
        # Search tactical moves
        for _, move in tactical_moves:
            try:
                # Skip bad captures in late quiescence unless they're checks
                if depth > 0 and board.is_capture(move):
                    victim = board.piece_at(move.to_square)
                    aggressor = board.piece_at(move.from_square)
                    if victim and aggressor:
                        victim_symbol = victim.symbol().upper()
                        aggressor_symbol = aggressor.symbol().upper()
                        victim_value = PIECE_VALUES.get(victim_symbol, (0, 0))[0]
                        aggressor_value = PIECE_VALUES.get(aggressor_symbol, (0, 0))[0]
                        
                        # Skip obviously bad trades but still investigate checks
                        if aggressor_value > victim_value + 200:
                            continue  # Skip obviously bad captures
                
                board_copy = board.copy()
                board_copy.push(move)
                
                # Check if we've won after this move
                if board_copy.is_variant_win():
                    return MATE_UPPER - depth - 1
                
                # Extend search depth for promising positions even beyond max_depth
                current_max_depth = max_depth
                if depth >= max_depth - 1:
                    # Check if our move created a very promising position
                    # such as king in danger or piece hanging
                    king_in_danger = False
                    for sq, piece in board_copy.piece_map().items():
                        if piece.piece_type == chess.KING and piece.color != board.turn:
                            attackers = board_copy.attackers(board.turn, sq)
                            if attackers:
                                king_in_danger = True
                                break
                    
                    # Extend depth for dangerous positions
                    if king_in_danger:
                        current_max_depth = max_depth + 2
                else:
                    current_max_depth = max_depth
                
                score = -self.quiescence(board_copy, -beta, -alpha, depth + 1, current_max_depth)
                
                if score >= beta:
                    return beta
                if score > alpha:
                    alpha = score
            except Exception as e:
                print(f"Error in quiescence search with move {move}: {str(e)}")
                continue  # Skip problematic moves instead of crashing
                
        return alpha
    
    def negamax(self, board, depth, alpha, beta, ply=0, null_ok=True, start_time=None, time_limit=None):
        """Enhanced negamax with improved move ordering and proper time checking"""
        # Check time limit more frequently
        if start_time and time_limit and time.time() - start_time > time_limit:
            # Return a flag indicating time's up
            raise TimeoutError("Search time limit reached")
            
        self.nodes += 1
        alpha_orig = alpha
        
        # Check for instant wins FIRST - before anything else
        
        # 1. Direct king capture - highest priority in Drawback Chess
        opponent_king_square = None
        for sq, piece in board.piece_map().items():
            if piece.piece_type == chess.KING and piece.color != board.turn:
                opponent_king_square = sq
                break
                
        # If we found the opponent's king, check if it can be captured directly
        if opponent_king_square:
            for move in board.legal_moves:
                if move.to_square == opponent_king_square:
                    return MATE_UPPER - ply  # Immediate king capture (checkmate)
        
        # 2. Atomic Bomb drawback special win condition
        # Check if we can capture a piece adjacent to opponent's king
        if opponent_king_square:
            # Get the active drawback for the opponent
            opponent_color = not board.turn
            opponent_drawback = board.get_active_drawback(opponent_color)
            
            if opponent_drawback == "atomic_bomb":
                # Check pieces adjacent to the king
                king_file, king_rank = chess.square_file(opponent_king_square), chess.square_rank(opponent_king_square)
                
                # Check all squares adjacent to king
                for file_offset in [-1, 0, 1]:
                    for rank_offset in [-1, 0, 1]:
                        if file_offset == 0 and rank_offset == 0:
                            continue  # Skip the king's own square
                            
                        adj_file = king_file + file_offset
                        adj_rank = king_rank + rank_offset
                        
                        # Check if valid square
                        if 0 <= adj_file <= 7 and 0 <= adj_rank <= 7:
                            adj_square = chess.square(adj_file, adj_rank)
                            piece_at_adj = board.piece_at(adj_square)
                            
                            # If there's an opponent's piece adjacent to their king
                            if piece_at_adj and piece_at_adj.color == opponent_color:
                                # Check if we can capture this piece
                                for move in board.legal_moves:
                                    if move.to_square == adj_square:
                                        return MATE_UPPER - ply - 1  # Immediate win via atomic bomb
        
        # Check transposition table
        key = board.fen()
        tt_entry = self.tt.get((key, depth))
        if tt_entry:
            if tt_entry.lower >= beta:
                return tt_entry.lower
            if tt_entry.upper <= alpha:
                return tt_entry.upper
            alpha = max(alpha, tt_entry.lower)
            beta = min(beta, tt_entry.upper)
            
        # Check for checkmate/stalemate/variant end
        if depth == 0 or board.is_variant_end():
            # Enhanced transition to quiescence search
            # Check for immediate checkmate or stalemate before going to quiescence
            if not any(True for _ in board.legal_moves):
                if board.is_variant_loss():
                    return -MATE_UPPER + ply
                return 0  # Draw
                
            # Add additional parameter to quiescence to indicate a promising position
            # This helps quiescence search know when to look deeper for checkmates
            score_estimate = self.evaluate_position(board)
            is_promising = score_estimate > 300 or score_estimate < -300
            
            # Pass extra hint to quiescence about promising positions
            return self.quiescence(board, alpha, beta, 0, 5 + (1 if is_promising else 0))
        
        # Null move pruning
        if depth > 2 and null_ok and not board.is_check():
            # Try a null move to see if we can get a beta cutoff
            board_copy = board.copy()
            board_copy.push(chess.Move.null())
            null_value = -self.negamax(board_copy, depth - 3, -beta, -beta + 1, ply + 1, False, start_time, time_limit)
            if null_value >= beta:
                return beta
        
        # Get all legal moves
        legal_moves = list(board.legal_moves)
        
        # Move ordering: Prioritize tactically powerful moves
        scored_moves = []
        
        # Track potential king threats for improved move ordering
        opponent_king_square = None
        for sq, piece in board.piece_map().items():
            if piece.piece_type == chess.KING and piece.color != board.turn:
                opponent_king_square = sq
                break
                
        for move in legal_moves:
            # Start with base score
            score = 0
            
            # 1. Check for transposition table hits
            if tt_entry and tt_entry.move == move:
                score += 10000  # Highest priority for TT moves
                
            # 2. Check for captures (MVV-LVA)
            if board.is_capture(move):
                target = board.piece_at(move.to_square)
                attacker = board.piece_at(move.from_square)
                if target and attacker:
                    # Most Valuable Victim - Least Valuable Attacker
                    t_symbol = target.symbol().upper()
                    a_symbol = attacker.symbol().upper()
                    t_value = PIECE_VALUES.get(t_symbol, (0, 0))[0]
                    a_value = PIECE_VALUES.get(a_symbol, (0, 0))[0]
                    score += t_value * 10 - a_value
                    
            # 3. Check for moves that attack the opponent's king area
            if opponent_king_square:
                # Prioritize moves that attack squares near the opponent's king
                king_file, king_rank = chess.square_file(opponent_king_square), chess.square_rank(opponent_king_square)
                to_file, to_rank = chess.square_file(move.to_square), chess.square_rank(move.to_square)
                
                # Calculate king distance
                file_dist = abs(king_file - to_file)
                rank_dist = abs(king_rank - to_rank)
                
                # Closer moves to king get higher priority
                if file_dist <= 1 and rank_dist <= 1:
                    # Adjacent to king
                    score += 300
                elif file_dist <= 2 and rank_dist <= 2:
                    # Close to king
                    score += 200
            
            # 4. Check for killer moves at this depth
            if self.killers[ply][0] == move or self.killers[ply][1] == move:
                score += 900  # Below TT moves but above most captures
            
            # 5. Check for history heuristic
            move_key = (move.from_square, move.to_square)
            score += self.history.get(move_key, 0)
            
            # Add to scored moves list
            scored_moves.append((score, move))
        
        # Sort moves by score, higher first
        scored_moves.sort(key=lambda x: x[0], reverse=True)
        
        # Variables to track best move and score
        best_score = -MATE_UPPER
        best_move = None
        
        # Try each move
        for _, move in scored_moves:
            # Check time limit during each move evaluation
            if start_time and time_limit and time.time() - start_time > time_limit:
                raise TimeoutError("Search time limit reached")
                
            board_copy = board.copy()
            board_copy.push(move)
            
            # REMOVE book bonus entirely - rely solely on PST adjustments
            # Let the PST table adjustments from book_handler influence evaluation
            score = -self.negamax(board_copy, depth - 1, -beta, -alpha, ply + 1, True, start_time, time_limit)
            
            # Update best score and move
            if score > best_score:
                best_score = score
                best_move = move
                
            # Alpha-beta pruning
            alpha = max(alpha, score)
            if alpha >= beta:
                # Store killer move for non-captures
                if not board.is_capture(move):
                    if move != self.killers[ply][0]:
                        self.killers[ply][1] = self.killers[ply][0]
                        self.killers[ply][0] = move
                
                # Update history heuristic
                if not board.is_capture(move):
                    key = (board.turn, move.from_square, move.to_square)
                    self.history[key] = self.history.get(key, 0) + depth * depth
                break

        # Store in transposition table
        if best_score <= alpha_orig:
            self.tt[(key, depth)] = Entry(best_score, beta, best_move)
        elif best_score >= beta:
            self.tt[(key, depth)] = Entry(alpha, best_score, best_move)
        else:
            self.tt[(key, depth)] = Entry(best_score, best_score, best_move)
        
        return best_score
    
    def search(self, board, depth, time_limit=5):
        """Improved search with better book move selection and PST adjustments"""
        try:
            self.nodes = 0
            self.tt.clear()
            self.history.clear()
            self.killers = [[None, None] for _ in range(MAX_DEPTH + 1)]
            self.eval_cache.clear()
            
            # Print key position info for debugging
            print(f"DEBUG: Searching position: {board.fen()}")
            print(f"DEBUG: Move count: {len(board.move_stack)}, Turn: {'White' if board.turn else 'Black'}")
            
            # Get book move suggestions with better debugging
            try:
                from AI.book_handler import BOOK_SELECTOR
                
                # Get book move and PST adjustment weights
                suggested_book_move, pst_weights = BOOK_SELECTOR.get_weighted_book_move(board)
                
                if suggested_book_move:
                    # Store the suggested move and weights to influence search
                    self.book_move_selected = suggested_book_move
                    self.pst_adjustment_weights = pst_weights
                    print(f"DEBUG: Book position found, biasing evaluation toward: {suggested_book_move}")
                    
                    # DO NOT directly return the book move - always search
                    # This ensures we still check tactics and don't blindly follow book
                else:
                    print("DEBUG: No book moves found for this position")
                    self.book_move_selected = None
                    self.pst_adjustment_weights = {}
                    
            except Exception as e:
                import traceback
                print(f"DEBUG: Book move selection error: {e}")
                traceback.print_exc()
                self.pst_adjustment_weights = {}
                self.book_move_selected = None
            
            # Check for immediate win conditions first - king captures and atomic bomb
            opponent_king_square = None
            for sq, piece in board.piece_map().items():
                if piece.piece_type == chess.KING and piece.color != board.turn:
                    opponent_king_square = sq
                    break
                    
            if opponent_king_square:
                # 1. Direct king capture
                for move in board.legal_moves:
                    if move.to_square == opponent_king_square:
                        print("Found immediate checkmate (king capture)!")
                        return move  # Return king capture immediately
                
                # 2. Atomic bomb win condition
                opponent_color = not board.turn
                opponent_drawback = board.get_active_drawback(opponent_color)
                
                if opponent_drawback == "atomic_bomb":
                    # Find winning moves that capture pieces adjacent to king
                    king_file, king_rank = chess.square_file(opponent_king_square), chess.square_rank(opponent_king_square)
                    for file_offset in [-1, 0, 1]:
                        for rank_offset in [-1, 0, 1]:
                            if file_offset == 0 and rank_offset == 0:
                                continue  # Skip the king's own square
                                
                            adj_file = king_file + file_offset
                            adj_rank = king_rank + rank_offset
                            
                            if 0 <= adj_file <= 7 and 0 <= adj_rank <= 7:
                                adj_square = chess.square(adj_file, adj_rank)
                                piece_at_adj = board.piece_at(adj_square)
                                
                                # If there's an opponent piece adjacent to their king
                                if piece_at_adj and piece_at_adj.color == opponent_color:
                                    # Find capturing moves
                                    for move in board.legal_moves:
                                        if move.to_square == adj_square:
                                            print("Found atomic bomb win condition!")
                                            return move  # Return winning move immediately
            
            # Check for drawback-related loss conditions first
            active_drawback = board.get_active_drawback(board.turn)
            if active_drawback:
                # Check if we have any legal moves with this drawback
                legal_moves = list(board.legal_moves)
                if not legal_moves:
                    print("WARNING: AI has no legal moves due to drawback restrictions")
                    return None  # No legal moves = loss
                    
                # Check for specific loss conditions
                from GameState.drawback_manager import get_drawback_loss_function
                loss_function = get_drawback_loss_function(active_drawback)
                if loss_function and loss_function(board, board.turn):
                    print(f"WARNING: AI detected it would lose due to drawback '{active_drawback}'")
                    # If we're going to lose, pick a random move as a last resort
                    return random.choice(legal_moves)
            
            # Check if the position is already a variant loss
            if board.is_variant_loss():
                print("WARNING: AI is already in a losing position")
                # Pick a random move if we're already lost
                legal_moves = list(board.legal_moves)
                if legal_moves:
                    return random.choice(legal_moves)
                return None
            
            start_time = time.time()
            best_move = None
            
            # Iterative deepening
            for d in range(1, depth + 1):
                print(f"Searching at depth {d}...")
                try:
                    # Aspiration window
                    alpha = -MATE_UPPER
                    beta = MATE_UPPER
                    score = self.negamax(board, d, alpha, beta, start_time=start_time, time_limit=time_limit)
                    
                    # Get the best move from the TT
                    key = (board.fen(), d)
                    if key in self.tt and self.tt[key].move:
                        best_move = self.tt[key].move
                        
                    # Print info
                    print(f"Depth: {d}, Score: {score}, Nodes: {self.nodes}, Best move: {best_move}")
                except TimeoutError:
                    print(f"Time limit reached at depth {d}")
                    break
                except Exception as e:
                    import traceback
                    print(f"Error at depth {d}: {str(e)}")
                    print(traceback.format_exc())
                    # Don't break - continue to next depth
                
                # Check if we're out of time
                elapsed = time.time() - start_time
                if elapsed >= time_limit:
                    print(f"Time limit reached: {elapsed:.2f}s")
                    break
            
            # Need a minimum result or we're in trouble
            if best_move is None:
                print("Warning: No best move found! Selecting safest available move...")
                moves = list(board.legal_moves)
                # Try to find a reasonable move
                if moves:
                    # For the first few moves, strongly bias toward center control
                    if len(board.move_stack) < 5:
                        # Try central pawn moves first
                        central_pawn_moves = []
                        for m in moves:
                            from_piece = board.piece_at(m.from_square)
                            if from_piece and from_piece.piece_type == chess.PAWN:
                                from_file = chess.square_file(m.from_square)
                                to_file = chess.square_file(m.to_square)
                                # Prioritize d and e pawns
                                if from_file in [3, 4] and to_file in [3, 4]:
                                    central_pawn_moves.append(m)
                        
                        if central_pawn_moves:
                            best_move = random.choice(central_pawn_moves)
                            return best_move
                    
                    # Otherwise, just pick a random move
                    best_move = random.choice(moves)
                print(f"Selected fallback move: {best_move}")
                
            return best_move
        except Exception as e:
            import traceback
            print(f"CRITICAL ERROR in search function: {str(e)}")
            print(traceback.format_exc())
            # Last-resort fallback - pick any legal move
            moves = list(board.legal_moves)
            if moves:
                fallback_move = random.choice(moves)
                print(f"Emergency fallback move: {fallback_move}")
                return fallback_move
            return None

# Simplified interface function
def best_move(board, depth, time_limit=5):
    """For use as the main AI interface"""
    try:
        # Track active drawback for debugging
        active_drawback = board.get_active_drawback(board.turn)
        if active_drawback:
            print(f"AI searching with active drawback: {active_drawback}")
            
            # Verify legal moves are available with the drawback
            legal_moves = list(board.legal_moves)
            print(f"Legal moves with '{active_drawback}' drawback: {len(legal_moves)}")
            
            # If we have very few legal moves, print them all for debugging
            if len(legal_moves) < 10:
                print("All legal moves available:")
                for i, m in enumerate(legal_moves):
                    print(f"  {i+1}. {m.uci()}")
            
            # If no legal moves, return None immediately
            if not legal_moves:
                print("WARNING: No legal moves available with this drawback!")
                return None
                
            # If only one legal move, return it immediately
            if len(legal_moves) == 1:
                print("Only one legal move available - returning it directly")
                return legal_moves[0]
        
        # Check for immediate win moves before starting the search
        # 1. King captures
        opponent_king_square = None
        for sq, piece in board.piece_map().items():
            if piece.piece_type == chess.KING and piece.color != board.turn:
                opponent_king_square = sq
                break
                
        if opponent_king_square:
            for move in board.legal_moves:
                if move.to_square == opponent_king_square:
                    print("DIRECT WIN: Found immediate king capture!")
                    return move
                    
            # 2. Atomic bomb win condition
            opponent_color = not board.turn
            opponent_drawback = board.get_active_drawback(opponent_color)
            
            if opponent_drawback == "atomic_bomb":
                king_file, king_rank = chess.square_file(opponent_king_square), chess.square_rank(opponent_king_square)
                
                for move in board.legal_moves:
                    target = board.piece_at(move.to_square)
                    if target and target.color == opponent_color:
                        target_file = chess.square_file(move.to_square)
                        target_rank = chess.square_rank(move.to_square)
                        
                        # If capturing a piece adjacent to opponent's king
                        if abs(target_file - king_file) <= 1 and abs(target_rank - king_rank) <= 1:
                            print("ATOMIC BOMB WIN: Found winning capture near opponent's king!")
                            return move
        
        engine = DrawbackSunfish()
        
        # Mark the board as being in a search to avoid triggering loss conditions during evaluation
        board_copy = board.copy()
        if hasattr(board_copy, "_in_search"):
            board_copy._in_search = True
        else:
            setattr(board_copy, "_in_search", True)
            
        result = engine.search(board_copy, depth, time_limit)
        
        # Verify the returned move is actually legal
        if result and result not in board.legal_moves:
            print(f"WARNING: AI returned illegal move {result}! Falling back to random move.")
            legal_moves = list(board.legal_moves)
            if legal_moves:
                return random.choice(legal_moves)
            return None
            
        return result
    except Exception as e:
        import traceback
        print(f"ENGINE ERROR: {str(e)}")
        print(traceback.print_exc())
        # Emergency fallback
        moves = list(board.legal_moves)
        if moves:
            return random.choice(moves)
        return None