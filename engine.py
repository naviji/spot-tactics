from chess.engine import SimpleEngine, Limit

# best_move_limit = Limit(depth = 50, time = 30, nodes = 25_000_000)
best_move_limit = Limit(depth = 20, time = 10, nodes = 10_000_000)


class Engine:
    def __init__(self, name, threads=6):
        self.engine = SimpleEngine.popen_uci(name)
        self.engine.configure({'Threads': threads})

    def find_best_move(self, board):
        info = self.engine.analyse(board, multipv = 1, limit = best_move_limit)
        return info[0]["pv"][0]
    
    def close(self):
        self.engine.close()