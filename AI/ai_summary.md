# Drawback Chess - AI System Documentation

## Overview

The Drawback Chess AI system is a custom chess engine designed specifically for the Drawback Chess variant. It features a modular architecture with specialized components for position evaluation, move search, opening book handling, and asynchronous operation within a GUI environment.

## System Architecture

The AI system consists of several interconnected modules:

```
┌─────────────────┐     ┌──────────────────┐     ┌───────────────────┐
│  Main Game UI   │────▶│  Async Handler   │────▶│  Engine Core      │
└─────────────────┘     └──────────────────┘     └───────────────────┘
                                                       │
                                                       ▼
┌─────────────────┐     ┌──────────────────┐     ┌───────────────────┐
│  Book Handler   │◀───▶│  Search Engine   │◀───▶│  Evaluation       │
└─────────────────┘     └──────────────────┘     └───────────────────┘
       │                        │                       │
       ▼                        ▼                       ▼
┌─────────────────┐     ┌──────────────────┐     ┌───────────────────┐
│  Opening Books  │     │  Zobrist Hashing │     │  Piece-Square     │
└─────────────────┘     └──────────────────┘     └───────────────────┘
```

### Core Modules

1. **Engine Core (`engine_core.py`)**
   - Central interface providing unified access to all AI components
   - Manages flow between search engine, evaluation, and book systems
   - Provides simplified interfaces for main game code to use

2. **Async Handler (`enhanced_async_engine.py`)**
   - Manages asynchronous search operations to prevent UI blocking
   - Provides status updates and progress reporting
   - Handles search cancellation and state management

3. **Search Engine (`drawback_sunfish.py`)**
   - Implements alpha-beta negamax search algorithm
   - Optimized with transposition tables, move ordering, and quiescence search
   - Specifically adapted for Drawback Chess rules and restrictions

4. **Evaluation (`evaluation.py`)**
   - Position evaluation considering piece values, placement, and mobility
   - Phase-based evaluation (opening, middlegame, endgame)
   - Special handling for Drawback Chess variant rules

5. **Opening Book System (`book_handler.py`, `book_parser.py`)**
   - Provides strong pre-computed opening moves
   - Statistical weighting for move selection with variability
   - Piece-square table adjustments based on opening themes

6. **Utility Modules**
   - `zobrist_hash.py`: Efficient position hashing for transposition tables
   - `piece_square_table.py`: Position-dependent piece evaluation data
   - `ai_utils.py`: Common constants and helper functions

## Search Algorithm

The engine uses an enhanced alpha-beta negamax search with:

- **Iterative Deepening**: Incrementally increases search depth for better time management
- **Move Ordering**: Orders moves to maximize alpha-beta pruning efficiency:
  1. Previously found best move (from transposition table)
  2. Captures (ordered by MVV-LVA - Most Valuable Victim, Least Valuable Attacker)
  3. Killer moves (non-captures that caused beta cutoffs)
  4. History heuristic moves (moves that were good in similar positions)
- **Transposition Tables**: Cache previously analyzed positions using Zobrist hashing
- **Null Move Pruning**: Skips turns to quickly identify non-tactical positions
- **Late Move Reduction**: Reduces search depth for moves unlikely to be best
- **Quiescence Search**: Continues searching captures beyond main search depth for tactical stability

## Position Evaluation

The evaluation function considers:

- **Material Balance**: Standard piece values enhanced with positional context
- **Piece Placement**: Position-dependent values using piece-square tables
- **Mobility**: Number and quality of available legal moves
- **Pawn Structure**: Analysis of pawn formations including:
  - Doubled/isolated pawns (penalized)
  - Passed pawns (rewarded)
  - Pawn shields for king safety
- **King Safety**: Distance from opponent pieces and pawn shield evaluation
- **Special Drawback Considerations**:
  - Variant win/loss detection
  - Mobility restrictions based on drawbacks
  - Adaptations for unique drawback rules

## Drawback-Specific Adaptations

The AI includes special handling for Drawback Chess mechanics:

- **Drawback Awareness**: Engine considers active drawbacks when evaluating positions
- **Legal Move Filtering**: Special handling for the unique move legality rules
- **King Capture Detection**: Immediate recognition of king capture possibilities
- **Variant Loss Detection**: Recognition of special drawback-related loss conditions
- **Mobility Adjustments**: Enhanced evaluation of move options under drawback restrictions

## Usage Pattern

From the main game loop:

```python
# Start a search (non-blocking)
start_search(board, depth, time_limit)

# In main game loop:
if player_turn == AI_COLOR:
    if not search_in_progress:
        # Start a new search
        start_search(board, depth, time_limit)
        search_in_progress = True
    elif is_search_complete():
        # Get and apply the AI move
        move = get_result()
        if move:
            board.push(move)
        search_in_progress = False
        reset_search()
    else:
        # Show search progress in UI
        status = get_progress()
        display_status(status)
```

## Performance Considerations

- **Transposition Tables**: Cache hit rate directly impacts performance
- **Move Ordering**: Efficient move ordering can reduce search space by >90%
- **Search Depth**: Each additional ply increases computational load ~6-10x
- **Asynchronous Operation**: Prevents UI freezing during search
- **Time Management**: Engine adjusts search based on position complexity and time remaining

## Future Enhancements

Potential areas for improvement:

1. **Neural Network Evaluation**: Replace handcrafted evaluation with learned features
2. **Endgame Tablebases**: Add support for standard chess endgame tablebases
3. **Parallel Search**: Multi-threaded search to utilize multiple cores
4. **Learning Capability**: Adjustment of evaluation weights based on game results
5. **Opening Book Expansion**: Support for more diverse opening repertoires
6. **Drawback-Specific Heuristics**: Additional specialized knowledge for each drawback type 