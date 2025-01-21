# game_state.py

import numpy as np
from bitboard import Bitboard
from GameState.constants import Color, Piece

# Import all the helpers from our separate file
from GameState.state_helpers import (
    MoveRecord, identify_piece_on_square, find_capture_target,
    clear_piece_bit, set_piece_bit, restore_rook_after_castle,
    update_castling_rights_on_move, update_castling_rights_on_capture
)

class GameState:
    """Manages the chess game state using bitboards for efficiency, with make/undo move logic."""
    
    def __init__(self, fen=None):
        self.pieces = np.zeros((2, 6), dtype=np.uint64)  # [Color][Piece]
        self.combined_color = np.zeros(2, dtype=np.uint64)
        self.combined_all = np.uint64(0)

        self.current_turn = Color.WHITE
        self.castling_rights = {'K': True, 'Q': True, 'k': True, 'q': True}
        self.en_passant_sq = -1

        self.move_log = []  # Stack of MoveRecord for undo
        self.board_ui = [['--' for _ in range(8)] for _ in range(8)]

        fen_to_load = fen if fen else self.default_fen()
        self.load_fen(fen_to_load)


    def load_fen(self, fen):
        """
        Initialize from a FEN string. Currently only reads piece placement and side to move.
        Extended fields (castling, halfmove clock, etc.) can be parsed if needed.
        """
        parts = fen.split()
        board_part, side_part = parts[0], parts[1]

        # Clear everything
        self.pieces.fill(0)
        self.combined_color.fill(0)
        self.combined_all = 0
        self.en_passant_sq = -1
        self.move_log.clear()

        piece_map = {
            'P': (Color.WHITE, Piece.PAWN),   'p': (Color.BLACK, Piece.PAWN),
            'N': (Color.WHITE, Piece.KNIGHT), 'n': (Color.BLACK, Piece.KNIGHT),
            'B': (Color.WHITE, Piece.BISHOP), 'b': (Color.BLACK, Piece.BISHOP),
            'R': (Color.WHITE, Piece.ROOK),   'r': (Color.BLACK, Piece.ROOK),
            'Q': (Color.WHITE, Piece.QUEEN),  'q': (Color.BLACK, Piece.QUEEN),
            'K': (Color.WHITE, Piece.KING),   'k': (Color.BLACK, Piece.KING),
        }

        rows = board_part.split('/')
        for rank_idx, row_data in enumerate(rows):
            col_idx = 0
            for char in row_data:
                if char.isdigit():
                    col_idx += int(char)
                else:
                    color, piece_type = piece_map[char]
                    square = self.get_square(7 - rank_idx, col_idx)
                    self.pieces[color][piece_type] = Bitboard.set_bit(
                        self.pieces[color][piece_type], square
                    )
                    col_idx += 1

        self.update_bitboards()
        self.current_turn = Color.WHITE if side_part == 'w' else Color.BLACK
        self.update_board_ui()

    def get_square(self, row, col):
        sq = row * 8 + col
        if not (0 <= sq < 64):
            raise ValueError(f"Invalid square -> row={row}, col={col}")
        return sq

    def get_piece_bb(self, piece, color=None):
        """Get bitboard of a specific piece type for a given color, or combined for both colors."""
        if color is None:
            return self.pieces[Color.WHITE][piece] | self.pieces[Color.BLACK][piece]
        return self.pieces[color][piece]

    def get_piece_at(self, row, col):
        """Return (color, piece_type) or None if empty."""
        square = self.get_square(row, col)
        for color in (Color.WHITE, Color.BLACK):
            for ptype in range(6):
                if Bitboard.get_bit(self.pieces[color][ptype], square):
                    return (color, ptype)
        return None

    def update_bitboards(self):
        self.combined_color[Color.WHITE] = 0
        self.combined_color[Color.BLACK] = 0
        for ptype in range(6):
            self.combined_color[Color.WHITE] |= self.pieces[Color.WHITE][ptype]
            self.combined_color[Color.BLACK] |= self.pieces[Color.BLACK][ptype]
        self.combined_all = self.combined_color[Color.WHITE] | self.combined_color[Color.BLACK]

    def update_board_ui(self):
        piece_fen_map = {
            (Color.WHITE, Piece.PAWN):   "wP",
            (Color.WHITE, Piece.KNIGHT): "wN",
            (Color.WHITE, Piece.BISHOP): "wB",
            (Color.WHITE, Piece.ROOK):   "wR",
            (Color.WHITE, Piece.QUEEN):  "wQ",
            (Color.WHITE, Piece.KING):   "wK",
            (Color.BLACK, Piece.PAWN):   "bP",
            (Color.BLACK, Piece.KNIGHT): "bN",
            (Color.BLACK, Piece.BISHOP): "bB",
            (Color.BLACK, Piece.ROOK):   "bR",
            (Color.BLACK, Piece.QUEEN):  "bQ",
            (Color.BLACK, Piece.KING):   "bK",
        }
        for r in range(8):
            for c in range(8):
                piece_data = self.get_piece_at(r, c)
                if piece_data:
                    self.board_ui[r][c] = piece_fen_map[piece_data]
                else:
                    self.board_ui[r][c] = "--"

    def default_fen(self):
        return "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

    # ----------------------------------------------------------------
    #  MAKE MOVE
    # ----------------------------------------------------------------
    def make_move(self, start_sq, end_sq, promotion_piece=None):
        """
        In-place: modifies self and logs the move in self.move_log for undo.
        """
        color_to_move = self.current_turn
        piece_moved = identify_piece_on_square(self, start_sq, color_to_move)
        if piece_moved is None:
            print(f"[DEBUG] No {color_to_move} piece at start_sq {start_sq}")
            return False

        # Normal capture detection
        piece_captured = find_capture_target(self, end_sq, color_to_move)

        # En passant detection
        was_en_passant = False
        if piece_moved == Piece.PAWN and piece_captured is None:
            if end_sq == self.en_passant_sq:
                was_en_passant = True
                # The captured pawn is actually behind the end_sq
                if color_to_move == Color.WHITE:
                    captured_pawn_sq = end_sq - 8
                else:
                    captured_pawn_sq = end_sq + 8
                piece_captured = identify_piece_on_square(self, captured_pawn_sq, ~color_to_move)
                # Remove that captured pawn right away
                if piece_captured is not None:
                    opp_color, opp_ptype = ~color_to_move, piece_captured
                    clear_piece_bit(self, captured_pawn_sq, opp_color, opp_ptype)

        # Castling detection
        was_castling = False
        rook_start_sq = -1
        rook_end_sq = -1
        if piece_moved == Piece.KING:
            if color_to_move == Color.WHITE:
                # e1 -> g1
                if start_sq == 4 and end_sq == 6:
                    was_castling = True
                    rook_start_sq = 7
                    rook_end_sq = 5
                # e1 -> c1
                elif start_sq == 4 and end_sq == 2:
                    was_castling = True
                    rook_start_sq = 0
                    rook_end_sq = 3
            else:
                # e8 -> g8
                if start_sq == 60 and end_sq == 62:
                    was_castling = True
                    rook_start_sq = 63
                    rook_end_sq = 61
                # e8 -> c8
                elif start_sq == 60 and end_sq == 58:
                    was_castling = True
                    rook_start_sq = 56
                    rook_end_sq = 59

        move_rec = MoveRecord(
            start_sq=start_sq,
            end_sq=end_sq,
            piece_moved=(color_to_move, piece_moved),
            piece_captured=piece_captured,
            was_en_passant=was_en_passant,
            en_passant_square_before=self.en_passant_sq,
            was_castling=was_castling,
            rook_start_sq=rook_start_sq,
            rook_end_sq=rook_end_sq,
            castling_rights_before=dict(self.castling_rights),
            current_turn_before=color_to_move
        )

        # 1) Remove the mover from start_sq
        clear_piece_bit(self, start_sq, color_to_move, piece_moved)
        # 2) If normal capture (not en passant), remove occupant from end_sq
        if piece_captured and not was_en_passant:
            opp_color, opp_ptype = piece_captured
            clear_piece_bit(self, end_sq, opp_color, opp_ptype)

        # 3) Place mover on end_sq
        set_piece_bit(self, end_sq, color_to_move, piece_moved)

        # 4) If castling, move rook
        if was_castling:
            clear_piece_bit(self, rook_start_sq, color_to_move, Piece.ROOK)
            set_piece_bit(self, rook_end_sq, color_to_move, Piece.ROOK)

        # 5) If the moved pawn advanced 2 squares, set en_passant_sq
        self.en_passant_sq = -1
        if piece_moved == Piece.PAWN:
            row_start = start_sq // 8
            row_end = end_sq // 8
            if abs(row_end - row_start) == 2:
                # The en_passant_sq is the square "behind" the pawn
                if color_to_move == Color.WHITE:
                    self.en_passant_sq = end_sq - 8
                else:
                    self.en_passant_sq = end_sq + 8

        # 6) Update castling rights on king/rook moves or rook capture
        update_castling_rights_on_move(self, start_sq, color_to_move, piece_moved)
        if piece_captured:
            update_castling_rights_on_capture(self, end_sq, piece_captured)

        # 7) If promotion is requested
        if piece_moved == Piece.PAWN and promotion_piece is not None:
            row_end = end_sq // 8
            if (color_to_move == Color.WHITE and row_end == 7) or \
               (color_to_move == Color.BLACK and row_end == 0):
                # Clear the pawn and set the new piece
                clear_piece_bit(self, end_sq, color_to_move, Piece.PAWN)
                set_piece_bit(self, end_sq, color_to_move, promotion_piece)
                move_rec.piece_moved = (color_to_move, promotion_piece)

        # Add to log, update boards, switch turn
        self.move_log.append(move_rec)
        self.update_bitboards()
        self.update_board_ui()
        self.current_turn = ~color_to_move
        return True


    def undo_move(self):
        if not self.move_log:
            print("[DEBUG] No move to undo.")
            return

        move_rec = self.move_log.pop()

        self.current_turn = move_rec.current_turn_before

        color_to_move, piece_moved = move_rec.piece_moved
        start_sq = move_rec.start_sq
        end_sq = move_rec.end_sq

        # 1) Move piece back from end_sq -> start_sq
        clear_piece_bit(self, end_sq, color_to_move, piece_moved)
        set_piece_bit(self, start_sq, color_to_move, piece_moved)

        # 2) Restore any captured piece
        if move_rec.piece_captured is not None:
            if move_rec.was_en_passant:
                if color_to_move == Color.WHITE:
                    captured_sq = end_sq - 8
                else:
                    captured_sq = end_sq + 8
                opp_color, opp_piece_type = move_rec.piece_captured
                set_piece_bit(self, captured_sq, opp_color, opp_piece_type)
            else:
                opp_color, opp_piece_type = move_rec.piece_captured
                set_piece_bit(self, end_sq, opp_color, opp_piece_type)

        # 3) If castling, move rook back
        if move_rec.was_castling:
            restore_rook_after_castle(self, move_rec.rook_start_sq, move_rec.rook_end_sq, color_to_move)

        # 4) Restore en_passant_sq
        self.en_passant_sq = move_rec.en_passant_square_before

        # 5) Restore castling rights
        self.castling_rights = dict(move_rec.castling_rights_before)

        # 6) Update boards/UI
        self.update_bitboards()
        self.update_board_ui()