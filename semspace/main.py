import numpy as np
from kivy.app import App
from kivy.graphics.texture import Texture
from kivy.graphics import *
from kivy.uix.button import Button
from kivy.uix.widget import Widget
from kivy.core.window import Window
from nodes import Node
from ctrl import ctrl, SPACING
from signal import Signal
from kivy.uix.label import Label

WIDTH = 1600
HEIGHT = 1024

NETWORK_HEIGHT = 20
NETWORK_WIDTH = 20
SCALING = 4
WORLD_PIXEL_SIZE = [d * SPACING for d in (NETWORK_WIDTH, NETWORK_HEIGHT)]
WORLD_GRAPHICS_SIZE = [d * SCALING for d in WORLD_PIXEL_SIZE]

sem_items = [
    ('Pekka', int(0.1 * NETWORK_WIDTH), int(0.1 * NETWORK_HEIGHT)),
    ('sanoi', int(0.9 * NETWORK_WIDTH), int(0.2 * NETWORK_HEIGHT)),
    ('että', int(0.7 * NETWORK_WIDTH), int(0.7 * NETWORK_HEIGHT)),
    ('ihailee', int(0.9 * NETWORK_WIDTH), int(0.4 * NETWORK_HEIGHT)),
    ('Merjaa', int(0.1 * NETWORK_WIDTH), int(0.2 * NETWORK_HEIGHT))
]


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
        self.size_hint = None, None
        self.size = Window.size
        self.graph_origo = 20, self.size[1] - 20 - WORLD_GRAPHICS_SIZE[1]
        self.nodes = {}
        self.edges = {}
        self.words = {}
        self.texture = Texture.create(size=WORLD_PIXEL_SIZE, colorfmt='rgba', bufferfmt='ubyte')
        self.texture.min_filter = 'nearest'
        self.texture.mag_filter = 'nearest'
        self.world_array = np.zeros(WORLD_PIXEL_SIZE + [4], dtype=np.uint8)

        self.next_button = Button(text='Next step', font_size=14)
        self.next_button.x = 10
        self.next_button.y = 10
        self.ongoing_sentence_label = Label(text="")
        self.ongoing_sentence_label.x = WIDTH / 2
        self.ongoing_sentence_label.y = 100
        self.found = False
        self.max_route_strength = 0
        self.add_widget(self.next_button)
        self.ongoing_sentence = ''
        self.word_index = -1
        self.next_button.on_press = self.next_word

    def update_canvas(self, *args):
        self.canvas.clear()
        self.clear_widgets()
        with self.canvas:
            Rectangle(pos=self.graph_origo, size=WORLD_GRAPHICS_SIZE,
                      texture=self.texture)

        for node in self.nodes.values():
            node.draw()
        #for edge in self.edges.values():
        #    edge.draw()
        for node in self.nodes.values():
            self.add_label(node)
        self.texture.blit_buffer(self.world_array.tobytes(), colorfmt='rgba', bufferfmt='ubyte')
        self.add_widget(self.next_button)
        #self.canvas.flag_update()

    def update_sentence(self):
        self.ongoing_sentence = ' '.join(sentence[:self.word_index])
        self.ongoing_sentence_label.text = self.ongoing_sentence

    def reset(self):
        for edge in list(self.edges.values()):
            edge.reset()
        for node in self.nodes.values():
            node.reset()
        self.world_array = np.zeros(WORLD_PIXEL_SIZE + [4], dtype=np.uint8)

    def next_word(self):
        self.word_index += 1
        if self.word_index == len(sentence):
            self.reset()
            self.word_index = 0
        self.update_sentence()
        #self.clear_activations()
        self.activate(self.word_index, sentence[self.word_index])
        for head, arg in connections[self.word_index]:
            self.activate((sentence.index(head), sentence.index(arg)), arg)
        self.update_canvas()

    def add_label(self, node):
        if not node.sem_word:
            return
        node.label_item = Label(text=node.sem_word)
        node.label_item.x = self.graph_origo[0] + node.x * SCALING * SPACING - 20
        node.label_item.y = self.graph_origo[1] + node.y * SCALING * SPACING - 10
        if node.active:
            node.label_item.color = [1.0, 1.0, 0.4]
        else:
            node.label_item.color = [0.7, 0.7, 0.7]
        self.add_widget(node.label_item)

    def draw_network(self):
        for y in range(NETWORK_HEIGHT):
            for x in range(NETWORK_WIDTH):
                node = Node(f'{x}_{y}')
                node.x = x
                node.y = y
                self.nodes[node.id] = node
        for y in range(NETWORK_HEIGHT):
            go_left = y % 2
            for x in range(NETWORK_WIDTH):
                go_up = x % 2
                node = self.nodes[f'{x}_{y}']
                if go_left:
                    if x:
                        edge = node.connect(self.nodes[f'{x-1}_{y}'])
                        edge.hue = 0
                    #if x < NETWORK_WIDTH - 1:
                    #    edge = node.connect(self.nodes[f'{x + 1}_{y}'])
                    #    edge.hue = 0.5
                else:
                    if x < NETWORK_WIDTH - 1:
                        edge = node.connect(self.nodes[f'{x+1}_{y}'])
                        edge.hue = 0.5
                if go_up:
                    if y:
                        edge = node.connect(self.nodes[f'{x}_{y-1}'])
                        edge.hue = 0.25
                    if y < NETWORK_HEIGHT - 1 and x < NETWORK_WIDTH - 1:
                        edge = node.connect(self.nodes[f'{x + 1}_{y + 1}'])
                        edge.hue = 0.75
                else:
                    if y < NETWORK_HEIGHT - 1:
                        edge = node.connect(self.nodes[f'{x}_{y+1}'])
                        edge.hue = 0.75
                    if y and x:
                        edge = node.connect(self.nodes[f'{x - 1}_{y - 1}'])
                        edge.hue = 0.75

        for word, x, y in sem_items:
            node = self.nodes[f'{x}_{y}']
            node.sem_word = word
            self.words[word] = node

        self.update_canvas()

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
        if not isinstance(signal, tuple):
            signal = (signal,)
        signal = Signal(tuple(signal), 1.0)
        self.found = False
        self.max_route_strength = 0
        self.words[signal_host_name].activate(signal)
        if len(signal.parts) > 1:
            print(f'*** activated route seeker {signal}, {signal_host_name}, {[sentence[s] for s in signal.parts]}')
            print('found it: ', self.found, self.max_route_strength)
        else:
            print(f'*** activated {signal}, {signal_host_name}')
        self.update_canvas()


class NetworkApp(App):
    def build(self):
        g = Network()
        ctrl.post_initialize(g)
        g.build()
        return g


if __name__ == '__main__':
    NetworkApp().run()
