import numpy as np
import chess
from AI import evaluation  # evaluation now uses unified Zobrist hash.
from AI import piece_square_table as piece_square_table
from AI.zobrist import get_zobrist_key  # NEW import
from collections import namedtuple
import random
from time import time

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

def eval_board(board):
    """Enhanced evaluation with pawn structure analysis"""
    score = evaluation.evaluate(board)
    
    # Add pawn structure bonuses
    for square in chess.SQUARES:
        piece = board.piece_at(square)
        if piece and piece.piece_type == chess.PAWN:
            # Bonus for protected pawns
            if board.is_protected(piece.color, square):
                score += 15 if piece.color == chess.WHITE else -15
            # Penalty for isolated pawns
            if not board.has_friendly_pawns(piece.color, square):
                score -= 20 if piece.color == chess.WHITE else +20
    return score

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
    # Use extra bonus if move gives check
    if hasattr(board, "gives_check") and board.gives_check(move):
        bonus += 600  # extra bonus for check
    # Bonus for capturing a high value piece (queen)
    captured = board.piece_at(move.to_square)
    if captured and captured.piece_type == chess.QUEEN:
        bonus += 800
    # Simulate move to see if enemy king remains under pressure
    board_copy = board.copy()
    board_copy.push(move)
    if board_copy.is_check():
        bonus += 300
    return bonus

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
    # Removed development bonus since piece–square tables handle development.
    # Add bonus for pawn moves that control center.
    score += central_control_bonus(board, move)
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
        self.tp_score = {}   # key: (zobrist key + ":" + depth)
        self.tp_move = {}    # key: zobrist key -> best move found
        self.nodes = 0
        self.use_incremental_eval = use_incremental_eval
        self.killer_moves = {}    # key: depth -> list of moves causing beta cutoffs
        self.history_table = {}   # key: move -> heuristic score
        self.search_board = None  # Internal board copy for search operations

    def move_ordering_score(self, board, move, depth):
        base = score_move(board, move)
        killer_bonus = 5000 if move in self.killer_moves.get(depth, []) else 0
        history_bonus = self.history_table.get(move, 0)
        return base + killer_bonus + history_bonus

    # NEW: helper to flip evaluation for side to move.
    def get_evaluation(self, board):
        val = evaluation.evaluate(board)
        return val if board.turn == chess.WHITE else -val

    def quiescence(self, board, alpha, beta):
        stand_pat = self.get_evaluation(board)
        if board.turn == chess.BLACK:
            stand_pat = -stand_pat  # Ensure proper perspective

        stand_pat = -stand_pat  # Ensure proper perspective
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
        # Add perspective correction before returning results
        if board.turn == chess.BLACK:
            gamma = -gamma

        # Terminal position check.
        result = is_game_over(board)
        if result is not None:
            return result
        if depth == 0:
            return self.quiescence(board, -evaluation.Score.CHECKMATE.value, evaluation.Score.CHECKMATE.value)

        # Null-move pruning.
        if depth >= 3 and hasattr(board, "push_null") and not board.is_check():
            board.push_null()
            null_score = -self.bound(board, 1 - gamma, depth - 2)
            board.pop_null()
            if null_score >= gamma:
                return null_score

        key = str(get_zobrist_key(board)) + f":{depth}"
        entry = self.tp_score.get(key, Entry(-evaluation.Score.CHECKMATE.value, evaluation.Score.CHECKMATE.value))
        if entry.lower >= gamma:
            return entry.lower
        if entry.upper < gamma:
            return entry.upper

        moves = list(board.generate_legal_moves())
        if not moves:
            return -evaluation.Score.CHECKMATE.value // 2
        if has_immediate_king_capture(board, moves):
            return evaluation.Score.CHECKMATE.value

        # Move ordering: incorporate base score, killer moves, and history heuristic.
        moves.sort(key=lambda m: self.move_ordering_score(board, m, depth), reverse=True)

        best = -evaluation.Score.CHECKMATE.value
        for i, move in enumerate(moves):
            # Late Move Reductions (LMR): reduce depth for moves beyond the first two that aren't captures.
            reduction = 1 if i >= 2 and depth >= 3 and not is_capture(board, move) else 0

            # Search Extensions for major threats.
            extension = 0
            if hasattr(board, "gives_check") and board.gives_check(move):
                extension = 1
            elif is_capture(board, move):
                captured = board.piece_at(move.to_square)
                if captured and captured.piece_type in (chess.QUEEN, chess.ROOK):
                    extension = 1

            board.push(move)
            score = -self.bound(board, 1 - gamma, depth - 1 - reduction + extension)
            board.pop()

            if score > best:
                best = score
            if best >= gamma:
                # Update killer moves and history heuristics.
                self.killer_moves.setdefault(depth, []).append(move)
                self.history_table[move] = self.history_table.get(move, 0) + depth * depth
                self.tp_move[get_zobrist_key(board)] = move
                break

        if best >= gamma:
            self.tp_score[key] = Entry(best, entry.upper)
        else:
            self.tp_score[key] = Entry(entry.lower, best)
        return best

    def get_principal_variation(self, board, max_length=10):
        pv = []
        local_board = board.copy()
        while True:
            key = get_zobrist_key(local_board)
            if key not in self.tp_move:
                break
            move = self.tp_move[key]
            pv.append(move)
            local_board.push(move)
            if len(pv) >= max_length:
                break
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
            best_move_found = self.tp_move.get(get_zobrist_key(self.search_board), None)
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