from io import StringIO

from kivy.app import App
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.graphics import *
import math

test_lexicon = """
sopimus :: N:nom3sg adjL:D|a =T:a-inf
ihailla :: T:a-inf, v =N:prt =N:lla
sitä :: N:prt a:D|n
Merjaa :: N:prt adjL:D <N:gen a:n
jonka :: adjL:n =T, N:acc
Pekka :: N:nom3sg n a:n
näki :: T:pst =N:nom3sg, =N:prt|acc
peruuntui :: =N:nom3sg T:pst
# ei :: =v =nom3sg adjL:advNeg
# enää :: a:advNeg
# rakasta :: v =prt
# rakastaa :: =nom3sg =prt
"""

# sentence = "Pekka ei enää rakasta Merjaa"
sentence = "sopimus ihailla sitä Merjaa jonka Pekka näki peruuntui"

N_SIZE = 2
WIDTH = 1600
HEIGHT = 1024


def hue(signal):
    h = 0.7 * signal
    return h - math.floor(h)


class Edge:
    def __init__(self, start, end):
        self.id = f'{start.id}_{end.id}'
        g.edges[self.id] = self
        self.activations = []
        self.start = start
        self.end = end

    def __repr__(self):
        return f'{self.__class__.__name__}({self.id})'

    def draw(self):
        cx = self.start.x + (self.end.x - self.start.x) * .9
        cy = self.start.y + (self.end.y - self.start.y) * .9
        with g.canvas:
            Color(*self.color)
            Line(points=[self.start.x, self.start.y, self.end.x, self.end.y], width=1)
            Line(circle=[cx, cy, 3], width=2)
            x_diff = 0
            y_diff = 0
            for activation in self.activations:
                x_diff += 2
                y_diff += 2
                Color(hue(activation), 0.8, 0.5, mode='hsv')
                Line(points=[self.start.x + x_diff, self.start.y + y_diff, self.end.x + x_diff, self.end.y + y_diff], width=2)
                Line(circle=[cx, cy, 3], width=2)

    def activate(self, n):
        if n not in self.activations:
            self.activations.append(n)
            self.end.activate(n)

    @property
    def color(self):
        return self.start.color

    @staticmethod
    def get(start, end):
        return g.edges.get(f'{start.id}_{end.id}')

    @staticmethod
    def get_or_create(start, end):
        return Edge.get(start, end) or __class__(start, end)


class MergeEdge:
    def __init__(self, start, end):
        print('** creating merge edge ', start.id, end.id)
        self.id = MergeEdge.create_id(start, end)
        g.edges[self.id] = self
        self.active = True
        self.start = start
        self.end = end
        self.signal = self.head.activations[0]

    @property
    def arg(self):
        return self.start

    @property
    def head(self):
        return self.end

    def draw(self):
        cx = self.start.x + (self.end.x - self.start.x) * .8
        cy = self.start.y + abs(self.end.x - self.start.x) * .3
        with g.canvas:
            Color(hue(self.signal), .5, .6, mode='hsv')
            Bezier(points=[self.start.x, self.start.y, cx, cy, self.end.x, self.end.y], width=3)

    @staticmethod
    def create_id(start, end):
        return f'D{start.id}_{end.id}'


class AdjunctEdge:
    color = [0.8, 0.2, 0.2]

    def __init__(self, start, end):
        print('** creating adjunct edge ', start.id, end.id)
        self.id = f'{start.id}_{end.id}'
        g.edges[self.id] = self
        self.active = True
        self.start = start
        self.end = end
        self.signal = self.start.activations[0]

    def draw(self):
        with g.canvas:
            Color(hue(self.signal), .5, .6, mode='hsv')
            Line(points=[self.start.x, self.start.y, self.end.x, self.end.y], width=1)

    def activate(self, n):
        self.start.activate(n)
        self.end.activate(n)


class Node:
    color = [64, 64, 64, 128]

    def __init__(self, id):
        self.id = id
        g.nodes[id] = self
        self.edges_out = []
        self.edges_in = []
        self.x = 0
        self.y = 0
        self.activations = []
        self.active = False
        self.label_item = None

    def __repr__(self):
        return f'{self.__class__.__name__}({self.id})'

    def get_label(self):
        return self.id

    def connect(self, other):
        edge = Edge.get_or_create(self, other)
        if edge not in self.edges_out:
            self.edges_out.append(edge)
        if edge not in other.edges_in:
            other.edges_in.append(edge)

    def activate(self, n):
        if n not in self.activations:
            self.activations.append(n)
            self.active = True
            for out in self.edges_out:
                out.activate(n)
        self.active = bool(self.activations)

    def deactivate(self):
        self.activations = []
        self.active = False

    def add_label(self):
        self.label_item = Label(text=self.id)
        self.label_item.x = self.x - 20
        self.label_item.y = self.y - 10
        self.label_item.color = [1.0, 1.0, 0.4] if self.active else [0.7, 0.7, 0.7]
        g.add_widget(self.label_item)

    def set_pos(self, x, y):
        self.x = x
        self.y = y
        if self.label_item:
            self.label_item.x = x
            self.label_item.y = y

    def draw(self):
        with g.canvas:
            Color(*self.color)
            r = 16
            Line(circle=[self.x, self.y, r], width=1)
            for activation in self.activations:
                r += 2
                Color(hue(activation), 0.8, 0.5, mode='hsv')
                Line(circle=[self.x, self.y, r], width=2)

    @staticmethod
    def find_edge(edges, start=None, end=None):
        if start and end:
            for edge in edges:
                if edge.start is start and edge.end is end:
                    return edge
        elif start:
            for edge in edges:
                if edge.start is start:
                    return edge
        elif end:
            for edge in edges:
                if edge.end is end:
                    return edge


class LexicalNode(Node):
    color = [0.8, 0.8, 0.8, 0.5]

    def __init__(self, word, cats, feats, lex_parts):
        super().__init__(word)
        self.word = word
        self.categories = cats
        self.feats = feats
        self.selected_color = [0, 0.8, 0]
        self.arg_edges = []
        self.head_edges = []
        self.adjunctions = []
        self.lex_parts = lex_parts
        for f_node in feats:
            self.connect(f_node)
        for c_node in cats:
            self.connect(c_node)
            c_node.connect(self)

    def activate(self, n):
        if n not in self.activations:
            self.activations.append(n)
            if self.activations:
                for out in self.edges_out:
                    out.activate(n)
            for edge in self.adjunctions:
                edge.activate(n)
        self.active = bool(self.activations)

    def remove_merge(self, arg):
        if found_edge := self.find_edge(self.arg_edges, start=arg):
            print('** removing edge ', arg.id, self.id, found_edge.id)
            del g.edges[found_edge.id]
            self.arg_edges.remove(found_edge)
            arg.head_edges.remove(found_edge)

    def add_adjunction(self, other):
        if self.find_edge(self.adjunctions, start=other) or self.find_edge(self.adjunctions, end=other):
            return
        edge = AdjunctEdge(self, other)
        self.adjunctions.append(edge)
        other.adjunctions.append(edge)

    def add_merge(self, arg):
        if self.find_edge(self.arg_edges, start=arg):
            return
        edge = MergeEdge(arg, self)
        self.arg_edges.append(edge)
        arg.head_edges.append(edge)


class FeatureNode(Node):
    def __init__(self, fstring):
        super().__init__(fstring)
        self.sign = ''
        self.name = ''
        self.values = []

    def values_match(self, other):
        for f in self.values:
            if f in other.values:
                return f


class PosFeatureNode(FeatureNode):
    color = [0, 1.0, 0, 0.5]

    def __init__(self, fstring):
        super().__init__(fstring)
        self.sign = ""
        if ':' in fstring:
            self.name, value_string = fstring.split(':', 1)
            self.values = value_string.split('|')
        else:
            self.name = fstring
            self.values = []
        assert fstring not in g.features
        self.adjunct_licensor = self.name == 'adjL'
        g.features[fstring] = self

    def connect_adjuncts(self):
        for feat in g.features.values():
            if feat.name == 'a' and feat.values_match(self):
                print('connect adj feats ', self, '+', feat)
                feat.connect(self)

    def activate(self, n):
        if (self.adjunct_licensor and n not in self.activations) or (not self.adjunct_licensor and not self.activations):
            self.activations.append(n)
            for out in self.edges_out:
                out.activate(n)
            self.active = True
        if not self.activations:
            self.active = False


class NegFeatureNode(Node):
    color = [1.0, 0, 0, 0.5]
    signs = '-=<>'

    def __init__(self, fstring):
        super().__init__(fstring)
        self.sign = fstring[0]
        name_string = fstring[1:]
        if ':' in name_string:
            self.name, value_string = name_string.split(':', 1)
            self.values = value_string.split('|')
        else:
            self.name = name_string
            self.values = []
        assert fstring not in g.features
        g.features[fstring] = self

    def connect_positive(self):
        for feat in g.features.values():
            if feat.name == self.name and not feat.sign and feat is not self and ((not self.values) or feat.values_match(self)):
               print('connect feats ', self, '+', feat)
               feat.connect(self)

    def _find_incoming_lexical_activation_signals(self):
        for e in self.edges_in:
            if isinstance(e.start, (LexicalNode, CategoryNode)) and e.activations:
                return e.activations[0]
        return 0

    def activate(self, n):
        if n not in self.activations:
            self.activations.append(n)
            lex_activations = []
            feat_activations = []
            for e in self.edges_in:
                # use activation from active lexical item, not that of supporting feature
                if isinstance(e.start, (LexicalNode, CategoryNode)) and e.activations:
                    i = e.activations[0]
                    lex_activations.append(i)
                elif e.activations:
                    feat_activations.append(e.activations[0])
            if lex_activations and feat_activations:
                for out in self.edges_out:
                    out.activate(i)
                self.active = True
            else:
                self.active = False
        if not self.activations:
            self.active = False


class CategoryNode(Node):
    color = [0.5, 0.75, 0.75, 0.5]

    def __init__(self, category):
        super().__init__(category)
        self.category = category
        g.categories.append(self)

    def activate(self, n):
        if n not in self.activations:
            self.activations.append(n)
        self.active = bool(self.activations)


class NumerationNode(Node):
    color = [0, 0, 1.0, 0.5]

    def __init__(self, label):
        super().__init__(label)
        g.numeration.append(self)

    def activate(self, n):
        if n not in self.activations:
            self.activations.append(n)
            if len(self.activations) > 1:
                print(f'at {self.id} adding merge ', self.activations)
                g.add_merge(self.activations[0], self.activations[1])
        self.active = len(self.activations) > 1


class LeftMergeNode(Node):
    color = [1.0, 1.0, 0, .5]

    def activate(self, n):
        if n not in self.activations:
            self.activations.append(n)
            for out in self.edges_out:
                out.activate(n)
        self.active = bool(self.activations)


class RightMergeNode(Node):
    color = [1.0, 1.0, 0, .5]

    def activate(self, n):
        if n not in self.activations:
            self.activations.append(n)
            for out in self.edges_out:
                out.activate(n)
        self.active = bool(self.activations)


class PairMergeNode(Node):
    def activate(self, n):
        if n not in self.activations:
            self.activations.append(n)
            if len(self.activations) > 1 and not g.ugly_adjunct_block:
                for out in self.edges_out:
                    for n in self.activations:
                        print('activation on edge ', out, out.start, out.end, n)
                        out.activate(n)
        self.active = len(self.activations) > 1


class MergeOkNode(Node):
    def activate(self, n):
        if n not in self.activations:
            self.activations.append(n)
        self.active = bool(self.activations)


class WordPartList:
    def __init__(self, words, lexicon):
        self.original = words
        self.words_left = list(reversed(words))
        self.lexicon = lexicon
        self.word_parts = []
        self.current_item = None
        self.prev_item = None
        self.current_i = 0
        self.prev_i = 0

    def reset(self):
        self.words_left = list(reversed(self.original))
        self.prev_i = 0
        self.prev_item = None
        self.current_i = 0
        self.current_item = None
        self.word_parts = []

    def pick_first(self):
        self.current_item = self.lexicon[self.words_left.pop()]
        self.word_parts.append(self.current_item)
        return self.current_item

    def pick_next(self):
        li = self.current_item
        if not li:
            return
        i = li.lex_parts.index(li)
        self.prev_item = self.current_item
        self.prev_i = self.current_i
        if i < len(li.lex_parts) - 1:
            self.current_item = li.lex_parts[i + 1]
            self.word_parts.append(self.current_item)
            self.current_i = len(self.word_parts) - 1
        elif self.words_left:
            self.current_item = self.lexicon[self.words_left.pop()]
            self.word_parts.append(self.current_item)
            self.current_i = len(self.word_parts) - 1
        else:
            self.current_item = None
        return self.current_item

    def can_merge(self):
        return self.prev_item and self.current_item

    def same_word(self, lex_item, other):
        return lex_item and other and lex_item.lex_parts is other.lex_parts

    def traverse_to_previous_free_item(self):
        self.prev_i -= 1
        if self.prev_i >= 0:
            p = self.word_parts[self.prev_i]
            # if previous word is in a group of adjuncts, walk to first of them, but collect heads on the way in order
            # to decide if the group already belongs to a head
            heads = list(p.head_edges)
            while [e for e in p.adjunctions if e.end is p]:
                self.prev_i -= 1
                p = self.word_parts[self.prev_i]
                heads += list(p.head_edges)
            self.prev_item = p
            if heads:
                self.traverse_to_previous_free_item()
        else:
            self.prev_item = None


class Network(Widget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.nodes = {}
        self.edges = {}
        self.lexicon = {}
        self.features = {}
        self.numeration = []
        self.categories = []
        self.merge_right = None
        self.merge_left = None
        self.merge_pair = None
        self.merge_ok = None
        self.words = None
        self.next_button = Button(text='Next', font_size=14)
        self.next_button.x = 20
        self.next_button.y = 20
        self.ugly_adjunct_block = False
        self.add_widget(self.next_button)
        self.next_button.on_press = self.next_pair

    def update_canvas(self, *args):
        self.canvas.clear()
        self.clear_widgets()
        for node in self.nodes.values():
            node.draw()
        for edge in self.edges.values():
            edge.draw()
        for node in self.nodes.values():
            node.add_label()
        self.add_widget(self.next_button)

    def read_lexicon(self, lexicon_file, append=False):
        if not append:
            self.lexicon.clear()
        for line in lexicon_file:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            word, feats = line.split('::', 1)
            word = word.strip()
            word_parts = feats.split(',')
            first = True
            lex_parts = []
            for feats in word_parts:
                if not first:
                    word = f'({word})'
                cats = []
                neg_feats = []
                pos_feats = []
                for feat in feats.strip().split():
                    if feat.startswith('cat:'):
                        cats.append(self.add(CategoryNode, feat))
                    elif feat[0] in NegFeatureNode.signs:
                        neg_feats.append(self.add(NegFeatureNode, feat))
                    else:
                        pos_feats.append(self.add(PosFeatureNode, feat))
                lex_node = self.add(LexicalNode, word, cats, neg_feats + pos_feats, lex_parts)
                lex_parts.append(lex_node)
                self.lexicon[word] = lex_node
                first = False

    def add_merge(self, arg_signal, head_signal):
        arg = None
        head = None
        for lex_item in self.lexicon.values():
            if arg_signal in lex_item.activations:
                arg = lex_item
                if arg and head:
                    break
            if head_signal in lex_item.activations:
                head = lex_item
                if arg and head:
                    break
        if not (arg and head):
            print('cannot find arg and head: ', arg_signal, arg, head_signal, head)
            return
        if head.find_edge(head.head_edges, end=arg):
            arg.remove_merge(head)
            head.add_adjunction(arg)
        else:
            head.add_merge(arg)

    def reset(self):
        self.words.reset()
        for edge in list(self.edges.values()):
            if isinstance(edge, (MergeEdge, AdjunctEdge)):
                del self.edges[edge.id]
        for node in self.nodes.values():
            if isinstance(node, LexicalNode):
                node.head_edges.clear()
                node.arg_edges.clear()
                node.adjunctions.clear()

    def next_pair(self):
        if not self.words:
            return
        self.ugly_adjunct_block = False
        if self.words.can_merge() and not self.merge_ok.active:
            self.ugly_adjunct_block = True
            self.words.traverse_to_previous_free_item()
        else:
            if not self.words.pick_next():
                self.reset()
                self.words.pick_first()
        self.clear_activations()
        if self.words.can_merge():
            self.activate()
        self.update_canvas()

    def add(self, node_class, label, *args, **kwargs):
        if label in self.nodes:
            return self.nodes[label]
        node = node_class(label, *args, **kwargs)
        self.nodes[label] = node
        return node

    def parse(self, sentence):
        self.words = WordPartList(sentence.split(), self.lexicon)
        self.words.pick_first()

    def build(self):
        row = 1
        row_height = HEIGHT / 5
        self.merge_right = self.add(RightMergeNode, 'M(A->B)')  # A→B
        self.merge_right.set_pos(WIDTH / 2 - 256, row * row_height)
        self.merge_left = self.add(LeftMergeNode, 'M(A<-B)')  # A←B
        self.merge_left.set_pos(WIDTH / 2, row * row_height)
        self.merge_pair = self.add(PairMergeNode, 'M(A<->B)')
        self.merge_pair.set_pos(WIDTH / 2 + 256, row * row_height)
        self.merge_ok = self.add(MergeOkNode, 'OK')
        self.merge_ok.set_pos(100, HEIGHT / 2)
        row += 1
        for num in range(N_SIZE):
            x = WIDTH / (N_SIZE + 1) * (num + 1)
            y = row * row_height
            num_node = self.add(NumerationNode, f'N{num + 1}')
            num_node.set_pos(x, y)
        lexicon_file = StringIO(test_lexicon)
        self.read_lexicon(lexicon_file)
        row += 1
        for n, cat_node in enumerate(self.categories):
            cat_node.set_pos(WIDTH / (len(self.categories) + 1) * (n + 1), row * row_height)
        left, right, *rest = self.numeration
        self.merge_right.connect(left)
        self.merge_right.connect(self.merge_ok)
        self.merge_left.connect(right)
        self.merge_left.connect(self.merge_ok)
        self.merge_pair.connect(left)
        self.merge_pair.connect(right)
        self.merge_pair.connect(self.merge_ok)
        row += 1
        y_shift = -100
        for n, feat_node in enumerate(self.features.values()):
            x = WIDTH / (len(self.features) + 1) * (n + 1)
            y = row * row_height + y_shift
            y_shift += 50
            if y_shift > 50:
                y_shift = -100
            if feat_node.sign:
                feat_node.connect(self.merge_right)
                feat_node.connect(self.merge_left)
                feat_node.connect_positive()
            if feat_node.name == 'adjL':
                feat_node.connect(self.merge_pair)
                feat_node.connect_adjuncts()
            if feat_node.name == 'a' and feat_node.values:
                feat_node.connect(self.merge_pair)
            feat_node.set_pos(x, y)
        row += 1
        y_shift = 0
        for n, lex_node in enumerate(self.lexicon.values()):
            x = WIDTH / (len(self.lexicon) + 1) * (n + 1)
            y = row * row_height + y_shift
            y_shift += 20
            if y_shift > 60:
                y_shift = 0
            lex_node.set_pos(x, y)
        self.update_canvas()
        return self

    def clear_activations(self):
        for node in self.nodes.values():
            node.activations = []
            node.active = False
        for edge in self.edges.values():
            edge.activations = []

    def activate(self):
        left = self.words.prev_item
        right = self.words.current_item
        left_signal = self.words.prev_i
        right_signal = self.words.current_i
        print(f'*** activate {left.id}+{right.id}')
        self.numeration[0].activate(left_signal)
        self.numeration[1].activate(right_signal)
        left.activate(left_signal)
        right.activate(right_signal)
        self.update_canvas()


class NetworkApp(App):
    def build(self):
        global g
        g = Network()
        g.build()
        g.parse(sentence)
        return g


if __name__ == '__main__':
    NetworkApp().run()
