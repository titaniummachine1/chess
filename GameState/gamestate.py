# game_state.py

import numpy as np
from bitboard import Bitboard
from GameState.constants import Color, Piece

# Import the helpers
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
        # board_ui[r][c], but r=0 is rank1, r=7 is rank8 if you “draw” directly
        # you might need to flip when displaying in the GUI
        self.board_ui = [['--' for _ in range(8)] for _ in range(8)]

        fen_to_load = fen if fen else self.default_fen()
        self.load_fen(fen_to_load)


    def load_fen(self, fen):
        """
        Parse a FEN string, which goes rank8..rank1.
        We'll invert it to store rank8 in row=7 and rank1 in row=0,
        so that a1=0, h1=7, a8=56, h8=63.
        """
        parts = fen.split()
        board_part, side_part = parts[0], parts[1]

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
        # FEN row 0 is "8th rank", which should be game_state row=7
        # FEN row 7 is "1st rank", which should be game_state row=0
        for fen_rank, row_data in enumerate(rows):
            rank = 7 - fen_rank  # invert
            col = 0
            for char in row_data:
                if char.isdigit():
                    col += int(char)
                else:
                    color, piece_type = piece_map[char]
                    square = rank * 8 + col
                    self.pieces[color][piece_type] = Bitboard.set_bit(
                        self.pieces[color][piece_type], square
                    )
                    col += 1

        self.update_bitboards()
        self.current_turn = Color.WHITE if side_part == 'w' else Color.BLACK
        self.update_board_ui()

    def get_square(self, row, col):
        """
        row=0 -> rank1, row=7 -> rank8
        col=0 -> file A, col=7 -> file H
        square index = row*8 + col
        """
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
        """
        Return (color, piece_type) or None if empty.
        row=0..7 from White’s side to Black’s side
        col=0..7 from A..H
        """
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
        # standard start, white at row=0 => a1=0..h1=7, black at row=7 => a8=56..h8=63
        return "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

    # ---------------------------------------------------------------
    # MAKE MOVE
    # ---------------------------------------------------------------
    def make_move(self, start_sq, end_sq, promotion_piece=None):
        color_to_move = self.current_turn
        piece_moved = identify_piece_on_square(self, start_sq, color_to_move)
        if piece_moved is None:
            print(f"[DEBUG] No {color_to_move} piece at start_sq {start_sq}")
            return False

        piece_captured = find_capture_target(self, end_sq, color_to_move)

        was_en_passant = False
        if piece_moved == Piece.PAWN and piece_captured is None:
            # Possibly en passant if end_sq == self.en_passant_sq
            if end_sq == self.en_passant_sq:
                was_en_passant = True
                # The captured pawn is behind the end_sq
                if color_to_move == Color.WHITE:
                    captured_sq = end_sq - 8
                else:
                    captured_sq = end_sq + 8
                cptype = identify_piece_on_square(self, captured_sq, ~color_to_move)
                if cptype is not None:
                    clear_piece_bit(self, captured_sq, ~color_to_move, cptype)
                # now piece_captured = (opp_color, cptype)
                piece_captured = (~color_to_move, cptype) if cptype is not None else None

        was_castling = False
        rook_start_sq = -1
        rook_end_sq = -1
        if piece_moved == Piece.KING:
            # White king on e1=4
            if color_to_move == Color.WHITE:
                # e1->g1 = 4->6 => rook h1=7->f1=5
                if start_sq == 4 and end_sq == 6:
                    was_castling = True
                    rook_start_sq = 7
                    rook_end_sq = 5
                # e1->c1 = 4->2 => rook a1=0->d1=3
                elif start_sq == 4 and end_sq == 2:
                    was_castling = True
                    rook_start_sq = 0
                    rook_end_sq = 3
            else:
                # Black king on e8=60
                # e8->g8 = 60->62 => rook h8=63->f8=61
                if start_sq == 60 and end_sq == 62:
                    was_castling = True
                    rook_start_sq = 63
                    rook_end_sq = 61
                # e8->c8 = 60->58 => rook a8=56->d8=59
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

        # 1) Remove piece from start_sq
        clear_piece_bit(self, start_sq, color_to_move, piece_moved)

        # 2) Normal capture if any occupant at end_sq
        if piece_captured and not was_en_passant:
            opp_color, opp_ptype = piece_captured
            clear_piece_bit(self, end_sq, opp_color, opp_ptype)

        # 3) Place mover on end_sq
        set_piece_bit(self, end_sq, color_to_move, piece_moved)

        # 4) If castling, move rook
        if was_castling:
            clear_piece_bit(self, rook_start_sq, color_to_move, Piece.ROOK)
            set_piece_bit(self, rook_end_sq, color_to_move, Piece.ROOK)

        # 5) If a pawn advanced 2 squares, set en_passant_sq
        self.en_passant_sq = -1
        if piece_moved == Piece.PAWN:
            row_start = start_sq // 8
            row_end = end_sq // 8
            # white pawns move up => row_start=1 => row_end=3 => difference=2
            # black pawns move down => row_start=6 => row_end=4 => difference=-2
            if abs(row_end - row_start) == 2:
                # The en_passant_sq is behind the pawn
                if color_to_move == Color.WHITE:
                    self.en_passant_sq = end_sq - 8
                else:
                    self.en_passant_sq = end_sq + 8

        # 6) Remove castling rights if king/rook moved or if rook captured
        update_castling_rights_on_move(self, start_sq, color_to_move, piece_moved)
        if piece_captured:
            update_castling_rights_on_capture(self, end_sq, piece_captured)

        # 7) If promotion
        if piece_moved == Piece.PAWN and promotion_piece is not None:
            row_end = end_sq // 8
            if color_to_move == Color.WHITE and row_end == 7:
                # white promotion
                clear_piece_bit(self, end_sq, color_to_move, Piece.PAWN)
                set_piece_bit(self, end_sq, color_to_move, promotion_piece)
                move_rec.piece_moved = (color_to_move, promotion_piece)
            elif color_to_move == Color.BLACK and row_end == 0:
                # black promotion
                clear_piece_bit(self, end_sq, color_to_move, Piece.PAWN)
                set_piece_bit(self, end_sq, color_to_move, promotion_piece)
                move_rec.piece_moved = (color_to_move, promotion_piece)

        self.move_log.append(move_rec)
        self.update_bitboards()
        self.update_board_ui()
        self.current_turn = ~color_to_move
        return True

    # ---------------------------------------------------------------
    # UNDO MOVE
    # ---------------------------------------------------------------
    def undo_move(self):
        if not self.move_log:
            print("[DEBUG] No move to undo.")
            return

        move_rec = self.move_log.pop()

        self.current_turn = move_rec.current_turn_before

        color_to_move, piece_moved = move_rec.piece_moved
        start_sq = move_rec.start_sq
        end_sq = move_rec.end_sq

        # Move piece back
        clear_piece_bit(self, end_sq, color_to_move, piece_moved)
        set_piece_bit(self, start_sq, color_to_move, piece_moved)

        # Restore captured
        if move_rec.piece_captured is not None:
            if move_rec.was_en_passant:
                if color_to_move == Color.WHITE:
                    captured_sq = end_sq - 8
                else:
                    captured_sq = end_sq + 8
                opp_color, opp_ptype = move_rec.piece_captured
                set_piece_bit(self, captured_sq, opp_color, opp_ptype)
            else:
                opp_color, opp_ptype = move_rec.piece_captured
                set_piece_bit(self, end_sq, opp_color, opp_ptype)

        # If castling, move rook back
        if move_rec.was_castling:
            restore_rook_after_castle(self, move_rec.rook_start_sq, move_rec.rook_end_sq, color_to_move)

        # Restore en_passant_sq
        self.en_passant_sq = move_rec.en_passant_square_before

        # Restore castling rights
        self.castling_rights = dict(move_rec.castling_rights_before)

        self.update_bitboards()
        self.update_board_ui()
