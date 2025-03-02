import numpy as np
import chess
from AI import evaluation  # evaluation now uses unified Zobrist hash.
from AI import piece_square_table as piece_square_table
from AI.zobrist import get_zobrist_key  # NEW import
from collections import namedtuple
import random
from time import time
from AI.search_improvement import ImprovedMoveOrdering
from AI.transposition import BoundedTranspositionTable  # Add this import

DEBUG = False

###############################################################################
# Evaluation & Move Helpers
###############################################################################

def compute_game_phase(board):
    """
    Compute the game phase based on non-pawn pieces remaining.
    Returns a value between 0.0 (endgame) and 1.0 (opening/midgame).
    """
    phase = 0
    for square, piece in board.piece_map().items():
        # Skip pawns and kings, only count other pieces
        if piece.piece_type not in [chess.PAWN, chess.KING]:
            phase += piece_square_table.piece_phase.get(piece.symbol().upper(), 0)
    # Maximum phase value (all pieces on board)
    max_phase = 24.0
    phase = min(phase, max_phase)
    return phase / max_phase

def eval_board(board):
    """
    Use the evaluation module's evaluate() function directly.
    """
    return evaluation.evaluate(board)

def development_bonus(board, move):
    """
    Award a bonus for moves that develop a bishop into the center.
    Knights no longer receive this bonus.
    """
    piece = board.piece_at(move.from_square)
    if piece is None:
        return 0
    if piece.piece_type != chess.BISHOP:
        return 0
    # Define central squares (using chess module square constants)
    center_squares = [chess.D4, chess.D5, chess.E4, chess.E5]
    return 50 if move.to_square in center_squares else 0

def pawn_capture_bonus(board, move):
    """
    Award an extra bonus for pawn captures aimed at the center.
    Applies when a pawn captures on d4, d5, e4, or e5.
    """
    piece = board.piece_at(move.from_square)
    if piece and piece.piece_type == chess.PAWN and board.piece_at(move.to_square):
        center_squares = {chess.D4, chess.D5, chess.E4, chess.E5}
        return 50 if move.to_square in center_squares else 0
    return 0

def central_control_bonus(board, move):
    """Award bonus for pawn moves controlling color-appropriate center squares"""
    piece = board.piece_at(move.from_square)
    if not piece or piece.piece_type != chess.PAWN:
        return 0
    
    if piece.color == chess.WHITE:
        center_squares = {chess.D3, chess.D4, chess.E3, chess.E4}
    else:
        center_squares = {chess.D5, chess.D4, chess.E5, chess.E4}
    
    return 100 if move.to_square in center_squares else 0

def tactical_bonus(board, move):
    """
    Award additional bonus if the move stacks tactical pressure:
    - Extra bonus if move gives check.
    - Extra bonus if capturing a high-value (queen) piece.
    - Bonus if after move enemy king remains in check.
    """
    bonus = 0
    
    # Use extra bonus if move gives check - add null check
    if hasattr(board, "gives_check") and board.gives_check(move):
        bonus += 600  # extra bonus for check
    
    # Bonus for capturing a high value piece (queen) - add null check
    captured = board.piece_at(move.to_square)
    if captured and captured.piece_type == chess.QUEEN:
        bonus += 800
    
    # Simulate move to see if enemy king remains under pressure - with safer check
    try:
        board_copy = board.copy()
        board_copy.push(move)
        if board_copy.is_check():
            bonus += 300
    except Exception:
        # Skip this part if any errors occur
        pass
        
    return bonus

def opening_penalty(board, move):
    """Penalize mistakes in the opening phase"""
    penalty = 0
    piece = board.piece_at(move.from_square)
    
    if not piece:
        return 0
        
    # Strongly penalize early king moves (loses castling rights)
    if piece.piece_type == chess.KING:
        # Count pieces on board to determine opening/midgame state
        piece_count = sum(1 for _ in board.piece_map())
        if piece_count > 25:  # We're in the opening
            # Only penalize if move isn't castling
            if not board.is_castling(move):
                penalty -= 1000
                
    # Penalize developing pawns to the edge in opening
    if piece.piece_type == chess.PAWN:
        # In opening, penalize a/h pawn moves
        from_file = chess.square_file(move.from_square)
        if from_file in (0, 7) and len(board.move_stack) < 10:
            penalty -= 100
            
    return penalty

def score_move(board, move):
    """
    Enhanced move ordering:
    - Uses evaluation functions for captures and positional improvement.
    - Additionally rewards moves giving check,
      pawn moves controlling center, and pawn captures toward the center.
    - Also adds a bonus for moves targeting the last moved square.
    - Penalizes unsound king moves (if not castling).
    - Adds extra tactical bonus for stacking pressure.
    """
    score = 0
    captured = board.piece_at(move.to_square)
    attacker = board.piece_at(move.from_square)
    if captured:
        score = evaluation.get_capture_score(board, attacker, captured)
    else:
        score = evaluation.get_positional_improvement(board, move)
    # Reward moves that give check.
    if hasattr(board, "gives_check") and board.gives_check(move):
        score += 500
    # Add bonus for pawn moves that control center.
    score += central_control_bonus(board, move)
    # Extra bonus for pawn captures toward the center.
    score += pawn_capture_bonus(board, move)
    # Bonus for targeting last moved square.
    if board.move_stack:
        last_move = board.move_stack[-1]
        if move.to_square == last_move.to_square:
            score += 300
    # Penalize unsound king moves (if not castling).
    if attacker and attacker.piece_type == chess.KING and not board.is_castling(move):
        score -= 500
    # Add extra tactical bonus to stack pressure.
    score += tactical_bonus(board, move)
    # Add opening-specific penalties
    score += opening_penalty(board, move)
    return score

def has_immediate_king_capture(board, moves):
    for move in moves:
        captured = board.piece_at(move.to_square)
        if captured and captured.piece_type == chess.KING:
            return True
    return False

def is_game_over(board):
    pieces = board.piece_map().values()
    white_alive = any(p.piece_type == chess.KING and p.color == chess.WHITE for p in pieces)
    black_alive = any(p.piece_type == chess.KING and p.color == chess.BLACK for p in pieces)
    if not white_alive:
        return -evaluation.Score.CHECKMATE.value
    if not black_alive:
        return evaluation.Score.CHECKMATE.value
    return None

def is_capture(board, move):
    return board.piece_at(move.to_square) is not None

###############################################################################
# Search Enhancements: Quiescence, Killer/History, Extensions, Null-Move, Aspiration
###############################################################################

# Transposition table entry: (lower bound, upper bound)
Entry = namedtuple("Entry", "lower upper")

class Searcher:
    def __init__(self, use_incremental_eval=False):
        self.tt = BoundedTranspositionTable(capacity=2**20)
        self.nodes = 0
        self.use_incremental_eval = use_incremental_eval
        self.killer_moves = {}    # key: depth -> list of moves causing beta cutoffs
        self.history_table = {}   # key: move -> heuristic score
        self.move_ordering = ImprovedMoveOrdering()
        self.search_board = None  # Internal board copy for search operations

    def move_ordering_score(self, board, move, depth):
        base = score_move(board, move)
        killer_bonus = 5000 if move in self.killer_moves.get(depth, []) else 0
        history_bonus = self.history_table.get(move, 0)
        return base + killer_bonus + history_bonus

    # NEW: helper to flip evaluation for side to move.
    def get_evaluation(self, board):
        """Returns the evaluation score from the perspective of the side to move"""
        val = evaluation.evaluate(board)  # This is always from White's perspective
        
        # If Black is to move, return negative of evaluation
        # This ensures the score shows how good the position is for the player to move
        if board.turn == chess.BLACK:
            return -val
        return val

    def quiescence(self, board, alpha, beta):
        stand_pat = self.get_evaluation(board)
        if stand_pat >= beta:
            return beta
        if alpha < stand_pat:
            alpha = stand_pat
        moves = [m for m in board.generate_legal_moves()
                 if is_capture(board, m) or (hasattr(board, "gives_check") and board.gives_check(m))]
        moves.sort(key=lambda m: score_move(board, m), reverse=True)
        for move in moves:
            board.push(move)
            score = -self.quiescence(board, -beta, -alpha)
            board.pop()
            if score >= beta:
                return beta
            if score > alpha:
                alpha = score
        return alpha

    def bound(self, board, gamma, depth):
        self.nodes += 1

        # Terminal position check.
        result = is_game_over(board)
        if result is not None:
            return result
        if depth == 0:
            return self.quiescence(board, -evaluation.Score.CHECKMATE.value, evaluation.Score.CHECKMATE.value)

        # Null-move pruning.
        if depth >= 3 and not board.is_check():
            nullmove_board = board.copy()
            if hasattr(nullmove_board, 'push_null'):
                nullmove_board.push_null()
                null_score = -self.bound(nullmove_board, 1 - gamma, depth - 2)
                if null_score >= gamma:
                    return null_score

        # Transposition table lookup
        key = str(get_zobrist_key(board)) + f":{depth}"
        tt_entry = self.tt.retrieve(key)
        
        # Correctly handle the stored entry
        if tt_entry:
            entry_data = tt_entry.get("entry")
            if entry_data:
                if entry_data.lower >= gamma:
                    return entry_data.lower
                if entry_data.upper < gamma:
                    return entry_data.upper
        else:
            entry_data = Entry(-evaluation.Score.CHECKMATE.value, evaluation.Score.CHECKMATE.value)

        # Get all legal moves
        moves = list(board.legal_moves)
        if not moves:
            return -evaluation.Score.CHECKMATE.value // 2
        
        # Get PV move from transposition table
        pv_move = None
        tt_move_entry = self.tt.retrieve(str(get_zobrist_key(board)))
        if tt_move_entry and "move" in tt_move_entry:
            pv_move = tt_move_entry["move"]
        
        # IMPROVED MOVE ORDERING
        ordered_moves = self.move_ordering.sort_moves(board, moves, pv_move, depth)

        # Search through ordered moves
        best = -evaluation.Score.CHECKMATE.value
        best_move = None
        for i, move in enumerate(ordered_moves):
            # Late Move Reductions with refinements from Numbfish
            reduction = 0
            is_quiet = not board.is_capture(move) and not board.gives_check(move)
            
            if i >= 3 and depth >= 3 and is_quiet and not board.is_check():
                reduction = 1
                # Even deeper reductions for later quiet moves
                if i >= 6:
                    reduction = 2
            
            # Search extension for check and important captures
            extension = 0
            if board.gives_check(move):
                extension = 1
            elif board.is_capture(move):
                captured = board.piece_at(move.to_square)
                if captured and captured.piece_type in (chess.QUEEN, chess.ROOK):
                    extension = 1

            # Make the move and search
            board.push(move)
            score = -self.bound(board, 1-gamma, depth-1-reduction+extension)
            board.pop()

            # Update best score
            if score > best:
                best = score
                best_move = move
            
            # Beta cutoff - update killer moves and history table
            if best >= gamma:
                if not board.is_capture(move):
                    self.move_ordering.add_killer_move(move, depth)
                self.move_ordering.update_history(board, move, depth)
                break
        
        # Store results in transposition table
        if best >= gamma:
            self.tt.store(key, {"entry": Entry(best, entry_data.upper), "move": best_move})
            # Also store the best move separately for PV retrieval
            self.tt.store(str(get_zobrist_key(board)), {"move": best_move})
        else:
            self.tt.store(key, {"entry": Entry(entry_data.lower, best), "move": best_move})
        
        return best

    def get_principal_variation(self, board, max_length=10):
        pv = []
        local_board = board.copy()
        visited = set()  # Prevent cycles
        
        while len(pv) < max_length:
            key = str(get_zobrist_key(local_board))
            if key in visited:
                break  # Avoid loops
                
            tt_entry = self.tt.retrieve(key)
            if not tt_entry or "move" not in tt_entry or not tt_entry["move"]:
                break
                
            move = tt_entry["move"]
            pv.append(move)
            visited.add(key)
            
            try:
                local_board.push(move)
            except:
                break  # Invalid move
                
        return pv

    def search(self, board, max_depth=4):
        print("Starting new search (preserving previous tables).")
        self.search_board = board.copy()
        best_move_found = None
        prev_score = 0
        ASPIRATION_WINDOW = 50
        start_time = time()  # record search start time
        for depth in range(1, max_depth + 1):
            # Check elapsed time; if over 10 seconds, break early.
            if time() - start_time > 10:
                print(f"Search time exceeded cutoff at depth {depth}.")
                break
            gamma = prev_score
            lower = gamma - ASPIRATION_WINDOW
            upper = gamma + ASPIRATION_WINDOW
            iteration = 0
            while iteration < 20:
                score = self.bound(self.search_board, gamma, depth)
                if score < lower:
                    gamma = score
                    lower = gamma - ASPIRATION_WINDOW
                elif score > upper:
                    gamma = score
                    upper = gamma + ASPIRATION_WINDOW
                else:
                    break
                iteration += 1
            if iteration >= 20:
                print(f"[Warning] Aspiration window failed to converge at depth {depth}; using last score.")
            prev_score = score
            
            # Get the best move from transposition table
            tt_entry = self.tt.retrieve(str(get_zobrist_key(self.search_board)))
            best_move_found = tt_entry["move"] if tt_entry and "move" in tt_entry else None
            
            pv = self.get_principal_variation(self.search_board)
            if DEBUG:
                print(f"[DEBUG] Depth: {depth}, Score: {score}, Best move: {best_move_found}, PV: {pv}")
            else:
                print(f"Depth: {depth}, Score: {score}, Best move: {best_move_found}, PV: {pv}")
        return best_move_found

def best_move(board, depth) -> int:
    try:
        # Always work with a copy of the board to avoid modifying the original
        board_copy = board.copy()
        searcher = Searcher()
        move = searcher.search(board_copy, max_depth=depth)
    except Exception as e:
        print(f"Error during search: {e}")
        move = None
    if move is None:
        moves = list(board.generate_legal_moves())
        if moves:
            move = moves[0]
            print(f"AI choosing fallback move: {move}")
        else:
            print("AI has no legal moves.")
    else:
        print(f"AI chooses {move}")
    return move