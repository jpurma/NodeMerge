import math

from kivy.graphics import *
from util import hue
from ctrl import ctrl, MARGIN_X, MARGIN_Y


class Edge:
    def __init__(self, start, end):
        self.id = f'{start.id}_{end.id}'
        ctrl.edges[self.id] = self
        self.activations = {}
        self.start = start
        self.end = end
        self.hue = 0
        self.loss = 0.01  # 0.03
        self.length = math.dist((start.x, start.y), (end.x, end.y))
        self.log_length = math.log10(self.length)
        self.weakening = self.loss * self.log_length

    def __repr__(self):
        return f'{self.__class__.__name__}({self.id})'

    def __lt__(self, other):
        return self.id < other.id

    def get_signal(self, signal):
        if isinstance(signal, str):
            return self.activations.get(signal, None)
        return self.activations.get(signal.key, None)

    def draw(self):
        if not self.activations:
            return
        with ctrl.g.canvas:
            x_diff = 0
            y_diff = 0
            sx = self.start.x + MARGIN_X
            sy = self.start.y + MARGIN_Y
            ex = self.end.x + MARGIN_X
            ey = self.end.y + MARGIN_Y

            # if sx > ex or sy > ey:
            #     y_diff += 2
            #     x_diff += 2
            #     h = 0.5
            # else:
            #     h = 0
            # Color(h, 0, 0.3, mode='hsv')
            # Line(points=[sx + x_diff, sy + y_diff, ex + x_diff, ey +
            #              y_diff], width=1)
            for signal in self.activations.values():
                if signal.is_seeker():
                    w = 0.5
                    s = 0.3
                    if (inbound_start_signal := self.start.get_inbound_signal(signal)) and inbound_start_signal.strength:
                        w = 2
                        s = 0.9
                    for signal_part in signal.parts:
                        Color(hue(signal_part), s, signal.strength * 2, mode='hsv')
                        Line(points=[sx + x_diff, sy + y_diff, ex + x_diff, ey +
                                     y_diff], width=w)
                        x_diff += 1
                elif signal.is_inwards() and False:
                    Color(hue(signal.parts[0]), 0.5, signal.strength / 2, mode='hsv')
                    Line(points=[sx + x_diff, sy + y_diff, ex + x_diff, ey +
                                 y_diff], width=0.5)
                x_diff += 1

    def set_signal(self, signal):
        existing = self.activations.get(signal.key, None)
        if (not existing) or existing.strength < signal.strength:
            self.activations[signal.key] = signal

    def activate(self, signal, loss=0):
        if not signal or signal.strength <= 0:
            return
        existing_activation = self.get_signal(signal)
        if (existing_activation
                and (signal.strength < existing_activation.strength
                or (signal.strength == existing_activation.strength and signal.is_outgoing()))):
            return
        signal = signal.copy()
        self.activations[signal.key] = signal
        if signal.is_seeker():
            # seeker signal has parts (source_head, target_attr)
            # replace weaker signal with current stronger one and activate edge end node
            # weaken seeker signals to avoid them looping infinitely?
            self.end.activate(signal, loss or self.loss)
        else:
            # outbound signal marks nodes for their distance to signal source
            self.end.activate(signal, self.weakening)

    def reset(self):
        self.activations = {}

    @property
    def color(self):
        return self.start.color

    @staticmethod
    def get(start, end):
        return ctrl.edges.get(f'{start.id}_{end.id}')

    @staticmethod
    def get_or_create(start, end):
        return Edge.get(start, end) or __class__(start, end)
