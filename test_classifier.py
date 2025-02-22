import unittest
from classifier import is_fork, is_piece_hanging, is_pin, is_mate_in_1, is_sacrifice, is_deflection

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
   
    def test_hanging_piece_3(self) -> None:
       fen = "6k1/1q1nppb1/2p3p1/2Pn3p/1rNP4/4P1P1/5P1P/2QRBBK1 w - - 1 27"
       best_move = "e1b4"
       self.assertTrue(is_piece_hanging(fen, best_move))
   
    def test_hanging_piece_4(self) -> None:
       fen = "4r1rk/pppq4/3pbp1p/6p1/4Pn2/1B3Q1P/PPP1NPPK/3RR3 w - - 2 21"
       best_move = "e2f4"
       self.assertTrue(is_piece_hanging(fen, best_move))
   
    def test_hanging_piece_5(self) -> None:
       fen = "r4r1k/pppq1p2/3pbn1p/6p1/4P3/1BN2QbP/PPP2PP1/R3R1K1 w - - 0 16"
       best_move = "f3f6"
       self.assertTrue(is_piece_hanging(fen, best_move))

    def test_hanging_piece_6(self) -> None:
       fen = "6rk/ppp3q1/3p1prp/8/2P1PQb1/1B5P/PP3P1K/3R2R1 w - - 0 26"
       best_move = "g1g4"
       self.assertTrue(is_piece_hanging(fen, best_move))

    def test_pin_1(self) -> None:
         fen = "7r/pR2pp2/B1p1k1pp/3q4/3b2PP/1Q6/P4P2/6K1 w - - 0 29"
         best_move = "a6c4"
         self.assertTrue(is_pin(fen, best_move)) 
      
    def test_pin_2(self) -> None:
         fen = "rnbk2nr/1p4pp/p2b1p2/2p1p3/2B1P3/2N1BN2/PPP2PPP/R3K2R w KQ - 0 9"
         best_move = "e1c1"
         self.assertTrue(is_pin(fen, best_move)) 
      
    def test_sacrifice(self) -> None:
         # TODO: Seems like this could also be a clearance
         fen = "r5nr/6pp/p1kbbp2/1ppNp3/4P3/2P1BP2/PP1R1P1P/2KR1B2 w - - 2 16"
         best_move = "d5b4"
         self.assertTrue(is_sacrifice(fen, best_move)) 

    @unittest.skip("TODO")
    def test_clearance_sacrifice(self) -> None:
         # TODO: Seems like this could also be a clearance
         fen = "r5nr/6pp/p1kbbp2/1ppNp3/4P3/2P1BP2/PP1R1P1P/2KR1B2 w - - 2 16"
         best_move = "d5b4"
         self.assertTrue(is_clearance_sacrifice(fen, best_move)) 

    def test_mate_in_1(self) -> None:
         fen = "6rk/ppp5/3p1p1p/8/2P1PQq1/1B6/PP3P1K/3R4 w - - 0 28"
         best_move = "f4h6"
         self.assertTrue(is_mate_in_1(fen, best_move))
 
    @unittest.skip("TODO")
    def test_deflection(self) -> None:
         fen = "3r2nr/6pp/p1kbbN2/1pp1p3/4P3/2P1BP2/PP1R1P1P/2KR1B2 w - - 1 17"
         best_move = "f6e8"
         self.assertTrue(is_deflection(fen, best_move))
     
    @unittest.skip("TODO")
    def test_mate_in_9(self) -> None:
         fen = "7r//B1p1k1pp/3q4/3b2PP/1Q6/P4P2/6K1 w - - 0 29"
         best_move = "d3d4"
         self.assertTrue(is_mate_in_9(fen, best_move)) 

    @unittest.skip("TODO")
    def test_ruin_pawn_structure(self) -> None:
         fen = "1r4k1/2qnppb1/2p2np1/2Pp3p/2bP3N/4P1P1/1B1N1PBP/Q2R2K1 w - - 4 19"
         best_move = "d2c4"
         self.assertTrue(is_ruin_pawn_structure(fen, best_move)) 
   



if __name__ == '__main__':
    unittest.main()
