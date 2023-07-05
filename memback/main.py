import time

import numpy as np
from kivy.app import App
from kivy.graphics.texture import Texture
from kivy.graphics import *
from kivy.uix.button import Button
from kivy.uix.widget import Widget
from kivy.core.window import Window
from memback.nodes import Node
from memback.ctrl import ctrl, NETWORK_WIDTH, NETWORK_HEIGHT, MAX_ITERATIONS, CYCLES
from kivy.uix.label import Label

WIDTH = 1600
HEIGHT = 1024

LAYERS = [20, 20, 20, 5]
IGNORE_CLOSE_NODE_CHANCE = 0.1
CREATE_LONG_DIST_CONNECTION_CHANCE = 0.1
CLOSE_CONNECTIONS_CAP = 6


data = [
    ("01010101010101010101", "00100"),
    ("11100011100011100011", "11100"),
    ("00000111100001111000", "00111"),
    ("11111111000000001111", "10000"),
    ("00000000000000000000", "00000"),
    ("11111111111111111111", "11111"),
    ("11111000000011111100", "00011"),
    ("01010101010101010110", "00101")
]

class Network(Widget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.layers = []
        self.word = None
        self.size_hint = None, None
        self.size = Window.size
        print(self.size)
        self.graph_origo = 20, self.size[1] - NETWORK_HEIGHT - 40
        print('origo: ', self.graph_origo)
        self.nodes = {}
        self.edges = {}
        self.words = {}
        self.cycle = 0
        self.cycle_error = 0
        self.total_cycles = 0
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
        self.debug = False

        self.ongoing_input_label = Label(text="")
        self.ongoing_input_label.x = WIDTH / 2
        self.ongoing_input_label.y = 50
        self.ongoing_input_label.color = [0.8, 0.8, 0.8]

        self.add_widget(self.next_button)
        self.add_widget(self.next_iter_button)
        self.add_widget(self.ongoing_input_label)
        self.input = ''
        self.input_index = -1
        self.next_button.on_press = self.next_input
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
        self.add_widget(self.ongoing_input_label)
        print('ongoing input label: ', self.ongoing_input_label.text)
        #self.canvas.flag_update()

    def handle_keyup(self, window, keycode):
        if keycode:
            if keycode[1] == 'right':
                self.next_input()
            elif keycode[1] == 'down':
                self.next_iteration(update=True)

    def update_input_label(self):
        self.ongoing_input_label.text = f'{self.input}: {self.expected_output} (cyc: {self.total_cycles}, iter: {self.iteration}, error: {self.total_error()})'

    def reset(self):
        for edge in list(self.edges.values()):
            edge.reset()
        for node in self.nodes.values():
            node.reset()
        self.world_array = np.zeros([NETWORK_HEIGHT, NETWORK_WIDTH, 4], dtype=np.uint8)

    def pick_next_input(self):
        self.input_index += 1
        if self.input_index == len(data):
            self.reset()
            self.input_index = 0
            print(f'== finished cycle {self.total_cycles}, avg error:  {self.cycle_error / (MAX_ITERATIONS * len(data))}')
            self.cycle_error = 0
            self.cycle += 1
            self.total_cycles += 1
        self.input, self.expected_output = data[self.input_index]
        self.update_input_label()
        for node in self.nodes.values():
            node.error = 0  # tätä ei saisi tehdä näin, noodi ei tiedä globaalista tilasta, mutta poistetaan näin virhelähde
        self.iteration = 0

    def next_input(self, update=True):
        while self.input:
            self.next_iteration(update=False)
        self.pick_next_input()
        self.next_iteration(update=False)
        #while self.input:
        #    self.next_iteration(update=False)
        if update:
            self.update_canvas()

    def next_iteration(self, update=True):
        if not self.input:
            self.pick_next_input()
        if self.debug:
            print(f'iteration {self.iteration} for input {self.input}')
        self.activate()
        self.iteration += 1
        if self.iteration == MAX_ITERATIONS:
            self.iteration = 0
            self.input = None

        if update:
            self.update_input_label()
            self.update_canvas()

    def total_error(self):
        return sum(abs(node.last_error) for node in self.layers[-1])

    def add_label(self, node):
        if not node.id:
            return
        node.label_item = Label(text=node.id)
        node.label_item.x = self.graph_origo[0] + node.x - 20
        node.label_item.y = self.graph_origo[1] + node.y - 10
        if node.active:
            node.label_item.color = [0.4, 1.0, 0.4]
        else:
            node.label_item.color = [0.4, 0.4, 0.4]
        self.add_widget(node.label_item)

    def draw_network(self):
        print('start creating nodes')
        t = time.time()
        layer_gap = int(WIDTH / (len(LAYERS) + 2))
        margin_x, margin_y = self.graph_origo
        x = layer_gap
        self.layers = []
        for l_index, layer_size in enumerate(LAYERS):
            cell_gap = int(HEIGHT / (layer_size + 2))
            y = cell_gap
            layer = []
            self.layers.append(layer)
            is_output = l_index == len(LAYERS) - 1
            for i in range(0, layer_size):
                node = Node(f'{l_index}_{i}')
                node.is_output = is_output
                node.i = i
                node.x = x
                node.y = y
                y += cell_gap
                self.nodes[node.id] = node
                layer.append(node)
            x += layer_gap
        print('done creating nodes ', time.time() - t)

        print('start creating connections')
        t = time.time()
        prev_layer = None
        for layer in self.layers:
            if prev_layer:
                for prev_node in prev_layer:
                    for node in layer:
                        edge = prev_node.connect(node)
                        self.edges[edge.id] = edge
            prev_layer = layer
        print('done creating connections ', time.time() - t)

    def build(self):
        self.draw_network()
        self.input_index = -1
        self.debug = False
        self.run_cycles(CYCLES)
        if not CYCLES:
            self.debug = True
        self.next_input()

    def run_cycles(self, count):
        self.cycle = 0
        while self.cycle < count:
            self.next_input(False)

    def clear_activations(self):
        for node in self.nodes.values():
            node.activations = {}
            node.active = False
        for edge in self.edges.values():
            edge.activations = {}

    def activate(self):
        #print('spreading, iteration ', self.iteration)
        if self.debug:
            print(f'### Forward phase i={self.iteration}, activate signals {self.input}, {self.input_index} ###')
        for i, (node, value) in enumerate(zip(self.layers[0], self.input)):
            node.receive([(i, float(value))])
        for node in self.nodes.values():
            node.activate()
            node.adjust_error()
        self.cycle_error += self.total_error()

class NetworkApp(App):
    def build(self):
        g = Network()
        ctrl.post_initialize(g)
        g.build()
        return g


if __name__ == '__main__':
    NetworkApp().run()
