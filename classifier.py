from typing import List, Tuple
import chess
import chess.pgn

ray_piece_types = [chess.QUEEN, chess.ROOK, chess.BISHOP]
values = { chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3, chess.ROOK: 5, chess.QUEEN: 9, chess.KING: 10**9 }

def is_fork(fen, last_move):
    game = game_from_fen(fen, last_move)
    nb = 0
    node = game.end() # child node of the last move of the game
    for _, square in attacked_opponent_squares(
        node.board(), node.move.to_square, not node.board().turn
    ):
        if is_square_attacked_more_than_defended(node.board(), square, node.board().turn):
            nb += 1
    return nb > 1

def is_piece_hanging(fen, last_move):
    game = game_from_fen(fen, last_move)
    node = game.end()
    to = node.move.to_square # 35 - > d5
    captured = node.parent.board().piece_at(to)
    if not captured:
        return False
    return is_hanging(node.parent.board(), captured, to)

def is_pin(fen, last_move):
    # TODO: Make it work with relative pins
    game = game_from_fen(fen, last_move)
    node = game.end()
    for pinned_square, pinned_piece in node.board().piece_map().items():
        if pinned_piece.color == (not node.turn()): #node.turn is black
            continue
        # Gives me absolute pin from square to king
        pin_dir = node.board().pin(pinned_piece.color, pinned_square)
        if pin_dir == chess.BB_ALL:
                continue
        for attacker_square in node.board().attackers(not node.turn(), pinned_square):
                if attacker_square in pin_dir:
                    attacker = node.board().piece_at(attacker_square)
                    assert attacker
                    if (
                        values[pinned_piece.piece_type]
                        > values[attacker.piece_type]
                    ):
                        return True
                    if (
                        # TODO: Test this part
                        is_hanging(node.board(), pinned_piece, pinned_square)
                        # confirms that the attacker is not attacked
                        and pinned_square not in node.board().attackers(node.turn(), attacker_square)
                        # piece hypothetically would have liked to escape
                        and [
                            m
                            for m in node.board().pseudo_legal_moves
                            if m.from_square == pinned_square
                            and m.to_square not in pin_dir
                        ]
                    ):
                        return True
    return False

def is_hanging(board: chess.Board, piece: chess.Piece, square: chess.Square) -> bool:
    return not is_defended(board, piece, square)

def is_defended(board: chess.Board, piece: chess.Piece, square: chess.Square) -> bool:
    # TODO: Doesn't account for defenders that do not defend due to absolute pins

    value_of_piece_under_attack = values[piece.piece_type]
    # Find direct and ray attackers and defenders 
    defenders = board.attackers(piece.color, square) | ray_attackers(board, piece.color, square)
    attackers = board.attackers(not piece.color, square) | ray_attackers(board, not piece.color, square)
    
    if len(attackers) == 0:
        return True  # No threats, so it's defended

    if len(defenders) == 0:
        return False  # No defenders, so it's hanging

    # If the piece is worth more than the cheapest attacking piece, it's hanging
    if value_of_piece_under_attack > min_value_piece(board, attackers):
        return False

    return True  # Otherwise, it's defended
    


def min_value_piece(board: chess.Board, squares: chess.SquareSet):
    if not squares:
        return 0
    min_value = values[chess.QUEEN]
    for square in squares:
        piece_at_square = board.piece_type_at(square)
        min_value = min(min_value, values[piece_at_square])
    return min_value

def ray_attackers(board: chess.Board, color: chess.Color, square: chess.Square) -> chess.SquareSet:
    attackers = chess.SquareSet()
    # ray defense https://lichess.org/editor/6k1/3q1pbp/2b1p1p1/1BPp4/rp1PnP2/4PRNP/4Q1P1/4B1K1_w_-_-_0_1
    for attacker in board.attackers(not color, square):
        attacker_piece = board.piece_at(attacker)
        assert(attacker_piece)
        if attacker_piece.piece_type in ray_piece_types:
            bc = board.copy(stack = False)
            bc.remove_piece_at(attacker)
            attackers = attackers.union(bc.attackers(color, square)) 
    return attackers

def is_square_attacked_more_than_defended(board: chess.Board, square: chess.Square, pov: chess.Color) -> bool:
    attackers_white = board.attackers_mask(chess.WHITE, square)
    attackers_black = board.attackers_mask(chess.BLACK, square)
    
    # Check for x-ray attacks
    for color, attackers in [(chess.WHITE, attackers_white), (chess.BLACK, attackers_black)]:
        for attacker_square in chess.scan_forward(attackers):
            attacker_piece = board.piece_at(attacker_square)
            if attacker_piece and attacker_piece.piece_type in [chess.BISHOP, chess.ROOK, chess.QUEEN]:
                # Create a copy of the board and remove the blocking piece
                board_copy = board.copy()
                board_copy.remove_piece_at(attacker_square)
                
                # Check for x-ray attacks
                xray_attackers = board_copy.attackers_mask(color, square)
                if color == chess.WHITE:
                    attackers_white |= xray_attackers
                else:
                    attackers_black |= xray_attackers
    
    num_attackers_white = chess.popcount(attackers_white)
    num_attackers_black = chess.popcount(attackers_black)
    
    if pov:
        return num_attackers_black > num_attackers_white
    return num_attackers_white > num_attackers_black

def game_from_fen(fen, last_move_uci):
    board = chess.Board(fen)
    last_move = chess.Move.from_uci(last_move_uci)
    board.push(last_move)
    game = chess.pgn.Game.from_board(board)
    return game

def attacked_opponent_squares(board: chess.Board, from_square: chess.Square, pov: chess.Color) -> List[Tuple[chess.Piece, chess.Square]]:
    pieces = []
    piece = board.piece_at(from_square)
    
    # Get direct attacks first
    direct_squares = board.attacks(from_square)
    for attacked_square in direct_squares:
        attacked_piece = board.piece_at(attacked_square)
        if attacked_piece and attacked_piece.color != pov:
            pieces.append((attacked_piece, attacked_square))
    
    # Check for x-ray attacks if it's a sliding piece
    if piece and piece.piece_type in [chess.BISHOP, chess.ROOK, chess.QUEEN]:
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