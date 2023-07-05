import random

from kivy.graphics import *
from memback.ctrl import ctrl, MARGIN_X, MARGIN_Y


class Edge:
    def __init__(self, start, end):
        self.id = f'{start.id}_{end.id}'
        ctrl.edges[self.id] = self
        self.start = start
        self.end = end
        self.hue = 0
        self.signals = []
        self.weight = random.random() / 4 - 0.125

    def __repr__(self):
        return f'{self.__class__.__name__}({self.id})'

    def __lt__(self, other):
        return self.id < other.id

    def draw(self):
        if not self.signals:
            return
        with ctrl.g.canvas:
            sx = self.start.x + MARGIN_X
            sy = self.start.y + MARGIN_Y
            ex = self.end.x + MARGIN_X
            ey = self.end.y + MARGIN_Y

            w = 0.5
            s = 0.7
            strength = self.total()
            Color(1.0 if strength < 0 else 0.3, s, strength, mode='hsv')
            Line(points=[sx, sy, ex, ey], width=w)

            # x_diff = 0
            # y_diff = 0
            # for signal, strength in self.signals:
            #     w = 0.5
            #     s = 0.7
            #     Color(hue(signal), s, strength * self.weight * 5, mode='hsv')
            #     Line(points=[sx + x_diff, sy + y_diff, ex + x_diff, ey +
            #                  y_diff], width=w)
            #     x_diff += 1

    def transfer(self, signals):
        self.signals = signals
        self.end.receive([(signal, strength * self.weight) for signal, strength in signals])

    def reset(self):
        self.signals = []

    def total(self):
        return sum(strength for signal, strength in self.signals) * self.weight

    def clear(self):
        self.signals = []

    @property
    def color(self):
        return self.start.color

    @staticmethod
    def get(start, end):
        return ctrl.edges.get(f'{start.id}_{end.id}')

    @staticmethod
    def get_or_create(start, end):
        return Edge.get(start, end) or __class__(start, end)
