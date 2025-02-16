from chess import square_rank, Color, Board, Square, Piece, square_distance, popcount, WHITE, BLACK, ray, scan_forward
from chess import KING, QUEEN, ROOK, BISHOP, KNIGHT, PAWN
from typing import List, Tuple

class Puzzle:

    def __init__(self, node):
        self.node = node
        self.tags = [name for name, fn  in self.tactics() if fn(node)]
    
    def tactics(self):
        return [
            ("fork", fork)
            # ("discovered_attack", self.discovered_attack),
            # ("pin", self.pin),
            # ("skewer", self.skewer),
            # ("double_attack", self.double_attack),
            # ("discovered_check", self.discovered_check),
            # ("double_check", self.double_check),
            # ("overloading", self.overloading),
            # ("deflection", self.deflection),
            # ("interference", self.interference),
            # ("undermining", self.undermining)
        ]

def fork(node):
    board = node.board()
    nb = 0
    for piece, square in attacked_opponent_squares(
        board, node.move.to_square, not node.board().turn
    ):
        if is_square_attacked_more_than_defended(board, square, node.board().turn):
            nb += 1
    return nb > 1
    

    
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
