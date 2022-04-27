from kivy.graphics import *
from util import hue
from edges import Edge
from ctrl import ctrl, SPACING


class Node:
    color = [32, 32, 128, 128]

    def __init__(self, id):
        self.id = id
        ctrl.nodes[id] = self
        self.edges_out = []
        self.edges_in = []
        self.x = 0
        self.y = 0
        self.sc_x = 0
        self.sc_y = 0
        self.activations = {}
        self.active = False
        self.label_item = None
        self.sem_word = ""
        self.loss = 0.01

    def __repr__(self):
        return f'{self.__class__.__name__}({self.id})'

    def get_label(self):
        return self.id

    def get_signal(self, signal):
        if isinstance(signal, str):
            return self.activations.get(signal, None)
        return self.activations.get(signal.key, None)

    def set_signal(self, signal):
        existing = self.activations.get(signal.key, None)
        if (not existing) or existing.strength < signal.strength:
            self.activations[signal.key] = signal

    def connect(self, other):
        edge = Edge.get_or_create(self, other)
        if edge not in self.edges_out:
            self.edges_out.append(edge)
        if edge not in other.edges_in:
            other.edges_in.append(edge)
        return edge

    def activate(self, signal):
        if signal.key not in self.activations or signal.strength > self.activations[signal.key].strength:
            self.activations[signal.key] = signal
            self.active = True
            if len(signal.parts) == 1:
                weakened_signal = signal.copy().weaken(self.loss / 2)
                if weakened_signal:
                    for out in self.edges_out:
                        out.end.activate(weakened_signal)
                for incoming in self.edges_in:
                    incoming.set_signal(signal)
            else:
                head = str(signal.parts[0])
                best_edges = []
                max_signal_strength = 0
                my_signal = self.activations.get(head, None)
                my_signal_strength = my_signal and my_signal.strength or 0
                if my_signal_strength > ctrl.g.max_route_strength:
                    ctrl.g.max_route_strength = my_signal_strength
                if my_signal_strength == 1.0:
                    #print('found it!')
                    self.active = True
                    ctrl.g.found = True
                    return

                for out in self.edges_out:
                    trail_signal = out.get_signal(head)
                    if trail_signal:
                        #print('outgoing edge signal strength:', trail_signal.strength)
                        #print('outgoing edge.end signal strength:', out.end.activations.get(head, None).strength)
                        if trail_signal.strength == max_signal_strength and trail_signal.strength > \
                                my_signal_strength:
                            best_edges.append(out)
                        elif trail_signal.strength > max_signal_strength and trail_signal.strength > my_signal_strength:
                            best_edges = [out]
                            max_signal_strength = trail_signal.strength
                if max_signal_strength and best_edges:
                    #print('--------------')
                    #print('signal strength here: ', my_signal_strength)
                    #print('activated route seeker signal ', signal, ' in node ', self, ' looking for ', repr(head))
                    #print('follow good lead: ', max_signal_strength, best_edges)
                    signal = signal.copy()
                    signal.strength = 1.0
                    signal.lost = False
                    #for out in best_edges:
                    #    print('good out: ', out, out.get_signal(head), out.end.get_signal(head))
                    for out in best_edges:
                        out.activate(signal)
                else:
                    #print('signal strength here: ', my_signal_strength, ' no good leads')
                    signal = signal.copy().weaken(0.5)
                    if signal:
                        signal.lost = True
                        for out in self.edges_out:
                            out.activate(signal)

        self.active = bool(self.activations)

    def deactivate(self):
        self.activations = {}
        self.active = False

    def reset(self):
        self.deactivate()

    def draw(self):
        c = Color(0.2, 0.8, 0.5, mode='hsv')
        y = self.y * SPACING
        x = self.x * SPACING
        ctrl.g.world_array[y][x] = [d * 255 for d in c.rgba]
        for signal in self.activations.values():
            if len(signal.parts) > 1:
                for signal_part in signal.parts:
                    c = Color(hue(signal_part), 0.8, signal.strength, mode='hsv')
                    ctrl.g.world_array[y][x] = [d * 255 for d in c.rgba]
                    y += 1
