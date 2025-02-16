from typing import List, Optional, Literal, Union, Set, Tuple
from dataclasses import dataclass, field
from chess.pgn import Game, GameNode, ChildNode
from chess import Move, Color, Board, WHITE, BLACK
from chess.engine import SimpleEngine, Mate, Cp, Score, PovScore


TagKind = Literal[
    "advancedPawn",
    "advantage",
    "anastasiaMate",
    "arabianMate",
    "attackingF2F7",
    "attraction",
    "backRankMate",
    "bishopEndgame",
    "bodenMate",
    "capturingDefender",
    "castling",
    "clearance",
    "coercion",
    "crushing",
    "defensiveMove",
    "discoveredAttack",
    "deflection",
    "doubleBishopMate",
    "doubleCheck",
    "dovetailMate",
    "equality",
    "enPassant",
    "exposedKing",
    "fork",
    "hangingPiece",
    "hookMate",
    "interference",
    "intermezzo",
    "kingsideAttack",
    "knightEndgame",
    "long",
    "mate",
    "mateIn5",
    "mateIn4",
    "mateIn3",
    "mateIn2",
    "mateIn1",
    "oneMove",
    "overloading",
    "pawnEndgame",
    "pin",
    "promotion",
    "queenEndgame",
    "queensideAttack",
    "quietMove",
    "rookEndgame",
    "queenRookEndgame",
    "sacrifice",
    "short",
    "simplification",
    "skewer",
    "smotheredMate",
    "trappedPiece",
    "underPromotion",
    "veryLong",
    "xRayAttack",
    "zugzwang"
]



@dataclass
class Puzzle:
    node: ChildNode
    moves: List[Move]
    cp: int
    tags: List[TagKind]
    game: Game
    pov : Color = field(init=False)
    mainline: List[ChildNode] = field(init=False)

    def __post_init__(self):
        self.pov = not self.game.turn()
        self.mainline = list(self.game.mainline())

@dataclass
class EngineMove:
    move: Move
    score: Score

@dataclass
class NextMovePair:
    node: GameNode
    winner: Color
    best: EngineMove
    second: Optional[EngineMove]



