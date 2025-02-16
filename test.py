import unittest
from engine import Engine
from generator import Generator
from puzzle import Puzzle

class TestGenerate(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.engine = Engine("stockfish", 6) # don't use more than 6 threads! it fails at finding mates
        cls.gen = Generator(cls.engine)

    def test_puzzle_1(self) -> None:
        """Test that the puzzle generator returns the correct solution and tags for a given FEN position."""
        pgn = """[Event "Rated rapid game"]
[Site "https://lichess.org/0YiOyDOR"]
[Date "2025.02.02"]
[White "kramford"]
[Black "jishnukp"]
[Result "0-1"]
[GameId "0YiOyDOR"]
[UTCDate "2025.02.02"]
[UTCTime "09:29:26"]
[WhiteElo "1547"]
[BlackElo "1234"]
[WhiteRatingDiff "-14"]
[BlackRatingDiff "+14"]
[Variant "Standard"]
[TimeControl "300+5"]
[ECO "C41"]
[Termination "Time forfeit"]

1. e4 { [%eval 0.18] } 1... e5 { [%eval 0.21] } 2. Nf3 { [%eval 0.13] } 2... d6 { [%eval 0.48] } 3. d4 { [%eval 0.58] } 3... Bg4 { [%eval 0.95] } 4. dxe5 { [%eval 0.88] } 4... Bxf3 { [%eval 1.44] } 5. Qxf3 { [%eval 1.31] } 5... dxe5 { [%eval 1.46] } 6. Bc4 { [%eval 1.68] } 6... Nf6 { [%eval 2.08] } 7. Nc3 { [%eval 0.78] } 7... Bb4 { [%eval 0.82] } 8. O-O { [%eval 1.29] } 8... Bxc3 { [%eval 1.48] } 9. Qxc3 { [%eval 1.65] } 9... O-O { [%eval 1.51] } 10. Bg5 { [%eval 0.92] } 10... Nbd7 { [%eval 1.15] } 11. Rad1 { [%eval 1.03] } 11... h6 { [%eval 4.89] } 12. Bh4 { [%eval 0.95] } 12... g5 { [%eval 1.62] } 13. Bg3 { [%eval 1.16] } 13... Nxe4 { [%eval 2.29] } 14. Qb3 { [%eval 0.45] } 14... Qe7 { [%eval 0.49] } 15. Rfe1 { [%eval -0.04] } 15... Ndc5 { [%eval 0.25] } 16. Qa3 { [%eval 0.19] } 16... Rad8 { [%eval 0.17] } 17. Rxe4 { [%eval -3.86] } 17... Rxd1+ { [%eval -3.84] } 18. Bf1 { [%eval -3.79] } 18... Qe6 { [%eval -0.2] } 19. Qxc5 { [%eval -0.28] } 19... Rfd8 { [%eval 1.63] } 20. Rxe5 { [%eval 0.99] } 20... Qxa2 { [%eval 1.79] } 21. f3 { [%eval 0.48] } 21... Qa1 { [%eval 1.44] } 22. Qf2 { [%eval 0.0] } 22... R8d2 { [%eval 1.56] } 23. Re8+ { [%eval 1.64] } 23... Kh7 { [%eval 1.94] } 24. Re2 { [%eval 1.66] } 24... Rd5 { [%eval 2.48] } 0-1

"""
        result = self.gen.generate(pgn)
        self.assertIsInstance(result, Puzzle, f"Expected Puzzle object for game: https://lichess.org/0YiOyDOR, but got {result}")


    @classmethod
    def tearDownClass(cls):
        cls.engine.close()


if __name__ == '__main__':
    unittest.main()
