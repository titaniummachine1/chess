import pygame as p
from bitboard import Bitboard
from GameState.constants import Color, Piece
import movegen  # Import move generation module

IMAGES = {}

# **Load Chess Piece Images**
def load_images():
    """Load chess piece images for UI rendering."""
    global IMAGES
    pieces = ['wP', 'wR', 'wN', 'wB', 'wQ', 'wK', 'bP', 'bR', 'bN', 'bB', 'bQ', 'bK']
    for piece in pieces:
        IMAGES[piece] = p.transform.smoothscale(
            p.image.load(f'images/{piece}.png'), (680 // 8, 680 // 8)
        )

# **Draw Board**
def draw_board(screen, width=680, height=680, dimension=8):
    """Draw the chessboard."""
    sq_size = height // dimension
    white = p.Color('#EBEBD0')
    dark = p.Color('#769455')

    for row in range(dimension):
        for col in range(dimension):
            color = white if (row + col) % 2 == 0 else dark
            p.draw.rect(screen, color, p.Rect(col * sq_size, row * sq_size, sq_size, sq_size))

# **Draw Pieces**
def draw_pieces(screen, game_state, flipped=False, dimension=8):
    """Draw chess pieces based on the correct game state, supporting board flipping."""
    sq_size = 680 // dimension

    for r in range(dimension):
        for c in range(dimension):
            display_r = 7 - r if flipped else r
            display_c = 7 - c if flipped else c

            piece_key = game_state.board_ui[r][c]  # Read from board_ui (FEN-style)
            if piece_key in IMAGES:
                screen.blit(IMAGES[piece_key], p.Rect(display_c * sq_size, display_r * sq_size, sq_size, sq_size))

# **Apply Move (Only If Legal)**
def apply_legal_move(game_state, move):
    """
    Move a piece *only if the move is legal*.
    `move` is expected as ((start_row, start_col), (end_row, end_col)).
    """
    (start_row, start_col), (end_row, end_col) = move

    # Convert row,col to bitboard square indices
    square_start = game_state.get_square(start_row, start_col)
    square_end   = game_state.get_square(end_row, end_col)

    # Generate *all* legal moves in bitboard form
    legal_moves = set(movegen.generate_legal_moves(game_state))

    # Check if the bitboard tuple is in legal_moves
    if (square_start, square_end, None) not in legal_moves:
        print(f"Illegal move: ({start_row}, {start_col}) -> ({end_row}, {end_col})")
        return  # Do nothing if illegal

    # If legal, proceed:
    piece_data = game_state.get_piece_at(start_row, start_col)
    if not piece_data:
        return  # No piece to move (shouldn't happen if it was legal, but just in case)

    color, piece_type = piece_data

    # Handle captures
    captured_piece_data = game_state.get_piece_at(end_row, end_col)
    is_capture = (captured_piece_data is not None)
    if is_capture:
        captured_color, captured_piece_type = captured_piece_data
        game_state.pieces[captured_color][captured_piece_type] = Bitboard.clear_bit(
            game_state.pieces[captured_color][captured_piece_type], square_end
        )
        game_state.combined_color[captured_color] = Bitboard.clear_bit(game_state.combined_color[captured_color], square_end)
        game_state.combined_all = Bitboard.clear_bit(game_state.combined_all, square_end)

    # Remove the piece from the start square
    game_state.pieces[color][piece_type] = Bitboard.clear_bit(game_state.pieces[color][piece_type], square_start)
    # Place the piece on the end square
    game_state.pieces[color][piece_type] = Bitboard.set_bit(game_state.pieces[color][piece_type], square_end)

    # Update bitboards + UI
    game_state.update_bitboards()
    game_state.update_board_ui()

    # Switch turn
    game_state.current_turn = ~game_state.current_turn

    # Log move
    game_state.move_log.append(((start_row, start_col), (end_row, end_col), piece_type, is_capture))

# **Draw Highlights**
def draw_highlights(screen, game_state, selected_square, flipped=False):
    """
    Highlight the selected square in translucent yellow,
    then show all legal moves for that piece as:
      - small black circle for normal moves
      - red ring for captures
    """
    if selected_square is None:
        return  # No selection => no highlights

    # 1) Highlight the selected square
    sel_row, sel_col = selected_square
    sq_size = 680 // 8

    # Convert for flipping
    disp_row = 7 - sel_row if flipped else sel_row
    disp_col = 7 - sel_col if flipped else sel_col

    # Highlight selected in translucent yellow
    highlight_surf = p.Surface((sq_size, sq_size), p.SRCALPHA)
    highlight_surf.fill((255, 255, 0, 100))
    screen.blit(highlight_surf, (disp_col * sq_size, disp_row * sq_size))

    # 2) Gather all moves for the selected piece
    from_index = game_state.get_square(sel_row, sel_col)
    all_legal = list(movegen.generate_legal_moves(game_state))

    # Filter moves that start at 'from_index'
    legal_for_selected = [m for m in all_legal if m[0] == from_index]

    # 3) For each move, draw a small circle or ring
    for (start, end, _) in legal_for_selected:
        end_row = end // 8
        end_col = end % 8

        # Flip
        drow = 7 - end_row if flipped else end_row
        dcol = 7 - end_col if flipped else end_col

        # Check if there's a piece of opposite color at destination => capture
        piece_at_dest = game_state.get_piece_at(end_row, end_col)
        is_capture = (piece_at_dest is not None and piece_at_dest[0] != game_state.current_turn)

        if is_capture:
            # capture ring
            ring_surface = p.Surface((sq_size, sq_size), p.SRCALPHA)
            center = (sq_size // 2, sq_size // 2)
            radius = sq_size // 2
            line_width = 7
            p.draw.circle(ring_surface, (0, 0, 0, 120), center, radius, line_width)
            screen.blit(ring_surface, (dcol * sq_size, drow * sq_size))
        else:
            # Small black circle
            circle_surface = p.Surface((sq_size, sq_size), p.SRCALPHA)
            center = (sq_size // 2, sq_size // 2)
            radius = sq_size // 7
            p.draw.circle(circle_surface, (0, 0, 0, 120), center, radius)
            screen.blit(circle_surface, (dcol * sq_size, drow * sq_size))
