from kivy.graphics import *
from util import hue
from ctrl import ctrl


class Edge:
    def __init__(self, start, end):
        self.id = f'{start.id}_{end.id}'
        ctrl.edges[self.id] = self
        self.activations = {}
        self.start = start
        self.end = end
        self.hue = 0
        self.loss = 0.03

    def __repr__(self):
        return f'{self.__class__.__name__}({self.id})'

    def get_signal(self, signal):
        if isinstance(signal, str):
            return self.activations.get(signal, None)
        return self.activations.get(signal.key, None)

    def draw(self):
        pass
        # with ctrl.g.canvas:
        #     x_diff = 0
        #     y_diff = 0
        #     for signal in self.activations.values():
        #         if len(signal.parts) > 1:
        #             for signal_part in signal.parts:
        #                 Color(hue(signal_part), 0.8, signal.strength, mode='hsv')
        #                 Point(points=[self.start.x + x_diff, self.start.y + y_diff, self.end.x + x_diff, self.end.y +
        #                           y_diff], pointsize=2)
        #                 x_diff += 2
        #             x_diff += 2

    def set_signal(self, signal):
        existing = self.activations.get(signal.key, None)
        if (not existing) or existing.strength < signal.strength:
            self.activations[signal.key] = signal

    def activate(self, signal):
        if not signal or signal.strength <= 0:
            return
        if len(signal.parts) > 1:
            # seeker signal
            if (not (existing := self.get_signal(signal))) or signal.strength > existing.strength:
                # weaken also seeker signals to avoid them looping infinitely
                weakened_signal = signal.copy() #.weaken(self.loss / 2)
                if weakened_signal:
                    self.activations[signal.key] = weakened_signal
                    self.end.activate(weakened_signal)
        else:
            # outbound activation, preparing the strongest route back to initial node
            end_signal = self.end.get_signal(signal)
            my_activation = self.get_signal(signal)
            if signal.strength > 0 and \
                    ((not my_activation) or my_activation.strength < signal.strength - self.loss):
                if end_signal and end_signal.strength > signal.strength - self.loss:
                    self.set_signal(end_signal)
                else:
                    weakened_signal = signal.copy().weaken(self.loss)
                    if weakened_signal:
                        self.set_signal(weakened_signal)
                        self.end.activate(weakened_signal)

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

