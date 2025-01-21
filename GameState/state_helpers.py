# state_helpers.py

import numpy as np
from bitboard import Bitboard
from GameState.constants import Color, Piece

class MoveRecord:
    """
    Holds all info needed to undo a move:
      - start_sq, end_sq
      - piece_moved, piece_captured (if any)
      - was_en_passant, en_passant_square_before
      - was_castling, old_castling_rights
      - rook_start_sq, rook_end_sq (for castling)
      - current_turn_before
    """
    __slots__ = (
        "start_sq", "end_sq",
        "piece_moved", "piece_captured",
        "was_en_passant", "en_passant_square_before",
        "was_castling",
        "rook_start_sq", "rook_end_sq",
        "castling_rights_before",
        "current_turn_before"
    )

    def __init__(self, start_sq, end_sq,
                 piece_moved, piece_captured,
                 was_en_passant, en_passant_square_before,
                 was_castling,
                 rook_start_sq, rook_end_sq,
                 castling_rights_before,
                 current_turn_before):
        self.start_sq = start_sq
        self.end_sq = end_sq
        self.piece_moved = piece_moved  # (color, piece_type)
        self.piece_captured = piece_captured  # (opp_color, opp_piece_type) or None
        self.was_en_passant = was_en_passant
        self.en_passant_square_before = en_passant_square_before
        self.was_castling = was_castling
        self.rook_start_sq = rook_start_sq
        self.rook_end_sq = rook_end_sq
        self.castling_rights_before = castling_rights_before
        self.current_turn_before = current_turn_before


def identify_piece_on_square(state, sq, color):
    """Return piece_type if a piece of 'color' occupies 'sq', else None."""
    for ptype in range(6):
        if Bitboard.get_bit(state.pieces[color][ptype], sq):
            return ptype
    return None


def find_capture_target(state, end_sq, color_to_move):
    """Return (opp_color, opp_piece_type) if end_sq is occupied by opponent, else None."""
    opp_color = ~color_to_move
    for ptype in range(6):
        if Bitboard.get_bit(state.pieces[opp_color][ptype], end_sq):
            return (opp_color, ptype)
    return None


def clear_piece_bit(state, sq, color, ptype):
    state.pieces[color][ptype] = Bitboard.clear_bit(state.pieces[color][ptype], sq)


def set_piece_bit(state, sq, color, ptype):
    state.pieces[color][ptype] = Bitboard.set_bit(state.pieces[color][ptype], sq)


def restore_rook_after_castle(state, rook_start_sq, rook_end_sq, color):
    """When undoing a castle, move the rook back."""
    clear_piece_bit(state, rook_end_sq, color, Piece.ROOK)
    set_piece_bit(state, rook_start_sq, color, Piece.ROOK)


def update_castling_rights_on_move(state, start_sq, color, piece_type):
    """
    If a rook or king moves away from its starting position, strip the relevant castling right.
    In standard bitboard indexing (a1=0..h1=7, a8=56..h8=63):
     - White King at e1=4 => remove 'K' and 'Q'
     - White Rook at h1=7 => remove 'K'
     - White Rook at a1=0 => remove 'Q'
     - Black King at e8=60 => remove 'k' and 'q'
     - Black Rook at h8=63 => remove 'k'
     - Black Rook at a8=56 => remove 'q'
    """
    from GameState.constants import Piece

    if piece_type == Piece.KING:
        if color == Color.WHITE:
            state.castling_rights['K'] = False
            state.castling_rights['Q'] = False
        else:
            state.castling_rights['k'] = False
            state.castling_rights['q'] = False

    if piece_type == Piece.ROOK:
        if color == Color.WHITE:
            if start_sq == 7:   # h1
                state.castling_rights['K'] = False
            elif start_sq == 0: # a1
                state.castling_rights['Q'] = False
        else:
            if start_sq == 63:  # h8
                state.castling_rights['k'] = False
            elif start_sq == 56: # a8
                state.castling_rights['q'] = False


def update_castling_rights_on_capture(state, end_sq, captured_piece):
    """
    If we captured an opponent's rook in a corner, that might remove its castling right.
    e.g. capturing black's rook on h8=63 => remove 'k'
    """
    opp_color, opp_ptype = captured_piece
    if opp_ptype != Piece.ROOK:
        return

    from GameState.constants import Color
    if opp_color == Color.WHITE:
        if end_sq == 0:  # a1
            state.castling_rights['Q'] = False
        elif end_sq == 7:  # h1
            state.castling_rights['K'] = False
    else:
        if end_sq == 56: # a8
            state.castling_rights['q'] = False
        elif end_sq == 63: # h8
            state.castling_rights['k'] = False
