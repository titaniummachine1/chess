import pygame as p
import chess
import random
from utils import load_images, draw_board, draw_pieces, apply_legal_move, draw_highlights
from GameState.movegen import DrawbackBoard
from GameState.drawback_manager import DRAWBACKS
from AI.search import best_move

WIDTH, HEIGHT = 680, 680
DIMENSION = 8
SQ_SIZE = HEIGHT // DIMENSION
FPS = 15
AI_DEPTH = 2

WHITE_AI = False
BLACK_AI = True

def assign_drawbacks(board):
    board.set_drawback(chess.WHITE, "no_knight_moves")
    board.set_drawback(chess.BLACK, "no_knight_moves")
    print("Drawbacks: no_knight_moves assigned to both players.")

def display_winner(screen, winner_color):
    font = p.font.Font(None, 50)
    text = f"{'White' if winner_color == chess.WHITE else 'Black'} wins! Press 'R' to restart."
    text_surf = font.render(text, True, p.Color("black"), p.Color("gold"))
    text_rect = text_surf.get_rect(center=(WIDTH // 2, HEIGHT // 2))
    screen.blit(text_surf, text_rect)
    p.display.flip()

def ai_move(board):
    global game_over, winner_color
    if not board.is_variant_end():
        move = best_move(board, AI_DEPTH)
        if move:
            board.push(move)
            print(f"AI moved: {move}")
            if board.is_variant_end():
                game_over = True
                winner_color = chess.WHITE if board.is_variant_win() else chess.BLACK
                print(f"Game over! {'White' if winner_color == chess.WHITE else 'Black'} wins!")
        else:
            print("AI has no legal moves!")

def main():
    p.init()
    screen = p.display.set_mode((WIDTH, HEIGHT))
    clock = p.time.Clock()
    p.display.set_caption("Drawback Chess")

    load_images()
    board = DrawbackBoard()
    assign_drawbacks(board)
    board.reset()

    global game_over, winner_color
    running = True
    flipped = True
    selected_square = None
    game_over = False
    winner_color = None

    while running:
        for event in p.event.get():
            if event.type == p.QUIT:
                running = False

            elif event.type == p.MOUSEBUTTONDOWN and not game_over:
                # Only allow user input if the current side is not AI
                if not (WHITE_AI and board.turn == chess.WHITE) and not (BLACK_AI and board.turn == chess.BLACK):
                    x, y = event.pos
                    row, col = y // SQ_SIZE, x // SQ_SIZE
                    if flipped:
                        row, col = 7 - row, 7 - col
                    clicked_square = row * 8 + col

                    if selected_square is None:
                        if board.piece_at(clicked_square) and board.color_at(clicked_square) == board.turn:
                            selected_square = (row, col)
                    else:
                        move_coords = (selected_square, (row, col))
                        new_selected_square = apply_legal_move(board, move_coords, selected_square)
                        selected_square = new_selected_square

                        draw_board(screen, DIMENSION, WIDTH, HEIGHT)
                        draw_pieces(screen, board, flipped, DIMENSION)
                        p.display.flip()

                        if board.is_variant_end():
                            winner_color = chess.WHITE if board.is_variant_win() else chess.BLACK
                            game_over = True

            elif event.type == p.KEYDOWN:
                if event.key == p.K_f:
                    flipped = not flipped
                elif event.key == p.K_r:
                    board = DrawbackBoard()
                    assign_drawbacks(board)
                    board.reset()
                    selected_square = None
                    game_over = False
                    winner_color = None
                    print("Game restarted!")

        if not game_over:
            # Let AI move if it's AI's turn
            if BLACK_AI and board.turn == chess.BLACK:
                ai_move(board)
            if WHITE_AI and board.turn == chess.WHITE:
                ai_move(board)

        draw_board(screen, DIMENSION, WIDTH, HEIGHT)
        if selected_square is not None:
            draw_highlights(screen, board, selected_square, flipped)
        draw_pieces(screen, board, flipped, DIMENSION)

        if game_over and winner_color is not None:
            display_winner(screen, winner_color)

        clock.tick(FPS)
        p.display.flip()

    p.quit()

if __name__ == "__main__":
    main()
