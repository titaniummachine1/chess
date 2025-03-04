import pygame as p
import chess
import random
import asyncio
import utils

from utils import load_images, draw_board, draw_pieces, draw_legal_move_indicators
from GameState.movegen import DrawbackBoard
from GameState.drawback_manager import DRAWBACKS
from Globals import FPS, AI_DEPTH, WHITE_AI, BLACK_AI, DRAWBACKS
from utils import WIDTH, HEIGHT, BOARD_HEIGHT, BOARD_Y_OFFSET, BOARD_X_OFFSET, DIMENSION, SQ_SIZE

# Use the constant defined in utils for board height
utils.WIDTH = 800
HEIGHT = 760
BOARD_HEIGHT = 640
BOARD_Y_OFFSET = 80
BOARD_X_OFFSET = 80
DIMENSION = 8
SQ_SIZE = BOARD_HEIGHT // DIMENSION

# UI panel setup
from ui.tinker_panel import TinkerPanel
HAS_TINKER_PANEL = True
print("Tinker Panel UI loaded successfully")

# Import AI async functions
print("Attempting to import AI module...")
from AI.async_engine import start_search, get_progress, get_result, is_search_complete, reset_search
HAS_AI = True
print("AI module imported successfully")


# Global state
game_over = False
winner_color = None
flipped = False

ai_move_cooldown = 0
tinker_button_rect = p.Rect(WIDTH - 120, 10, 100, 35)
search_in_progress = False

def display_drawbacks(screen, board, flipped):
    font = p.font.SysFont(None, 22)
    white_drawback = board.get_active_drawback(chess.WHITE) or "None"
    black_drawback = board.get_active_drawback(chess.BLACK) or "None"
    
    # Format the drawback names for display
    white_display = white_drawback.replace('_', ' ').title()
    black_display = black_drawback.replace('_', ' ').title()
    
    # Create the text surfaces
    white_text = font.render(f"White: {white_display}", True, p.Color("white"), p.Color("black"))
    black_text = font.render(f"Black: {black_display}", True, p.Color("black"), p.Color("white"))
    
    # Position based on flipped state - this ensures they're always on the correct side
    if not flipped:
        # Flipped: White on bottom of screen, black on top
        screen.blit(white_text, (10, HEIGHT - 30))
        screen.blit(black_text, (10, 10))
    else:
        # Normal: White on top of screen, black on bottom
        screen.blit(white_text, (10, 10))
        screen.blit(black_text, (10, HEIGHT - 30))

def display_current_turn(screen, board):
    font = p.font.SysFont(None, 22)
    turn_text = "White's Turn" if board.turn == chess.WHITE else "Black's Turn"
    color = p.Color("white") if board.turn == chess.WHITE else p.Color("black")
    bg_color = p.Color("black") if board.turn == chess.WHITE else p.Color("white")
    text_surf = font.render(turn_text, True, color, bg_color)
    screen.blit(text_surf, (WIDTH//2 - text_surf.get_width()//2, 10))

def display_winner(screen, winner_color):
    font = p.font.Font(None, 50)
    text = f"{'White' if winner_color == chess.WHITE else 'Black'} wins by capturing the king! Press 'R' to restart."
    text_surf = font.render(text, True, p.Color("black"), p.Color("gold"))
    text_rect = text_surf.get_rect(center=(WIDTH//2, HEIGHT//2))
    screen.blit(text_surf, text_rect)
    p.display.flip()

def draw_tinker_button(screen):
    font = p.font.SysFont(None, 22)
    p.draw.rect(screen, (100,100,150), tinker_button_rect)
    text = font.render("Tinker Panel", True, p.Color("white"))
    text_rect = text.get_rect(center=tinker_button_rect.center)
    screen.blit(text, text_rect)

def open_tinker_panel(board):
    global WHITE_AI, BLACK_AI, flipped, AI_DEPTH
    
    # Stop AI search while in tinker panel to prevent lag
    old_search_in_progress = False
    if 'search_in_progress' in globals() and search_in_progress:
        old_search_in_progress = search_in_progress
        reset_search()  # Stop any ongoing AI search
    
    if HAS_TINKER_PANEL:
        try:
            ai_settings = {"WHITE_AI": WHITE_AI, "BLACK_AI": BLACK_AI, "AI_DEPTH": AI_DEPTH}
            print("Opening Tinker Panel...")
            tinker_panel = TinkerPanel(board_reference=board, ai_settings=ai_settings)
            result = tinker_panel.run()
            if result:
                white_drawback, black_drawback, updated_ai_settings, options = result
                WHITE_AI = updated_ai_settings["WHITE_AI"]
                BLACK_AI = updated_ai_settings["BLACK_AI"]
                AI_DEPTH = updated_ai_settings.get("AI_DEPTH", AI_DEPTH)
                
                # Update drawbacks on the board
                board.set_white_drawback(white_drawback)
                board.set_black_drawback(black_drawback)
                
                # Only flip if the option changed
                old_flipped = flipped
                if options.get("FLIP_BOARD", False):
                    flipped = not old_flipped
                    print(f"Board flipped: {old_flipped} -> {flipped}")
                
                print("Tinker Panel settings applied successfully")
            else:
                print("Tinker Panel closed without changes")
                
            # Restore main window
            p.display.set_mode((WIDTH, HEIGHT))
            p.display.set_caption("Drawback Chess")
            
            # Clear all events that built up while panel was open
            p.event.clear()
            
        except Exception as e:
            print(f"Error in Tinker Panel: {e}")
            import traceback
            traceback.print_exc()
            # Make sure we restore the main window
            p.display.set_mode((WIDTH, HEIGHT))
            p.display.set_caption("Drawback Chess")
    else:
        print("Tinker Panel not available - see above errors for details.")
        
    # Ensure pygame is properly initialized after returning
    p.display.update()

def display_ai_status(screen, board):
    if not HAS_AI:
        return
    font = p.font.SysFont(None, 20)
    player_color = "White" if board.turn == chess.WHITE else "Black"
    drawback = board.get_active_drawback(board.turn) or "None"
    status_text = f"{player_color} AI ({drawback.replace('_',' ').title()})"
    status_surf = font.render(status_text, True, p.Color("white"), p.Color("darkblue"))
    thinking_surf = font.render(get_progress(), True, p.Color("white"), p.Color("darkblue"))
    status_rect = status_surf.get_rect(topright=(WIDTH-10,40))
    thinking_rect = thinking_surf.get_rect(topright=(WIDTH-10,65))
    screen.blit(status_surf, status_rect)
    screen.blit(thinking_surf, thinking_rect)

def handle_ai_turn(board):
    """Non-blocking AI turn handler that starts a search if needed,
    or applies the move if search is complete"""
    global game_over, winner_color, ai_move_cooldown, search_in_progress
    
    if not HAS_AI or game_over or board.is_variant_end():
        return
    
    # If AI's turn and no search is in progress, start one
    if not search_in_progress:
        print(f"Starting AI search for turn {board.turn} at depth {AI_DEPTH}")
        start_search(board, AI_DEPTH)
        search_in_progress = True
        return
    
    # If a search is already in progress, check if it's done
    if is_search_complete():
        move = get_result()
        if move is None:
            # No good move found, pick a random legal move
            legal_moves = list(board.legal_moves)
            if legal_moves:
                move = random.choice(legal_moves)
                print(f"No move from search; fallback move: {move}")
            else:
                # No legal moves available
                game_over = True
                winner_color = chess.WHITE if board.turn == chess.BLACK else chess.BLACK
                print("No legal moves available for AI; ending game.")
                search_in_progress = False
                reset_search()
                return
        
        # Apply the selected move
        if move and move in board.legal_moves:
            board.push(move)
            print(f"AI moved: {move}")
            print("Board FEN after AI move:", board.fen())
            
            if not list(board.legal_moves):
                game_over = True
                winner_color = board.turn
                print("No legal moves available for opponent; ending game.")
            
            if board.is_variant_end():
                game_over = True
                winner_color = chess.WHITE if board.is_variant_win() else chess.BLACK
                print(f"Game over! {'White' if winner_color == chess.WHITE else 'Black'} wins!")
            
            ai_move_cooldown = FPS // 2
        else:
            print("AI move invalid.")
        
        # Reset search state for next turn
        search_in_progress = False
        reset_search()

async def async_main():
    global game_over, winner_color, WHITE_AI, BLACK_AI, flipped, ai_move_cooldown, search_in_progress
    p.init()
    screen = p.display.set_mode((WIDTH, HEIGHT))
    clock = p.time.Clock()
    p.display.set_caption("Drawback Chess")
    
    # Load images for pieces at the beginning
    square_size = BOARD_HEIGHT // DIMENSION
    IMAGES = load_images(square_size)
    
    ai_move_cooldown = 0
    board = DrawbackBoard()
    board.reset()
    running = True
    flipped = False
    selected_square = None
    game_over = False
    winner_color = None
    search_in_progress = False

    while running:
        # Process pygame events and update game state
        for event in p.event.get():
            if event.type == p.QUIT:
                running = False
            elif event.type == p.MOUSEBUTTONDOWN:
                x, y = event.pos
                if tinker_button_rect.collidepoint(x, y):
                    open_tinker_panel(board)
                    continue
                if not game_over and not ((WHITE_AI and board.turn == chess.WHITE) or (BLACK_AI and board.turn == chess.BLACK)):
                    board_x = x - BOARD_X_OFFSET
                    board_y = y - BOARD_Y_OFFSET
                    if 0 <= board_y < BOARD_HEIGHT and 0 <= board_x < BOARD_HEIGHT:
                        row, col = board_y // SQ_SIZE, board_x // SQ_SIZE
                        board_row, board_col = (row, 7 - col) if flipped else (7 - row, col)
                        clicked_square = chess.square(board_col, board_row)
                        if selected_square is None:
                            piece = board.piece_at(clicked_square)
                            if piece and piece.color == board.turn:
                                selected_square = clicked_square
                                print(f"Selected {piece.symbol()} at {chess.square_name(clicked_square)}")
                        else:
                            pawn = board.piece_at(selected_square)
                            if pawn and pawn.piece_type == chess.PAWN and (
                                (pawn.color == chess.WHITE and chess.square_rank(clicked_square) == 7) or
                                (pawn.color == chess.BLACK and chess.square_rank(clicked_square) == 0)
                            ):
                                import promotion_panel
                                promo = promotion_panel.run()
                                move_obj = chess.Move(selected_square, clicked_square, promotion=promo)
                            else:
                                move_obj = chess.Move(selected_square, clicked_square)
                            
                            if board.is_legal(move_obj):
                                board.push(move_obj)
                                print(f"Human moved: {move_obj}")
                                selected_square = None
                                if board.is_variant_end():
                                    winner_color = chess.WHITE if board.is_variant_win() else chess.BLACK
                                    game_over = True
                            else:
                                piece = board.piece_at(clicked_square)
                                if piece and piece.color == board.turn:
                                    selected_square = clicked_square
                                    print(f"Selected {piece.symbol()} at {chess.square_name(clicked_square)}")
                                else:
                                    print(f"Illegal move: {chess.square_name(selected_square)} to {chess.square_name(clicked_square)}")
                                    selected_square = None
            elif event.type == p.KEYDOWN:
                if event.key == p.K_r:
                    board = DrawbackBoard()
                    board.reset()
                    selected_square = None
                    game_over = False
                    winner_color = None
                    search_in_progress = False
                    print("Game restarted!")
                elif event.key == p.K_t:
                    open_tinker_panel(board)
                    
        # Handle AI turn - non-blocking approach
        if not game_over:
            if (BLACK_AI and board.turn == chess.BLACK) or (WHITE_AI and board.turn == chess.WHITE):
                handle_ai_turn(board)
                    
        # Draw everything
        screen.fill(p.Color("black"))
        draw_board(screen, DIMENSION, BOARD_HEIGHT, BOARD_HEIGHT, flipped, BOARD_Y_OFFSET, BOARD_X_OFFSET)
        draw_pieces(screen, board, flipped, DIMENSION, BOARD_Y_OFFSET, BOARD_X_OFFSET)
        display_drawbacks(screen, board, flipped)
        display_current_turn(screen, board)
        draw_tinker_button(screen)
        display_ai_status(screen, board)
        
        if selected_square is not None:
            square_size = BOARD_HEIGHT // DIMENSION
            r = chess.square_rank(selected_square)
            c = chess.square_file(selected_square)
            draw_row, draw_col = (r, 7 - c) if flipped else (7 - r, c)
            highlight = p.Surface((square_size, square_size), p.SRCALPHA)
            highlight.fill((255, 255, 0, 100))
            screen.blit(highlight, (BOARD_X_OFFSET + draw_col * square_size, BOARD_Y_OFFSET + draw_row * square_size))
            draw_legal_move_indicators(screen, board, selected_square, flipped, DIMENSION, BOARD_Y_OFFSET, BOARD_X_OFFSET)
        if game_over and winner_color is not None:
            display_winner(screen, winner_color)
        clock.tick(FPS)
        p.display.flip()
        
        # Give more time for background tasks
        await asyncio.sleep(0.01)
    
    p.quit()

if __name__ == "__main__":
    asyncio.run(async_main())