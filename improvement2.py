from io import StringIO

from kivy.app import App
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.graphics import *

from lexicon2 import test_lexicon, sentence

import math

N_SIZE = 3
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

    @property
    def signal(self):
        return self.activations[0] if self.activations else None

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
                if not isinstance(activation, tuple):
                    activation = [activation]
                for signal in activation:
                    Color(hue(signal), 0.8, 0.5, mode='hsv')
                    Line(points=[self.start.x + x_diff, self.start.y + y_diff, self.end.x + x_diff, self.end.y + y_diff], width=2)
                    Line(circle=[cx, cy, 3], width=2)
                    x_diff += 2
                x_diff += 2

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


class LexEdge(Edge):
    @staticmethod
    def get_or_create(start, end):
        return LexEdge.get(start, end) or __class__(start, end)

    def activate(self, n):
        pass


class MergeEdge:
    def __init__(self, start, end):
        print(f'** creating merge edge arg: {start} head: {end}')
        self.id = MergeEdge.create_id(start, end)
        g.edges[self.id] = self
        self.active = True
        self.start = start
        self.end = end
        self.signal = start.signal

    def __repr__(self):
        return f'{self.__class__.__name__}({self.id})'

    @property
    def arg(self):
        return self.start

    @property
    def head(self):
        return self.end

    def draw(self):
        sn = self.start.li
        en = self.end.li
        cx = sn.x + (en.x - sn.x) * .9
        cy = sn.y + (en.x - sn.x) * -.3
        with g.canvas:
            Color(hue(self.signal), .5, .6, mode='hsv')
            Bezier(points=[sn.x, sn.y + self.start.signal * 2, cx, cy, en.x, en.y + self.end.signal * 2], width=3)

    @staticmethod
    def create_id(start, end):
        return f'D{start.li.id}{start.signal}_{end.li.id}{end.signal}'


class AdjunctEdge:
    color = [0.8, 0.2, 0.2]

    def __init__(self, start, end):
        print('** creating adjunct edge ', start, end)
        self.id = f'{start.li.id}{start.signal}_{end.li.id}{end.signal}'
        g.edges[self.id] = self
        self.active = True
        self.start = start
        self.end = end

    def __repr__(self):
        return f'{self.__class__.__name__}({self.id})'

    def draw(self):
        sn = self.start.li
        en = self.end.li
        with g.canvas:
            Color(hue(self.start.signal), .5, .6, mode='hsv')
            Line(points=[sn.x, sn.y - self.start.signal, en.x, en.y - self.end.signal], width=1)


def find_edge(edges, start=None, end=None):
    for edge in edges:
        if edge.start == start and edge.end == end:
            return edge


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
        if g.words and g.words.current_item and g.words.current_item.li is self:
            self.label_item.color = [1.0, 0.5, 0.5]
        elif g.words and g.words.closest_item and g.words.closest_item.li is self:
            self.label_item.color = [1.0, 0.4, 1.0]
        elif self.active:
            self.label_item.color = [1.0, 1.0, 0.4]
        else:
            self.label_item.color = [0.7, 0.7, 0.7]
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
                if not isinstance(activation, tuple):
                    activation = [activation]
                for signal in activation:
                    Color(hue(signal), 0.8, 0.5, mode='hsv')
                    Line(circle=[self.x, self.y, r], width=2)
                    r += 4


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
        self.active = bool(self.activations)

    def connect_lex_parts(self):
        if len(self.lex_parts) == 1:
            return
        i = self.lex_parts.index(self)
        if i + 1 == len(self.lex_parts):
            return
        other = self.lex_parts[i + 1]
        edge = LexEdge.get_or_create(self, other)
        if edge not in self.edges_out:
            self.edges_out.append(edge)
        if edge not in other.edges_in:
            other.edges_in.append(edge)

    @staticmethod
    def add_adjunction(first, second):
        if (find_edge(first.li.adjunctions, start=second, end=first)
           or find_edge(second.li.adjunctions, start=first, end=second)):
            print('exists already')
            return
        edge = AdjunctEdge(first, second)
        first.li.adjunctions.append(edge)
        second.li.adjunctions.append(edge)

    @staticmethod
    def add_merge(head, arg):
        if find_edge(head.li.arg_edges, start=arg, end=head):
            return
        edge = MergeEdge(arg, head)
        head.li.arg_edges.append(edge)
        arg.li.head_edges.append(edge)


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
        if self.adjunct_licensor:
            if n not in self.activations:
                self.activations.append(n)
                if len(self.activations) > 1:
                    for out in self.edges_out:
                        out.activate(tuple(self.activations[:2]))
                    self.active = True
                else:
                    self.active = False
        else:
            if n not in self.activations:
                self.activations.append(n)
                for out in self.edges_out:
                    out.activate(n)
                self.active = True
            if not self.activations:
                self.active = False


class NegFeatureNode(FeatureNode):
    color = [1.0, 0, 0, 0.5]
    signs = '-=<>'

    def __init__(self, fstring):
        super().__init__(fstring)
        self.banned_signals = []
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

    def activate(self, n):
        if n not in self.activations:
            self.activations.append(n)
            lex_activations = []
            feat_activations = []
            self.active = []
            for e in self.edges_in:
                # use activation from active lexical item, not that of supporting feature
                if isinstance(e.start, (LexicalNode, CategoryNode)) and e.activations:
                    for signal in e.activations:
                        if signal not in lex_activations and signal not in self.banned_signals:
                            lex_activations.append(signal)
                elif e.activations:
                    for signal in e.activations:
                        if signal not in lex_activations:
                            feat_activations.append(signal)
            if lex_activations and feat_activations:
                for head_signal in lex_activations:
                    self.banned_signals.append(head_signal)
                    for arg_signal in feat_activations:
                        self.active.append((head_signal, arg_signal))
                        for out in self.edges_out:
                            out.activate((head_signal, arg_signal))
            else:
                self.active = []
        if not self.activations:
            self.active = []

    def activated_at(self, signal):
        if not self.active:
            return False
        for out in self.edges_out:
            for head_signal, arg_signal in out.activations:
                if signal == head_signal:
                    return True


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


class MergeNode(Node):
    color = [1.0, 1.0, 0, .5]


class LeftMergeNode(MergeNode):
    def activate(self, n):
        if self.activations:
            self.active = True
            return
        arg_signal = g.words.current_item.signal
        accepted_signals = []
        for e in self.edges_in:
            if e.activations and isinstance(e.start, FeatureNode):
                for head_signal_in, arg_signal_in in e.activations:
                    if arg_signal_in == arg_signal:
                        accepted_signals.append((head_signal_in, arg_signal_in))
        if accepted_signals:
            accepted_signals.sort()
            if n == accepted_signals[-1]:
                self.activations.append(n)
                print(f'at {self.id} adding left merge {n[0]}<-{n[1]}')
                g.add_merge(n[0], n[1])
                for out in self.edges_out:
                    for n in accepted_signals:
                        out.activate(n)
        self.active = bool(self.activations)


class RightMergeNode(MergeNode):
    def activate(self, n):
        if self.activations:
            self.active = True
            return
        head_signal = g.words.current_item.signal
        accepted_signals = []
        for e in self.edges_in:
            if e.activations and isinstance(e.start, FeatureNode):
                for head_signal_in, arg_signal_in in e.activations:
                    if head_signal_in == head_signal:
                        accepted_signals.append((arg_signal_in, head_signal_in, arg_signal_in))
        if accepted_signals:
            accepted_signals.sort()
            if n == tuple(accepted_signals[-1][1:]):
                self.activations.append(n)
                print(f'at {self.id} adding right merge {n[0]}->{n[1]}')
                g.add_merge(n[0], n[1])
                for out in self.edges_out:
                    for n in accepted_signals:
                        out.activate(n)
        self.active = bool(self.activations)


class PairMergeNode(MergeNode):

    def activate(self, n):
        if n not in self.activations:
            right_signal = g.words.current_item.signal
            left_signal = right_signal - 1
            accepted_signals = []
            for e in self.edges_in:
                if e.activations and isinstance(e.start, FeatureNode):
                    for signal1_in, signal2_in in e.activations:
                        if signal1_in == right_signal and signal2_in == left_signal:
                            accepted_signals.append((signal1_in, signal2_in))
            if n in accepted_signals and n not in self.activations:
                self.activations.append(n)
                print(f'at {self.id} adding pair merge ', n)
                g.add_adjunction(n[0], n[1])
                for out in self.edges_out:
                    for n in accepted_signals:
                        out.activate(n)
        self.active = bool(self.activations)


class MergeOkNode(Node):
    def activate(self, n):
        if n not in self.activations:
            self.activations.append(n)
        self.active = bool(self.activations)


class WordPart:
    def __init__(self, li, signal):
        self.li = li
        self.signal = signal

    def __str__(self):
        return f'({self.li.id}, {self.signal})'

    def __repr__(self):
        return str(self)

    def __eq__(self, other):
        return self.li is other.li and self.signal == other.signal

    def __hash__(self):
        return hash((self.li.id, self.signal))


class WordPartList:
    def __init__(self, words, lexicon):
        self.original = words
        self.words_left = list(reversed(words))
        self.lexicon = lexicon
        self.word_parts = []
        self.current_item = None
        self.prev_items = []
        self.closest_item = None

    def reset(self):
        self.words_left = list(reversed(self.original))
        self.prev_items = []
        self.current_item = None
        self.closest_item = None
        self.word_parts = []

    def get_by_signal(self, signal):
        return self.word_parts[signal - 1]

    def pick_first(self):
        self.current_item = WordPart(self.lexicon[self.words_left.pop()], 1)
        self.word_parts.append(self.current_item)
        return self.current_item

    def get_lex_parts(self, word_part):
        """ return li:s parts as WordPart instances which include their place in the sentence """
        lex_parts = word_part.li.lex_parts
        if len(lex_parts) == 1:
            return [word_part]
        i = self.word_parts.index(word_part)
        lex_part_i = lex_parts.index(word_part.li)
        start = i - lex_part_i
        end = i - lex_part_i + len(lex_parts)
        return self.word_parts[start:end]

    def print_state(self):
        print(f'''prev_items: {list(reversed(self.prev_items))} closest_item: {self.closest_item
              } current_item: {self.current_item}''')

    def pick_next(self):
        if not self.current_item:
            return
        li = self.current_item.li
        i = li.lex_parts.index(li)
        self.closest_item = self.current_item
        if i < len(li.lex_parts) - 1:
            self.current_item = WordPart(li.lex_parts[i + 1], self.current_item.signal + 1)
            self.word_parts.append(self.current_item)
        elif self.words_left:
            self.current_item = WordPart(self.lexicon[self.words_left.pop()], self.current_item.signal + 1)
            self.word_parts.append(self.current_item)
        else:
            self.current_item = None
        self.prev_items = self.collect_previous_items() if self.current_item else []
        # self.print_state()
        return self.current_item

    def can_merge(self):
        return self.prev_items and self.current_item

    def collect_previous_items(self):
        """ Seuraava haaste on tunnistaa tilanne, jossa sanan sisäinen elementti on arg, jolloin se koko sana on arg.

        Oikeastaan tätä ei pitäisi luoda joka iteraatioaskelella uudestaan, tämän pitäisi perustua signaalien sammuttamiseen
        silloin kun elementti on argumenttina.
         """

        def is_unsatisfied_blocker(b_part: WordPart):
            for e in b_part.li.edges_out:
                if isinstance(e.end, NegFeatureNode) and e.end.sign == '-' and not e.end.activated_at(b_part.signal):
                    return True

        def collect_adj_parts(adj_part, adj_parts):
            adj_parts.add(adj_part)
            for e in adj_part.li.adjunctions:
                if e.end == adj_part:
                    collect_adj_parts(e.start, adj_parts)

        def collect_complex_parts(c_parts):
            prev_li_parts = None
            for c_part in set(c_parts):
                if c_part.li.lex_parts is not prev_li_parts:
                    c_parts |= set(self.get_lex_parts(c_part))
                    prev_li_parts = c_part.li.lex_parts

        part_stack = list(self.word_parts)
        prev_items = []
        current = part_stack.pop()
        args = set()
        inner_parts = current.li.lex_parts
        related_parts = set()
        while part_stack:
            part = part_stack.pop()
            if part not in related_parts:
                related_parts = set()
                collect_adj_parts(part, related_parts)
                #collect_complex_parts(related_parts)
                print(f'related parts for {part}: ', related_parts)
                for related_part in related_parts:
                    if [head_edge for head_edge in related_part.li.head_edges if head_edge.arg == related_part]:
                        print(f'found one part being arg {related_part}, adding all related parts as args: ', related_parts)
                        args |= related_parts
            if part.li in inner_parts:
                continue
            else:
                inner_parts = part.li.lex_parts
                if part not in args:
                    prev_items.append(part)
            # if is_unsatisfied_blocker(part):
            #    break

        print(f'current {current}, known args: ', args)
        return prev_items


class Network(Widget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.nodes = {}
        self.edges = {}
        self.lexicon = {}
        self.features = {}
        self.categories = []
        self.merge_right = None
        self.merge_left = None
        self.merge_pair = None
        self.merge_ok = None
        self.words = None
        self.next_button = Button(text='Next', font_size=14)
        self.next_button.x = 20
        self.next_button.y = 20
        self.add_widget(self.next_button)
        self.next_button.on_press = self.next_word

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

    def find_by_signal(self, signal):
        for lex_item in reversed(self.lexicon.values()):
            if signal in lex_item.activations:
                return lex_item

    def add_merge(self, head_signal, arg_signal):
        head = self.find_by_signal(head_signal)
        arg = self.find_by_signal(arg_signal)
        if head and arg:
            LexicalNode.add_merge(WordPart(head, head_signal), WordPart(arg, arg_signal))

    def add_adjunction(self, first_signal, second_signal):
        first = self.find_by_signal(first_signal)
        second = self.find_by_signal(second_signal)
        if first and second:
            LexicalNode.add_adjunction(WordPart(first, first_signal), WordPart(second, second_signal))

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

    def next_word(self):
        if not self.words:
            return
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
        lexicon_file = StringIO(test_lexicon)
        self.read_lexicon(lexicon_file)
        row += 1
        for n, cat_node in enumerate(self.categories):
            cat_node.set_pos(WIDTH / (len(self.categories) + 1) * (n + 1), row * row_height)
        self.merge_right.connect(self.merge_ok)
        self.merge_left.connect(self.merge_ok)
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
            lex_node.connect_lex_parts()
        self.update_canvas()
        return self

    def clear_activations(self):
        for node in self.nodes.values():
            node.activations = []
            node.active = False
        for edge in self.edges.values():
            edge.activations = []

    def activate(self):
        lefts = list(reversed(self.words.prev_items))
        closest = self.words.closest_item
        right = self.words.current_item
        right.li.activate(right.signal)
        closest.li.activate(closest.signal)
        for left in reversed(lefts):
            left.li.activate(left.signal)
        print(f'*** activate {lefts}+{closest}+{right}')
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
