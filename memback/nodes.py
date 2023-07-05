from collections import defaultdict

from kivy.graphics import *

from memback.util import hue
from memback.edges import Edge
from memback.ctrl import ctrl, NETWORK_WIDTH, NETWORK_HEIGHT, THRESHOLD, LEARNING_SPEED


INACTIVE = 0
ACTIVE = 1
PRIMED = 2


class Node:
    color = [32, 32, 128, 128]

    def __init__(self, id):
        self.id = id
        ctrl.nodes[id] = self
        self.edges_out = []
        self.edges_in = []
        self.x = 0
        self.y = 0
        self.i = 0
        self.is_output = False
        self.error = 0
        self.last_error = 0
        self.activations = defaultdict(float)
        self.active = False
        self.label_item = None
        self.color = None

    def __repr__(self):
        return f'{self.__class__.__name__}({self.id})'

    def __lt__(self, other):
        if self.y == other.y:
            return self.x < other.x
        return self.y < other.y

    def __hash__(self):
        return hash(self.id)

    def get_label(self):
        return self.id

    def get_signal_by_key(self, signal: str):
        return self.activations.get(signal, None)

    def connect(self, other):
        edge = Edge.get_or_create(self, other)
        if edge not in self.edges_out:
            self.edges_out.append(edge)
        if edge not in other.edges_in:
            other.edges_in.append(edge)
        return edge

    @property
    def activation(self):
        return sum(self.activations.values())

    def receive(self, signals):
        for signal, strength in signals:
            self.activations[signal] += strength

    def activate(self):
        total = self.activation
        if ctrl.g.debug:
            print(f'{self.id}: {total} {total > THRESHOLD} {ctrl.g.expected_output[self.i] if self.is_output else self.error}')
        if total > THRESHOLD:
            if total > 0.5:
                self.active = ACTIVE
            else:
                self.active = INACTIVE
            if total > 1:
                total = 1.0
            signals = [(signal, strength / total) for signal, strength in self.activations.items()]
            for out in self.edges_out:
                out.transfer(signals)
        else:
            self.active = INACTIVE
            for out in self.edges_out:
                out.clear()

    def deactivate(self):
        self.activations = defaultdict(float)
        self.active = False

    def reset(self):
        self.deactivate()

    def adjust_error(self):
        if self.is_output:
            self.error = int(ctrl.g.expected_output[self.i]) - self.activation
            if ctrl.g.debug:
                print(f'output error at {self.i}: {self.error}, activation {self.activation}')
        if self.error: # and self.is_output or ctrl.g.iteration > 2:  # ärsykkeen vaihdon jälkeen jätetään ensimmäisillä kierroksilla
            # oppimatta jotta ei opita edellisen ärsykkeen virheen perusteella ja väärin
            for incoming_edge in self.edges_in:
                edge_strength = max(incoming_edge.total(), 1 / len(self.edges_in))
                error_portion = edge_strength * self.error
                adjustment = error_portion * LEARNING_SPEED
                if ctrl.g.debug:
                    print(f'share of error {self.error} for edge {incoming_edge.id} is {error_portion}, modifying its weight {incoming_edge.weight} by {adjustment}')
                incoming_edge.weight += adjustment
                if incoming_edge.weight > 1:
                    incoming_edge.weight = 1.0
                elif incoming_edge.weight < -1:
                    incoming_edge.weight = -1.0
                incoming_edge.start.error += error_portion
        self.last_error = self.error
        self.error = 0
        self.activations.clear()  # eivät kasaannu

    def draw(self):
        if not self.active or True:
            return
        c = Color(0.2, 0.8, 0.5, mode='hsv')
        y = self.y
        x = self.x
        ctrl.g.world_array[y][x] = [d * 255 for d in c.rgba]

        for signal, strength in self.activations.items():
            c = Color(hue(signal), 1.0, strength * 2, mode='hsv')
            ctrl.g.world_array[y][x] = [d * 255 for d in c.rgba]
            if y < NETWORK_HEIGHT - 1:
                ctrl.g.world_array[y + 1][x] = [d * 255 for d in c.rgba]
            if x < NETWORK_WIDTH - 1:
                x += 1
                ctrl.g.world_array[y][x] = [d * 255 for d in c.rgba]
                if y < NETWORK_HEIGHT - 1:
                    ctrl.g.world_array[y + 1][x] = [d * 255 for d in c.rgba]
            if x < NETWORK_WIDTH - 1:
                x += 1

        with ctrl.g.canvas:
            if self.active:
                sx = self.x
                sy = self.y
                Color(1.0, 1.0, 1.0 if self.active == PRIMED else 0.2, mode='hsv')
                Point(points=[sx, sy], pointsize=4)

    def set_color_from_signal(self, signal):
        self.color = Color(hue(signal), 0.8, 1.0, mode='hsv').rgba