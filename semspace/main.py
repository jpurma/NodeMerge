import math
import random
import time
from collections import defaultdict

import numpy as np
from kivy.app import App
from kivy.graphics.texture import Texture
from kivy.graphics import *
from kivy.uix.button import Button
from kivy.uix.widget import Widget
from kivy.core.window import Window
from nodes import Node
from ctrl import ctrl, NETWORK_WIDTH, NETWORK_HEIGHT
from semspace.signal import Signal
from kivy.uix.label import Label

WIDTH = 1600
HEIGHT = 1024

NODE_COUNT = 800
IGNORE_CLOSE_NODE_CHANCE = 0.1
CREATE_LONG_DIST_CONNECTION_CHANCE = 0.1
CLOSE_CONNECTIONS_CAP = 6

MAX_ITERATIONS = 30

connections = [
    [],
    [('sanoi', 'Pekka')],
    [('sanoi', 'että')],
    [('että', 'ihailee'), ('ihailee', 'Pekka')],
    [('ihailee', 'Merjaa')]
]

sentence = 'Pekka sanoi että ihailee Merjaa'.split()


class Network(Widget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.word = None
        self.size_hint = None, None
        self.size = Window.size
        print(self.size)
        self.graph_origo = 20, self.size[1] - NETWORK_HEIGHT - 40
        print('origo: ', self.graph_origo)
        self.nodes = {}
        self.edges = {}
        self.words = {}
        self.outgoing_phase = True
        self.found_route = defaultdict(bool)
        self.texture = Texture.create(size=[NETWORK_WIDTH, NETWORK_HEIGHT], colorfmt='rgba', bufferfmt='ubyte')
        self.texture.min_filter = 'nearest'
        self.texture.mag_filter = 'nearest'
        self.world_array = np.zeros([NETWORK_HEIGHT, NETWORK_WIDTH, 4], dtype=np.uint8)

        self.next_button = Button(text='Next step', font_size=14)
        self.next_button.x = 10
        self.next_button.y = 10

        self.next_iter_button = Button(text='Next iteration', font_size=14)
        self.next_iter_button.x = 110
        self.next_iter_button.y = 10
        self.iteration = 0

        self.ongoing_sentence_label = Label(text="")
        self.ongoing_sentence_label.x = WIDTH / 2
        self.ongoing_sentence_label.y = 100
        self.found = defaultdict(bool)
        self.max_route_strength = 0
        self.add_widget(self.next_button)
        self.add_widget(self.next_iter_button)
        self.ongoing_sentence = ''
        self.word_index = -1
        self.next_button.on_press = self.next_word
        self.next_iter_button.on_press = self.next_iteration
        keyboard = Window.request_keyboard(self.handle_keyup, self)
        keyboard.bind(on_key_up=self.handle_keyup)

    def update_canvas(self, *args):
        self.canvas.clear()
        self.clear_widgets()
        with self.canvas:
            Rectangle(pos=self.graph_origo, size=(NETWORK_WIDTH, NETWORK_HEIGHT),
                      texture=self.texture)

        for node in self.nodes.values():
            node.draw()
        for edge in self.edges.values():
            edge.draw()
        for node in self.nodes.values():
            self.add_label(node)
        self.texture.blit_buffer(self.world_array.tobytes(), colorfmt='rgba', bufferfmt='ubyte')
        self.add_widget(self.next_button)
        self.add_widget(self.next_iter_button)
        #self.canvas.flag_update()

    def handle_keyup(self, window, keycode):
        if keycode:
            if keycode[1] == 'right':
                self.next_word()
            elif keycode[1] == 'down':
                self.next_iteration(update=True)

    def update_sentence(self):
        self.ongoing_sentence = ' '.join(sentence[:self.word_index])
        self.ongoing_sentence_label.text = self.ongoing_sentence

    def reset(self):
        for edge in list(self.edges.values()):
            edge.reset()
        for node in self.nodes.values():
            node.reset()
        self.world_array = np.zeros([NETWORK_HEIGHT, NETWORK_WIDTH, 4], dtype=np.uint8)

    def pick_next_word(self):
        self.word_index += 1
        if self.word_index == len(sentence):
            self.reset()
            self.word_index = 0
        self.word = sentence[self.word_index]
        self.iteration = 0
        self.found.clear()
        self.found_route.clear()
        self.outgoing_phase = True

    def next_word(self):
        while self.word:
            self.next_iteration(update=False)
        self.pick_next_word()
        while self.word:
            self.next_iteration(update=False)
        self.update_sentence()
        self.update_canvas()

    def next_iteration(self, update=True):
        if not self.word:
            self.pick_next_word()
        if self.outgoing_phase:
            outgoing_signal = Signal([self.word_index], 1.0, outgoing=True)
            self.activate(outgoing_signal, sentence[self.word_index])
        else:
            for head, arg in connections[self.word_index]:
                seeker_signal = Signal([sentence.index(head), sentence.index(arg)], 1.0)
                self.activate(seeker_signal, arg)
        self.iteration += 1
        if (self.found and all(self.found.values())) or (not any(ctrl.primed.values())) or self.iteration == MAX_ITERATIONS:
            #print(self.found, self.iteration)
            ctrl.primed.clear()
            self.iteration = 0
            if self.outgoing_phase:
                self.outgoing_phase = False
            else:
                self.word = None

        if update:
            self.update_canvas()

    def add_label(self, node):
        if not node.sem_word:
            return
        node.label_item = Label(text=node.sem_word)
        node.label_item.x = self.graph_origo[0] + node.x - 20
        node.label_item.y = self.graph_origo[1] + node.y - 10
        if node.active:
            node.label_item.color = node.color
        else:
            node.label_item.color = [0.7, 0.7, 0.7]
        self.add_widget(node.label_item)

    def draw_network(self):
        def maybe():
            return random.random() < 0.9

        used_coords = set()
        i = 0
        print('start creating nodes')
        t = time.time()
        while i < NODE_COUNT:
            pos = (random.randint(0, NETWORK_WIDTH - 1), random.randint(0, NETWORK_HEIGHT - 1))
            while pos in used_coords:
                pos = (random.randint(0, NETWORK_WIDTH - 1), random.randint(0, NETWORK_HEIGHT - 1))
            used_coords.add(pos)
            x, y = pos
            node = Node(f'{x}_{y}')
            node.x = x
            node.y = y
            self.nodes[node.id] = node
            i += 1
        print('done creating nodes ', time.time() - t)

        print('start creating connections')
        t = time.time()

        for node in self.nodes.values():
            dists = []
            for other_node in self.nodes.values():
                if node is other_node:
                    continue
                dists.append((math.dist((node.x, node.y), (other_node.x, other_node.y)), other_node))
            dists.sort()
            close_nodes = []
            for d, other_node in dists[:CLOSE_CONNECTIONS_CAP]:
                if random.random() > IGNORE_CLOSE_NODE_CHANCE:
                    edge = node.connect(other_node)
                    close_nodes.append(other_node)
                    self.edges[edge.id] = edge
            if random.random() < CREATE_LONG_DIST_CONNECTION_CHANCE:
                ld_node = random.choice(list(self.nodes.values()))
                if ld_node not in close_nodes and ld_node is not node:
                    edge = node.connect(ld_node)
                    self.edges[edge.id] = edge
        print('done creating connections ', time.time() - t)

        word_nodes = random.choices(list(self.nodes.values()), k=len(sentence))
        for signal, word in enumerate(sentence):
            node = word_nodes[signal]
            node.sem_word = word
            node.set_color_from_signal(signal)
            self.words[word] = node

    def build(self):
        self.draw_network()
        self.word_index = -1
        self.next_word()

    def clear_activations(self):
        for node in self.nodes.values():
            node.activations = {}
            node.active = False
        for edge in self.edges.values():
            edge.activations = {}

    def activate(self, signal, signal_host_name):
        if self.outgoing_phase:
            #print('spreading, iteration ', self.iteration)
            if self.iteration == 0:
                print(f'### Phase one, activate outgoing spreader {self.word}, {self.word_index} ###')
                self.words[signal_host_name].activate(signal, primary=True, origin=True)
            elif ctrl.primed[signal.key]:
                print(f'spreading outgoing signal, {len(ctrl.primed[signal.key])} primed cells')
                old_primed = set(ctrl.primed[signal.key])
                ctrl.primed[signal.key].clear()
                for node in old_primed:
                    node.activate(node.get_similar_signal(signal), primary=True)
        else:
            #print('seeking, iteration ', self.iteration, ctrl.primed)
            if self.iteration == 0:
                ctrl.g.found[signal.key] = False
                head, arg = signal.parts
                print(f'### Phase two, activate seeker {sentence[arg]} with known target {sentence[head]} ###')
                self.found_route[signal.key] = self.words[signal_host_name].activate(signal, primary=True, origin=True)
            elif ctrl.primed[signal.key]:
                if not self.found_route[signal.key]:
                    print('reactivating seeker cell')
                    self.found_route[signal.key] = self.words[signal_host_name].activate(signal, primary=True, origin=True)
                old_primed = set(ctrl.primed[signal.key])
                ctrl.primed[signal.key].clear()
                for node in old_primed:
                    node.activate(node.get_similar_signal(signal), primary=True)
            else:
                self.found[signal.key] = True


class NetworkApp(App):
    def build(self):
        g = Network()
        ctrl.post_initialize(g)
        g.build()
        return g


if __name__ == '__main__':
    NetworkApp().run()
