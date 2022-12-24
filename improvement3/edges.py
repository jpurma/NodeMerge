from kivy.graphics import *
from util import hue
from ctrl import ctrl
import math


def radial_pos(i, node_i, signal_count, lex_item_count, size):
    a = (math.pi / signal_count) * (i - 1)
    b = ((2 * math.pi) / lex_item_count) * -(node_i - 1)
    a = b - a
    x = math.cos(a) * size
    y = math.sin(a) * size
    return x, y


class Edge:
    draw_in_route_mode = False
    draw_in_feature_mode = True

    def __init__(self, start, end, id=''):
        self.id = id or f'{start.id}_{end.id}'
        ctrl.edges[self.id] = self
        self.activations = []
        self.start = start
        self.end = end

    def __repr__(self):
        return f'{self.__class__.__name__}({self.id})'

    @property
    def signal(self):
        return self.activations[0] if self.activations else None

    def draw(self):
        cx = self.start.x + (self.end.x - self.start.x) * .9
        cy = self.start.y + (self.end.y - self.start.y) * .9
        with ctrl.g.canvas:
            Color(*self.color)
            Line(points=[self.start.x, self.start.y, self.end.x, self.end.y], width=1)
            Line(circle=[cx, cy, 3], width=2)
            x_diff = 0
            y_diff = 0
            for activation in self.activations:
                if not isinstance(activation, tuple):
                    activation = [activation]
                for signal in activation:
                    Color(hue(signal), 0.8, 0.5, mode='hsv')
                    Line(points=[self.start.x + x_diff, self.start.y + y_diff, self.end.x + x_diff, self.end.y + y_diff], width=2)
                    Line(circle=[cx, cy, 3], width=2)
                    x_diff += 2
                x_diff += 2

    def activate(self, n):
        if n not in self.activations:
            self.activations.append(n)
            self.end.activate(n)

    @property
    def color(self):
        return self.start.color

    @staticmethod
    def get(start, end):
        return ctrl.edges.get(f'{start.id}_{end.id}')

    @staticmethod
    def get_or_create(start, end):
        return Edge.get(start, end) or __class__(start, end)


class RouteEdge(Edge):
    draw_in_route_mode = True
    draw_in_feature_mode = False

    def __init__(self, start, end, origin):
        edge_id = f'{start.signal}_{end.signal}O{origin.signal}'
        super().__init__(start.li, end.li, id=edge_id)
        self.start_signal = start.signal
        self.end_signal = end.signal
        self.origin = origin

    def draw(self):
        dx, dy = radial_pos(self.origin.signal, self.start_signal, ctrl.words.signal_count, len(ctrl.g.lexicon), 40)
        ex, ey = radial_pos(self.origin.signal, self.end_signal, ctrl.words.signal_count, len(ctrl.g.lexicon), 40)
        cx = self.start.x + dx + (self.end.x + ex - (self.start.x + dx)) * .9
        cy = self.start.y + dy + (self.end.y + ey - (self.start.y + dy)) * .9

        with ctrl.g.canvas:
            Color(hue(self.origin.signal), 0.8, 0.5, mode='hsv')
            Line(points=[self.start.x + dx, self.start.y + dy, self.end.x + ex, self.end.y + ey], width=2)
            Line(circle=[cx, cy, 3], width=2)

    @staticmethod
    def exists(start, end, origin):
        return f'{start.signal}_{end.signal}O{origin.signal}' in ctrl.edges

class LexEdge(Edge):
    @staticmethod
    def get_or_create(start, end):
        return LexEdge.get(start, end) or __class__(start, end)

    def activate(self, n):
        pass


class MergeEdge:
    draw_in_route_mode = False
    draw_in_feature_mode = True

    def __init__(self, start, end):
        print(f'** creating merge edge arg: {start} head: {end}')
        self.id = MergeEdge.create_id(start, end)
        ctrl.edges[self.id] = self
        self.active = True
        self.start = start
        self.end = end
        self.signal = start.signal

    def __repr__(self):
        return f'{self.__class__.__name__}({self.id})'

    @property
    def arg(self):
        return self.start

    @property
    def head(self):
        return self.end

    def draw(self):
        sn = self.start.li
        en = self.end.li
        cx = sn.x + (en.x - sn.x) * .9
        cy = sn.y + (en.x - sn.x) * -.3
        with ctrl.g.canvas:
            Color(hue(self.signal), .5, .6, mode='hsv')
            Bezier(points=[sn.x, sn.y + self.start.signal * 2, cx, cy, en.x, en.y + self.end.signal * 2], width=3)

    @staticmethod
    def create_id(start, end):
        return f'D{start.li.id}{start.signal}_{end.li.id}{end.signal}'


class AdjunctEdge:
    color = [0.8, 0.2, 0.2]
    draw_in_route_mode = False
    draw_in_feature_mode = True

    def __init__(self, start, end):
        print('** creating adjunct edge ', start, end)
        self.id = f'{start.li.id}{start.signal}_{end.li.id}{end.signal}'
        ctrl.edges[self.id] = self
        self.active = True
        self.start = start
        self.end = end

    def __repr__(self):
        return f'{self.__class__.__name__}({self.id})'

    def draw(self):
        sn = self.start.li
        en = self.end.li
        with ctrl.g.canvas:
            Color(hue(self.start.signal), .5, .6, mode='hsv')
            Line(points=[sn.x, sn.y - self.start.signal, en.x, en.y - self.end.signal], width=1)
