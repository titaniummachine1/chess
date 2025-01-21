import pygame as p
import os
import chess

IMAGES = {}
SQ_SIZE = 680 // 8  # If you prefer, pass dimension from outside

def load_images():
    """
    Load chess piece images into IMAGES dict, e.g. IMAGES['wP'].
    Adjust the path as needed to point to your 'images' folder.
    """
    global IMAGES
    # If your filenames are e.g. wP.png, bK.png, etc.
    pieces = ['wP', 'wR', 'wN', 'wB', 'wQ', 'wK', 'bP', 'bR', 'bN', 'bB', 'bQ', 'bK']
    for piece_key in pieces:
        # images/wP.png etc.
        img_path = os.path.join('images', f'{piece_key}.png')
        image_surf = p.image.load(img_path)
        IMAGES[piece_key] = p.transform.smoothscale(image_surf, (SQ_SIZE, SQ_SIZE))

def draw_board(screen, dimension=8, width=680, height=680):
    """Draw an 8x8 chessboard (alternating squares)."""
    sq_size = height // dimension
    white = p.Color('#EBEBD0')
    dark = p.Color('#769455')

    for row in range(dimension):
        for col in range(dimension):
            color = white if (row + col) % 2 == 0 else dark
            p.draw.rect(screen, color, p.Rect(col * sq_size, row * sq_size, sq_size, sq_size))

def draw_pieces(screen, board_obj, flipped=False, dimension=8):
    """
    Render the pieces from a python-chess.Board on the squares.
    If flipped=True, draw from black's perspective.
    """
    sq_size = 680 // dimension
    for sq in chess.SQUARES:  # 0..63, a8=0 -> h1=63
        piece = board_obj.piece_at(sq)
        if piece:
            # piece.symbol() => 'P','p','R','r', etc.
            # piece.color => True (white) or False (black)
            row = sq // 8  # 0 for rank 8, 7 for rank 1
            col = sq % 8
            # If flipped, invert row,col
            if flipped:
                draw_row = 7 - row
                draw_col = 7 - col
            else:
                draw_row = row
                draw_col = col

            # 'w' or 'b' 
            color_char = 'w' if piece.color == chess.WHITE else 'b'
            # 'P','N','B','R','Q','K' (uppercase)
            piece_type = piece.symbol().upper()
            image_key = color_char + piece_type  # e.g. 'wR'

            if image_key in IMAGES:
                screen.blit(IMAGES[image_key], p.Rect(draw_col * sq_size, draw_row * sq_size, sq_size, sq_size))

def apply_legal_move(board_obj, move):
    """
    Attempt to push a move onto a python-chess.Board if it's legal.
    `move` is a tuple: ((start_row, start_col), (end_row, end_col))

    We'll convert that into a python-chess Move and if it's in board_obj.legal_moves,
    we do board_obj.push(move). 
    """
    (start_row, start_col), (end_row, end_col) = move

    # Convert to python-chess square
    # python-chess: row=0 => a8, row=7 => a1 
    # so the square index = row*8 + col
    start_sq = start_row * 8 + start_col
    end_sq = end_row * 8 + end_col

    candidate = chess.Move(start_sq, end_sq)

    if candidate in board_obj.legal_moves:
        board_obj.push(candidate)
    else:
        print(f"Illegal move from {start_sq} to {end_sq} (row,col)=({start_row},{start_col})->({end_row},{end_col})")

def draw_highlights(screen, board_obj, selected_square, flipped=False):
    """
    Highlight the selected square in translucent yellow,
    then show all possible moves for that piece as:
      - small black circle for normal moves
      - black ring for captures
    """
    if selected_square is None:
        return  # No piece is currently selected

    row, col = selected_square
    sq_size = 680 // 8  # Adjust if needed

    # Convert for flipping
    disp_row = 7 - row if flipped else row
    disp_col = 7 - col if flipped else col

    # 1) Highlight the selected square in translucent yellow
    highlight_surf = p.Surface((sq_size, sq_size), p.SRCALPHA)
    highlight_surf.fill((255, 255, 0, 100))  # RGBA => yellow with some transparency
    screen.blit(highlight_surf, (disp_col * sq_size, disp_row * sq_size))

    # 2) Gather all moves for the piece on that square
    # In python-chess, row=0 => rank 8 => squares [0..7], row=7 => rank 1 => squares [56..63]
    start_sq = row * 8 + col

    # Filter legal moves in board_obj for those that start at start_sq
    valid_dest_squares = []
    for mv in board_obj.legal_moves:
        if mv.from_square == start_sq:
            valid_dest_squares.append(mv.to_square)

    # 3) Draw a small black circle for normal moves, or a black ring for captures
    for dest_sq in valid_dest_squares:
        end_row = dest_sq // 8
        end_col = dest_sq % 8

        drow = 7 - end_row if flipped else end_row
        dcol = 7 - end_col if flipped else end_col

        # Check if this move is a capture
        move_candidate = chess.Move(start_sq, dest_sq)
        is_capture = board_obj.is_capture(move_candidate)

        if is_capture:
            # Draw a black ring
            ring_surface = p.Surface((sq_size, sq_size), p.SRCALPHA)
            center = (sq_size // 2, sq_size // 2)
            radius = sq_size // 2
            line_width = 7
            # RGBA => black ring with some transparency
            p.draw.circle(ring_surface, (0, 0, 0, 120), center, radius, line_width)
            screen.blit(ring_surface, (dcol * sq_size, drow * sq_size))
        else:
            # Draw a small black circle
            circle_surface = p.Surface((sq_size, sq_size), p.SRCALPHA)
            center = (sq_size // 2, sq_size // 2)
            radius = sq_size // 7
            # black circle with transparency
            p.draw.circle(circle_surface, (0, 0, 0, 120), center, radius)
            screen.blit(circle_surface, (dcol * sq_size, drow * sq_size))
