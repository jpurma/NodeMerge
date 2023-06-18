from kivy.graphics import *

from semspace.signal import Signal
from util import hue
from edges import Edge
from ctrl import ctrl, NETWORK_WIDTH, NETWORK_HEIGHT, MARGIN_X, MARGIN_Y
import math

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
        self.activations = {}
        self.active = False
        self.label_item = None
        self.sem_word = ""
        self.loss = 0.03
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

    def get_signal(self, signal: str or Signal):
        if isinstance(signal, str):
            return self.activations.get(signal, None)
        return self.activations.get(signal.key, None)

    def get_signal_by_key(self, signal: str):
        return self.activations.get(signal, None)

    def get_similar_signal(self, signal: Signal):
        return self.activations.get(signal.key, None)

    def get_inbound_signal(self, signal: Signal):
        return self.activations.get(str(signal.parts[0]) + '<', None)

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

    def has_already_stronger_signal(self, signal, weakening):
        new_strength = signal.strength - weakening
        if new_strength <= 0:
            return True
        old_signal = self.get_similar_signal(signal)
        return old_signal and old_signal.strength > new_strength

    def replace_signal(self, signal, weakening=0):
        new_strength = signal.strength - weakening
        signal = Signal(signal.parts, new_strength, signal.key)
        self.activations[signal.key] = signal
        return signal

    def handle_outgoing_signal(self, outgoing_signal):
        inward_signal_key = str(outgoing_signal.parts[0]) + '<'
        max_incoming_strength = 0
        best_out = None
        if outgoing_signal.strength == 1.0:
            max_incoming_strength = 1.0
        else:
            for out in self.edges_out:
                inward_signal = out.end.get_signal_by_key(inward_signal_key)
                if inward_signal:
                    if inward_signal.strength - out.weakening > max_incoming_strength:
                        max_incoming_strength = inward_signal.strength - out.weakening
                        best_out = out
        if max_incoming_strength > 0:
            inward_signal = Signal(outgoing_signal.parts, max_incoming_strength, key=inward_signal_key)
            self.activations[inward_signal_key] = inward_signal
            if best_out:
                best_out.activations[inward_signal_key] = inward_signal.copy()

        for out in self.edges_out:
            out.activate(outgoing_signal)

    def find_promising_routes(self, target_key, local_signal_strength):
        best_edges = []
        max_signal_strength = 0
        for out in self.edges_out:
            trail_end_signal = out.end.get_signal(target_key)
            if trail_end_signal:
                # print('outgoing edge signal strength:', trail_signal.strength)
                # print('outgoing edge.end signal strength:', out.end.activations.get(head, None).strength)
                trail_strength = trail_end_signal.strength
                if trail_strength > local_signal_strength:
                    if trail_strength == max_signal_strength:
                        best_edges.append(out)
                        print('two best edges: ', best_edges)
                    elif trail_strength > max_signal_strength:
                        best_edges = [out]
                        max_signal_strength = trail_strength
                        # print(f'best edge for {self} ({target_signal_strength}): ', out.end, trail_strength)
        return best_edges

    def handle_seeker_signal(self, signal):
        target, src = signal.parts
        target_key = str(target) + '<'
        # print(f'attr/src {src} seeking {target}')
        target_signal = self.get_signal_by_key(target_key)
        local_signal_strength = target_signal and target_signal.strength or 0
        if local_signal_strength == 1.0:
            print('found it!')
            self.active = True
            ctrl.g.found[signal.key] = True
            return

        promising_routes = self.find_promising_routes(target_key, local_signal_strength)
        if promising_routes:
            # print('--------------')
            # print('signal strength here: ', my_signal_strength)
            # print('activated route seeker signal ', signal, ' in node ', self, ' looking for ', repr(head))

            for out in promising_routes:
                # print('activate promising route to target ', out.end, signal)
                trail_end_signal = out.end.get_signal(target_key)
                if trail_end_signal.strength - out.weakening > local_signal_strength:
                    local_signal = trail_end_signal.copy()
                    local_signal.strength = trail_end_signal.strength - out.weakening
                    self.activations[local_signal.key] = local_signal
                    # print(f'extending good route {out} with {local_signal}, seeker signal {signal.strength}')
                out.activate(signal, out.loss)
        else:
            # print('signal strength here: ', my_signal_strength, ' no good leads')
            for out in self.edges_out:
                out.activate(signal, 0.2)
        return promising_routes

    def activate(self, signal, weakening=0, primary=False, origin=False):
        if not signal:
            return
        if self.has_already_stronger_signal(signal, weakening):
            return
        signal = self.replace_signal(signal, weakening)

        if not primary:
            self.active = PRIMED
            ctrl.primed[signal.key].add(self)
            return
        self.active = ACTIVE
        if signal.is_outgoing():
            self.handle_outgoing_signal(signal)
            return True
        else:
            promising_routes = self.handle_seeker_signal(signal)
            #if promising_routes:
            #    print(f'{signal.strength}, got promising route: ', promising_routes)
            if origin:
                print('at origin, promising routes: ', promising_routes)
            return promising_routes

    def deactivate(self):
        self.activations = {}
        self.active = False

    def reset(self):
        self.deactivate()

    def draw(self):
        if not self.active:
            return
        c = Color(0.2, 0.8, 0.5, mode='hsv')
        y = self.y
        x = self.x
        ctrl.g.world_array[y][x] = [d * 255 for d in c.rgba]

        for signal in self.activations.values():
            if signal.is_outgoing() and False:
                for signal_part in signal.parts:
                    c = Color(hue(signal_part), 1.0, signal.strength * 2, mode='hsv')
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
                sx = self.x + MARGIN_X
                sy = self.y + MARGIN_Y
                Color(1.0, 1.0, 1.0 if self.active == PRIMED else 0.2, mode='hsv')
                Point(points=[sx, sy], pointsize=4)

    def set_color_from_signal(self, signal):
        self.color = Color(hue(signal), 0.8, 1.0, mode='hsv').rgba