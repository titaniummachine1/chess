"""
Zobrist hashing implementation for chess positions.
Provides efficient position hashing for transposition tables.
"""
import chess
import random

class ZobristHasher:
    """
    Class to compute Zobrist hash values for chess positions.
    Uses precomputed random numbers to represent each piece at each square.
    """
    def __init__(self, seed=42):
        # Set random seed for reproducibility
        random.seed(seed)
        self.piece_square = {}  # (piece_type, color, square) -> random number
        self.side_to_move = random.getrandbits(64)  # Random number for black to move
        self.castling = {}     # Castling rights changes
        self.en_passant = {}   # En passant target square keys
        
        # Initialize piece-square random values
        for piece_type in range(1, 7):  # PAWN=1, ..., KING=6
            for color in [chess.WHITE, chess.BLACK]:
                for square in range(64):
                    self.piece_square[(piece_type, color, square)] = random.getrandbits(64)
        
        # Initialize castling right random values
        for white_king in [True, False]:
            for white_queen in [True, False]:
                for black_king in [True, False]:
                    for black_queen in [True, False]:
                        self.castling[(white_king, white_queen, black_king, black_queen)] = random.getrandbits(64)
        
        # Initialize en passant random values (only for files, not the whole square)
        for file in range(8):
            self.en_passant[file] = random.getrandbits(64)
    
    def compute_hash(self, board):
        """
        Compute the Zobrist hash for the current board position.
        """
        h = 0
        
        # Hash pieces
        for square, piece in board.piece_map().items():
            h ^= self.piece_square[(piece.piece_type, piece.color, square)]
        
        # Hash side to move
        if board.turn == chess.BLACK:
            h ^= self.side_to_move
        
        # Hash castling rights
        castling_key = (
            bool(board.castling_rights & chess.BB_H1),  # White kingside
            bool(board.castling_rights & chess.BB_A1),  # White queenside
            bool(board.castling_rights & chess.BB_H8),  # Black kingside
            bool(board.castling_rights & chess.BB_A8),  # Black queenside
        )
        h ^= self.castling[castling_key]
        
        # Hash en passant
        if board.ep_square is not None:
            file = chess.square_file(board.ep_square)
            h ^= self.en_passant[file]
        
        return h

    def update_hash_after_move(self, board, move, old_hash):
        """
        Incrementally update the hash after a move, which is more efficient
        than recomputing the entire hash.
        """
        h = old_hash
        
        # Toggle side to move
        h ^= self.side_to_move
        
        from_square = move.from_square
        to_square = move.to_square
        piece = board.piece_at(to_square)  # Piece that moved
        capture = board.piece_at(to_square)  # Captured piece, if any
        
        if piece:
            # Remove piece from old square
            h ^= self.piece_square[(piece.piece_type, piece.color, from_square)]
            # Add piece to new square
            h ^= self.piece_square[(piece.piece_type, piece.color, to_square)]
        
        if capture and capture != piece:  # Don't double count on self-captures
            # Remove captured piece
            h ^= self.piece_square[(capture.piece_type, capture.color, to_square)]
        
        # Update hash if castling rights changed
        old_castling_key = (
            bool(board.castling_rights & chess.BB_H1),
            bool(board.castling_rights & chess.BB_A1),
            bool(board.castling_rights & chess.BB_H8),
            bool(board.castling_rights & chess.BB_A8),
        )
        
        # Simulate the move to get new castling rights
        board.push(move)
        new_castling_key = (
            bool(board.castling_rights & chess.BB_H1),
            bool(board.castling_rights & chess.BB_A1),
            bool(board.castling_rights & chess.BB_H8),
            bool(board.castling_rights & chess.BB_A8),
        )
        board.pop()
        
        if old_castling_key != new_castling_key:
            h ^= self.castling[old_castling_key]
            h ^= self.castling[new_castling_key]
        
        # Update hash if en passant changed
        old_ep = board.ep_square
        
        # Predict if move creates a new en passant opportunity
        new_ep = None
        if piece and piece.piece_type == chess.PAWN:
            if abs(to_square - from_square) == 16:  # Double pawn push
                if piece.color == chess.WHITE:
                    new_ep = to_square - 8
                else:
                    new_ep = to_square + 8
        
        if old_ep is not None:
            h ^= self.en_passant[chess.square_file(old_ep)]
        if new_ep is not None:
            h ^= self.en_passant[chess.square_file(new_ep)]
        
        return h


# Create a global instance for use throughout the engine
ZOBRIST_HASHER = ZobristHasher()
