import numpy as np
import chess
from AI import evaluation  # now evaluation handles both material & positional evaluation
from AI import piece_square_table as piece_square_table
from collections import namedtuple
import random

DEBUG = False

###############################################################################
# Zobrist Hashing
###############################################################################

# Global Zobrist table for pieces (square, symbol) -> 64-bit random integer.
ZOBRIST_TABLE = {}

# Precomputed random numbers for castling rights and en passant.
ZOBRIST_CASTLING = { right: random.getrandbits(64) for right in "KQkq" }
# For each of the 64 squares, a random number to be used if an en passant square exists.
ZOBRIST_EP_64 = [random.getrandbits(64) for _ in range(64)]

# Constants for turn: using fixed constants.
ZOBRIST_WHITE_TURN = 0xF0F0F0F0F0F0F0F0
ZOBRIST_BLACK_TURN = 0x0F0F0F0F0F0F0F0F

def compute_zobrist_key(board):
    key = 0
    # Incorporate pieces.
    for square, piece in board.piece_map().items():
        symbol = piece.symbol() if hasattr(piece, "symbol") else str(piece)
        if (square, symbol) not in ZOBRIST_TABLE:
            ZOBRIST_TABLE[(square, symbol)] = random.getrandbits(64)
        key ^= ZOBRIST_TABLE[(square, symbol)]
    # Incorporate turn.
    key ^= ZOBRIST_WHITE_TURN if board.turn == chess.WHITE else ZOBRIST_BLACK_TURN
    # Incorporate castling rights.
    # (Assuming board.castling_xfen() returns a string like "KQkq" or "-" if none.)
    castling = board.castling_xfen() if hasattr(board, "castling_xfen") else board.castling_xfen()
    for char in castling:
        if char in ZOBRIST_CASTLING:
            key ^= ZOBRIST_CASTLING[char]
    # Incorporate en passant square.
    if board.ep_square is not None:
        key ^= ZOBRIST_EP_64[board.ep_square]
    return key

def get_transposition_key(board):
    """
    Returns a Zobrist hash key for the board.
    If the board already has a 'zobrist_key' attribute, we assume it is up to date.
    Otherwise, compute the key from scratch.
    """
    if hasattr(board, "zobrist_key"):
        return board.zobrist_key
    return compute_zobrist_key(board)


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
    Uses incremental evaluation if available; otherwise, calls the full evaluation.
    Also includes piece-square table evaluation.
    """
    if hasattr(board, "incremental_evaluate"):
        return board.incremental_evaluate()
    
    # Base evaluation
    score = evaluation.evaluate(board)
    
    # Add piece-square table evaluation
    phase = piece_square_table.compute_game_phase(board)
    
    for square, piece in board.piece_map().items():
        piece_symbol = piece.symbol().upper()
        
        # Use the interpolation function from the piece_square_table module
        piece_square_value = piece_square_table.interpolate_piece_square(
            piece_symbol, square, piece.color, board
        )
        
        # Adjust the score based on piece color
        if piece.color == chess.WHITE:
            score += piece_square_value
        else:
            score -= piece_square_value
    
    return score

def score_move(board, move):
    """
    Enhanced move ordering:
    - If the move is a capture, use evaluation.get_capture_score.
    - Otherwise, use the positional improvement from evaluation.get_positional_improvement.
    Also add a bonus if the move attacks the last moved piece.
    """
    score = 0
    captured = board.piece_at(move.to_square)
    attacker = board.piece_at(move.from_square)
    if captured:
        score = evaluation.get_capture_score(board, attacker, captured)
    else:
        score = evaluation.get_positional_improvement(board, move)
    # Bonus for targeting last moved opponent piece (if available)
    if board.move_stack:
        last_move = board.move_stack[-1]
        if move.to_square == last_move.to_square:
            score += 300
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

    def quiescence(self, board, alpha, beta):
        stand_pat = evaluation.evaluate(board)
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

        key = str(evaluation.get_transposition_key(board)) + f":{depth}"
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
                self.tp_move[evaluation.get_transposition_key(board)] = move
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
            key = evaluation.get_transposition_key(local_board)
            if key not in self.tp_move:
                break
            move = self.tp_move[key]
            pv.append(move)
            local_board.push(move)
            if len(pv) >= max_length:
                break
        return pv

    def search(self, board, max_depth=4):
        # Create internal copy of the board for search operations
        self.search_board = board.copy()
        
        best_move_found = None
        prev_score = 0
        ASPIRATION_WINDOW = 50
        # Iterative deepening with aspiration windows.
        for depth in range(1, max_depth + 1):
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
            best_move_found = self.tp_move.get(evaluation.get_transposition_key(self.search_board), None)
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