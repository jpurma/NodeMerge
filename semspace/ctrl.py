
SPACING = 12


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
