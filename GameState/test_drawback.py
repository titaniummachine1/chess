"""
Utility script to test a specific drawback for legal moves
"""
import chess
from movegen import DrawbackBoard
from drawback_manager import get_drawback_function

def test_drawback_moves(drawback_name, color=chess.WHITE):
    """Test a specific drawback to see which moves it allows or blocks"""
    assert drawback_name is not None, "Drawback name cannot be None"
    assert color in [chess.WHITE, chess.BLACK], f"Invalid color: {color}"
    
    board = DrawbackBoard()
    board.reset()
    
    # Apply the drawback to test
    if color == chess.WHITE:
        board.set_white_drawback(drawback_name)
    else:
        board.set_black_drawback(drawback_name)
    
    # Set the turn to the color with the drawback
    if board.turn != color:
        board.push(chess.Move.null())  # Change turn without altering the board
    
    # Get the drawback function
    check_func = get_drawback_function(drawback_name)
    assert check_func is not None, f"No check function found for drawback '{drawback_name}'"
        
    # Generate moves without drawbacks first
    standard_moves = list(super(DrawbackBoard, board).generate_pseudo_legal_moves())
    print(f"Standard moves count: {len(standard_moves)}")
    
    # Test each move with the drawback
    legal_moves = []
    illegal_moves = []
    
    for move in standard_moves:
        is_illegal = check_func(board, move, color)
        if is_illegal:
            illegal_moves.append(move)
        else:
            legal_moves.append(move)
    
    print(f"\nDrawback '{drawback_name}' results:")
    print(f"  Legal moves: {len(legal_moves)}")
    print(f"  Illegal moves: {len(illegal_moves)}")
    
    # Print sample legal moves
    if legal_moves:
        print("\nSample legal moves:")
        for i, move in enumerate(legal_moves[:5]):
            from_piece = board.piece_at(move.from_square)
            to_piece = board.piece_at(move.to_square)
            piece_name = chess.piece_name(from_piece.piece_type) if from_piece else "?"
            capture = "captures" if to_piece else "to"
            target = chess.piece_name(to_piece.piece_type) if to_piece else "empty"
            print(f"  {i+1}. {piece_name} {move.uci()} ({capture} {target})")
    
    return legal_moves, illegal_moves

if __name__ == "__main__":
    import sys
    drawback = "chivalry" if len(sys.argv) <= 1 else sys.argv[1]
    test_drawback_moves(drawback)
