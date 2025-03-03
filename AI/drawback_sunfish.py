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
from AI.book_parser import is_book_position, BOOK_MOVE_BONUS

# Constants for search
MATE_LOWER = 10000
MATE_UPPER = 20000
MAX_DEPTH = 20

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
        """Use the dedicated evaluation function for more accurate results"""
        # Check cache first
        key = board.fen()
        if key in self.eval_cache:
            return self.eval_cache[key]
        
        # Use the improved evaluation function
        score = eval_position(board)
        
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
        """Enhanced negamax with improved move ordering, book move prioritization and proper time checking"""
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
        from AI.book_parser import OPENING_BOOK
        
        # Get book moves for this position
        book_move_list = OPENING_BOOK.get_book_moves(board)
        # Lower move ordering priority for book moves - still high but not absolute
        book_move_bonus = 1000000  # Reduced priority from previous value
        book_move_dict = {move: weight for move, weight in book_move_list}
        
        # Check if book moves are legal with current drawbacks
        legal_move_set = set(legal_moves)  # Convert to set for faster lookups
        valid_book_moves = {move: weight for move, weight in book_move_dict.items() 
                           if move in legal_move_set}
        
        for move in legal_moves:
            score = 0
            
            # Book moves get good but not overwhelming priority
            if move in valid_book_moves:
                # Give book moves high priority but don't make it overwhelming
                # This ensures book moves are tried first but not forced
                weight = valid_book_moves[move]
                score = 5000000 + (weight * 1000)  # Still high priority but more balanced
                
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
            
            # Special bonus for book moves in evaluation
            book_bonus = 0
            if move in book_move_dict:
                book_bonus = BOOK_MOVE_BONUS  # +35 centipawn bonus for book moves
            
            # Recursive search
            score = -self.negamax(board_copy, depth - 1, -beta, -alpha, ply + 1, True, start_time, time_limit) + book_bonus
            
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
        """Improved search with better checkmate detection and opening book"""
        try:
            self.nodes = 0
            self.tt.clear()
            self.history.clear()
            self.killers = [[None, None] for _ in range(MAX_DEPTH + 1)]
            self.eval_cache.clear()
            
            # Simple opening book for the first move
            if len(board.move_stack) == 0:
                # White's first move - use a mini opening book
                if board.turn == chess.WHITE:
                    # Strong preference for e4 or d4
                    e4 = chess.Move.from_uci("e2e4")
                    d4 = chess.Move.from_uci("d2d4")
                    if e4 in board.legal_moves:
                        print("Opening book: e4")
                        return e4
                    elif d4 in board.legal_moves:
                        print("Opening book: d4")
                        return d4
            # Black's response to e4
            elif board.turn == chess.BLACK and board.move_stack[-1].uci() == "e2e4":
                e5 = chess.Move.from_uci("e7e5")
                if e5 in board.legal_moves:
                    print("Opening book: e5")
                    return e5
            # Black's response to d4
            elif board.turn == chess.BLACK and board.move_stack[-1].uci() == "d2d4":
                d5 = chess.Move.from_uci("d7d5")
                if d5 in board.legal_moves:
                    print("Opening book: d5")
                    return d5
            
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