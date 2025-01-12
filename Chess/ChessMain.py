import pygame as p
import threading  # For the progress window and AI computation
import tkinter as tk  # For the progress window
import ChessEngine
import AI.ChessAI as ChessAI  # Import AI functions
import time

# Player settings
player_one = True  # White: Player
player_two = False  # Black: AI

p.init()

board_width = board_height = 680
dimension = 8
sq_size = board_height // dimension
max_fps = 60
images = {}
colours = [p.Color('#EBEBD0'), p.Color('#769455')]

move_log_panel_width = 210
move_log_panel_height = board_height

# Initialize shared variables in ChessAI module
ChessAI.current_depth = 0
ChessAI.current_evaluation = 0
ChessAI.positions_analyzed = 0
ChessAI.best_move = None
ChessAI.is_computing = False
ChessAI.lock = threading.Lock()

def load_images():
    pieces = ['bR', 'bN', 'bB', 'bQ', 'bK', 'bP', 'wR', 'wN', 'wB', 'wQ', 'wK', 'wP']
    for piece in pieces:
        images[piece] = p.transform.smoothscale(
            p.image.load(f'Chess/images/{piece}.png'), (sq_size, sq_size)
        )

def show_progress_window():
    """Tkinter window for showing engine progress."""
    root = tk.Tk()
    root.title("AI Analysis Progress")
    root.geometry("300x200")

    # Labels to display depth, evaluation, and positions analyzed
    depth_label = tk.Label(root, text="Depth: 0", font=("Arial", 14))
    eval_label = tk.Label(root, text="Eval: 0.00 (cp)", font=("Arial", 14))
    positions_label = tk.Label(root, text="Positions: 0", font=("Arial", 14))

    depth_label.pack(pady=10)
    eval_label.pack(pady=10)
    positions_label.pack(pady=10)

    def update_labels():
        """Update labels with real-time AI analysis progress."""
        with ChessAI.lock:  # Ensure thread-safe access
            depth = ChessAI.current_depth
            eval_cp = ChessAI.current_evaluation
            positions = ChessAI.positions_analyzed
        depth_label.config(text=f"Depth: {depth}")
        eval_label.config(text=f"Eval: {eval_cp / 100:.2f} (cp)")
        positions_label.config(text=f"Positions: {positions}")
        root.after(100, update_labels)  # Update every 100 ms

    root.after(0, update_labels)
    root.mainloop()

def ai_move_thread(game_state, valid_moves):
    """Thread target for computing the AI's best move."""
    with ChessAI.lock:
        ChessAI.is_computing = True
        ChessAI.best_move = None
        # Reset progress variables
        ChessAI.current_depth = 0
        ChessAI.current_evaluation = 0
        ChessAI.positions_analyzed = 0

    best_move, depth, evaluation = ChessAI.find_best_move(game_state, valid_moves)

    with ChessAI.lock:
        ChessAI.best_move = best_move
        ChessAI.is_computing = False

def main():
    # Run the progress window in a separate thread so it doesn't block the main GUI.
    threading.Thread(target=show_progress_window, daemon=True).start()

    screen = p.display.set_mode((board_width + move_log_panel_width, board_height))
    clock = p.time.Clock()
    screen.fill(p.Color('white'))
    move_log_font = p.font.SysFont('Arial', 14, False, False)
    game_state = ChessEngine.GameState()
    valid_moves = game_state.get_valid_moves()
    move_made = False
    load_images()
    running = True
    square_selected = ()
    player_clicks = []
    game_over = False
    ai_thread = None  # To keep track of the AI thread

    while running:
        human_turn = (game_state.white_to_move and player_one) or (not game_state.white_to_move and player_two)

        for event in p.event.get():
            if event.type == p.QUIT:
                running = False

            elif event.type == p.MOUSEBUTTONDOWN:
                if not game_over and human_turn and not ChessAI.is_computing:
                    location = p.mouse.get_pos()
                    column, row = location[0] // sq_size, location[1] // sq_size
                    if square_selected == (row, column) or column >= dimension:
                        square_selected = ()
                        player_clicks = []
                    else:
                        square_selected = (row, column)
                        player_clicks.append(square_selected)
                    if len(player_clicks) == 2:
                        move = ChessEngine.Move(player_clicks[0], player_clicks[1], game_state.board)
                        for i in range(len(valid_moves)):
                            if move == valid_moves[i]:
                                game_state.make_move(valid_moves[i])
                                move_log_font = p.font.SysFont('Arial', 14, False, False)
                                move_made = True
                                square_selected = ()
                                player_clicks = []
                                break
                        if not move_made:
                            player_clicks = [square_selected]

            elif event.type == p.KEYDOWN:
                if event.key == p.K_z:  # Undo move
                    game_state.undo_move()
                    game_state.undo_move()
                    move_made = True
                    game_over = False
                if event.key == p.K_r:  # Reset game
                    game_state = ChessEngine.GameState()
                    valid_moves = game_state.get_valid_moves()
                    square_selected = ()
                    player_clicks = []
                    move_made = False
                    game_over = False

        if not game_over and not human_turn and not ChessAI.is_computing and ChessAI.best_move is None:
            # Start the AI computation in a separate thread
            ai_thread = threading.Thread(target=ai_move_thread, args=(game_state, valid_moves), daemon=True)
            ai_thread.start()

        if not game_over and not human_turn and ChessAI.best_move is not None:
            # AI has finished computing its move
            game_state.make_move(ChessAI.best_move)
            move_made = True
            ChessAI.best_move = None
            valid_moves = game_state.get_valid_moves()

        if move_made:
            valid_moves = game_state.get_valid_moves()
            move_made = False

        draw_game_state(screen, game_state, square_selected, move_log_font)

        if game_state.checkmate or game_state.stalemate:
            game_over = True
            text = 'Stalemate' if game_state.stalemate else f"{'Black' if game_state.white_to_move else 'White'} wins by checkmate"
            draw_endgame_text(screen, text)

        clock.tick(max_fps)
        p.display.flip()

def draw_game_state(screen, game_state, square_selected, move_log_font):
    draw_board(screen)
    highlight_squares(screen, game_state, square_selected)
    draw_pieces(screen, game_state.board)
    draw_move_log(screen, game_state, move_log_font)

def draw_board(screen):
    for row in range(dimension):
        for column in range(dimension):
            colour = colours[((row + column) % 2)]
            p.draw.rect(screen, colour, p.Rect(column * sq_size, row * sq_size, sq_size, sq_size))

def highlight_squares(screen, game_state, square_selected):
    if square_selected != ():
        row, column = square_selected
        if game_state.board[row][column][0] == ('w' if game_state.white_to_move else 'b'):
            s = p.Surface((sq_size, sq_size))
            s.set_alpha(70)
            s.fill(p.Color('yellow'))
            screen.blit(s, (column * sq_size, row * sq_size))

    if len(game_state.move_log) != 0:
        last_move = game_state.move_log[-1]
        start_row, start_column = last_move.start_row, last_move.start_column
        end_row, end_column = last_move.end_row, last_move.end_column
        s = p.Surface((sq_size, sq_size))
        s.set_alpha(70)
        s.fill(p.Color('yellow'))
        screen.blit(s, (start_column * sq_size, start_row * sq_size))
        screen.blit(s, (end_column * sq_size, end_row * sq_size))

def draw_pieces(screen, board):
    for row in range(dimension):
        for column in range(dimension):
            piece = board[row][column]
            if piece != '--':
                screen.blit(images[piece], p.Rect(column * sq_size, row * sq_size, sq_size, sq_size))

def draw_move_log(screen, game_state, font):
    move_log_area = p.Rect(board_width, 0, move_log_panel_width, move_log_panel_height)
    p.draw.rect(screen, p.Color('#2d2d2e'), move_log_area)
    move_log = game_state.move_log
    move_texts = []
    for i in range(0, len(move_log), 2):
        move_string = f'{i // 2 + 1}. {str(move_log[i])} '
        if i + 1 < len(move_log):
            move_string += f'{str(move_log[i + 1])} '
        move_texts.append(move_string)

    move_per_row = 2
    padding = 5
    line_spacing = 2
    text_y = padding
    for i in range(0, len(move_texts), move_per_row):
        text = ''
        for j in range(move_per_row):
            if i + j < len(move_texts):
                text += move_texts[i + j]
        text_object = font.render(text, True, p.Color('whitesmoke'))
        text_location = move_log_area.move(padding, text_y)
        screen.blit(text_object, text_location)
        text_y += text_object.get_height() + line_spacing

def draw_endgame_text(screen, text):
    font = p.font.SysFont('Helvetica', 32, True, False)
    text_object = font.render(text, True, p.Color('gray'), p.Color('mintcream'))
    text_location = p.Rect(0, 0, board_width, board_height).move(
        board_width / 2 - text_object.get_width() / 2,
        board_height / 2 - text_object.get_height() / 2
    )
    screen.blit(text_object, text_location)
    text_object = font.render(text, True, p.Color('black'))
    screen.blit(text_object, text_location.move(2, 2))

if __name__ == '__main__':
    main()
