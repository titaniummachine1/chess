import numpy as np
import chess
from GameState.movegen import DrawbackBoard
import AI.evaluation as evaluation

# Add a global transposition table.
transposition_table = {}

def score_move(board, move):
    """
    Simple move-ordering heuristic with king capture priority:
    1. King captures are always preferred (highest priority)
    2. Other captures based on MVV-LVA (Most Valuable Victim - Least Valuable Aggressor)
    3. Non-captures have lowest priority
    """
    captured_piece = board.piece_at(move.to_square)
    
    # If capturing the king, give it maximum priority
    if captured_piece and captured_piece.piece_type == chess.KING:
        return 1000000  # Extremely high priority for king capture
    
    if captured_piece:
        attacker = board.piece_at(move.from_square)
        # MVV-LVA approach:
        # capturedValue - (1/10)*attackerValue
        # This tries to encourage big captures and cheap attackers.
        victim_value = evaluation.get_piece_value(board, captured_piece.piece_type, captured_piece.color)
        attacker_value = evaluation.get_piece_value(board, attacker.piece_type, attacker.color)
        return victim_value * 10 - attacker_value  # scaled so that big captures stand out
    # Non-captures => 0
    return 0

def negamax(board, depth, alpha, beta):
    """
    Negamax with alpha-beta pruning and basic move-ordering.
    Correctly handles Drawback Chess where kings can be captured.
    """
    # Transposition table check
    board_key = board.fen()
    if board_key in transposition_table:
        stored_depth, stored_score = transposition_table[board_key]
        if stored_depth >= depth:
            return stored_score

    # Check if a king has been captured (game over)
    white_king_alive = any(p.piece_type == chess.KING and p.color == chess.WHITE
                           for p in board.piece_map().values())
    black_king_alive = any(p.piece_type == chess.KING and p.color == chess.BLACK
                           for p in board.piece_map().values())
    
    # If a king is captured, return the appropriate win/loss score
    if not white_king_alive:
        return -evaluation.Score.CHECKMATE.value  # Black wins
    if not black_king_alive:
        return evaluation.Score.CHECKMATE.value   # White wins
    
    # Base case for regular evaluation
    if depth == 0:
        eval_score = evaluation.evaluate(board)
        # Optionally comment out debug prints here.
        # print(f"Depth 0 evaluation: {eval_score}")
        return eval_score

    max_score = -evaluation.Score.CHECKMATE.value
    
    # First check for immediate king captures
    for move in board.generate_legal_moves():
        captured = board.piece_at(move.to_square)
        if captured and captured.piece_type == chess.KING:
            # Immediate king capture is a win
            return evaluation.Score.CHECKMATE.value
    
    # Get all legal moves
    moves = list(board.generate_legal_moves())

    if not moves:
        # No legal moves, but in Drawback Chess this isn't necessarily a loss
        # Return a very bad score but not immediate loss
        return -evaluation.Score.CHECKMATE.value // 2

    # Sort moves by a simple heuristic: capture priority
    # Higher score_move => earlier in list => improved pruning
    moves.sort(key=lambda mv: score_move(board, mv), reverse=True)

    for move in moves:
        new_board = board.copy()
        new_board.push(move)
        
        # Check for immediate win after our move
        captured = board.piece_at(move.to_square)
        if captured and captured.piece_type == chess.KING:
            return evaluation.Score.CHECKMATE.value  # Immediate win

        score = -negamax(new_board, depth - 1, -beta, -alpha)

        if score > max_score:
            max_score = score

        alpha = max(alpha, score)
        if alpha >= beta:
            # beta cutoff
            break

    # Store result in transposition table.
    transposition_table[board_key] = (depth, max_score)
    
    # print(f"Depth {depth} max score: {max_score}")
    return max_score

def best_move(board, depth) -> int:
    """
    Determines the best move using Negamax with alpha-beta and basic move-ordering.
    Prioritizes king captures in Drawback Chess.
    """
    max_score = -evaluation.Score.CHECKMATE.value
    chosen_move = None

    # Gather all legal moves
    moves = list(board.generate_legal_moves())
    
    if not moves:
        print("AI has no legal moves.")
        return None
    
    # Check for immediate king captures
    for move in moves:
        captured_piece = board.piece_at(move.to_square)
        if captured_piece and captured_piece.piece_type == chess.KING:
            print("AI finds king capture!")
            return move  # Immediately return the king capture move
    
    # Sort moves for better pruning
    moves.sort(key=lambda mv: score_move(board, mv), reverse=True)

    alpha = -evaluation.Score.CHECKMATE.value
    beta = evaluation.Score.CHECKMATE.value

    for move in moves:
        new_board = board.copy()
        new_board.push(move)
        score = -negamax(new_board, depth - 1, -beta, -alpha)

        if score > max_score:
            max_score = score
            chosen_move = move

        alpha = max(alpha, score)
        if alpha >= beta:
            break

    if chosen_move is None:
        # If we somehow have no best move but do have legal moves,
        # just choose a random one to avoid crashes
        if moves:
            chosen_move = moves[0]
            print(f"AI choosing random move {chosen_move}")
    else:
        print(f"AI chooses {chosen_move}, eval={max_score}")

    return chosen_move
