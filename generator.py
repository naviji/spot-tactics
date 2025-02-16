import logging
from chess.pgn import Game, read_game
from io import StringIO
from chess import Board
from chess.engine import Cp, Score
import math
import copy
from puzzle import Puzzle
from typing import List
MISTAKE_THRESHOLD = 0.23

class Generator:
    def __init__(self, engine):
        self.engine = engine
        self.logger = logging.getLogger(__name__)
        logging.basicConfig(format='%(asctime)s %(levelname)-4s %(message)s', datefmt='%m/%d %H:%M')
        self.logger.setLevel(logging.DEBUG)
                

    def generate(self, pgn) -> List[Puzzle]:
        puzzles = []
        for line in pgn.split('\n'):
            if line.startswith("[Event"):
                site = line
            elif "%eval" in line:
                game = read_game(StringIO("{}\n{}".format(site, line)))
                prev_score: Score = Cp(20)
                for node in game.mainline():
                    current_eval = node.eval()
                    if not current_eval:
                        self.logger.debug("Skipping game without eval: %s", node)
                        return puzzles
                    winner = node.board().turn
                    score = current_eval.pov(winner)
                    if self.win_chances(score) > self.win_chances(prev_score) + MISTAKE_THRESHOLD:
                        self.logger.debug("Found tactical opportunity: %s", node.board().fen())
                        best_move = self.engine.find_best_move(node.board())
                        
                        # Create new game from current position
                        game_snapshot = Game()
                        game_snapshot.setup(node.board().fen())
                        # Add the best move as main variation
                        tactic_node = game_snapshot.add_variation(best_move)
                        puzzles.append(Puzzle(tactic_node))
                    prev_score = -score
        return puzzles

    def win_chances(self, score: Score) -> float:
        """
        winning chances from -1 to 1 https://graphsketch.com/?eqn1_color=1&eqn1_eqn=100+*+%282+%2F+%281+%2B+exp%28-0.004+*+x%29%29+-+1%29&eqn2_color=2&eqn2_eqn=&eqn3_color=3&eqn3_eqn=&eqn4_color=4&eqn4_eqn=&eqn5_color=5&eqn5_eqn=&eqn6_color=6&eqn6_eqn=&x_min=-1000&x_max=1000&y_min=-100&y_max=100&x_tick=100&y_tick=10&x_label_freq=2&y_label_freq=2&do_grid=0&do_grid=1&bold_labeled_lines=0&bold_labeled_lines=1&line_width=4&image_w=850&image_h=525
        """
        mate = score.mate()
        if mate is not None:
            return 1 if mate > 0 else -1

        cp = score.score()
        MULTIPLIER = -0.00368208 # https://github.com/lichess-org/lila/pull/11148
        return 2 / (1 + math.exp(MULTIPLIER * cp)) - 1 if cp is not None else 0


