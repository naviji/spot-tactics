import unittest
from classifier import is_fork

class TestClassifier(unittest.TestCase):

    def test_fork(self) -> None:
       fen = "rn1qkb1r/ppp2ppp/5n2/4p3/2B1P3/5Q2/PPP2PPP/RNB1K2R w KQkq - 2 7"
       self.assertTrue(is_fork(fen, "f3b3"))

   #  def test_pin(self) -> None:
   #     fen = "r2q1rk1/pppn1pp1/5n1p/4p1B1/2B1P3/2Q5/PPP2PPP/3R1RK1 w - - 0 12"
   #     self.assertTrue(pin(fen, 'g5f6'), f"Expected pin for {fen}")

if __name__ == '__main__':
    unittest.main()
