##main.py do nto remove this comment you damn idiot
import pygame as p
import chess
import random
from utils import (load_images, draw_board, draw_pieces, apply_legal_move, 
                   draw_highlights, draw_legal_move_indicators)
from GameState.movegen import DrawbackBoard
from GameState.drawback_manager import DRAWBACKS

# Add BOARD_HEIGHT to utils.py's global scope for square size calculation
import utils
BOARD_HEIGHT = 640  # Actual board height
utils.BOARD_HEIGHT = BOARD_HEIGHT

# Rest of imports
try:
    from ui.tinker_panel import TinkerPanel
    HAS_TINKER_PANEL = True
except ImportError:
    print("Warning: pygame_gui not found. Tinker's Control Panel will have limited functionality.")
    HAS_TINKER_PANEL = False

try:
    from AI.search import best_move
    from AI.async_search import async_best_move, is_thinking, get_best_move, get_current_depth, get_progress
    HAS_AI = True
except ImportError:
    print("Warning: AI module not available.")
    HAS_AI = False

# Game Settings
WIDTH = 800  # Wider to accommodate centered board with coordinates
HEIGHT = 760  # Taller to accommodate info bars
BOARD_HEIGHT = 640  # Actual board height
BOARD_Y_OFFSET = 80  # Space at the top for white info
BOARD_X_OFFSET = 80  # Space at the left for board centering
DIMENSION = 8
SQ_SIZE = BOARD_HEIGHT // DIMENSION
FPS = 60  # Increased for smoother UI during AI thinking
AI_DEPTH = 3  # Adjust AI search depth (higher = stronger)
AI_MAX_DEPTH = 14  # Maximum allowed depth

# Important: Set the BOARD_HEIGHT in utils for consistent square sizing
import utils
utils.BOARD_HEIGHT = BOARD_HEIGHT

# Global variables
game_over = False
winner_color = None
flipped = False  # Make flipped global to be accessible in open_tinker_panel

# AI control flags - will be updated from the Tinker Panel
WHITE_AI = False
BLACK_AI = True

# Button rect for Tinker Panel
tinker_button_rect = p.Rect(WIDTH - 120, 10, 100, 35)

# List of available drawbacks
AVAILABLE_DRAWBACKS = [
    "no_knight_moves",
    "no_bishop_captures",
    "no_knight_captures",
    "punching_down"
]

def assign_random_drawbacks(board):
    """Assign random drawbacks to each player."""
    # Choose random drawbacks for each player
    white_drawback = random.choice(AVAILABLE_DRAWBACKS)
    black_drawback = random.choice(AVAILABLE_DRAWBACKS)
    
    # Assign the drawbacks
    board.set_drawback(chess.WHITE, white_drawback)
    board.set_drawback(chess.BLACK, black_drawback)
    
    print(f"White drawback: {white_drawback}")
    print(f"Black drawback: {black_drawback}")

def display_drawbacks(screen, board, flipped):
    """Display the active drawbacks for each player at the top and bottom of the screen."""
    font = p.font.SysFont(None, 22)
    
    # Get drawback names
    white_drawback = board.get_active_drawback(chess.WHITE) or "None"
    black_drawback = board.get_active_drawback(chess.BLACK) or "None"
    
    # Format drawback names for display
    white_drawback_name = white_drawback.replace("_", " ").title()
    black_drawback_name = black_drawback.replace("_", " ").title()
    
    # Create text surfaces
    white_text = font.render(f"White: {white_drawback_name}", True, p.Color("white"), p.Color("black"))
    black_text = font.render(f"Black: {black_drawback_name}", True, p.Color("black"), p.Color("white"))
    
    # If flipped, swap top/bottom positions
    if flipped:
        # White at bottom, Black at top
        screen.blit(black_text, (10, 10))
        screen.blit(white_text, (10, HEIGHT - 30))
    else:
        # White at top, Black at bottom
        screen.blit(white_text, (10, 10))
        screen.blit(black_text, (10, HEIGHT - 30))

def display_current_turn(screen, board):
    """Display whose turn it is."""
    font = p.font.SysFont(None, 22)
    turn_text = "White's Turn" if board.turn == chess.WHITE else "Black's Turn"
    color = p.Color("white") if board.turn == chess.WHITE else p.Color("black")
    bg_color = p.Color("black") if board.turn == chess.WHITE else p.Color("white")
    
    text_surf = font.render(turn_text, True, color, bg_color)
    screen.blit(text_surf, (WIDTH // 2 - text_surf.get_width() // 2, 10))

def display_winner(screen, winner_color):
    """Display the winner and stop the game."""
    font = p.font.Font(None, 50)
    text = f"{'White' if winner_color == chess.WHITE else 'Black'} wins by capturing the king! Press 'R' to restart."
    text_surf = font.render(text, True, p.Color("black"), p.Color("gold"))
    text_rect = text_surf.get_rect(center=(WIDTH // 2, HEIGHT // 2))
    screen.blit(text_surf, text_rect)
    p.display.flip()

def draw_tinker_button(screen):
    """Draw the button to open Tinker Panel."""
    font = p.font.SysFont(None, 22)
    p.draw.rect(screen, (100, 100, 150), tinker_button_rect)
    text = font.render("Tinker Panel", True, p.Color("white"))
    text_rect = text.get_rect(center=tinker_button_rect.center)
    screen.blit(text, text_rect)

def open_tinker_panel(board):
    """Open the Tinker's Control Panel to modify drawbacks and AI settings"""
    global WHITE_AI, BLACK_AI, flipped, AI_DEPTH
    
    if HAS_TINKER_PANEL:
        # Pass current AI settings to the panel
        ai_settings = {
            "WHITE_AI": WHITE_AI,
            "BLACK_AI": BLACK_AI,
            "AI_DEPTH": AI_DEPTH
        }
        
        tinker_panel = TinkerPanel(board_reference=board, ai_settings=ai_settings)
        result = tinker_panel.run()
        
        if result:
            # Correctly unpack the 4 values returned from tinker_panel.run()
            white_drawback, black_drawback, updated_ai_settings, options = result
            
            # Update AI control flags
            WHITE_AI = updated_ai_settings["WHITE_AI"]
            BLACK_AI = updated_ai_settings["BLACK_AI"]
            AI_DEPTH = updated_ai_settings.get("AI_DEPTH", AI_DEPTH)
            
            # Handle flip board option
            if options.get("FLIP_BOARD", False):
                flipped = not flipped
                print("Board flipped from tinker panel")
        
        # Reinitialize the main screen
        p.display.set_mode((WIDTH, HEIGHT))
        p.display.set_caption("Drawback Chess")
    else:
        print("Tinker's Control Panel is not available due to missing pygame_gui.")

def display_ai_status(screen, board):
    """Display the AI thinking status if AI is active."""
    if not HAS_AI or not is_thinking():
        return
    
    font = p.font.SysFont(None, 20)
    
    # Determine which player's AI is thinking
    player_color = "White" if board.turn == chess.WHITE else "Black"
    drawback = board.get_active_drawback(board.turn) or "None"
    drawback_name = drawback.replace("_", " ").title()
    
    # Create status text
    status_text = f"{player_color} AI ({drawback_name}) - Depth: {get_current_depth()}"
    thinking_text = get_progress()
    
    # Render text with background
    status_surf = font.render(status_text, True, p.Color("white"), p.Color("darkblue"))
    thinking_surf = font.render(thinking_text, True, p.Color("white"), p.Color("darkblue"))
    
    # Position on the right side of the screen
    status_rect = status_surf.get_rect(topright=(WIDTH - 10, 40))
    thinking_rect = thinking_surf.get_rect(topright=(WIDTH - 10, 65))
    
    # Draw to screen
    screen.blit(status_surf, status_rect)
    screen.blit(thinking_surf, thinking_rect)

def ai_move(board):
    """
    Executes AI move if it's AI's turn and the game isn't over.
    Uses asynchronous processing to avoid UI lag.
    """
    global game_over, winner_color

    if not HAS_AI:
        print("AI module not available - skipping AI move")
        return

    # If AI is already thinking, check if it has a move ready
    if is_thinking():
        move = get_best_move()
        if move is not None:
            # Check if this is a king capture move
            target = board.piece_at(move.to_square)
            if target and target.piece_type == chess.KING:
                print(f"AI is capturing the {'White' if target.color == chess.WHITE else 'Black'} king!")
            
            board.push(move)
            print(f"AI moved: {move}")

            # Check if the AI won by capturing the king
            if board.is_variant_end():
                game_over = True
                winner_color = chess.WHITE if board.is_variant_win() else chess.BLACK
                print(f"Game over! {'White' if winner_color == chess.WHITE else 'Black'} wins by capturing the king!")
        return
    
    # Otherwise, start a new AI search
    if not board.is_variant_end():
        async_best_move(board, AI_DEPTH)

def change_drawback(board, color, new_drawback=None):
    """
    Change the drawback for a specific player.
    If no drawback is specified, choose randomly.
    """
    if new_drawback is None:
        new_drawback = random.choice(AVAILABLE_DRAWBACKS)
    
    board.set_drawback(color, new_drawback)
    color_name = "White" if color == chess.WHITE else "Black"
    print(f"Changed {color_name}'s drawback to: {new_drawback}")

def main():
    """Main game loop for Drawback Chess."""
    global game_over, winner_color, WHITE_AI, BLACK_AI, flipped
    
    p.init()
    screen = p.display.set_mode((WIDTH, HEIGHT))
    clock = p.time.Clock()
    p.display.set_caption("Drawback Chess")

    board = DrawbackBoard()
    assign_random_drawbacks(board)  # Assign random drawbacks to each player
    board.reset()
    
    # Print the FEN for debugging
    print(f"Starting position FEN: {board.fen()}")
    
    # Debug the initial board state
    for r in range(8):
        rank_str = ""
        for f in range(8):
            sq = chess.square(f, r)  # file (0-7), rank (0-7)
            piece = board.piece_at(sq)
            if piece:
                rank_str += piece.symbol() + " "
            else:
                rank_str += "· "
        print(f"{8-r} {rank_str}")
    print("  a b c d e f g h")

    running = True

    # Default orientation: White on bottom, Black on top
    flipped = False

    selected_square = None
    game_over = False
    winner_color = None

    while running:
        for event in p.event.get():
            if event.type == p.QUIT:
                running = False

            elif event.type == p.MOUSEBUTTONDOWN:
                x, y = event.pos
                
                # Check if Tinker Panel button was clicked
                if tinker_button_rect.collidepoint(x, y):
                    open_tinker_panel(board)
                    continue
                
                # Then handle game moves if not in game over state
                if not game_over:
                    # Only allow user input if the current side is not AI
                    if not (WHITE_AI and board.turn == chess.WHITE) and not (BLACK_AI and board.turn == chess.BLACK):
                        # Adjust for board offset
                        board_x = x - BOARD_X_OFFSET
                        board_y = y - BOARD_Y_OFFSET
                        
                        # Check if click is within board bounds
                        if (0 <= board_y < BOARD_HEIGHT and 
                            0 <= board_x < BOARD_HEIGHT):  # Board is square
                            
                            row, col = board_y // SQ_SIZE, board_x // SQ_SIZE

                            # Convert screen coordinates to board coordinates
                            if flipped:
                                board_row = row 
                                board_col = 7 - col
                            else:
                                board_row = 7 - row
                                board_col = col

                            clicked_square = chess.square(board_col, board_row)  # file, rank

                            if selected_square is None:
                                piece = board.piece_at(clicked_square)
                                if piece and piece.color == board.turn:
                                    selected_square = clicked_square
                                    print(f"Selected {piece.symbol()} at {chess.square_name(clicked_square)}")
                            else:
                                move = chess.Move(selected_square, clicked_square)
                                
                                # Check if this move captures a king
                                target = board.piece_at(clicked_square)
                                is_king_capture = target and target.piece_type == chess.KING
                                
                                if board.is_legal(move):
                                    if is_king_capture:
                                        print(f"Capturing the {'White' if target.color == chess.WHITE else 'Black'} king!")
                                        
                                    print(f"Moving {board.piece_at(selected_square).symbol()} from {chess.square_name(selected_square)} to {chess.square_name(clicked_square)}")
                                    board.push(move)
                                    selected_square = None
                                    
                                    # Check if the move resulted in a king capture (game over)
                                    if board.is_variant_end():
                                        winner_color = chess.WHITE if board.is_variant_win() else chess.BLACK
                                        game_over = True
                                else:
                                    # Check if clicked on another piece of same color
                                    piece = board.piece_at(clicked_square)
                                    if piece and piece.color == board.turn:
                                        selected_square = clicked_square
                                        print(f"Selected {piece.symbol()} at {chess.square_name(clicked_square)}")
                                    else:
                                        print(f"Illegal move: {chess.square_name(selected_square)} to {chess.square_name(clicked_square)}")
                                        selected_square = None

            elif event.type == p.KEYDOWN:
                if event.key == p.K_r:
                    # Reset board and game state properly
                    board = DrawbackBoard()
                    assign_random_drawbacks(board)
                    board.reset()

                    selected_square = None
                    game_over = False
                    winner_color = None

                    print("Game restarted!")
                elif event.key == p.K_t:
                    # Open Tinker's Control Panel
                    open_tinker_panel(board)

        if not game_over:
            # Let AI move if it's AI's turn
            if BLACK_AI and board.turn == chess.BLACK and HAS_AI:
                ai_move(board)
            if WHITE_AI and board.turn == chess.WHITE and HAS_AI:
                ai_move(board)

        # Clear screen before drawing
        screen.fill(p.Color("black"))

        # Draw the board and pieces with consistent offsets
        draw_board(screen, DIMENSION, BOARD_HEIGHT, BOARD_HEIGHT, flipped, BOARD_Y_OFFSET, BOARD_X_OFFSET)
        draw_pieces(screen, board, flipped, DIMENSION, BOARD_Y_OFFSET, BOARD_X_OFFSET)
        
        # Display active drawbacks and turn info
        display_drawbacks(screen, board, flipped)
        display_current_turn(screen, board)
        draw_tinker_button(screen)
        
        # Display AI thinking status if available
        if 'display_ai_status' in globals():
            display_ai_status(screen, board)
        
        # Highlight the selected square and legal moves
        if selected_square is not None:
            # Calculate correct position for highlight using the BOARD_HEIGHT for square size
            square_size = BOARD_HEIGHT // DIMENSION
            row = chess.square_rank(selected_square)
            col = chess.square_file(selected_square)
            
            if flipped:
                draw_row = row
                draw_col = 7 - col
            else:
                draw_row = 7 - row
                draw_col = col
                
            # Draw highlight
            highlight_surf = p.Surface((square_size, square_size), p.SRCALPHA)
            highlight_surf.fill((255, 255, 0, 100))
            screen.blit(highlight_surf, 
                       (BOARD_X_OFFSET + draw_col * square_size, 
                        BOARD_Y_OFFSET + draw_row * square_size))
            
            # Draw legal move indicators
            draw_legal_move_indicators(screen, board, selected_square, flipped, 
                                      DIMENSION, BOARD_Y_OFFSET, BOARD_X_OFFSET)

        # Display winner if game over
        if game_over and winner_color is not None:
            display_winner(screen, winner_color)

        # Update the display
        clock.tick(FPS)
        p.display.flip()

    # Clean up and exit
    p.quit()

# Make sure main() is called when the script is run directly
if __name__ == "__main__":
    main()