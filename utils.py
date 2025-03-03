##utils.py do nto remove this comment you damn idiot

import pygame as p
import os
import chess
from GameState.movegen import DrawbackBoard  # Your custom board

# Global image cache to prevent reloading
PIECES_CACHE = {}
BOARD_HEIGHT = 640  # Default value, will be overridden by main.py

def load_images(square_size):
    """
    Load the chess piece images once, scaled to the square size.
    Uses a cache to avoid reloading images unnecessarily.
    """
    global PIECES_CACHE
    
    # Return cached images if they exist for this square size
    cache_key = f"size_{square_size}"
    if cache_key in PIECES_CACHE:
        return PIECES_CACHE[cache_key]
    
    pieces = ['wP', 'wR', 'wN', 'wB', 'wQ', 'wK', 'bP', 'bR', 'bN', 'bB', 'bQ', 'bK']
    piece_images = {}
    
    try:
        for piece in pieces:
            filename = f"images/{piece}.png"
            img = p.image.load(filename)
            # Scale to square size (with a small margin)
            piece_images[piece] = p.transform.scale(img, (square_size, square_size))
        print(f"Loaded images: {pieces}")
        
        # Store in cache
        PIECES_CACHE[cache_key] = piece_images
        
    except Exception as e:
        print(f"Error loading images: {e}")
    
    return piece_images

def draw_board(screen, dimension, width, height, flipped=False, offset_y=40, offset_x=0):
    """
    Draw the chess board with coordinates.
    Uses BOARD_HEIGHT for consistent square sizing.
    """
    colors = [p.Color("white"), p.Color("gray")]
    square_size = BOARD_HEIGHT // dimension
    font = p.font.SysFont(None, 20)
    
    # Fill background
    screen.fill(p.Color("black"))
    
    # Draw squares
    for row in range(dimension):
        for col in range(dimension):
            color = colors[(row + col) % 2]
            
            p.draw.rect(
                screen, color, 
                p.Rect(offset_x + col * square_size, offset_y + row * square_size, 
                       square_size, square_size)
            )
    
    # Draw coordinates - files (a-h)
    for col in range(dimension):
        # Adjust column index for flipped board
        file_idx = col if not flipped else 7 - col
        file_label = chr(97 + file_idx)  # ASCII 'a' = 97
        
        # Draw at bottom of board
        label = font.render(file_label, True, p.Color("white"))
        screen.blit(label, (
            offset_x + col * square_size + square_size//2 - label.get_width()//2, 
            offset_y + dimension * square_size + 5
        ))
        
    # Draw coordinates - ranks (1-8)
    for row in range(dimension):
        # Adjust row index for flipped board
        rank_idx = row if flipped else 7 - row
        rank_label = str(rank_idx + 1)
        
        # Draw at left of board
        label = font.render(rank_label, True, p.Color("white"))
        screen.blit(label, (
            offset_x - label.get_width() - 5, 
            offset_y + row * square_size + square_size//2 - label.get_height()//2
        ))

def draw_pieces(screen, board, flipped, dimension, y_offset=0, x_offset=0):
    """Draw the chess pieces on the board with proper flipping."""
    square_size = BOARD_HEIGHT // dimension
    
    # Check if images are loaded for this square size, and load them if not
    cache_key = f"size_{square_size}"
    if cache_key not in PIECES_CACHE:
        load_images(square_size)
    
    # Draw all pieces from the board
    for square, piece in board.piece_map().items():
        file, rank = chess.square_file(square), chess.square_rank(square)
        
        # Adjust drawing position based on flip state
        if flipped:
            draw_row, draw_col = rank, 7 - file
        else:
            draw_row, draw_col = 7 - rank, file
            
        # Get the piece image
        color = "w" if piece.color == chess.WHITE else "b"
        piece_type = chess.piece_symbol(piece.piece_type).upper()
        image_key = color + piece_type
        
        # Calculate centered position 
        image = PIECES_CACHE[cache_key][image_key]
        image_width, image_height = image.get_width(), image.get_height()
        pos_x = x_offset + draw_col * square_size + (square_size - image_width) // 2
        pos_y = y_offset + draw_row * square_size + (square_size - image_height) // 2
        
        # Draw at the calculated position
        screen.blit(image, (pos_x, pos_y))

def apply_legal_move(board, move):
    """Apply a legal move to the board."""
    if board.is_legal(move):
        board.push(move)
        return True
    return False

def draw_highlights(screen, board, selected_square, flipped, dimension, offset_y=40, offset_x=0):
    """Draw highlighted squares and legal move indicators."""
    if selected_square is None:
        return
        
    # Use BOARD_HEIGHT for consistent square size
    square_size = BOARD_HEIGHT // dimension
    
    # Highlight the selected square
    row = chess.square_rank(selected_square)
    col = chess.square_file(selected_square)
    if flipped:
        draw_row = row
        draw_col = 7 - col
    else:
        draw_row = 7 - row
        draw_col = col
        
    highlight_surf = p.Surface((square_size, square_size), p.SRCALPHA)
    highlight_surf.fill((255, 255, 0, 100))
    screen.blit(highlight_surf, (offset_x + draw_col * square_size, offset_y + draw_row * square_size))

def draw_legal_move_indicators(screen, board, from_square, flipped, dimension, y_offset=0, x_offset=0):
    """Draw indicators for legal moves from the selected square."""
    square_size = BOARD_HEIGHT // dimension
    
    # Get all legal moves from the selected square
    for move in board.legal_moves:
        if move.from_square == from_square:
            to_file, to_rank = chess.square_file(move.to_square), chess.square_rank(move.to_square)
            
            # Adjust for flipping
            if flipped:
                draw_row, draw_col = to_rank, 7 - to_file
            else:
                draw_row, draw_col = 7 - to_rank, to_file
            
            # Draw a semi-transparent circle for the legal move
            center_x = x_offset + draw_col * square_size + square_size // 2
            center_y = y_offset + draw_row * square_size + square_size // 2
            
            # Create a surface for alpha blending
            s = p.Surface((square_size, square_size), p.SRCALPHA)
            
            # Check if it's a capture
            if board.is_capture(move):
                # Draw a red circle for captures
                p.draw.circle(s, (255, 0, 0, 100), (square_size//2, square_size//2), square_size//4)
                p.draw.circle(s, (255, 0, 0, 150), (square_size//2, square_size//2), square_size//4, 3)
            else:
                # Draw a green circle for non-captures
                p.draw.circle(s, (0, 255, 0, 100), (square_size//2, square_size//2), square_size//6)
                
            # Blit the surface to the screen
            screen.blit(s, (x_offset + draw_col * square_size, y_offset + draw_row * square_size))
