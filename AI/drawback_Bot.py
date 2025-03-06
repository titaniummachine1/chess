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
        
    def search(self, board, depth):
        """
        Search for the best move in the current position to the specified depth.
        Delegates to the negamax function for the actual search.
        
        Args:
            board: Current position
            depth: Search depth
            
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
        
        for current_depth in range(1, depth + 1):
            start_time = time.time()
            
            # Use narrow windows for deeper searches
            if current_depth >= 3:
                # Start with previous best score plus a small window
                alpha = max(-MATE_UPPER, best_score - 50)
                beta = min(MATE_UPPER, best_score + 50)
                
                # First attempt with narrow window
                score = negamax(self, board, current_depth, alpha, beta)
                
                # If score outside window, re-search with full window
                if score <= alpha or score >= beta:
                    alpha = -MATE_UPPER
                    beta = MATE_UPPER
                    score = negamax(self, board, current_depth, alpha, beta)
            else:
                # Full window for shallow searches
                score = negamax(self, board, current_depth, -MATE_UPPER, MATE_UPPER)
            
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
        """Get a move from the opening book if available"""
        try:
            from AI.book_handler import get_book_move
            move = get_book_move(board)
            if move:
                print(f"Book move found: {move}")
                return move
        except ImportError:
            print("Book handler not available")
            pass
        return None
        
    def get_best_move(self, board, depth=3, use_book=True):
        """Get the best move from the current position"""
        # First, check for terminal state
        if self.check_terminal_state(board):
            print("Terminal state detected")
            return None
            
        # Then try book move
        if use_book:
            book_move = self.get_book_move(board)
            if book_move:
                return book_move
                
        # Mark the board for search
        if hasattr(board, "_in_search"):
            board._in_search = True
            
        # Fall back to search
        active_drawback = board.get_active_drawback(board.turn)
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
                # Prefer non-captures of our pieces
                safe_moves = []
                for m in moves:
                    if not board.is_capture(m):
                        safe_moves.append(m)
                if safe_moves:
                    return random.choice(safe_moves)
                return random.choice(moves)
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