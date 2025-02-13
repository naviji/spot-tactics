
import chess.pgn
from chess.engine import SimpleEngine, Mate, Cp, Score, PovScore
from typing import List, Optional, Union, Set

from io import StringIO

from dataclasses import dataclass
from chess.pgn import GameNode, ChildNode

from chess import Move, Color

@dataclass
class Puzzle:
    node: ChildNode
    moves: List[Move]
    cp: int

# --- SETTINGS ---
PGN_FILE = "kramford_games.pgn"  # Change this to the actual filename
mate_soon = Mate(15)


def process_pgn_file():
    """ Reads a PGN file and analyzes each game to extract puzzles. """
    with open(PGN_FILE, "r", encoding="utf-8") as pgn:
        game_data = ""
        for line in pgn:
            if line.startswith("[Site "):  
                if game_data:  # If a game was already collected, process it
                    analyze_game(game_data)
                game_data = line  # Start new game collection
            else:
                game_data += line

        # Process the last game in the file
        if game_data:
            analyze_game(game_data)

def maximum_castling_rights(board: chess.Board) -> chess.Bitboard:
    return (
        (board.pieces_mask(chess.ROOK, chess.WHITE) & (chess.BB_A1 | chess.BB_H1) if board.king(chess.WHITE) == chess.E1 else chess.BB_EMPTY) |
        (board.pieces_mask(chess.ROOK, chess.BLACK) & (chess.BB_A8 | chess.BB_H8) if board.king(chess.BLACK) == chess.E8 else chess.BB_EMPTY)
    )


class Generator:
    def analyze_game(self, game):
        
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
                return None

            board.push(node.move)
            epd = board.epd()
            if epd in seen_epds:
                skip_until_irreversible = True
                continue
            seen_epds.add(epd)

            if board.castling_rights != maximum_castling_rights(board):
                continue

            result = self.analyze_position(node, prev_score, current_eval)

            if isinstance(result, Puzzle):
                return result

            prev_score = -result

        print("Found nothing from {}".format(game.headers.get("Site")))

        return None

    def analyze_position(self, node: ChildNode, prev_score: Score, current_eval: PovScore) -> Union[Puzzle, Score]:

        board = node.board()
        winner = board.turn
        score = current_eval.pov(winner)

        if board.legal_moves.count() < 2:
            return score

        game_url = node.game().headers.get("Site")

        print("{} {} to {}".format(node.ply(), node.move.uci() if node.move else None, score))

        if prev_score > Cp(300) and score < mate_soon:
            print("{} Too much of a winning position to start with {} -> {}".format(node.ply(), prev_score, score))
            return score
        if is_up_in_material(board, winner):
            print("{} already up in material {} {} {}".format(node.ply(), winner, material_count(board, winner), material_count(board, not winner)))
            return score
        elif score >= Mate(1):
            print("{} mate in one".format(node.ply()))
            return score
        elif score > mate_soon:
            print("Mate {}#{} Probing...".format(game_url, node.ply()))
            if self.server.is_seen_pos(node):
                print("Skip duplicate position")
                return score
            mate_solution = self.cook_mate(copy.deepcopy(node), winner)
            if mate_solution is None or (tier == 1 and len(mate_solution) == 3):
                return score
            return Puzzle(node, mate_solution, 999999999)
        elif score >= Cp(200) and win_chances(score) > win_chances(prev_score) + 0.6:
            if score < Cp(400) and material_diff(board, winner) > -1:
                print("Not clearly winning and not from being down in material, aborting")
                return score
            print("Advantage {}#{} {} -> {}. Probing...".format(game_url, node.ply(), prev_score, score))
            if self.server.is_seen_pos(node):
                print("Skip duplicate position")
                return score
            puzzle_node = copy.deepcopy(node)
            solution : Optional[List[NextMovePair]] = self.cook_advantage(puzzle_node, winner)
            self.server.set_seen(node.game())
            if not solution:
                return score
            while len(solution) % 2 == 0 or not solution[-1].second:
                if not solution[-1].second:
                    print("Remove final only-move")
                solution = solution[:-1]
            if not solution or len(solution) == 1 :
                print("Discard one-mover")
                return score
            if tier < 3 and len(solution) == 3:
                print("Discard two-mover")
                return score
            cp = solution[len(solution) - 1].best.score.score()
            return Puzzle(node, [p.best.move for p in solution], 999999998 if cp is None else cp)
        else:
            return score

generator = Generator()

def analyze_game(game_data: str):
    """ Parses a PGN game and analyzes it for puzzles. """
    game = chess.pgn.read_game(StringIO(game_data))
    if game:
        print(f"Analyzing game {game.headers.get('Site', 'Unknown')}")
        puzzle = generator.analyze_game(game)
        if puzzle:
            print(f"Puzzle found for game {game.headers.get('Site', 'Unknown')}")
    else:
        print("Failed to parse a game.")

if __name__ == "__main__":
    process_pgn_file()
