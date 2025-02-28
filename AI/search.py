import numpy as np
import chess
from GameState.movegen import DrawbackBoard
import AI.evaluation as evaluation
from collections import namedtuple
import random

# Set to True to see verbose debug output including principal variation.
DEBUG = False

###############################################################################
# Zobrist Hashing
###############################################################################
# Global Zobrist table: maps (square, piece_symbol) -> 64-bit random integer.
ZOBRIST_TABLE = {}

def compute_zobrist_key(board):
    key = 0
    # board.piece_map() should return a dict: square -> piece.
    for square, piece in board.piece_map().items():
        # Use piece.symbol() if available; else fallback to str(piece)
        symbol = piece.symbol() if hasattr(piece, "symbol") else str(piece)
        if (square, symbol) not in ZOBRIST_TABLE:
            ZOBRIST_TABLE[(square, symbol)] = random.getrandbits(64)
        key ^= ZOBRIST_TABLE[(square, symbol)]
    return key

def get_transposition_key(board):
    """
    Returns a Zobrist hash key for the board.
    If the board already provides a 'zobrist_key' attribute, use it.
    Otherwise, compute it from the piece map.
    """
    if hasattr(board, "zobrist_key"):
        return board.zobrist_key
    return compute_zobrist_key(board)

###############################################################################
# Evaluation & Move Helpers
###############################################################################

def eval_board(board):
    """
    Uses incremental evaluation if available; otherwise, calls the full evaluation.
    """
    if hasattr(board, "incremental_evaluate"):
        return board.incremental_evaluate()
    return evaluation.evaluate(board)

def score_move(board, move):
    """
    Basic heuristic for move ordering:
      - King captures get highest priority.
      - Other captures use MVV-LVA.
      - Non-captures score 0.
    """
    captured_piece = board.piece_at(move.to_square)
    if captured_piece:
        if captured_piece.piece_type == chess.KING:
            return 1000000
        attacker = board.piece_at(move.from_square)
        victim_value = evaluation.get_piece_value(board, captured_piece.piece_type, captured_piece.color)
        attacker_value = evaluation.get_piece_value(board, attacker.piece_type, attacker.color)
        return victim_value * 10 - attacker_value
    return 0

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

    def move_ordering_score(self, board, move, depth):
        base = score_move(board, move)
        killer_bonus = 5000 if move in self.killer_moves.get(depth, []) else 0
        history_bonus = self.history_table.get(move, 0)
        return base + killer_bonus + history_bonus

    def quiescence(self, board, alpha, beta):
        stand_pat = eval_board(board)
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
        if depth >= 3 and hasattr(board, "push_null") and not board.is_check():
            board.push_null()
            null_score = -self.bound(board, 1 - gamma, depth - 2)
            board.pop_null()
            if null_score >= gamma:
                return null_score

        key = str(get_transposition_key(board)) + f":{depth}"
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
                self.tp_move[get_transposition_key(board)] = move
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
        best_move_found = None
        prev_score = 0
        ASPIRATION_WINDOW = 50
        # Iterative deepening with aspiration windows.
        for depth in range(1, max_depth + 1):
            gamma = prev_score
            lower = gamma - ASPIRATION_WINDOW
            upper = gamma + ASPIRATION_WINDOW
            while True:
                score = self.bound(board, gamma, depth)
                if score < lower:
                    gamma = score
                    lower = gamma - ASPIRATION_WINDOW
                elif score > upper:
                    gamma = score
                    upper = gamma + ASPIRATION_WINDOW
                else:
                    break
            prev_score = score
            best_move_found = self.tp_move.get(get_transposition_key(board), None)
            pv = self.get_principal_variation(board)
            if DEBUG:
                print(f"[DEBUG] Depth: {depth}, Score: {score}, Best move: {best_move_found}, PV: {pv}")
            else:
                print(f"Depth: {depth}, Score: {score}, Best move: {best_move_found}, PV: {pv}")
        return best_move_found

def best_move(board, depth) -> int:
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
