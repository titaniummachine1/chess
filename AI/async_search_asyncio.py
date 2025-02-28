import asyncio
import sys
from AI.search import best_move  # Blocking search function
from GameState.movegen import DrawbackBoard

def get_initial_board():
    # Initialize a new board using your custom DrawbackBoard and reset it.
    board = DrawbackBoard()
    board.reset()
    return board

async def run_search(board, depth):
    loop = asyncio.get_running_loop()
    # Offload the blocking best_move call to an executor;
    # This allows the event loop to process UI events in the meantime.
    result = await loop.run_in_executor(None, best_move, board, depth)
    return result

async def async_main():
    board = get_initial_board()
    # Await the best move asynchronously
    best_move_result = await run_search(board, depth=4)
    print("bestmove", best_move_result)
    sys.stdout.flush()

if __name__ == '__main__':
    asyncio.run(async_main())
