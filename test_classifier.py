import unittest
from classifier import is_fork, is_piece_hanging

class TestClassifier(unittest.TestCase):

    def test_fork(self) -> None:
       fen = "rn1qkb1r/ppp2ppp/5n2/4p3/2B1P3/5Q2/PPP2PPP/RNB1K2R w KQkq - 2 7"
       best_move = "f3b3"
       self.assertTrue(is_fork(fen, best_move))
    
    def test_hanging_piece_1(self) -> None:
       fen = "rn2kb1r/pp2pppp/2pp1n2/7b/3PP3/2NBBN1P/PqP2PP1/1R1QK2R b Kkq - 1 9"
       best_move = "b2c3"
       self.assertTrue(is_piece_hanging(fen, best_move))

    def test_hanging_piece_2(self) -> None:
       fen = "7r/pR2pp2/B1p1k1pp/2qn4/2Pb2PP/1Q6/P4P2/6K1 w - - 1 28"
       best_move = "c4d5"
       self.assertTrue(is_piece_hanging(fen, best_move))

if __name__ == '__main__':
    unittest.main()
