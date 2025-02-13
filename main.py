import sqlite3
import pickle

import sys
import chess.pgn
from chess.engine import SimpleEngine, Mate, Cp, Score, PovScore
from typing import List, Optional, Literal, Union, Set, Tuple
import copy
from io import StringIO
import math
from dataclasses import dataclass, field
from chess.pgn import Game, GameNode, ChildNode
import util
from chess import Move, Color, Board, WHITE, BLACK
from chess import KING, QUEEN, ROOK, BISHOP, KNIGHT, PAWN
from chess import (
    square_rank,
    square_file,
    Board,
    SquareSet,
    Piece,
    PieceType,
    square_distance,
)

pair_limit = chess.engine.Limit(depth = 50, time = 30, nodes = 25_000_000)
mate_defense_limit = chess.engine.Limit(depth = 15, time = 10, nodes = 8_000_000)

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

from util import get_next_move_pair, material_count, material_diff, is_up_in_material, maximum_castling_rights, win_chances, count_mates


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
# @dataclass
# class Puzzle:
#     id: str
#     game: Game
#     pov : Color = field(init=False)
#     mainline: List[ChildNode] = field(init=False)
#     cp: int

    # def __post_init__(self):
    #     self.pov = not self.game.turn()
    #     self.mainline = list(self.game.mainline())

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



def advanced_pawn(puzzle: Puzzle) -> bool:
    for node in puzzle.mainline[1::2]:
        if util.is_very_advanced_pawn_move(node):
            return True
    return False


def double_check(puzzle: Puzzle) -> bool:
    for node in puzzle.mainline[1::2]:
        if len(node.board().checkers()) > 1:
            return True
    return False


def sacrifice(puzzle: Puzzle) -> bool:
    # down in material compared to initial position, after moving
    diffs = [util.material_diff(n.board(), puzzle.pov) for n in puzzle.mainline]
    initial = diffs[0]
    for d in diffs[1::2][1:]:
        if d - initial <= -2:
            return not any(n.move.promotion for n in puzzle.mainline[::2][1:])
    return False


def x_ray(puzzle: Puzzle) -> bool:
    for node in puzzle.mainline[1::2][1:]:
        if not util.is_capture(node):
            continue
        prev_op_node = node.parent
        assert isinstance(prev_op_node, ChildNode)
        if (
            prev_op_node.move.to_square != node.move.to_square
            or util.moved_piece_type(prev_op_node) == KING
        ):
            continue
        prev_pl_node = prev_op_node.parent
        assert isinstance(prev_pl_node, ChildNode)
        if prev_pl_node.move.to_square != prev_op_node.move.to_square:
            continue
        if prev_op_node.move.from_square in SquareSet.between(
            node.move.from_square, node.move.to_square
        ):
            return True

    return False


def fork(puzzle: Puzzle) -> bool:
    for node in puzzle.mainline[1::2][:-1]:
        if util.moved_piece_type(node) is not KING:
            board = node.board()
            if util.is_in_bad_spot(board, node.move.to_square):
                continue
            nb = 0
            for piece, square in util.attacked_opponent_squares(
                board, node.move.to_square, puzzle.pov
            ):
                if piece.piece_type == PAWN:
                    continue
                if util.king_values[piece.piece_type] > util.king_values[
                    util.moved_piece_type(node)
                ] or (
                    util.is_hanging(board, piece, square)
                    and square
                    not in board.attackers(not puzzle.pov, node.move.to_square)
                ):
                    nb += 1
            if nb > 1:
                return True
    return False


def hanging_piece(puzzle: Puzzle) -> bool:
    to = puzzle.mainline[1].move.to_square
    captured = puzzle.mainline[0].board().piece_at(to)
    if puzzle.mainline[0].board().is_check() and (
        not captured or captured.piece_type == PAWN
    ):
        return False
    if captured and captured.piece_type != PAWN:
        if util.is_hanging(puzzle.mainline[0].board(), captured, to):
            op_move = puzzle.mainline[0].move
            op_capture = puzzle.game.board().piece_at(op_move.to_square)
            if (
                op_capture
                and util.values[op_capture.piece_type]
                >= util.values[captured.piece_type]
                and op_move.to_square == to
            ):
                return False
            if len(puzzle.mainline) < 4:
                return True
            if util.material_diff(puzzle.mainline[3].board(), puzzle.pov) >= util.material_diff(
                puzzle.mainline[1].board(), puzzle.pov
            ):
                return True
    return False


def trapped_piece(puzzle: Puzzle) -> bool:
    for node in puzzle.mainline[1::2][1:]:
        square = node.move.to_square
        captured = node.parent.board().piece_at(square)
        if captured and captured.piece_type != PAWN:
            prev = node.parent
            assert isinstance(prev, ChildNode)
            if prev.move.to_square == square:
                square = prev.move.from_square
            if util.is_trapped(prev.parent.board(), square):
                return True
    return False


def overloading(puzzle: Puzzle) -> bool:
    return False


def discovered_attack(puzzle: Puzzle) -> bool:
    if discovered_check(puzzle):
        return True
    for node in puzzle.mainline[1::2][1:]:
        if util.is_capture(node):
            between = SquareSet.between(node.move.from_square, node.move.to_square)
            assert isinstance(node.parent, ChildNode)
            if node.parent.move.to_square == node.move.to_square:
                return False
            prev = node.parent.parent
            assert isinstance(prev, ChildNode)
            if (
                prev.move.from_square in between
                and node.move.to_square != prev.move.to_square
                and node.move.from_square != prev.move.to_square
                and not util.is_castling(prev)
            ):
                return True
    return False


def discovered_check(puzzle: Puzzle) -> bool:
    for node in puzzle.mainline[1::2]:
        board = node.board()
        checkers = board.checkers()
        if checkers and not node.move.to_square in checkers:
            return True
    return False


def quiet_move(puzzle: Puzzle) -> bool:
    for node in puzzle.mainline:
        if (
            # on player move, not the last move of the puzzle
            node.turn() != puzzle.pov
            and not node.is_end()
            and
            # no check given or escaped
            not node.board().is_check()
            and not node.parent.board().is_check()
            and
            # no capture made or threatened
            not util.is_capture(node)
            and not util.attacked_opponent_pieces(
                node.board(), node.move.to_square, puzzle.pov
            )
            and
            # no advanced pawn push
            not util.is_advanced_pawn_move(node)
            and util.moved_piece_type(node) != KING
        ):
            return True
    return False


def defensive_move(puzzle: Puzzle) -> bool:
    # like quiet_move, but on last move
    # at least 3 legal moves
    if puzzle.mainline[-2].board().legal_moves.count() < 3:
        return False
    node = puzzle.mainline[-1]
    # no check given, no piece taken
    if node.board().is_check() or util.is_capture(node):
        return False
    # no piece attacked
    if util.attacked_opponent_pieces(node.board(), node.move.to_square, puzzle.pov):
        return False
    # no advanced pawn push
    return not util.is_advanced_pawn_move(node)


def check_escape(puzzle: Puzzle) -> bool:
    for node in puzzle.mainline[1::2]:
        if node.board().is_check() or util.is_capture(node):
            return False
        if node.parent.board().legal_moves.count() < 3:
            return False
        if node.parent.board().is_check():
            return True
    return False


def attraction(puzzle: Puzzle) -> bool:
    for node in puzzle.mainline[1:]:
        if node.turn() == puzzle.pov:
            continue
        # 1. player moves to a square
        first_move_to = node.move.to_square
        opponent_reply = util.next_node(node)
        # 2. opponent captures on that square
        if opponent_reply and opponent_reply.move.to_square == first_move_to:
            attracted_piece = util.moved_piece_type(opponent_reply)
            if attracted_piece in [KING, QUEEN, ROOK]:
                attracted_to_square = opponent_reply.move.to_square
                next_node = util.next_node(opponent_reply)
                if next_node:
                    attackers = next_node.board().attackers(
                        puzzle.pov, attracted_to_square
                    )
                    # 3. player attacks that square
                    if next_node.move.to_square in attackers:
                        # 4. player checks on that square
                        if attracted_piece == KING:
                            return True
                        n3 = util.next_next_node(next_node)
                        # 4. or player later captures on that square
                        if n3 and n3.move.to_square == attracted_to_square:
                            return True
    return False


def deflection(puzzle: Puzzle) -> bool:
    for node in puzzle.mainline[1::2][1:]:
        captured_piece = node.parent.board().piece_at(node.move.to_square)
        if captured_piece or node.move.promotion:
            capturing_piece = util.moved_piece_type(node)
            if (
                captured_piece
                and util.king_values[captured_piece.piece_type]
                > util.king_values[capturing_piece]
            ):
                continue
            square = node.move.to_square
            prev_op_move = node.parent.move
            assert prev_op_move
            grandpa = node.parent.parent
            assert isinstance(grandpa, ChildNode)
            prev_player_move = grandpa.move
            prev_player_capture = grandpa.parent.board().piece_at(
                prev_player_move.to_square
            )
            if (
                (
                    not prev_player_capture
                    or util.values[prev_player_capture.piece_type]
                    < util.moved_piece_type(grandpa)
                )
                and square != prev_op_move.to_square
                and square != prev_player_move.to_square
                and (
                    prev_op_move.to_square == prev_player_move.to_square
                    or grandpa.board().is_check()
                )
                and (
                    square in grandpa.board().attacks(prev_op_move.from_square)
                    or node.move.promotion
                    and square_file(node.move.to_square)
                    == square_file(prev_op_move.from_square)
                    and node.move.from_square
                    in grandpa.board().attacks(prev_op_move.from_square)
                )
                and (not square in node.parent.board().attacks(prev_op_move.to_square))
            ):
                return True
    return False


def exposed_king(puzzle: Puzzle) -> bool:
    if puzzle.pov:
        pov = puzzle.pov
        board = puzzle.mainline[0].board()
    else:
        pov = not puzzle.pov
        board = puzzle.mainline[0].board().mirror()
    king = board.king(not pov)
    assert king is not None
    if chess.square_rank(king) < 5:
        return False
    squares = SquareSet.from_square(king - 8)
    if chess.square_file(king) > 0:
        squares.add(king - 1)
        squares.add(king - 9)
    if chess.square_file(king) < 7:
        squares.add(king + 1)
        squares.add(king - 7)
    for square in squares:
        if board.piece_at(square) == Piece(PAWN, not pov):
            return False
    for node in puzzle.mainline[1::2][1:-1]:
        if node.board().is_check():
            return True
    return False


def skewer(puzzle: Puzzle) -> bool:
    for node in puzzle.mainline[1::2][1:]:
        prev = node.parent
        assert isinstance(prev, ChildNode)
        capture = prev.board().piece_at(node.move.to_square)
        if (
            capture
            and util.moved_piece_type(node) in util.ray_piece_types
            and not node.board().is_checkmate()
        ):
            between = SquareSet.between(node.move.from_square, node.move.to_square)
            op_move = prev.move
            assert op_move
            if (
                op_move.to_square == node.move.to_square
                or not op_move.from_square in between
            ):
                continue
            if util.king_values[util.moved_piece_type(prev)] > util.king_values[
                capture.piece_type
            ] and util.is_in_bad_spot(prev.board(), node.move.to_square):
                return True
    return False


def self_interference(puzzle: Puzzle) -> bool:
    # intereference by opponent piece
    for node in puzzle.mainline[1::2][1:]:
        prev_board = node.parent.board()
        square = node.move.to_square
        capture = prev_board.piece_at(square)
        if capture and util.is_hanging(prev_board, capture, square):
            grandpa = node.parent.parent
            assert grandpa
            init_board = grandpa.board()
            defenders = init_board.attackers(capture.color, square)
            defender = defenders.pop() if defenders else None
            defender_piece = init_board.piece_at(defender) if defender else None
            if (
                defender
                and defender_piece
                and defender_piece.piece_type in util.ray_piece_types
            ):
                if node.parent.move and node.parent.move.to_square in SquareSet.between(
                    square, defender
                ):
                    return True
    return False


def interference(puzzle: Puzzle) -> bool:
    # intereference by player piece
    for node in puzzle.mainline[1::2][1:]:
        prev_board = node.parent.board()
        square = node.move.to_square
        capture = prev_board.piece_at(square)
        assert node.parent.move
        if (
            capture
            and square != node.parent.move.to_square
            and util.is_hanging(prev_board, capture, square)
        ):
            assert node.parent
            assert node.parent.parent
            assert node.parent.parent.parent
            init_board = node.parent.parent.parent.board()
            defenders = init_board.attackers(capture.color, square)
            defender = defenders.pop() if defenders else None
            defender_piece = init_board.piece_at(defender) if defender else None
            if (
                defender
                and defender_piece
                and defender_piece.piece_type in util.ray_piece_types
            ):
                interfering = node.parent.parent
                if interfering.move and interfering.move.to_square in SquareSet.between(
                    square, defender
                ):
                    return True
    return False


def intermezzo(puzzle: Puzzle) -> bool:
    for node in puzzle.mainline[1::2][1:]:
        if util.is_capture(node):
            capture_move = node.move
            capture_square = node.move.to_square
            op_node = node.parent
            assert isinstance(op_node, ChildNode)
            prev_pov_node = node.parent.parent
            assert isinstance(prev_pov_node, ChildNode)
            if not op_node.move.from_square in prev_pov_node.board().attackers(
                not puzzle.pov, capture_square
            ):
                if prev_pov_node.move.to_square != capture_square:
                    prev_op_node = prev_pov_node.parent
                    assert isinstance(prev_op_node, ChildNode)
                    return (
                        prev_op_node.move.to_square == capture_square
                        and util.is_capture(prev_op_node)
                        and capture_move in prev_op_node.board().legal_moves
                    )
    return False


# the pinned piece can't attack a player piece
def pin_prevents_attack(puzzle: Puzzle) -> bool:
    for node in puzzle.mainline[1::2]:
        board = node.board()
        for square, piece in board.piece_map().items():
            if piece.color == puzzle.pov:
                continue
            pin_dir = board.pin(piece.color, square)
            if pin_dir == chess.BB_ALL:
                continue
            for attack in board.attacks(square):
                attacked = board.piece_at(attack)
                if (
                    attacked
                    and attacked.color == puzzle.pov
                    and not attack in pin_dir
                    and (
                        util.values[attacked.piece_type] > util.values[piece.piece_type]
                        or util.is_hanging(board, attacked, attack)
                    )
                ):
                    return True
    return False


# the pinned piece can't escape the attack
def pin_prevents_escape(puzzle: Puzzle) -> bool:
    for node in puzzle.mainline[1::2]:
        board = node.board()
        for pinned_square, pinned_piece in board.piece_map().items():
            if pinned_piece.color == puzzle.pov:
                continue
            pin_dir = board.pin(pinned_piece.color, pinned_square)
            if pin_dir == chess.BB_ALL:
                continue
            for attacker_square in board.attackers(puzzle.pov, pinned_square):
                if attacker_square in pin_dir:
                    attacker = board.piece_at(attacker_square)
                    assert attacker
                    if (
                        util.values[pinned_piece.piece_type]
                        > util.values[attacker.piece_type]
                    ):
                        return True
                    if (
                        util.is_hanging(board, pinned_piece, pinned_square)
                        and pinned_square
                        not in board.attackers(not puzzle.pov, attacker_square)
                        and [
                            m
                            for m in board.pseudo_legal_moves
                            if m.from_square == pinned_square
                            and m.to_square not in pin_dir
                        ]
                    ):
                        return True
    return False


def attacking_f2_f7(puzzle: Puzzle) -> bool:
    for node in puzzle.mainline[1::2]:
        square = node.move.to_square
        if node.parent.board().piece_at(node.move.to_square) and square in [
            chess.F2,
            chess.F7,
        ]:
            king = node.board().piece_at(chess.E8 if square == chess.F7 else chess.E1)
            return (
                king is not None
                and king.piece_type == KING
                and king.color != puzzle.pov
            )
    return False


def kingside_attack(puzzle: Puzzle) -> bool:
    return side_attack(puzzle, 7, [6, 7], 20)


def queenside_attack(puzzle: Puzzle) -> bool:
    return side_attack(puzzle, 0, [0, 1, 2], 18)


def side_attack(
    puzzle: Puzzle, corner_file: int, king_files: List[int], nb_pieces: int
) -> bool:
    back_rank = 7 if puzzle.pov else 0
    init_board = puzzle.mainline[0].board()
    king_square = init_board.king(not puzzle.pov)
    if (
        not king_square
        or square_rank(king_square) != back_rank
        or square_file(king_square) not in king_files
        or len(init_board.piece_map()) < nb_pieces  # no endgames
        or not any(node.board().is_check() for node in puzzle.mainline[1::2])
    ):
        return False
    score = 0
    corner = chess.square(corner_file, back_rank)
    for node in puzzle.mainline[1::2]:
        corner_dist = square_distance(corner, node.move.to_square)
        if node.board().is_check():
            score += 1
        if util.is_capture(node) and corner_dist <= 3:
            score += 1
        elif corner_dist >= 5:
            score -= 1
    return score >= 2


def clearance(puzzle: Puzzle) -> bool:
    for node in puzzle.mainline[1::2][1:]:
        board = node.board()
        if not node.parent.board().piece_at(node.move.to_square):
            piece = board.piece_at(node.move.to_square)
            if piece and piece.piece_type in util.ray_piece_types:
                prev = node.parent.parent
                assert prev
                prev_move = prev.move
                assert prev_move
                assert isinstance(node.parent, ChildNode)
                if (
                    not prev_move.promotion
                    and prev_move.to_square != node.move.from_square
                    and prev_move.to_square != node.move.to_square
                    and not node.parent.board().is_check()
                    and (
                        not board.is_check()
                        or util.moved_piece_type(node.parent) != KING
                    )
                ):
                    if (
                        prev_move.from_square == node.move.to_square
                        or prev_move.from_square
                        in SquareSet.between(node.move.from_square, node.move.to_square)
                    ):
                        if (
                            prev.parent
                            and not prev.parent.board().piece_at(prev_move.to_square)
                            or util.is_in_bad_spot(prev.board(), prev_move.to_square)
                        ):
                            return True
    return False


def en_passant(puzzle: Puzzle) -> bool:
    for node in puzzle.mainline[1::2]:
        if (
            util.moved_piece_type(node) == PAWN
            and square_file(node.move.from_square) != square_file(node.move.to_square)
            and not node.parent.board().piece_at(node.move.to_square)
        ):
            return True
    return False


def castling(puzzle: Puzzle) -> bool:
    for node in puzzle.mainline[1::2]:
        if util.is_castling(node):
            return True
    return False


def promotion(puzzle: Puzzle) -> bool:
    for node in puzzle.mainline[1::2]:
        if node.move.promotion:
            return True
    return False


def under_promotion(puzzle: Puzzle) -> bool:
    for node in puzzle.mainline[1::2]:
        if node.board().is_checkmate():
            return True if node.move.promotion == KNIGHT else False
        elif node.move.promotion and node.move.promotion != QUEEN:
            return True
    return False


def capturing_defender(puzzle: Puzzle) -> bool:
    for node in puzzle.mainline[1::2][1:]:
        board = node.board()
        capture = node.parent.board().piece_at(node.move.to_square)
        assert isinstance(node.parent, ChildNode)
        if board.is_checkmate() or (
            capture
            and util.moved_piece_type(node) != KING
            and util.values[capture.piece_type]
            <= util.values[util.moved_piece_type(node)]
            and util.is_hanging(node.parent.board(), capture, node.move.to_square)
            and node.parent.move.to_square != node.move.to_square
        ):
            prev = node.parent.parent
            assert isinstance(prev, ChildNode)
            if (
                not prev.board().is_check()
                and prev.move.to_square != node.move.from_square
            ):
                assert prev.parent
                init_board = prev.parent.board()
                defender_square = prev.move.to_square
                defender = init_board.piece_at(defender_square)
                if (
                    defender
                    and defender_square
                    in init_board.attackers(defender.color, node.move.to_square)
                    and not init_board.is_check()
                ):
                    return True
    return False


def back_rank_mate(puzzle: Puzzle) -> bool:
    node = puzzle.game.end()
    board = node.board()
    king = board.king(not puzzle.pov)
    assert king is not None
    assert isinstance(node, ChildNode)
    back_rank = 7 if puzzle.pov else 0
    if board.is_checkmate() and square_rank(king) == back_rank:
        squares = SquareSet.from_square(king + (-8 if puzzle.pov else 8))
        if puzzle.pov:
            if chess.square_file(king) < 7:
                squares.add(king - 7)
            if chess.square_file(king) > 0:
                squares.add(king - 9)
        else:
            if chess.square_file(king) < 7:
                squares.add(king + 9)
            if chess.square_file(king) > 0:
                squares.add(king + 7)
        for square in squares:
            piece = board.piece_at(square)
            if (
                piece is None
                or piece.color == puzzle.pov
                or board.attackers(puzzle.pov, square)
            ):
                return False
        return any(square_rank(checker) == back_rank for checker in board.checkers())
    return False


def anastasia_mate(puzzle: Puzzle) -> bool:
    node = puzzle.game.end()
    board = node.board()
    king = board.king(not puzzle.pov)
    assert king is not None
    assert isinstance(node, ChildNode)
    if square_file(king) in [0, 7] and square_rank(king) not in [0, 7]:
        if square_file(node.move.to_square) == square_file(
            king
        ) and util.moved_piece_type(node) in [QUEEN, ROOK]:
            if square_file(king) != 0:
                board.apply_transform(chess.flip_horizontal)
            king = board.king(not puzzle.pov)
            assert king is not None
            blocker = board.piece_at(king + 1)
            if blocker is not None and blocker.color != puzzle.pov:
                knight = board.piece_at(king + 3)
                if (
                    knight is not None
                    and knight.color == puzzle.pov
                    and knight.piece_type == KNIGHT
                ):
                    return True
    return False


def hook_mate(puzzle: Puzzle) -> bool:
    node = puzzle.game.end()
    board = node.board()
    king = board.king(not puzzle.pov)
    assert king is not None
    assert isinstance(node, ChildNode)
    if (
        util.moved_piece_type(node) == ROOK
        and square_distance(node.move.to_square, king) == 1
    ):
        for rook_defender_square in board.attackers(puzzle.pov, node.move.to_square):
            defender = board.piece_at(rook_defender_square)
            if (
                defender
                and defender.piece_type == KNIGHT
                and square_distance(rook_defender_square, king) == 1
            ):
                for knight_defender_square in board.attackers(
                    puzzle.pov, rook_defender_square
                ):
                    pawn = board.piece_at(knight_defender_square)
                    if pawn and pawn.piece_type == PAWN:
                        return True
    return False


def arabian_mate(puzzle: Puzzle) -> bool:
    node = puzzle.game.end()
    board = node.board()
    king = board.king(not puzzle.pov)
    assert king is not None
    assert isinstance(node, ChildNode)
    if (
        square_file(king) in [0, 7]
        and square_rank(king) in [0, 7]
        and util.moved_piece_type(node) == ROOK
        and square_distance(node.move.to_square, king) == 1
    ):
        for knight_square in board.attackers(puzzle.pov, node.move.to_square):
            knight = board.piece_at(knight_square)
            if (
                knight
                and knight.piece_type == KNIGHT
                and (
                    abs(square_rank(knight_square) - square_rank(king)) == 2
                    and abs(square_file(knight_square) - square_file(king)) == 2
                )
            ):
                return True
    return False


def boden_or_double_bishop_mate(puzzle: Puzzle) -> Optional[TagKind]:
    node = puzzle.game.end()
    board = node.board()
    king = board.king(not puzzle.pov)
    assert king is not None
    assert isinstance(node, ChildNode)
    bishop_squares = list(board.pieces(BISHOP, puzzle.pov))
    if len(bishop_squares) < 2:
        return None
    for square in [s for s in SquareSet(chess.BB_ALL) if square_distance(s, king) < 2]:
        if not all(
            [
                p.piece_type == BISHOP
                for p in util.attacker_pieces(board, puzzle.pov, square)
            ]
        ):
            return None
    if (square_file(bishop_squares[0]) < square_file(king)) == (
        square_file(bishop_squares[1]) > square_file(king)
    ):
        return "bodenMate"
    else:
        return "doubleBishopMate"


def dovetail_mate(puzzle: Puzzle) -> bool:
    node = puzzle.game.end()
    board = node.board()
    king = board.king(not puzzle.pov)
    assert king is not None
    assert isinstance(node, ChildNode)
    if square_file(king) in [0, 7] or square_rank(king) in [0, 7]:
        return False
    queen_square = node.move.to_square
    if (
        util.moved_piece_type(node) != QUEEN
        or square_file(queen_square) == square_file(king)
        or square_rank(queen_square) == square_rank(king)
        or square_distance(queen_square, king) > 1
    ):
        return False
    for square in [s for s in SquareSet(chess.BB_ALL) if square_distance(s, king) == 1]:
        if square == queen_square:
            continue
        attackers = list(board.attackers(puzzle.pov, square))
        if attackers == [queen_square]:
            if board.piece_at(square):
                return False
        elif attackers:
            return False
    return True


def piece_endgame(puzzle: Puzzle, piece_type: PieceType) -> bool:
    for board in [puzzle.mainline[i].board() for i in [0, 1]]:
        if not board.pieces(piece_type, WHITE) and not board.pieces(piece_type, BLACK):
            return False
        for piece in board.piece_map().values():
            if not piece.piece_type in [KING, PAWN, piece_type]:
                return False
    return True


def queen_rook_endgame(puzzle: Puzzle) -> bool:
    def test(board: Board) -> bool:
        pieces = board.piece_map().values()
        return (
            len([p for p in pieces if p.piece_type == QUEEN]) == 1
            and any(p.piece_type == ROOK for p in pieces)
            and all(p.piece_type in [QUEEN, ROOK, PAWN, KING] for p in pieces)
        )

    return all(test(puzzle.mainline[i].board()) for i in [0, 1])


def smothered_mate(puzzle: Puzzle) -> bool:
    board = puzzle.game.end().board()
    king_square = board.king(not puzzle.pov)
    assert king_square is not None
    for checker_square in board.checkers():
        piece = board.piece_at(checker_square)
        assert piece
        if piece.piece_type == KNIGHT:
            for escape_square in [
                s for s in chess.SQUARES if square_distance(s, king_square) == 1
            ]:
                blocker = board.piece_at(escape_square)
                if not blocker or blocker.color == puzzle.pov:
                    return False
            return True
    return False


def mate_in(puzzle: Puzzle) -> Optional[TagKind]:
    if not puzzle.game.end().board().is_checkmate():
        return None
    moves_to_mate = len(puzzle.mainline) // 2
    if moves_to_mate == 1:
        return "mateIn1"
    elif moves_to_mate == 2:
        return "mateIn2"
    elif moves_to_mate == 3:
        return "mateIn3"
    elif moves_to_mate == 4:
        return "mateIn4"
    return "mateIn5"

def process_pgn_file(pgn_file, generator):
    """ Reads a PGN file and analyzes each game to extract puzzles. """
    with open(pgn_file, "r", encoding="utf-8") as pgn:
        game_data = ""
        for line in pgn:
            if line.startswith("[Site "):  
                if game_data:  # If a game was already collected, process it
                    puzzles = analyze_game(game_data, generator)
                    for puzzle in puzzles:
                        save_puzzle(puzzle)
                game_data = line  # Start new game collection
            else:
                game_data += line

        # Process the last game in the file
        if game_data:
            puzzles = analyze_game(game_data, generator)
            for puzzle in puzzles:
                save_puzzle(puzzle)
def maximum_castling_rights(board: chess.Board) -> chess.Bitboard:
    return (
        (board.pieces_mask(chess.ROOK, chess.WHITE) & (chess.BB_A1 | chess.BB_H1) if board.king(chess.WHITE) == chess.E1 else chess.BB_EMPTY) |
        (board.pieces_mask(chess.ROOK, chess.BLACK) & (chess.BB_A8 | chess.BB_H8) if board.king(chess.BLACK) == chess.E8 else chess.BB_EMPTY)
    )


def win_chances(score: Score) -> float:
    """
    winning chances from -1 to 1 https://graphsketch.com/?eqn1_color=1&eqn1_eqn=100+*+%282+%2F+%281+%2B+exp%28-0.004+*+x%29%29+-+1%29&eqn2_color=2&eqn2_eqn=&eqn3_color=3&eqn3_eqn=&eqn4_color=4&eqn4_eqn=&eqn5_color=5&eqn5_eqn=&eqn6_color=6&eqn6_eqn=&x_min=-1000&x_max=1000&y_min=-100&y_max=100&x_tick=100&y_tick=10&x_label_freq=2&y_label_freq=2&do_grid=0&do_grid=1&bold_labeled_lines=0&bold_labeled_lines=1&line_width=4&image_w=850&image_h=525
    """
    mate = score.mate()
    if mate is not None:
        return 1 if mate > 0 else -1

    cp = score.score()
    MULTIPLIER = -0.00368208 # https://github.com/lichess-org/lila/pull/11148
    return 2 / (1 + math.exp(MULTIPLIER * cp)) - 1 if cp is not None else 0

class Generator:
    def __init__(self, engine: SimpleEngine):
        self.engine = engine
    def analyze_game(self, game: Game) -> List[Puzzle]:
        result = []
        prev_score: Score = Cp(20)
        seen_epds: Set[str] = set()
        board = game.board()
        skip_until_irreversible = False

        for node in game.mainline():
            if skip_until_irreversible:
                if board.is_irreversible(node.move):
                    skip_until_irreversible = False
                    seen_epds.clear()
                else:
                    board.push(node.move)
                    continue

            current_eval = node.eval()

            if not current_eval:
                print("Skipping game without eval on ply {}".format(node.ply()))
                return []

            board.push(node.move)
            epd = board.epd()
            if epd in seen_epds:
                skip_until_irreversible = True
                continue
            seen_epds.add(epd)

            if board.castling_rights != maximum_castling_rights(board):
                continue

            puzzle, score = self.analyze_position(node, prev_score, current_eval, game)

            if puzzle:
                result.append(puzzle)

            prev_score = -score

        print("Found nothing from {}".format(game.headers.get("Site")))
        for puzzle in result:
            self.tag_puzzle(puzzle)
        return result
    
    def tag_puzzle(self, puzzle: Puzzle) -> None:
        tags: List[TagKind] = []
        mate_tag = mate_in(puzzle)
        if mate_tag:
            tags.append(mate_tag)
            tags.append("mate")
            if smothered_mate(puzzle):
                tags.append("smotheredMate")
            elif back_rank_mate(puzzle):
                tags.append("backRankMate")
            elif anastasia_mate(puzzle):
                tags.append("anastasiaMate")
            elif hook_mate(puzzle):
                tags.append("hookMate")
            elif arabian_mate(puzzle):
                tags.append("arabianMate")
            else:
                found = boden_or_double_bishop_mate(puzzle)
                if found:
                    tags.append(found)
                elif dovetail_mate(puzzle):
                    tags.append("dovetailMate")
        elif puzzle.cp > 600:
            tags.append("crushing")
        elif puzzle.cp > 200:
            tags.append("advantage")
        else:
            tags.append("equality")

        if attraction(puzzle):
            tags.append("attraction")

        if deflection(puzzle):
            tags.append("deflection")
        elif overloading(puzzle):
            tags.append("overloading")

        if advanced_pawn(puzzle):
            tags.append("advancedPawn")

        if double_check(puzzle):
            tags.append("doubleCheck")

        if quiet_move(puzzle):
            tags.append("quietMove")

        if defensive_move(puzzle) or check_escape(puzzle):
            tags.append("defensiveMove")

        if sacrifice(puzzle):
            tags.append("sacrifice")

        if x_ray(puzzle):
            tags.append("xRayAttack")

        if fork(puzzle):
            tags.append("fork")

        if hanging_piece(puzzle):
            tags.append("hangingPiece")

        if trapped_piece(puzzle):
            tags.append("trappedPiece")

        if discovered_attack(puzzle):
            tags.append("discoveredAttack")

        if exposed_king(puzzle):
            tags.append("exposedKing")

        if skewer(puzzle):
            tags.append("skewer")

        if self_interference(puzzle) or interference(puzzle):
            tags.append("interference")

        if intermezzo(puzzle):
            tags.append("intermezzo")

        if pin_prevents_attack(puzzle) or pin_prevents_escape(puzzle):
            tags.append("pin")

        if attacking_f2_f7(puzzle):
            tags.append("attackingF2F7")

        if clearance(puzzle):
            tags.append("clearance")

        if en_passant(puzzle):
            tags.append("enPassant")

        if castling(puzzle):
            tags.append("castling")

        if promotion(puzzle):
            tags.append("promotion")

        if under_promotion(puzzle):
            tags.append("underPromotion")

        if capturing_defender(puzzle):
            tags.append("capturingDefender")

        if piece_endgame(puzzle, PAWN):
            tags.append("pawnEndgame")
        elif piece_endgame(puzzle, QUEEN):
            tags.append("queenEndgame")
        elif piece_endgame(puzzle, ROOK):
            tags.append("rookEndgame")
        elif piece_endgame(puzzle, BISHOP):
            tags.append("bishopEndgame")
        elif piece_endgame(puzzle, KNIGHT):
            tags.append("knightEndgame")
        elif queen_rook_endgame(puzzle):
            tags.append("queenRookEndgame")

        if "backRankMate" not in tags and "fork" not in tags:
            if kingside_attack(puzzle):
                tags.append("kingsideAttack")
            elif queenside_attack(puzzle):
                tags.append("queensideAttack")

        if len(puzzle.mainline) == 2:
            tags.append("oneMove")
        elif len(puzzle.mainline) == 4:
            tags.append("short")
        elif len(puzzle.mainline) >= 8:
            tags.append("veryLong")
        else:
            tags.append("long")

        puzzle.tags = tags




    def analyze_position(self, node: ChildNode, prev_score: Score, current_eval: PovScore, game: Game) -> Tuple[Optional[Puzzle], Score]:

        board = node.board()
        winner = board.turn
        score = current_eval.pov(winner)

        if board.legal_moves.count() < 2:
            return None, score

        game_url = node.game().headers.get("Site")

        print("{} {} to {}".format(node.ply(), node.move.uci() if node.move else None, score))
        if score > mate_soon:
            print("Mate {}#{} Probing...".format(game_url, node.ply()))
            mate_solution = self.cook_mate(copy.deepcopy(node), winner)
            if mate_solution is None:
                return None, score
            return Puzzle(node, mate_solution, 999999999, [], game), score
        elif score >= Cp(200) and win_chances(score) > win_chances(prev_score) + 0.6:
            print("Advantage {}#{} {} -> {}. Probing...".format(game_url, node.ply(), prev_score, score))
            puzzle_node = copy.deepcopy(node)
            solution : Optional[List[NextMovePair]] = self.cook_advantage(puzzle_node, winner)
            if not solution:
                return None, score
            while len(solution) % 2 == 0 or not solution[-1].second:
                if not solution[-1].second:
                    print("Remove final only-move")
                solution = solution[:-1]
            if not solution or len(solution) == 1 :
                print("Discard one-mover")
                return None, score
            cp = solution[len(solution) - 1].best.score.score()
            return Puzzle(node, [p.best.move for p in solution], 999999998 if cp is None else cp, [], game), score
        else:
            return None, score
    
    def cook_advantage(self, node: ChildNode, winner: Color) -> Optional[List[NextMovePair]]:

        board = node.board()

        if board.is_repetition(2):
            print("Found repetition, canceling")
            return None

        pair = self.get_next_pair(node, winner)
        if not pair:
            return []
        if pair.best.score < Cp(200):
            print("Not winning enough, aborting")
            return None

        follow_up = self.cook_advantage(node.add_main_variation(pair.best.move), winner)

        if follow_up is None:
            return None

        return [pair] + follow_up


    def is_valid_mate_in_one(self, pair: NextMovePair) -> bool:
        if pair.best.score != Mate(1):
            return False
        non_mate_win_threshold = 0.6
        if not pair.second or win_chances(pair.second.score) <= non_mate_win_threshold:
            return True
        if pair.second.score == Mate(1):
            # if there's more than one mate in one, gotta look if the best non-mating move is bad enough
            print('Looking for best non-mating move...')
            mates = util.count_mates(copy.deepcopy(pair.node.board()))
            info = self.engine.analyse(pair.node.board(), multipv = mates + 1, limit = pair_limit)
            scores =  [pv["score"].pov(pair.winner) for pv in info]
            # the first non-matein1 move is the last element
            if scores[-1] < Mate(1) and win_chances(scores[-1]) > non_mate_win_threshold:
                    return False
            return True
        return False

    # is pair.best the only continuation?
    def is_valid_attack(self, pair: NextMovePair) -> bool:
        return (
            pair.second is None or
            self.is_valid_mate_in_one(pair) or
            win_chances(pair.best.score) > win_chances(pair.second.score) + 0.7
        )

    def get_next_pair(self, node: ChildNode, winner: Color) -> Optional[NextMovePair]:
        pair = get_next_move_pair(self.engine, node, winner, pair_limit)
        if node.board().turn == winner and not self.is_valid_attack(pair):
            print("No valid attack {}".format(pair))
            return None
        return pair

    def get_next_move(self, node: ChildNode, limit: chess.engine.Limit) -> Optional[Move]:
        result = self.engine.play(node.board(), limit = limit)
        return result.move if result else None

    def cook_mate(self, node: ChildNode, winner: Color) -> Optional[List[Move]]:

        board = node.board()

        if board.is_game_over():
            return []

        if board.turn == winner:
            pair = self.get_next_pair(node, winner)
            if not pair:
                return None
            if pair.best.score < mate_soon:
                print("Best move is not a mate, we're probably not searching deep enough")
                return None
            move = pair.best.move
        else:
            next = self.get_next_move(node, mate_defense_limit)
            if not next:
                return None
            move = next

        follow_up = self.cook_mate(node.add_main_variation(move), winner)

        if follow_up is None:
            return None

        return [move] + follow_up


def analyze_game(game_data: str, generator) -> List[Puzzle]:
    """ Parses a PGN game and analyzes it for puzzles. """
    game = chess.pgn.read_game(StringIO(game_data))
    if game:
        print(f"Analyzing game {game.headers.get('Site', 'Unknown')}")
        puzzles = generator.analyze_game(game)
        return puzzles
    else:
        print("Failed to parse a game.")
        return []


def make_engine(executable: str, threads: int) -> SimpleEngine:
    engine = SimpleEngine.popen_uci(executable)
    engine.configure({'Threads': threads})
    return engine

# --- SETTINGS ---
PGN_FILE = "./data/kramford_games.pgn"  # Change this to the actual filename
mate_soon = Mate(15)
DB_FILE = "puzzles.db"


def create_database():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS puzzles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        moves BLOB,
        cp INTEGER,
        tags TEXT,
        game BLOB
    )
    """)
    
    conn.commit()
    conn.close()

def save_puzzle(puzzle: Puzzle):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Convert list of tags to a string
    tags_str = ",".join(puzzle.tags)

    # Serialize moves and game using pickle
    moves_blob = pickle.dumps(puzzle.moves)
    game_blob = pickle.dumps(puzzle.game)

    cursor.execute("""
    INSERT INTO puzzles (moves, cp, tags, game) 
    VALUES (?, ?, ?, ?)
    """, (moves_blob, puzzle.cp, tags_str, game_blob))
    
    conn.commit()
    conn.close()

def load_puzzles():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("SELECT moves, cp, tags, game FROM puzzles")
    rows = cursor.fetchall()

    puzzles = []
    for row in rows:
        moves = pickle.loads(row[0])
        cp = row[1]
        tags = row[2].split(",")
        game = pickle.loads(row[3])

        puzzle = Puzzle(node=None, moves=moves, cp=cp, tags=tags, game=game)
        puzzles.append(puzzle)

    conn.close()
    return puzzles


if __name__ == "__main__":
    sys.setrecursionlimit(10000) # else node.deepcopy() sometimes fails?
    create_database()
    engine = make_engine('stockfish', '16')
    generator = Generator(engine)
    process_pgn_file(PGN_FILE, generator)
