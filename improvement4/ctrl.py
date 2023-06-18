

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
    def features(self):
        return self.g.features

    @property
    def signaler(self):
        return self.g.signaler


def decay_function(strength):
    return 0.8 * strength


decay_threshold = 0.1

ctrl = Controller()
