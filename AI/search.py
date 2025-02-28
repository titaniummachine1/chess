import numpy as np
import chess
import random
from GameState.movegen import DrawbackBoard
import AI.evaluation as evaluation
from collections import namedtuple
from AI.piece_square_table import PIECE_VALUES, interpolate_piece_square, compute_game_phase

DEBUG = False

# Zobrist Hashing
ZOBRIST_TABLE = {}
ZOBRIST_CASTLING = {right: random.getrandbits(64) for right in "KQkq"}
ZOBRIST_EP_64 = [random.getrandbits(64) for _ in range(64)]
ZOBRIST_WHITE_TURN = random.getrandbits(64)
ZOBRIST_BLACK_TURN = random.getrandbits(64)

def compute_zobrist_key(board):
    key = 0
    for square, piece in board.piece_map().items():
        symbol = piece.symbol()
        if (square, symbol) not in ZOBRIST_TABLE:
            ZOBRIST_TABLE[(square, symbol)] = random.getrandbits(64)
        key ^= ZOBRIST_TABLE[(square, symbol)]
    
    key ^= ZOBRIST_WHITE_TURN if board.turn == chess.WHITE else ZOBRIST_BLACK_TURN
    castling = board.castling_xfen()
    for char in castling:
        if char in ZOBRIST_CASTLING:
            key ^= ZOBRIST_CASTLING[char]
    
    if board.ep_square is not None:
        key ^= ZOBRIST_EP_64[board.ep_square]
    
    return key

def get_transposition_key(board):
    return compute_zobrist_key(board)

# Evaluation & Move Helpers
def eval_board(board):
    return evaluation.evaluate(board)

def get_piece_value_full(board, piece_type, color, square):
    symbol = chess.piece_symbol(piece_type).upper()
    base_tuple = PIECE_VALUES.get(symbol, (0, 0))
    phase = compute_game_phase(board)
    base_value = base_tuple[0] * phase + base_tuple[1] * (1 - phase)
    bonus = interpolate_piece_square(symbol, square, color, board)
    return base_value + bonus

def score_move(board, move):
    if board.is_capture(move):
        captured = board.piece_at(move.to_square)
        attacker = board.piece_at(move.from_square)
        
        if captured.piece_type == chess.KING:
            return 1000000
        
        victim_val = get_piece_value_full(board, captured.piece_type, captured.color, move.to_square)
        aggressor_val = get_piece_value_full(board, attacker.piece_type, attacker.color, move.from_square)
        return (victim_val - aggressor_val) * 100  # MVV-LVA ordering
        
    if board.gives_check(move):
        return 5000
        
    return 0

# Search Enhancements
Entry = namedtuple("Entry", "lower upper")

class Searcher:
    def __init__(self):
        self.tp_score = {}  # (zobrist_key, depth): Entry
        self.tp_move = {}   # zobrist_key: move
        self.nodes = 0
        self.killer_moves = {}  # depth: [move1, move2]
        self.history_table = {} # (from_sq, to_sq): score

    def quiescence(self, board, alpha, beta):
        stand_pat = eval_board(board)
        if stand_pat >= beta:
            return beta
        alpha = max(alpha, stand_pat)
        
        for move in sorted(board.generate_legal_captures(), 
                         key=lambda m: -score_move(board, m)):
            board.push(move)
            score = -self.quiescence(board, -beta, -alpha)
            board.pop()
            
            if score >= beta:
                return beta
            if score > alpha:
                alpha = score
        
        return alpha

    def alphabeta(self, board, depth, alpha, beta):
        self.nodes += 1
        original_alpha = alpha
        
        # Check transposition table
        key = (get_transposition_key(board), depth)
        if key in self.tp_score:
            entry = self.tp_score[key]
            if entry.lower >= beta:
                return entry.lower
            if entry.upper <= alpha:
                return entry.upper
            alpha = max(alpha, entry.lower)
            beta = min(beta, entry.upper)
        
        # Terminal node checks
        if board.is_checkmate():
            return -evaluation.Score.CHECKMATE.value
        if depth == 0:
            return self.quiescence(board, alpha, beta)
        
        # Null move pruning
        if depth >= 3 and not board.is_check():
            board.push(chess.Move.null())
            score = -self.alphabeta(board, depth-3, -beta, -beta+1)
            board.pop()
            if score >= beta:
                return beta
        
        moves = list(board.legal_moves)
        moves.sort(key=lambda m: (
            self.tp_move.get(get_transposition_key(board)) == m,
            board.is_capture(m),
            self.killer_moves.get(depth, {}).get(m, 0),
            self.history_table.get((m.from_square, m.to_square), 0),
            score_move(board, m)
        ), reverse=True)
        
        best_value = -np.inf
        best_move = None
        
        for move in moves:
            board.push(move)
            score = -self.alphabeta(board, depth-1, -beta, -alpha)
            board.pop()
            
            if score >= beta:
                self._update_killers(depth, move)
                self.tp_score[key] = Entry(score, score)
                return score
                
            if score > best_value:
                best_value = score
                best_move = move
                alpha = max(alpha, score)
        
        # Store in transposition table
        if best_value <= original_alpha:
            self.tp_score[key] = Entry(-np.inf, best_value)
        elif best_value >= beta:
            self.tp_score[key] = Entry(best_value, np.inf)
        else:
            self.tp_score[key] = Entry(best_value, best_value)
        
        if best_move:
            self.tp_move[get_transposition_key(board)] = best_move
        
        return best_value

    def _update_killers(self, depth, move):
        killers = self.killer_moves.get(depth, [])
        if move not in killers:
            killers = [move] + killers[:1]
            self.killer_moves[depth] = killers
        self.history_table[(move.from_square, move.to_square)] = \
            self.history_table.get((move.from_square, move.to_square), 0) + 2**depth

    def search(self, board, max_depth=4):
        best_move = None
        aspiration_window = 50
        alpha = -np.inf
        beta = np.inf
        
        for depth in range(1, max_depth+1):
            try:
                score = self.alphabeta(board, depth, alpha, beta)
                
                if score <= alpha:
                    alpha = -np.inf
                elif score >= beta:
                    beta = np.inf
                else:
                    aspiration_window *= 2
                    alpha = score - aspiration_window
                    beta = score + aspiration_window
                
                best_move = self.tp_move.get(get_transposition_key(board))
                if DEBUG:
                    pv = self.get_pv(board)
                    print(f"Depth {depth}: {score} {best_move} PV: {pv}")
                    
            except Exception as e:
                if DEBUG:
                    print(f"Search error at depth {depth}: {e}")
                break
        
        return best_move or next(iter(board.legal_moves)), score

    def get_pv(self, board):
        pv = []
        current_board = board.copy()
        for _ in range(10):
            key = get_transposition_key(current_board)
            if key not in self.tp_move:
                break
            move = self.tp_move[key]
            pv.append(move)
            current_board.push(move)
        return pv

def best_move(board, depth=4):
    searcher = Searcher()
    best_move = searcher.search(board.copy(), depth)[0]
    return best_move