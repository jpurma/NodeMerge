NETWORK_WIDTH = 1440
NETWORK_HEIGHT = 960
MARGIN_X = 20
MARGIN_Y = 200

THRESHOLD = 0 # 0.5
LEARNING_SPEED = 0.005
MAX_ITERATIONS = 23
CYCLES = 1000


class Controller:
    def __init__(self):
        self.g = None

    def post_initialize(self, g):
        self.g = g

    @property
    def nodes(self):
        return self.g.nodes

    @property
    def edges(self):
        return self.g.edges

    @property
    def words(self):
        return self.g.words


ctrl = Controller()
