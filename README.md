# Drawback Chess

A creative chess variant where each player has a secret handicap ("drawback") that affects their gameplay. This implementation includes both a playable game and an AI opponent.

## Features

- Over 100 unique drawbacks affecting movement, captures, and win conditions
- AI opponent with drawback-aware strategy
- Beautiful PyGame-based UI
- Async engine for smooth gameplay
- Elo-based drawback balancing system

## Installation

```bash
pip install -r requirements.txt
```

## Quick Start

```bash
python -r drawback_chess.main
```

## Project Structure

```
drawback_chess/
├── core/                 # Core game logic
│   ├── board.py         # Board representation
│   ├── piece.py         # Piece logic
│   └── movegen.py       # Move generation
├── drawbacks/           # Drawback implementations
│   ├── base.py          # Base drawback class
│   └── registry.py      # Drawback registration
├── ai/                  # AI implementation
│   ├── engine.py        # Main engine
│   └── evaluation.py    # Position evaluation
├── ui/                  # User interface
│   ├── game_window.py   # Main game window
│   └── components/      # UI components
└── utils/              # Utility functions
```

## Development

1. Clone the repository
2. Install development dependencies: `pip install -r requirements-dev.txt`
3. Run tests: `pytest tests/`

## Contributing

See CONTRIBUTING.md for guidelines.

## License

MIT License - see LICENSE file for details.