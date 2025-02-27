##main.py do nto remove this comment you damn idiot
import pygame as p
import chess
import random
from utils import load_images, draw_board, draw_pieces, apply_legal_move, draw_highlights
from GameState.movegen import DrawbackBoard
from GameState.drawback_manager import DRAWBACKS

# Try to import the TinkerPanel, but don't fail if pygame_gui is missing
try:
    from ui.tinker_panel import TinkerPanel
    HAS_TINKER_PANEL = True
except ImportError:
    print("Warning: pygame_gui not found. Tinker's Control Panel will have limited functionality.")
    HAS_TINKER_PANEL = False

try:
    from AI.search import best_move
    HAS_AI = True
except ImportError:
    print("Warning: AI module not available.")
    HAS_AI = False

# Game Settings
WIDTH, HEIGHT = 680, 680
DIMENSION = 8
SQ_SIZE = HEIGHT // DIMENSION
FPS = 12
AI_DEPTH = 3  # Adjust AI search depth (higher = stronger)

# Global variables
game_over = False
winner_color = None
# AI control flags - will be updated from the Tinker Panel
WHITE_AI = False
BLACK_AI = True

# UI elements for AI control in main game
white_ai_checkbox = p.Rect(10, HEIGHT - 25, 15, 15)
black_ai_checkbox = p.Rect(WIDTH - 80, HEIGHT - 25, 15, 15)

# List of available drawbacks
AVAILABLE_DRAWBACKS = [
    "no_knight_moves",
    "no_bishop_captures",
    "no_knight_captures",
    "punching_down"  # Added the new drawback
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

def display_drawbacks(screen, board):
    """Display the active drawbacks for each player at the top of the screen."""
    font = p.font.SysFont(None, 24)
    
    # Get drawback names
    white_drawback = board.get_active_drawback(chess.WHITE) or "None"
    black_drawback = board.get_active_drawback(chess.BLACK) or "None"
    
    # Format drawback names for display
    white_drawback_name = white_drawback.replace("_", " ").title()
    black_drawback_name = black_drawback.replace("_", " ").title()
    
    # Create text surfaces
    white_text = font.render(f"White: {white_drawback_name}", True, p.Color("white"), p.Color("black"))
    black_text = font.render(f"Black: {black_drawback_name}", True, p.Color("black"), p.Color("white"))
    
    # Place text at top of screen
    screen.blit(white_text, (10, 5))
    screen.blit(black_text, (WIDTH - black_text.get_width() - 10, 5))

def display_winner(screen, winner_color):
    """Display the winner and stop the game."""
    font = p.font.Font(None, 50)
    text = f"{'White' if winner_color == chess.WHITE else 'Black'} wins by capturing the king! Press 'R' to restart."
    text_surf = font.render(text, True, p.Color("black"), p.Color("gold"))
    text_rect = text_surf.get_rect(center=(WIDTH // 2, HEIGHT // 2))
    screen.blit(text_surf, text_rect)
    p.display.flip()

def display_ai_status(screen):
    """Display which sides are controlled by AI with checkboxes"""
    font = p.font.SysFont(None, 20)
    
    # Draw white AI checkbox and label
    p.draw.rect(screen, (255, 255, 255), white_ai_checkbox)
    if WHITE_AI:
        # Draw X in checkbox when AI is on
        p.draw.line(screen, (0, 0, 0), 
                   (white_ai_checkbox.left + 2, white_ai_checkbox.top + 2),
                   (white_ai_checkbox.right - 2, white_ai_checkbox.bottom - 2), 2)
        p.draw.line(screen, (0, 0, 0), 
                   (white_ai_checkbox.left + 2, white_ai_checkbox.bottom - 2),
                   (white_ai_checkbox.right - 2, white_ai_checkbox.top + 2), 2)
    
    white_text = font.render("White AI", True, p.Color("white"))
    screen.blit(white_text, (white_ai_checkbox.right + 5, white_ai_checkbox.top))
    
    # Draw black AI checkbox and label
    p.draw.rect(screen, (255, 255, 255), black_ai_checkbox)
    if BLACK_AI:
        # Draw X in checkbox when AI is on
        p.draw.line(screen, (0, 0, 0), 
                   (black_ai_checkbox.left + 2, black_ai_checkbox.top + 2),
                   (black_ai_checkbox.right - 2, black_ai_checkbox.bottom - 2), 2)
        p.draw.line(screen, (0, 0, 0), 
                   (black_ai_checkbox.left + 2, black_ai_checkbox.bottom - 2),
                   (black_ai_checkbox.right - 2, black_ai_checkbox.top + 2), 2)
    
    black_text = font.render("Black AI", True, p.Color("white"))
    screen.blit(black_text, (black_ai_checkbox.right + 5, black_ai_checkbox.top))

def check_ai_checkbox_click(pos):
    """Check if an AI checkbox was clicked and toggle it"""
    global WHITE_AI, BLACK_AI
    x, y = pos
    
    if white_ai_checkbox.collidepoint(x, y):
        WHITE_AI = not WHITE_AI
        print(f"White AI toggled: {'ON' if WHITE_AI else 'OFF'}")
        return True
    
    if black_ai_checkbox.collidepoint(x, y):
        BLACK_AI = not BLACK_AI
        print(f"Black AI toggled: {'ON' if BLACK_AI else 'OFF'}")
        return True
    
    return False

def open_tinker_panel(board):
    """Open the Tinker's Control Panel to modify drawbacks and AI settings"""
    global WHITE_AI, BLACK_AI
    
    if HAS_TINKER_PANEL:
        # Pass current AI settings to the panel
        ai_settings = {
            "WHITE_AI": WHITE_AI,
            "BLACK_AI": BLACK_AI
        }
        
        tinker_panel = TinkerPanel(board_reference=board, ai_settings=ai_settings)
        result = tinker_panel.run()
        
        if result:
            white_drawback, black_drawback, updated_ai_settings = result
            
            # Update AI control flags
            WHITE_AI = updated_ai_settings["WHITE_AI"]
            BLACK_AI = updated_ai_settings["BLACK_AI"]
        
        # Reinitialize the main screen
        p.display.set_mode((WIDTH, HEIGHT))
        p.display.set_caption("Drawback Chess")
    else:
        print("Tinker's Control Panel is not available due to missing pygame_gui.")

def ai_move(board):
    """Executes AI move if it's AI's turn and the game isn't over."""
    global game_over, winner_color

    if not HAS_AI:
        print("AI module not available - skipping AI move")
        return

    if not board.is_variant_end():
        move = best_move(board, AI_DEPTH)
        if move:
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
        else:
            print("AI has no legal moves!")

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

def display_help(screen):
    """Display help text with keyboard controls"""
    help_font = p.font.SysFont(None, 20)
    help_texts = [
        "R: Restart Game",
        "F: Flip Board",
        "T: Open Tinker Panel",
        "1: Random White Drawback",
        "2: Random Black Drawback", 
        "W: Toggle White AI",
        "B: Toggle Black AI",
        "H: Toggle Help"
    ]
    
    for i, text in enumerate(help_texts):
        text_surf = help_font.render(text, True, p.Color("white"), p.Color("black"))
        screen.blit(text_surf, (10, HEIGHT - 30 * (len(help_texts) - i)))

def main():
    """Main game loop for Drawback Chess."""
    global game_over, winner_color, WHITE_AI, BLACK_AI
    
    p.init()
    screen = p.display.set_mode((WIDTH, HEIGHT))
    clock = p.time.Clock()
    p.display.set_caption("Drawback Chess")

    load_images()
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
    show_help = True

    while running:
        for event in p.event.get():
            if event.type == p.QUIT:
                running = False

            elif event.type == p.MOUSEBUTTONDOWN:
                x, y = event.pos
                
                # First check if an AI checkbox was clicked
                if check_ai_checkbox_click((x, y)):
                    continue
                
                # Then handle game moves if not in game over state
                if not game_over:
                    # Only allow user input if the current side is not AI
                    if not (WHITE_AI and board.turn == chess.WHITE) and not (BLACK_AI and board.turn == chess.BLACK):
                        row, col = y // SQ_SIZE, x // SQ_SIZE

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
                if event.key == p.K_f:
                    # Flip the board
                    flipped = not flipped
                    print("Board flipping:", flipped)
                elif event.key == p.K_r:
                    # Reset board and game state properly
                    board = DrawbackBoard()
                    assign_random_drawbacks(board)
                    board.reset()

                    selected_square = None
                    game_over = False
                    winner_color = None

                    print("Game restarted!")
                elif event.key == p.K_1:
                    # Change White's drawback randomly
                    change_drawback(board, chess.WHITE)
                elif event.key == p.K_2:
                    # Change Black's drawback randomly
                    change_drawback(board, chess.BLACK)
                elif event.key == p.K_t:
                    # Open Tinker's Control Panel
                    open_tinker_panel(board)
                elif event.key == p.K_h:
                    # Toggle help display
                    show_help = not show_help
                elif event.key == p.K_w:
                    # Toggle White AI
                    WHITE_AI = not WHITE_AI
                    print(f"White AI: {'ON' if WHITE_AI else 'OFF'}")
                elif event.key == p.K_b:
                    # Toggle Black AI
                    BLACK_AI = not BLACK_AI
                    print(f"Black AI: {'ON' if BLACK_AI else 'OFF'}")

        if not game_over:
            # Let AI move if it's AI's turn
            if BLACK_AI and board.turn == chess.BLACK and HAS_AI:
                ai_move(board)
            if WHITE_AI and board.turn == chess.WHITE and HAS_AI:
                ai_move(board)

        draw_board(screen, DIMENSION, WIDTH, HEIGHT, flipped)
        draw_pieces(screen, board, flipped, DIMENSION)
        
        # Display active drawbacks
        display_drawbacks(screen, board)
        
        # Highlight the selected square
        if selected_square is not None:
            row = chess.square_rank(selected_square)
            col = chess.square_file(selected_square)
            if flipped:
                draw_row = row
                draw_col = 7 - col
            else:
                draw_row = 7 - row
                draw_col = col
                
            highlight_surf = p.Surface((SQ_SIZE, SQ_SIZE), p.SRCALPHA)
            highlight_surf.fill((255, 255, 0, 100))
            screen.blit(highlight_surf, (draw_col * SQ_SIZE, draw_row * SQ_SIZE))
            
            # Also highlight legal moves
            for move in board.legal_moves:
                if move.from_square == selected_square:
                    to_row = chess.square_rank(move.to_square)
                    to_col = chess.square_file(move.to_square)
                    
                    if flipped:
                        to_draw_row = to_row
                        to_draw_col = 7 - to_col
                    else:
                        to_draw_row = 7 - to_row
                        to_draw_col = to_col
                    
                    # Draw a circle for the legal move
                    circle_surface = p.Surface((SQ_SIZE, SQ_SIZE), p.SRCALPHA)
                    is_capture = board.piece_at(move.to_square) is not None
                    
                    # Special highlight for king captures
                    target = board.piece_at(move.to_square)
                    if target and target.piece_type == chess.KING:
                        # Bright red highlight for king capture
                        p.draw.circle(circle_surface, (255, 0, 0, 180), 
                                    (SQ_SIZE // 2, SQ_SIZE // 2), SQ_SIZE // 2, 7)
                    elif is_capture:
                        p.draw.circle(circle_surface, (0, 0, 0, 120), 
                                    (SQ_SIZE // 2, SQ_SIZE // 2), SQ_SIZE // 2, 7)
                    else:
                        p.draw.circle(circle_surface, (0, 0, 0, 120), 
                                    (SQ_SIZE // 2, SQ_SIZE // 2), SQ_SIZE // 7)
                    screen.blit(circle_surface, (to_draw_col * SQ_SIZE, to_draw_row * SQ_SIZE))

        if game_over and winner_color is not None:
            display_winner(screen, winner_color)
            
        # Display help if enabled
        if show_help:
            display_help(screen)
        
        # Display AI status
        display_ai_status(screen)

        clock.tick(FPS)
        p.display.flip()

    p.quit()

if __name__ == "__main__":
    main()
