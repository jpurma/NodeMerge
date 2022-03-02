from kivy.uix.label import Label
from kivy.graphics import *
from util import hue, find_edge
from edges import Edge, LexEdge, AdjunctEdge, MergeEdge
from ctrl import ctrl


class Node:
    color = [64, 64, 64, 128]

    def __init__(self, id):
        self.id = id
        ctrl.nodes[id] = self
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

    def reset(self):
        self.deactivate()

    def add_label(self):
        self.label_item = Label(text=self.id)
        self.label_item.x = self.x - 20
        self.label_item.y = self.y - 10
        words = ctrl.words
        if words and words.current_item and words.current_item.li is self:
            self.label_item.color = [1.0, 0.5, 0.5]
        elif words and words.closest_item and words.closest_item.li is self:
            self.label_item.color = [1.0, 0.4, 1.0]
        elif self.active:
            self.label_item.color = [1.0, 1.0, 0.4]
        else:
            self.label_item.color = [0.7, 0.7, 0.7]
        ctrl.g.add_widget(self.label_item)

    def set_pos(self, x, y):
        self.x = x
        self.y = y
        if self.label_item:
            self.label_item.x = x
            self.label_item.y = y

    def draw(self):
        with ctrl.g.canvas:
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
        assert fstring not in ctrl.features
        self.adjunct_licensor = self.name == 'adjL'
        ctrl.features[fstring] = self

    def connect_adjuncts(self):
        for feat in ctrl.features.values():
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
        self.banned_signals = set()
        self.sign = fstring[0]
        name_string = fstring[1:]
        if ':' in name_string:
            self.name, value_string = name_string.split(':', 1)
            self.values = value_string.split('|')
        else:
            self.name = name_string
            self.values = []
        assert fstring not in ctrl.features
        ctrl.features[fstring] = self

    def connect_positive(self):
        for feat in ctrl.features.values():
            if feat.name == self.name and not feat.sign and feat is not self and ((not self.values) or feat.values_match(self)):
               print('connect feats ', self, '+', feat)
               feat.connect(self)

    def reset(self):
        super(NegFeatureNode, self).reset()
        self.banned_signals = set()

    def activate(self, n):
        if n not in self.activations:
            self.activations.append(n)
            lex_activations = []
            feat_activations = []
            self.active = False
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
                    self.banned_signals.add(head_signal)
                    for arg_signal in feat_activations:
                        for out in self.edges_out:
                            out.activate((head_signal, arg_signal))
                self.active = True
        if not self.activations:
            self.active = False

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
        ctrl.categories.append(self)

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
        arg_signal = ctrl.words.current_item.signal
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
                ctrl.g.add_merge(n[0], n[1])
                for out in self.edges_out:
                    for n in accepted_signals:
                        out.activate(n)
        self.active = bool(self.activations)


class RightMergeNode(MergeNode):
    def activate(self, n):
        if self.activations:
            self.active = True
            return
        head_signal = ctrl.words.current_item.signal
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
                ctrl.g.add_merge(n[0], n[1])
                for out in self.edges_out:
                    for n in accepted_signals:
                        out.activate(n)
        self.active = bool(self.activations)


class PairMergeNode(MergeNode):

    def activate(self, n):
        if n not in self.activations:
            right_signal = ctrl.words.current_item.signal
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
                ctrl.g.add_adjunction(n[0], n[1])
                for out in self.edges_out:
                    for n in accepted_signals:
                        out.activate(n)
        self.active = bool(self.activations)


class MergeOkNode(Node):
    def activate(self, n):
        if n not in self.activations:
            self.activations.append(n)
        self.active = bool(self.activations)

