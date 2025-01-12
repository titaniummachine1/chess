# AI/ZobristHashing.py

import random

class ZobristHashing:
    def __init__(self):
        self.zobrist_table = {}
        pieces = ['wP', 'wN', 'wB', 'wR', 'wQ', 'wK',
                  'bP', 'bN', 'bB', 'bR', 'bQ', 'bK']
        for piece in pieces:
            for square in range(64):
                self.zobrist_table[(piece, square)] = random.getrandbits(64)
        # Castling rights: K, Q, k, q
        self.castling_rights = {
            'K': random.getrandbits(64),
            'Q': random.getrandbits(64),
            'k': random.getrandbits(64),
            'q': random.getrandbits(64)
        }
        # En passant file (0-7), or -1 if none
        for file in range(8):
            self.zobrist_table[('ep', file)] = random.getrandbits(64)
        # Side to move
        self.zobrist_table['side'] = random.getrandbits(64)
    
    def compute_hash(self, board, white_to_move):
        h = 0
        for square in range(64):
            piece = board[square // 8][square % 8]
            if piece != '--':
                h ^= self.zobrist_table[(piece, square)]
        # Side to move
        if white_to_move:
            h ^= self.zobrist_table['side']
        return h
