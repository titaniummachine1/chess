##main.py do nto remove this comment you damn idiot
import pygame as p
import chess
import random
import asyncio  # For letting async tasks run briefly each frame
from utils import load_images, draw_board, draw_pieces, draw_legal_move_indicators
from GameState.movegen import DrawbackBoard
from GameState.drawback_manager import DRAWBACKS

# Set BOARD_HEIGHT in utils for consistent square sizing
import utils
BOARD_HEIGHT = 640  # Actual board height
utils.BOARD_HEIGHT = BOARD_HEIGHT

# UI panel (optional)
try:
    from ui.tinker_panel import TinkerPanel
    HAS_TINKER_PANEL = True
except ImportError:
    print("Warning: pygame_gui not found. Tinker Panel disabled.")
    HAS_TINKER_PANEL = False

# Import AI async functions
try:
    from AI.search import best_move
    from AI.async_search import async_best_move, is_thinking, is_search_complete, get_best_move, reset_ai_state
    HAS_AI = True
except ImportError:
    print("Warning: AI module not available.")
    HAS_AI = False

# Game Settings
WIDTH = 800
HEIGHT = 760
BOARD_HEIGHT = 640
BOARD_Y_OFFSET = 80
BOARD_X_OFFSET = 80
DIMENSION = 8
SQ_SIZE = BOARD_HEIGHT // DIMENSION
FPS = 60
AI_DEPTH = 3

# Global state
game_over = False
winner_color = None
flipped = False

# AI control flags (if AI is enabled)
WHITE_AI = False
BLACK_AI = True

# Cooldown to delay successive AI moves
ai_move_cooldown = 0

# Tinker Panel button rect
tinker_button_rect = p.Rect(WIDTH - 120, 10, 100, 35)

AVAILABLE_DRAWBACKS = [
    "no_knight_moves",
    "no_bishop_captures",
    "no_knight_captures",
    "punching_down"
]

def assign_random_drawbacks(board):
    white_drawback = random.choice(AVAILABLE_DRAWBACKS)
    black_drawback = random.choice(AVAILABLE_DRAWBACKS)
    board.set_drawback(chess.WHITE, white_drawback)
    board.set_drawback(chess.BLACK, black_drawback)
    print(f"White drawback: {white_drawback}")
    print(f"Black drawback: {black_drawback}")

def display_drawbacks(screen, board, flipped):
    font = p.font.SysFont(None, 22)
    white_drawback = board.get_active_drawback(chess.WHITE) or "None"
    black_drawback = board.get_active_drawback(chess.BLACK) or "None"
    white_text = font.render(f"White: {white_drawback.replace('_',' ').title()}", True, p.Color("white"), p.Color("black"))
    black_text = font.render(f"Black: {black_drawback.replace('_',' ').title()}", True, p.Color("black"), p.Color("white"))
    if flipped:
        screen.blit(black_text, (10, 10))
        screen.blit(white_text, (10, HEIGHT - 30))
    else:
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
    if HAS_TINKER_PANEL:
        ai_settings = {"WHITE_AI": WHITE_AI, "BLACK_AI": BLACK_AI, "AI_DEPTH": AI_DEPTH}
        tinker_panel = TinkerPanel(board_reference=board, ai_settings=ai_settings)
        result = tinker_panel.run()
        if result:
            white_drawback, black_drawback, updated_ai_settings, options = result
            WHITE_AI = updated_ai_settings["WHITE_AI"]
            BLACK_AI = updated_ai_settings["BLACK_AI"]
            AI_DEPTH = updated_ai_settings.get("AI_DEPTH", AI_DEPTH)
            if options.get("FLIP_BOARD", False):
                flipped = not flipped
                print("Board flipped from Tinker Panel")
        p.display.set_mode((WIDTH, HEIGHT))
        p.display.set_caption("Drawback Chess")
    else:
        print("Tinker Panel not available.")

def display_ai_status(screen, board):
    if not HAS_AI or not is_thinking():
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

def ai_move(board):
    global game_over, winner_color, ai_move_cooldown
    if not HAS_AI or game_over or board.is_variant_end():
        return False
    if is_thinking():
        if is_search_complete():
            move = get_best_move()
            print(f"AI completed search; move: {move}")
            if move and move in board.legal_moves:
                board.push(move)
                print(f"AI moved: {move}")
                if board.is_variant_end():
                    game_over = True
                    winner_color = chess.WHITE if board.is_variant_win() else chess.BLACK
                    print(f"Game over! {'White' if winner_color == chess.WHITE else 'Black'} wins!")
                reset_ai_state()
                ai_move_cooldown = FPS // 2
                return True
            else:
                print("AI move invalid; resetting")
                reset_ai_state()
        return False
    if ai_move_cooldown > 0:
        ai_move_cooldown -= 1
        return False
    if ((WHITE_AI and board.turn == chess.WHITE) or (BLACK_AI and board.turn == chess.BLACK)):
        print(f"Starting AI search at depth {AI_DEPTH}")
        success = async_best_move(board, AI_DEPTH)
        if not success:
            p.time.delay(50)
    return False

def main():
    global game_over, winner_color, WHITE_AI, BLACK_AI, flipped, ai_move_cooldown
    p.init()
    screen = p.display.set_mode((WIDTH, HEIGHT))
    clock = p.time.Clock()
    p.display.set_caption("Drawback Chess")

    # Create and set a new asyncio event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    ai_move_cooldown = 0
    board = DrawbackBoard()
    assign_random_drawbacks(board)
    board.reset()
    running = True
    flipped = False
    selected_square = None
    game_over = False
    winner_color = None

    if HAS_AI:
        reset_ai_state()

    while running:
        for event in p.event.get():
            if event.type == p.QUIT:
                running = False
            elif event.type == p.MOUSEBUTTONDOWN:
                x, y = event.pos
                if tinker_button_rect.collidepoint(x,y):
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
                            move = chess.Move(selected_square, clicked_square)
                            if board.is_legal(move):
                                board.push(move)
                                print(f"Human moved: {move}")
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
                    assign_random_drawbacks(board)
                    board.reset()
                    selected_square = None
                    game_over = False
                    winner_color = None
                    print("Game restarted!")
                elif event.key == p.K_t:
                    open_tinker_panel(board)

        loop.run_until_complete(asyncio.sleep(0))

        if not game_over:
            move_made = False
            if (BLACK_AI and board.turn == chess.BLACK) or (WHITE_AI and board.turn == chess.WHITE):
                move_made = ai_move(board)
                if move_made:
                    p.time.delay(100)
        screen.fill(p.Color("black"))
        draw_board(screen, DIMENSION, BOARD_HEIGHT, BOARD_HEIGHT, flipped, BOARD_Y_OFFSET, BOARD_X_OFFSET)
        draw_pieces(screen, board, flipped, DIMENSION, BOARD_Y_OFFSET, BOARD_X_OFFSET)
        display_drawbacks(screen, board, flipped)
        display_current_turn(screen, board)
        draw_tinker_button(screen)
        display_ai_status(screen, board)
        if selected_square is not None:
            square_size = BOARD_HEIGHT // DIMENSION
            row = chess.square_rank(selected_square)
            col = chess.square_file(selected_square)
            draw_row, draw_col = (row, 7 - col) if flipped else (7 - row, col)
            highlight = p.Surface((square_size, square_size), p.SRCALPHA)
            highlight.fill((255,255,0,100))
            screen.blit(highlight, (BOARD_X_OFFSET + draw_col * square_size, BOARD_Y_OFFSET + draw_row * square_size))
            draw_legal_move_indicators(screen, board, selected_square, flipped, DIMENSION, BOARD_Y_OFFSET, BOARD_X_OFFSET)
        if game_over and winner_color is not None:
            display_winner(screen, winner_color)
        clock.tick(FPS)
        p.display.flip()
    p.quit()

if __name__ == "__main__":
    main()