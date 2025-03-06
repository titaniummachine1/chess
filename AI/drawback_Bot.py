"""
Drawback Bot - A custom chess engine designed specifically for Drawback Chess.
Uses the DrawbackBoard move generation and optimized for the unique rules of Drawback Chess.
Core engine logic with improved win/loss detection.
"""
import chess
import time
import random
from collections import namedtuple
from GameState.movegen import DrawbackBoard
from AI.evaluation import evaluate_position as eval_position
from AI.piece_square_table import PIECE_VALUES
from AI.search_utils import quiescence_search, negamax, Entry

# Safe imports to avoid circular references
try:
    from AI.book_parser import is_book_position
except ImportError:
    # Define a fallback function if module not available
    def is_book_position(board):
        return False

from AI.ai_utils import MATE_LOWER, MATE_UPPER, MAX_DEPTH, BOOK_MOVE_BONUS, BOOK_MOVE_BONUS_REGULAR

class DrawbackBot:
    """Custom chess engine designed specifically for Drawback Chess rules"""
    
    def __init__(self):
        self.nodes = 0
        self.tt = {}  # Transposition table
        self.history = {}  # Move history heuristic
        self.killers = [[None, None] for _ in range(MAX_DEPTH + 1)]  # Killer moves
        self.eval_cache = {}  # Cache for position evaluations
        self.book_move_bonuses = {}  # Book move bonuses in centipawns
        
    def evaluate_position(self, board, drawbacks=None):
        """Enhanced evaluation function that considers drawbacks"""
        # Check if the position is a variant loss due to drawbacks
        if board.is_variant_loss():
            return -MATE_UPPER  # Return worst possible score
            
        # Get active drawback for current side
        active_drawback = board.get_active_drawback(board.turn)
        
        # Initialize evaluation components
        mobility_score = 0
        safety_score = 0
        
        # Calculate mobility with consideration for active drawbacks
        if active_drawback:
            # Count legal moves - heavily penalize positions with few moves
            legal_moves = list(board.legal_moves)
            legal_count = len(legal_moves)
            
            if legal_count == 0:
                return -MATE_UPPER  # No legal moves is a loss
            
            # Calculate mobility score based on move count
            mobility_score = min(150, legal_count * 5)  # Cap at 150 to avoid overvaluing
            
            # Additional evaluations for specific drawbacks
            if active_drawback == "covering_fire":
                # Count how many pieces can be captured with covering fire
                capturable_count = 0
                for move in legal_moves:
                    if board.is_capture(move):
                        capturable_count += 1
                
                # Bonus for having more potential captures
                mobility_score += capturable_count * 10
            
            elif active_drawback == "punching_down":
                # Count how many safe captures of lower-value pieces
                safe_captures = 0
                for move in legal_moves:
                    if board.is_capture(move):
                        victim = board.piece_at(move.to_square)
                        aggressor = board.piece_at(move.from_square)
                        if victim and aggressor and victim.piece_type < aggressor.piece_type:
                            safe_captures += 1
                
                # Bonus for having pieces that can capture lower-value targets
                mobility_score += safe_captures * 15
        else:
            mobility_score = 0
        
        # Calculate king safety based on surrounding squares and attackers
        king_square = None
        for square in chess.SQUARES:
            piece = board.piece_at(square)
            if piece and piece.piece_type == chess.KING and piece.color == board.turn:
                king_square = square
                break
        
        if king_square:
            # Calculate king safety based on surrounding squares and attackers
            attackers = board.attackers(not board.turn, king_square)
            defenders = board.attackers(board.turn, king_square)
            
            # Penalty for each attacker, bonus for each defender
            safety_score = (len(defenders) - len(attackers)) * 30
        
        # Use regular evaluation + mobility and safety bonuses
        regular_eval = eval_position(board, drawbacks)
        
        return regular_eval + mobility_score + safety_score
        
    def search(self, board, depth, time_limit=None):
        """
        Search for the best move in the current position to the specified depth.
        Delegates to the negamax function for the actual search.
        
        Args:
            board: Current position
            depth: Search depth
            time_limit: Optional time limit in seconds
            
        Returns:
            Tuple of (score, best_move)
        """
        # Reset node counter
        self.nodes = 0
        
        # Reset cached data for new search
        self.tt = {}
        self.history = {}
        self.killers = [[None, None] for _ in range(MAX_DEPTH + 1)]
        self.eval_cache = {}
        
        # Start search with iterative deepening
        best_move = None
        best_score = -MATE_UPPER
        start_overall = time.time()
        
        for current_depth in range(1, depth + 1):
            start_time = time.time()
            
            # Check if we've already exceeded the time limit
            if time_limit and time.time() - start_overall > time_limit:
                print(f"Time limit reached after depth {current_depth-1}, stopping search")
                break
                
            # Use narrow windows for deeper searches
            if current_depth >= 3:
                # Start with previous best score plus a small window
                alpha = max(-MATE_UPPER, best_score - 50)
                beta = min(MATE_UPPER, best_score + 50)
                
                # First attempt with narrow window
                score = negamax(self, board, current_depth, alpha, beta, start_time=start_overall, time_limit=time_limit)
                
                # If score outside window, re-search with full window
                if score <= alpha or score >= beta:
                    # Check time limit again before researching
                    if time_limit and time.time() - start_overall > time_limit:
                        print(f"Time limit reached during aspiration window retry at depth {current_depth}")
                        break
                        
                    alpha = -MATE_UPPER
                    beta = MATE_UPPER
                    score = negamax(self, board, current_depth, alpha, beta, start_time=start_overall, time_limit=time_limit)
            else:
                # Full window for shallow searches
                score = negamax(self, board, current_depth, -MATE_UPPER, MATE_UPPER, start_time=start_overall, time_limit=time_limit)
            
            search_time = time.time() - start_time
            
            # Find best move from tt
            key = board.zobrist_hash() if hasattr(board, 'zobrist_hash') else str(board.fen())
            if key in self.tt and self.tt[key].move:
                best_move = self.tt[key].move
                best_score = score
                
                # Report search results
                print(f"Depth: {current_depth}, Score: {score}, Nodes: {self.nodes}, Best move: {best_move}")
                
                # Early exit if we found a forced mate
                if score > MATE_LOWER or score < -MATE_LOWER:
                    print(f"Found mate in {(MATE_UPPER - abs(score)) // 2} moves, stopping search")
                    break
                    
                # Check time after completing a depth
                if time_limit and time.time() - start_overall > time_limit:
                    print(f"Time limit reached after completing depth {current_depth}")
                    break
            else:
                # If no move found in TT, we're in trouble - report this
                print(f"Depth: {current_depth}, Score: {score}, Nodes: {self.nodes}, Best move: None")
                
        return best_score, best_move
        
    def check_terminal_state(self, board):
        """Check for terminal state conditions in Drawback Chess"""
        # No legal moves - stalemate or checkmate
        if not any(True for _ in board.legal_moves):
            return True
        
        # Check for variant loss due to drawbacks
        if board.is_variant_loss():
            return True
            
        # Check for king capture on next move - terminal state
        for move in board.legal_moves:
            target = board.piece_at(move.to_square)
            if target and target.piece_type == chess.KING:
                return True
                
        return False
        
    def get_book_move(self, board):
        """Get a move from the opening book if available, considering drawbacks"""
        try:
            from AI.book_handler import get_book_move, get_weighted_book_move
            
            # Get the active drawback for current player
            active_drawback = board.get_active_drawback(board.turn)
            
            # If we have a drawback, use weighted selection with drawback consideration
            if active_drawback:
                # Get weighted book moves with drawback info
                weighted_result = get_weighted_book_move(board, active_drawback)
                
                if weighted_result and weighted_result[0]:
                    move, info = weighted_result
                    
                    # Store the move bonuses for search if we need to fall back
                    if info and "book_move_bonuses" in info:
                        self.book_move_bonuses = info["book_move_bonuses"]
                        
                    print(f"Drawback-adjusted book move found: {move}")
                    return move
            
            # If no drawback or no weighted move found, fall back to standard book move
            move = get_book_move(board)
            if move:
                print(f"Standard book move found: {move}")
                return move
            
        except ImportError:
            print("Book handler not available")
            pass
        return None
        
    def get_best_move(self, board, depth=3, use_book=True):
        """Get the best move from the current position with drawback considerations"""
        # First, check for terminal state
        if self.check_terminal_state(board):
            print("Terminal state detected")
            return None
            
        # Get active drawback
        active_drawback = board.get_active_drawback(board.turn)
        
        # Then try book move with drawback consideration
        if use_book:
            book_move = self.get_book_move(board)
            if book_move:
                # Double check that the book move complies with drawback restrictions
                if not active_drawback or not board._is_drawback_illegal(book_move, board.turn):
                    return book_move
                else:
                    print(f"Book move {book_move} rejected due to drawback: {active_drawback}")
                
        # Mark the board for search
        if hasattr(board, "_in_search"):
            board._in_search = True
            
        # Fall back to search
        print(f"Searching with active drawback: {active_drawback}")
        score, move = self.search(board, depth)
        
        # Reset search flag
        if hasattr(board, "_in_search"):
            board._in_search = False
            
        # If no move was found, find a legal move
        if not move:
            print("Warning: No best move found! Selecting safest available move...")
            # Just return any legal move - preferably one that doesn't lose a piece
            moves = list(board.legal_moves)
            if moves:
                # Sort moves by safety (non-captures first)
                safe_moves = []
                other_moves = []
                
                for m in moves:
                    # Prefer moves that don't put our pieces in danger
                    if not board.is_capture(m):
                        # Check if the move puts the piece in danger
                        board_copy = board.copy()
                        try:
                            board_copy.push(m)
                            # Check if the moved piece is under attack
                            is_safe = True
                            target_piece = board_copy.piece_at(m.to_square)
                            
                            if target_piece:
                                attackers = board_copy.attackers(not board.turn, m.to_square)
                                defenders = board_copy.attackers(board.turn, m.to_square)
                                
                                # If more attackers than defenders, the move is unsafe
                                if len(attackers) > len(defenders):
                                    is_safe = False
                                    
                            if is_safe:
                                safe_moves.append(m)
                            else:
                                other_moves.append(m)
                        except Exception:
                            # If error occurs, consider it other move
                            other_moves.append(m)
                    else:
                        # Captures go to other moves - we'll only use them if no safe moves
                        other_moves.append(m)
                
                # Return safe moves if available, otherwise any legal move
                if safe_moves:
                    return random.choice(safe_moves)
                return random.choice(other_moves)
            return None
            
        print(f"Search complete. Chosen move: {move.uci()}")
        return move
    
def best_move(board, depth=3, time_limit=5, book_move_bonuses=None):
    """
    Convenience function to get the best move without creating an engine instance.
    
    Args:
        board: Current position
        depth: Search depth
        time_limit: Time limit in seconds (not used directly but kept for compatibility)
        book_move_bonuses: Dictionary of book moves with their bonus values (not used directly)
        
    Returns:
        Best move object or None if no move available
    """
    engine = DrawbackBot()
    
    # If book move bonuses are provided, set them in the engine
    if book_move_bonuses:
        engine.book_move_bonuses = book_move_bonuses
        
    # Convert time_limit to a simple use_book flag for compatibility
    use_book = time_limit > 0
    
    return engine.get_best_move(board, depth, use_book) 