import numpy as np
import chess
from GameState.movegen import DrawbackBoard
import AI.evaluation as evaluation
from collections import namedtuple

# Debug flag for verbose output; set to True to see PV details.
DEBUG = False

###############################################################################
# Helper Functions (Modular, Replaceable)
###############################################################################

def get_transposition_key(board):
    """
    Returns a key for the transposition table.
    Checks for a dedicated Zobrist hash if available, otherwise falls back.
    """
    if hasattr(board, "zobrist_key"):
        return board.zobrist_key
    return board.transposition_key() if hasattr(board, "transposition_key") else board.fen()

def eval_board(board):
    """
    Evaluates the board.
    If the board supports incremental evaluation, that method is used; otherwise,
    the standard evaluation function is called.
    """
    if hasattr(board, "incremental_evaluate"):
        return board.incremental_evaluate()
    return evaluation.evaluate(board)

def score_move(board, move):
    """
    Heuristic for move ordering:
      1. King captures are highest priority.
      2. Other captures use MVV-LVA.
      3. Non-captures get a base score of 0.
    """
    captured_piece = board.piece_at(move.to_square)
    if captured_piece:
        if captured_piece.piece_type == chess.KING:
            return 1000000  # Maximum score for king capture
        attacker = board.piece_at(move.from_square)
        victim_value = evaluation.get_piece_value(board, captured_piece.piece_type, captured_piece.color)
        attacker_value = evaluation.get_piece_value(board, attacker.piece_type, attacker.color)
        return victim_value * 10 - attacker_value
    return 0

def has_immediate_king_capture(board, moves):
    """
    Returns True if any move in moves captures a king.
    """
    for move in moves:
        captured = board.piece_at(move.to_square)
        if captured and captured.piece_type == chess.KING:
            return True
    return False

def is_game_over(board):
    """
    Checks if either king is missing.
    """
    pieces = board.piece_map().values()
    white_alive = any(p.piece_type == chess.KING and p.color == chess.WHITE for p in pieces)
    black_alive = any(p.piece_type == chess.KING and p.color == chess.BLACK for p in pieces)
    if not white_alive:
        return -evaluation.Score.CHECKMATE.value  # Black wins
    if not black_alive:
        return evaluation.Score.CHECKMATE.value   # White wins
    return None

def is_capture(board, move):
    """
    Returns True if the move is a capture (including en passant, if applicable).
    """
    return board.piece_at(move.to_square) is not None

###############################################################################
# Updated Search Methods: Sunfish-Style Iterative Deepening (MTD-bi) with PV & LMR
###############################################################################

# Constants analogous to Sunfish's values.
MATE_UPPER = evaluation.Score.CHECKMATE.value
MATE_LOWER = evaluation.Score.CHECKMATE.value  # (Assuming mate scores are symmetric)
QS = 40       # Quiescence threshold value
QS_A = 140    # Adjustment factor for quiescence pruning
EVAL_ROUGHNESS = 15  # Tolerance for iterative deepening convergence

# Transposition table entry.
Entry = namedtuple("Entry", "lower upper")

class Searcher:
    def __init__(self, use_incremental_eval=False):
        # Local transposition table: key = get_transposition_key(board) + ":" + depth
        self.tp_score = {}
        # Cache best moves: key = board's transposition key, value = best move found
        self.tp_move = {}
        self.nodes = 0
        self.use_incremental_eval = use_incremental_eval

    def bound(self, board, gamma, depth):
        """
        Recursively search for a bound on board's score.
        Returns a score r such that:
          if r < gamma then r is an upper bound,
          if r >= gamma then r is a lower bound.
        Incorporates LMR: for moves after the first two that are not captures, 
        the search depth is reduced by 1.
        """
        self.nodes += 1

        # Terminal check: if a king is missing or evaluation stops the search.
        result = is_game_over(board)
        if result is not None:
            return result
        if depth == 0:
            return eval_board(board)

        key = get_transposition_key(board) + f":{depth}"
        entry = self.tp_score.get(key, Entry(-MATE_UPPER, MATE_UPPER))
        if entry.lower >= gamma:
            return entry.lower
        if entry.upper < gamma:
            return entry.upper

        moves = list(board.generate_legal_moves())
        if not moves:
            return -evaluation.Score.CHECKMATE.value // 2

        # Early exit: if any move can capture the king.
        if has_immediate_king_capture(board, moves):
            return evaluation.Score.CHECKMATE.value

        # Order moves for better pruning.
        moves.sort(key=lambda m: score_move(board, m), reverse=True)

        best = -MATE_UPPER
        for i, move in enumerate(moves):
            # Apply Late Move Reductions (LMR):
            reduction = 0
            # For moves beyond the first two, if not a capture and depth is sufficient,
            # reduce depth by 1.
            if i >= 2 and depth >= 3 and not is_capture(board, move):
                reduction = 1

            board.push(move)
            score = -self.bound(board, 1 - gamma, depth - 1 - reduction)
            board.pop()

            best = max(best, score)
            if best >= gamma:
                # Cache the move that caused the beta-cutoff.
                self.tp_move[get_transposition_key(board)] = move
                break

        if best >= gamma:
            self.tp_score[key] = Entry(best, entry.upper)
        else:
            self.tp_score[key] = Entry(entry.lower, best)
        return best

    def get_principal_variation(self, board, max_length=10):
        """
        Reconstructs the principal variation (PV) from cached best moves.
        Returns a list of moves representing the PV.
        """
        pv = []
        local_board = board.copy()
        while True:
            key = get_transposition_key(local_board)
            if key not in self.tp_move:
                break
            move = self.tp_move[key]
            pv.append(move)
            local_board.push(move)
            if len(pv) >= max_length:
                break
        return pv

    def search(self, board, max_depth=4):
        """
        Iterative deepening MTD-bi search with principal variation.
        Yields a tuple (depth, gamma, score, best_move, principal_variation)
        for each depth iteration. Returns the best move found.
        """
        best_move_found = None
        gamma = 0
        for depth in range(1, max_depth + 1):
            lower, upper = -MATE_UPPER, MATE_UPPER
            while lower < upper - EVAL_ROUGHNESS:
                score = self.bound(board, gamma, depth)
                if score >= gamma:
                    lower = score
                else:
                    upper = score
                gamma = (lower + upper + 1) // 2
            best_move_found = self.tp_move.get(get_transposition_key(board), None)
            pv = self.get_principal_variation(board)
            if DEBUG:
                print(f"[DEBUG] Depth: {depth}, Score: {lower}, Best move: {best_move_found}, PV: {pv}")
            else:
                print(f"Depth: {depth}, Score: {lower}, Best move: {best_move_found}, PV: {pv}")
        return best_move_found

def best_move(board, depth) -> int:
    """
    Determines the best move using the updated Searcher (MTD-bi iterative deepening),
    with principal variation extraction and late move reductions.
    """
    searcher = Searcher()
    move = searcher.search(board, max_depth=depth)
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
