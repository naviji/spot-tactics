import chess
from chess import square_rank, Color, Board, Square, Piece, square_distance, popcount, WHITE, BLACK, ray, scan_forward
from chess import KING, QUEEN, ROOK, BISHOP, KNIGHT, PAWN
from typing import List, Tuple
from chess.pgn import ChildNode

values = { PAWN: 1, KNIGHT: 3, BISHOP: 3, ROOK: 5, QUEEN: 9 }
ray_piece_types = [QUEEN, ROOK, BISHOP]
class Puzzle:

    def __init__(self, node):
        self.node = node
        self.tags = [name for name, fn  in self.tactics() if fn(node)]
    
    def tactics(self):
        return [
            ("fork", fork),
            ("pin", pin)
        ]

def fork(node: ChildNode) -> bool:
    board = node.board()
    nb = 0
    for piece, square in attacked_opponent_squares(
        board, node.move.to_square, not node.board().turn
    ):
        if is_square_attacked_more_than_defended(board, square, node.board().turn):
            nb += 1
    return nb > 1

def pin(node: ChildNode) -> bool:
    return pin_prevents_attack(node) or pin_prevents_escape(node)


# the pinned piece can't attack a player piece
def pin_prevents_attack(node: ChildNode) -> bool:
    board = node.board()
    for square, piece in board.piece_map().items():
        if piece.color == node.board().turn:
            continue
        pin_dir = board.pin(piece.color, square)
        if pin_dir == chess.BB_ALL:
            continue
        for attack in board.attacks(square):
            attacked = board.piece_at(attack)
            if (
                attacked
                and attacked.color == node.board().turn
                and not attack in pin_dir
                and (
                    values[attacked.piece_type] > values[piece.piece_type]
                    or is_hanging(board, attacked, attack)
                )
            ):
                return True
    return False


# the pinned piece can't escape the attack
def pin_prevents_escape(node: ChildNode) -> bool:
    board = node.board()
    for pinned_square, pinned_piece in board.piece_map().items():
        if pinned_piece.color == node.board().turn:
            continue
        pin_dir = board.pin(pinned_piece.color, pinned_square)
        if pin_dir == chess.BB_ALL:
            continue
        for attacker_square in board.attackers(node.board().turn, pinned_square):
            if attacker_square in pin_dir:
                attacker = board.piece_at(attacker_square)
                assert attacker
                if (
                    values[pinned_piece.piece_type]
                    > values[attacker.piece_type]
                ):
                    return True
                if (
                    is_hanging(board, pinned_piece, pinned_square)
                    and pinned_square
                    not in board.attackers(not node.board().turn, attacker_square)
                    and [
                        m
                        for m in board.pseudo_legal_moves
                        if m.from_square == pinned_square
                        and m.to_square not in pin_dir
                    ]
                ):
                    return True
    return False

def attacked_opponent_squares(board: Board, from_square: Square, pov: Color) -> List[Tuple[Piece, Square]]:
    pieces = []
    piece = board.piece_at(from_square)
    
    # Get direct attacks first
    direct_squares = board.attacks(from_square)
    for attacked_square in direct_squares:
        attacked_piece = board.piece_at(attacked_square)
        if attacked_piece and attacked_piece.color != pov:
            pieces.append((attacked_piece, attacked_square))
    
    # Check for x-ray attacks if it's a sliding piece
    if piece and piece.piece_type in [BISHOP, ROOK, QUEEN]:
        # Check for x-ray attacks through blocking pieces
        for attacked_square in direct_squares:
            blocking_piece = board.piece_at(attacked_square)
            if blocking_piece and blocking_piece.color == pov:
                # Create a copy of the board and remove the blocking piece
                board_copy = board.copy()
                board_copy.remove_piece_at(attacked_square)
                
                # Get attacks from the original square on the modified board
                xray_squares = board_copy.attacks(from_square)
                for xray_square in xray_squares:
                    xray_piece = board.piece_at(xray_square)
                    if xray_piece and xray_piece.color != pov and (xray_piece, xray_square) not in pieces:
                        pieces.append((xray_piece, xray_square))
                    
    return pieces

def is_square_attacked_more_than_defended(board: Board, square: Square, pov: Color) -> bool:
    attackers_white = board.attackers_mask(WHITE, square)
    attackers_black = board.attackers_mask(BLACK, square)
    
    # Check for x-ray attacks
    for color, attackers in [(WHITE, attackers_white), (BLACK, attackers_black)]:
        for attacker_square in scan_forward(attackers):
            attacker_piece = board.piece_at(attacker_square)
            if attacker_piece and attacker_piece.piece_type in [BISHOP, ROOK, QUEEN]:
                # Create a copy of the board and remove the blocking piece
                board_copy = board.copy()
                board_copy.remove_piece_at(attacker_square)
                
                # Check for x-ray attacks
                xray_attackers = board_copy.attackers_mask(color, square)
                if color == WHITE:
                    attackers_white |= xray_attackers
                else:
                    attackers_black |= xray_attackers
    
    num_attackers_white = popcount(attackers_white)
    num_attackers_black = popcount(attackers_black)
    
    if pov:
        return num_attackers_black > num_attackers_white
    return num_attackers_white > num_attackers_black



def is_hanging(board: Board, piece: Piece, square: Square) -> bool:
    return not is_defended(board, piece, square)


def is_defended(board: Board, piece: Piece, square: Square) -> bool:
    if board.attackers(piece.color, square):
        return True
    # ray defense https://lichess.org/editor/6k1/3q1pbp/2b1p1p1/1BPp4/rp1PnP2/4PRNP/4Q1P1/4B1K1_w_-_-_0_1
    for attacker in board.attackers(not piece.color, square):
        attacker_piece = board.piece_at(attacker)
        assert(attacker_piece)
        if attacker_piece.piece_type in ray_piece_types:
            bc = board.copy(stack = False)
            bc.remove_piece_at(attacker)
            if bc.attackers(piece.color, square):
                return True

    return False