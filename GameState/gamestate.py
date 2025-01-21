## gamestate.py ensure this is here this comment is important
import numpy as np
from bitboard import Bitboard
from GameState.constants import Color, Piece

class GameState:
    """Manages the chess game state using bitboards for efficiency."""

    def __init__(self, fen=None):
        """
        Initialize the game state from a FEN string or the default starting position.
        
        :param fen: Optional FEN string to set up the board. If not provided,
                    the default starting position is used.
        """
        self.pieces = np.zeros((2, 6), dtype=np.uint64)  # Bitboards for each piece type per color
        self.combined_color = np.zeros(2, dtype=np.uint64)  # Bitboards for white and black
        self.combined_all = np.uint64(0)  # Bitboard representing all pieces

        # Game metadata
        self.current_turn = Color.WHITE
        self.castling_rights = {'K': True, 'Q': True, 'k': True, 'q': True}
        self.en_passant_sq = None
        self.move_log = []
        
        # Textual board representation for UI or debugging
        self.board_ui = [['--' for _ in range(8)] for _ in range(8)]

        # Load position from FEN or use default
        self.load_fen(fen if fen else self.default_fen())

    def load_fen(self, fen):
        """
        Load the board state from a FEN string.
        
        :param fen: A valid FEN string describing the board state.
        """
        parts = fen.split()
        board_fen, turn = parts[0], parts[1]

        # Clear bitboards before loading new position
        self.pieces.fill(0)
        self.combined_color.fill(0)
        self.combined_all = 0

        # Map character symbols in FEN to (color, piece_type)
        piece_map = {
            'P': (Color.WHITE, Piece.PAWN),   'p': (Color.BLACK, Piece.PAWN),
            'N': (Color.WHITE, Piece.KNIGHT), 'n': (Color.BLACK, Piece.KNIGHT),
            'B': (Color.WHITE, Piece.BISHOP), 'b': (Color.BLACK, Piece.BISHOP),
            'R': (Color.WHITE, Piece.ROOK),   'r': (Color.BLACK, Piece.ROOK),
            'Q': (Color.WHITE, Piece.QUEEN),  'q': (Color.BLACK, Piece.QUEEN),
            'K': (Color.WHITE, Piece.KING),   'k': (Color.BLACK, Piece.KING),
        }

        rows = board_fen.split("/")
        for rank_idx, row_data in enumerate(rows):
            col_idx = 0
            for char in row_data:
                # If it's a digit, skip that many columns
                if char.isdigit():
                    col_idx += int(char)
                else:
                    color, piece_type = piece_map[char]
                    square = self.get_square(7 - rank_idx, col_idx)
                    self.pieces[color][piece_type] = Bitboard.set_bit(
                        self.pieces[color][piece_type], square
                    )
                    col_idx += 1

        # Refresh combined bitboards and set current turn
        self.update_bitboards()
        self.current_turn = Color.WHITE if turn == 'w' else Color.BLACK
        
        # Update the board UI array for easier visualization
        self.update_board_ui()

    def get_square(self, row, col):
        """
        Convert (row, col) indices into a 0-63 square index.
        
        :param row: Row on the board (0-based from the top).
        :param col: Column on the board (0-based from the left).
        :return: Integer representing the square index in 0..63.
        """
        sq = row * 8 + col
        if not (0 <= sq < 64):
            print(f"DEBUG: Invalid square requested -> row={row}, col={col}")
            raise ValueError(f"Invalid square -> row={row}, col={col}")
        return sq

    def get_piece_bb(self, piece, color=None):
        """
        Get bitboard of a specific piece type for a given color, or combined for both colors.
        
        :param piece: Piece type (e.g., Piece.PAWN).
        :param color: Color (Color.WHITE / Color.BLACK) or None for both.
        :return: Bitboard representing squares where the piece(s) reside.
        """
        if color is None:
            return self.pieces[Color.WHITE][piece] | self.pieces[Color.BLACK][piece]
        return self.pieces[color][piece]

    def get_piece_at(self, row, col):
        """
        Get piece information at a specific (row, col).
        
        :param row: Row on the board.
        :param col: Column on the board.
        :return: Tuple (color, piece_type) if there's a piece, or None if empty.
        """
        square = self.get_square(row, col)
        for color in (Color.WHITE, Color.BLACK):
            for piece_type in range(6):
                if Bitboard.get_bit(self.pieces[color][piece_type], square):
                    return (color, piece_type)
        return None

    def update_bitboards(self):
        """Update the combined_color and combined_all bitboards based on self.pieces."""
        self.combined_color[Color.WHITE] = sum(self.pieces[Color.WHITE])
        self.combined_color[Color.BLACK] = sum(self.pieces[Color.BLACK])
        self.combined_all = self.combined_color[Color.WHITE] | self.combined_color[Color.BLACK]

    def update_board_ui(self):
        """
        Update the board_ui array so each cell has a string like 'wP', 'bQ', or '--' for empty.
        """
        piece_fen_map = {
            (Color.WHITE, Piece.PAWN): "wP",
            (Color.WHITE, Piece.KNIGHT): "wN",
            (Color.WHITE, Piece.BISHOP): "wB",
            (Color.WHITE, Piece.ROOK): "wR",
            (Color.WHITE, Piece.QUEEN): "wQ",
            (Color.WHITE, Piece.KING): "wK",
            (Color.BLACK, Piece.PAWN): "bP",
            (Color.BLACK, Piece.KNIGHT): "bN",
            (Color.BLACK, Piece.BISHOP): "bB",
            (Color.BLACK, Piece.ROOK): "bR",
            (Color.BLACK, Piece.QUEEN): "bQ",
            (Color.BLACK, Piece.KING): "bK",
        }
        for r in range(8):
            for c in range(8):
                piece_data = self.get_piece_at(r, c)
                self.board_ui[r][c] = piece_fen_map.get(piece_data, "--") if piece_data else "--"

    def apply_move(self, move):
        """
        Apply a chess move to the board and return a new GameState.
        
        :param move: A tuple (start_sq, end_sq, promotion).
        :return: A new GameState object reflecting the move.
        """
        new_state = self.copy()

        start_sq, end_sq, promotion = move

        # Identify which piece is at the start square
        color_piece = new_state.get_piece_at(*Bitboard.from_square(start_sq))
        if not color_piece:
            print("DEBUG: No piece at start_sq -> invalid move")
            return new_state

        color, piece_type = color_piece

        # Capture or handle en passant if needed
        new_state._remove_occupant_if_any(end_sq, piece_type, color)
        # Move the piece on the bitboard
        new_state._move_piece(start_sq, end_sq, piece_type, color)
        # Handle promotions, castling, en passant
        new_state._handle_special_moves(start_sq, end_sq, piece_type, color, promotion)
        # Finalize (update bitboards, switch turn, etc.)
        new_state._finalize_move(move)

        return new_state

    def _remove_occupant_if_any(self, end_sq, piece_type, color):
        """
        Remove any occupant piece from the end square (typical capture),
        or handle en passant capture if relevant.
        """
        self.en_passant_sq = -1
        occupant_piece = self.get_piece_at(*Bitboard.from_square(end_sq))
        if occupant_piece:
            occ_color, occ_piece_type = occupant_piece
            self.pieces[occ_color][occ_piece_type] = Bitboard.clear_bit(
                self.pieces[occ_color][occ_piece_type], end_sq
            )
        else:  # Possibly en passant capture
            if piece_type == Piece.PAWN and end_sq == self.en_passant_sq:
                direction = 8 if color == Color.BLACK else -8
                captured_sq = end_sq + direction
                opp_color = ~color
                self.pieces[opp_color][Piece.PAWN] = Bitboard.clear_bit(
                    self.pieces[opp_color][Piece.PAWN], captured_sq
                )

    def _move_piece(self, start_sq, end_sq, piece_type, color):
        """
        Clear the piece's starting bit, then set the end bit,
        effectively moving the piece on its bitboard.
        """
        self.pieces[color][piece_type] = Bitboard.clear_bit(
            self.pieces[color][piece_type], start_sq
        )
        self.pieces[color][piece_type] = Bitboard.set_bit(
            self.pieces[color][piece_type], end_sq
        )

    def _handle_special_moves(self, start_sq, end_sq, piece_type, color, promotion):
        """
        Handle special move cases like double pawn advance (en passant),
        pawn promotion, and castling.
        """
        # Handle double pawn move (en passant possibility)
        if piece_type == Piece.PAWN:
            start_row = start_sq // 8
            end_row = end_sq // 8
            if abs(end_row - start_row) == 2:
                if color == Color.WHITE:
                    self.en_passant_sq = start_sq + 8
                else:
                    self.en_passant_sq = start_sq - 8

        # Pawn promotion
        if piece_type == Piece.PAWN:
            end_row = end_sq // 8
            if (color == Color.WHITE and end_row == 7) or (color == Color.BLACK and end_row == 0):
                promo_piece = promotion if promotion is not None else Piece.QUEEN
                self.pieces[color][Piece.PAWN] = Bitboard.clear_bit(
                    self.pieces[color][Piece.PAWN], end_sq
                )
                self.pieces[color][promo_piece] = Bitboard.set_bit(
                    self.pieces[color][promo_piece], end_sq
                )

        # Castling
        if piece_type == Piece.KING:
            if color == Color.WHITE:
                # King-side castle (e1 -> g1)
                if start_sq == 4 and end_sq == 6 and self.castling_rights['K']:
                    self.pieces[Color.WHITE][Piece.ROOK] = Bitboard.clear_bit(
                        self.pieces[Color.WHITE][Piece.ROOK], 7
                    )
                    self.pieces[Color.WHITE][Piece.ROOK] = Bitboard.set_bit(
                        self.pieces[Color.WHITE][Piece.ROOK], 5
                    )
                # Queen-side castle (e1 -> c1)
                elif start_sq == 4 and end_sq == 2 and self.castling_rights['Q']:
                    self.pieces[Color.WHITE][Piece.ROOK] = Bitboard.clear_bit(
                        self.pieces[Color.WHITE][Piece.ROOK], 0
                    )
                    self.pieces[Color.WHITE][Piece.ROOK] = Bitboard.set_bit(
                        self.pieces[Color.WHITE][Piece.ROOK], 3
                    )
                # Lose castling rights
                self.castling_rights['K'] = False
                self.castling_rights['Q'] = False
            else:
                # King-side castle (e8 -> g8)
                if start_sq == 60 and end_sq == 62 and self.castling_rights['k']:
                    self.pieces[Color.BLACK][Piece.ROOK] = Bitboard.clear_bit(
                        self.pieces[Color.BLACK][Piece.ROOK], 63
                    )
                    self.pieces[Color.BLACK][Piece.ROOK] = Bitboard.set_bit(
                        self.pieces[Color.BLACK][Piece.ROOK], 61
                    )
                # Queen-side castle (e8 -> c8)
                elif start_sq == 60 and end_sq == 58 and self.castling_rights['q']:
                    self.pieces[Color.BLACK][Piece.ROOK] = Bitboard.clear_bit(
                        self.pieces[Color.BLACK][Piece.ROOK], 56
                    )
                    self.pieces[Color.BLACK][Piece.ROOK] = Bitboard.set_bit(
                        self.pieces[Color.BLACK][Piece.ROOK], 59
                    )
                # Lose castling rights
                self.castling_rights['k'] = False
                self.castling_rights['q'] = False

        # If a rook moves, disable its side’s castling rights if necessary
        if piece_type == Piece.ROOK:
            print(piece_type)
            if color == Color.WHITE:
                if start_sq == 0:
                    print("DEBUG: lost castling right Q (WHITE)")
                    self.castling_rights['Q'] = False
                elif start_sq == 7:
                    print("DEBUG: lost castling right K (WHITE)")
                    self.castling_rights['K'] = False
            else:
                if start_sq == 56:
                    print("DEBUG: lost castling right q (BLACK)")
                    self.castling_rights['q'] = False
                elif start_sq == 63:
                    print("DEBUG: lost castling right k (BLACK)")
                    self.castling_rights['k'] = False

    def _finalize_move(self, move):
        """
        Update state after a move: refresh bitboards, update UI, switch turn, 
        and append move to move log.
        """
        self.update_bitboards()
        self.update_board_ui()
        self.current_turn = ~self.current_turn
        self.move_log.append(move)

    def copy(self):
        """
        Create a deep copy of the GameState (except for any external references).
        
        :return: A new GameState object with the same data.
        """
        new_state = GameState.__new__(GameState)

        new_state.pieces = np.copy(self.pieces)
        new_state.combined_color = np.copy(self.combined_color)
        new_state.combined_all = np.uint64(self.combined_all)

        new_state.current_turn = self.current_turn
        new_state.move_log = self.move_log[:]
        new_state.board_ui = [row[:] for row in self.board_ui]
        new_state.castling_rights = dict(self.castling_rights)
        new_state.en_passant_sq = self.en_passant_sq

        return new_state

    def default_fen(self):
        """
        :return: The standard chess starting position in FEN notation.
        """
        return "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
