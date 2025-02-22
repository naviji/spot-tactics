from typing import List, Tuple
import chess
import chess.pgn

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