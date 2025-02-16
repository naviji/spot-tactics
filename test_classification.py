import unittest
from puzzle import fork

class TestDetection(unittest.TestCase):

    def test_fork(self) -> None:
       fen = "rn1qkb1r/ppp2ppp/5n2/4p3/2B1P3/5Q2/PPP2PPP/RNB1K2R w KQkq - 2 7"
       self.assertTrue(fork(fen, 'f3b3'), f"Expected fork for {fen}")

if __name__ == '__main__':
    unittest.main()
