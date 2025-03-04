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
        """Use the dedicated evaluation function with PST adjustments if available"""
        # Check cache first
        key = board.fen()
        if key in self.eval_cache:
            return self.eval_cache[key]
        
        # Check if we have book weights to apply
        pst_weights = getattr(self, 'pst_adjustment_weights', None)
        
        # Use the improved evaluation function with possible PST adjustments
        score = eval_position(board, pst_weights)
        
        # Cache the result
        self.eval_cache[key] = score
        return score
        
    def quiescence(self, board, alpha, beta, depth=0, max_depth=5):
        """Quiescence search to only evaluate quiet positions"""
        self.nodes += 1
        stand_pat = self.evaluate_position(board)
        
        # Stand pat cutoff
        if stand_pat >= beta:
            return beta
        if alpha < stand_pat:
            alpha = stand_pat
            
        # Maximum depth check
        if depth >= max_depth:
            return alpha
            
        # Generate and filter only captures
        captures = []
        for move in board.legal_moves:
            if board.is_capture(move):
                # Score captures by MVV-LVA
                target = board.piece_at(move.to_square)
                attacker = board.piece_at(move.from_square)
                if target and attacker:  # Make sure pieces exist
                    target_symbol = target.symbol().upper()
                    attacker_symbol = attacker.symbol().upper()
                    target_value = PIECE_VALUES.get(target_symbol, (0, 0))[0]
                    attacker_value = PIECE_VALUES.get(attacker_symbol, (0, 0))[0]
                    score = target_value - attacker_value/10
                    captures.append((score, move))
        
        # FIXED: Sort captures by score using key parameter
        captures.sort(key=lambda x: x[0], reverse=True)
        
        # Search captures
        for _, move in captures:
            try:
                # Skip bad captures in late quiescence
                if depth > 0:
                    # Skip capturing with higher value piece
                    victim = board.piece_at(move.to_square)
                    aggressor = board.piece_at(move.from_square)
                    if victim and aggressor:
                        victim_symbol = victim.symbol().upper()
                        aggressor_symbol = aggressor.symbol().upper()
                        victim_value = PIECE_VALUES.get(victim_symbol, (0, 0))[0]
                        aggressor_value = PIECE_VALUES.get(aggressor_symbol, (0, 0))[0]
                        if aggressor_value > victim_value + 50:
                            continue  # Skip obviously bad captures
                
                board_copy = board.copy()
                board_copy.push(move)
                score = -self.quiescence(board_copy, -beta, -alpha, depth + 1, max_depth)
                
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
        
        # Check for checkmate opportunity - do this early to find mates quickly!
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
            return self.quiescence(board, alpha, beta)
            
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
        # First shuffle moves randomly for variety
        random.shuffle(legal_moves)
        
        # Move ordering - score moves after shuffling
        scored_moves = []
        
        # Get book moves for this position - avoid circular imports
        try:
            from AI.book_parser import OPENING_BOOK
            
            # Get book moves for this position
            book_move_list = OPENING_BOOK.get_book_moves(board)
            book_move_dict = {move: weight for move, weight in book_move_list}
            
            # Use the pre-selected random book move from the search function
            random_book_move = getattr(self, 'random_book_move', None)
            
        except (ImportError, Exception) as e:
            print(f"Book move error: {e}")
            book_move_dict = {}
            random_book_move = None
        
        # Check if book moves are legal with current drawbacks
        legal_move_set = set(legal_moves)  # Convert to set for faster lookups
        
        for move in legal_moves:
            score = 0
            
            # Random selected book move gets highest priority
            if move == random_book_move:
                score = 30000000  # Much higher priority than other book moves
            # Other book moves still get good priority
            elif move in book_move_dict:
                weight = book_move_dict[move]
                score = 5000000 + (weight * 1000)
            
            # TT move gets high priority
            if tt_entry and move == tt_entry.move:
                score = 10000000
                
            # King captures get highest priority
            if opponent_king_square and move.to_square == opponent_king_square:
                score = 20000000
            
            # In opening game, prioritize central pawn moves for BOTH colors
            if len(board.move_stack) < 15:  
                from_piece = board.piece_at(move.from_square)
                if from_piece:
                    # Central pawn advances get a bonus
                    if from_piece.piece_type == chess.PAWN:
                        from_file = chess.square_file(move.from_square)
                        from_rank = chess.square_rank(move.from_square)
                        to_file = chess.square_file(move.to_square)
                        to_rank = chess.square_rank(move.to_square)
                        
                        # Common logic for both colors - central pawn moves
                        if from_file in [3, 4]:  # d or e file
                            # 2-square advance in opening gets huge bonus
                            if abs(from_rank - to_rank) == 2:
                                score += 1000000
                            else:
                                score += 800000
                        elif from_file in [2, 5]:  # c or f file
                            score += 600000
                    
                    # SEVERELY penalize knight moves if central pawns haven't moved
                    if from_piece.piece_type == chess.KNIGHT:
                        # Check if central pawns have moved based on color
                        if from_piece.color == chess.WHITE:
                            d_pawn_moved = board.piece_at(chess.D2) is None
                            e_pawn_moved = board.piece_at(chess.E2) is None
                            if not d_pawn_moved and not e_pawn_moved:
                                score -= 700000  # Huge penalty!
                        else:  # Black
                            d_pawn_moved = board.piece_at(chess.D7) is None
                            e_pawn_moved = board.piece_at(chess.E7) is None
                            if not d_pawn_moved and not e_pawn_moved:
                                score -= 700000  # Huge penalty!
                        
                        # Edge penalties
                        to_file = chess.square_file(move.to_square)
                        if to_file == 0 or to_file == 7:  # Knight to a or h file
                            score -= 500000
            
            # Capture scoring
            if board.is_capture(move):
                victim = board.piece_at(move.to_square)
                attacker = board.piece_at(move.from_square)
                if victim and attacker:
                    victim_symbol = victim.symbol().upper()
                    attacker_symbol = attacker.symbol().upper()
                    victim_value = PIECE_VALUES.get(victim_symbol, (0, 0))[0]
                    attacker_value = PIECE_VALUES.get(attacker_symbol, (0, 0))[0]
                    # MVV-LVA scoring
                    capture_score = victim_value * 100 - attacker_value
                    score += 1000000 + capture_score
            
            # Checks get priority
            if board.gives_check(move):
                score += 500000
            
            # Killer moves
            if move == self.killers[ply][0]:
                score += 90000
            elif move == self.killers[ply][1]:
                score += 80000
            
            # History heuristic
            score += self.history.get((board.turn, move.from_square, move.to_square), 0)
            
            scored_moves.append((score, move))
        
        # Sort all moves by score
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
            
            # Check for immediate checkmate moves first (king captures in drawback chess)
            opponent_king_square = None
            for sq, piece in board.piece_map().items():
                if piece.piece_type == chess.KING and piece.color != board.turn:
                    opponent_king_square = sq
                    break
                    
            if opponent_king_square:
                for move in board.legal_moves:
                    if move.to_square == opponent_king_square:
                        print("Found immediate checkmate (king capture)!")
                        return move  # Return king capture immediately
            
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
            if not legal_moves:
                print("WARNING: No legal moves available with this drawback!")
                return None
        
        engine = DrawbackSunfish()
        return engine.search(board.copy(), depth, time_limit)
    except Exception as e:
        import traceback
        print(f"ENGINE ERROR: {str(e)}")
        print(traceback.format_exc())
        # Emergency fallback
        moves = list(board.legal_moves)
        if moves:
            return random.choice(moves)
        return None