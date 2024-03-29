from kivy.uix.label import Label
from kivy.graphics import *

from util import hue, find_edge
from edges import Edge, LexEdge, AdjunctEdge, MergeEdge
from ctrl import ctrl


class Node:
    color = [64, 64, 64, 128]
    draw_in_route_mode = False
    draw_in_feature_mode = True

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

    def activate(self, n, source=None):
        if n not in self.activations:
            self.activations.append(n)
            self.active = True
            for out in self.edges_out:
                out.activate(n)
        self.active = bool(self.activations)

    def deactivate(self):
        self.activations = {}
        self.active = False

    def reset(self):
        self.deactivate()

    def add_label(self):
        self.label_item = Label(text=self.id)
        self.label_item.x = self.x - 20
        self.label_item.y = self.y - 10
        if self.active:
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
                    Line(circle=[self.x, self.y, r], width=4)
                    r += 4


class LexicalNode(Node):
    color = [0.8, 0.8, 0.8, 0.5]
    draw_in_route_mode = True

    def __init__(self, word, cats, feats, lex_parts):
        super().__init__(word)
        self.word = word
        self.categories = cats
        self.feats = feats
        self.selected_color = [0, 0.8, 0]
        self.arg_edges = []
        self.head_edges = []
        self.adjunctions = []
        self.adjunct_to = []
        self.routes_down = []
        self.route_edges = []
        self.lex_parts = lex_parts
        self.info_item = None
        for f_node in feats:
            self.connect(f_node)
        for c_node in cats:
            self.connect(c_node)
            c_node.connect(self)

    def activate(self, n, source=None):
        if n not in self.activations:
            self.activations.append(n)
            if self.activations:
                for out in self.edges_out:
                    out.activate(n)
        self.active = bool(self.activations)

    def count_routes_down(self):
        edges_by_signal = {}
        for edge in self.route_edges:
            if edge.end_signal not in edges_by_signal:
                edges_by_signal[edge.end_signal] = {edge.origin}
            else:
                edges_by_signal[edge.end_signal].add(edge.origin)
        return '\n'.join(f'{signal}: {len(edges)}' for signal, edges in edges_by_signal.items())

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
        self.info_item = Label(text=self.count_routes_down())
        self.info_item.x = self.x - 20
        self.info_item.y = self.y - 50
        self.info_item.color = [0.7, 0.7, 0.7]
        ctrl.g.add_widget(self.info_item)

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

    def has_mover_feature(self):
        for f_node in self.feats:
            if f_node.name == 'moves':
                return True
        return False

    def is_word_head(self):
        return self.lex_parts[0] is self

    def is_free_to_move(self):
        return self.has_mover_feature()

    @staticmethod
    def add_adjunction(head, adj):
        if (find_edge(head.li.adjunctions, start=head, end=adj)
           or find_edge(adj.li.adjunct_to, start=head, end=adj)):
            print('  Nodes: exists already')
            return
        edge = AdjunctEdge(adj, head)
        head.li.adjunctions.append(edge)
        adj.li.adjunct_to.append(edge)

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
        if not (self.values and other.values):
            return True
        for f in self.values:
            if f in other.values:
                return f

    def sortable(self):
        return self.name, ''.join(self.values), self.sign


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
        ctrl.features[fstring] = self

    def activate(self, n, source=None):
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
        self.sign = fstring[0]
        name_string = fstring[1:]
        if ':' in name_string:
            self.name, value_string = name_string.split(':', 1)
            self.values = value_string.split('|')
        else:
            self.name = name_string
            self.values = []
        assert fstring not in ctrl.features
        self.lex_activations = []
        self.feat_activations = []
        ctrl.features[fstring] = self

    def connect_positive(self):
        for feat in ctrl.features.values():
            if feat.name == self.name \
                    and not feat.sign \
                    and feat is not self \
                    and feat.values_match(self):
               feat.connect(self)

    def activate(self, n, source=None):
        if not self.activations:
            self.lex_activations = []
            self.feat_activations = []
            self.active = False
        if n not in self.activations:
            self.activations.append(n)
        if source:
            if isinstance(source.start, (LexicalNode, CategoryNode)):
                if n not in self.lex_activations:
                    self.lex_activations.append(n)
                    for arg_signal in self.feat_activations:
                        for out in self.edges_out:
                            out.activate((n, arg_signal))
                        self.active = True
            else:
                if n not in self.feat_activations:
                    if self.sign == '-' or n not in self.lex_activations:
                        self.feat_activations.append(n)
                        for head_signal in self.lex_activations:
                            for out in self.edges_out:
                                out.activate((head_signal, n))
                            self.active = True

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

    def activate(self, n, source=None):
        if n not in self.activations:
            self.activations.append(n)
        self.active = bool(self.activations)


class MergeNode(Node):
    color = [1.0, 1.0, 0, .5]


class SymmetricMergeNode(MergeNode):
    def activate(self, n, source=None):
        right_signal = ctrl.words.current_item.signal
        accepted_signals = []
        for e in self.edges_in:
            if e.activations and isinstance(e.start, FeatureNode):
                print('  Nodes: received activations:', e.activations)
                for head_signal_in, arg_signal_in in e.activations:
                    if arg_signal_in == right_signal:
                        accepted_signals.append((head_signal_in, arg_signal_in))
                    elif head_signal_in == right_signal:
                        accepted_signals.append((head_signal_in, arg_signal_in))
        print('  Nodes: accepted signals at symmetric merge: ', accepted_signals)
        print('  Nodes: n: ', n)
        if n in accepted_signals:
            self.activations.append(n)
            print(f'  Nodes: at {self.id} adding left/right merge {n[0]}<->?{n[1]} where {n[0]} is head')
            ctrl.g.add_merge(n[0], n[1])
            for out in self.edges_out:
                for n in accepted_signals:
                    out.activate(n)
        self.active = bool(self.activations)


# class LeftMergeNode(MergeNode):
#     def activate(self, n):
#         arg_signal = ctrl.words.current_item.signal
#         accepted_signals = []
#         for e in self.edges_in:
#             if e.activations and isinstance(e.start, FeatureNode):
#                 for head_signal_in, arg_signal_in in e.activations:
#                     if arg_signal_in == arg_signal:
#                         accepted_signals.append((head_signal_in, arg_signal_in))
#         print('accepted signals at left merge: ', accepted_signals)
#         print('n: ', n)
#         if n in accepted_signals:
#             self.activations.append(n)
#             print(f'at {self.id} adding left merge {n[0]}<-{n[1]}')
#             ctrl.g.add_merge(n[0], n[1])
#             for out in self.edges_out:
#                 for n in accepted_signals:
#                     out.activate(n)
#         self.active = bool(self.activations)
#
#
# class RightMergeNode(MergeNode):
#     def activate(self, n):
#         head_signal = ctrl.words.current_item.signal
#         accepted_signals = []
#         for e in self.edges_in:
#             if e.activations and isinstance(e.start, FeatureNode):
#                 for head_signal_in, arg_signal_in in e.activations:
#                     if head_signal_in == head_signal:
#                         accepted_signals.append((head_signal_in, arg_signal_in))
#
#         print('accepted signals at right merge: ', accepted_signals)
#         print('n: ', n)
#         if n in accepted_signals:
#             self.activations.append(n)
#             print(f'at {self.id} adding right merge {n[0]}->{n[1]}')
#             ctrl.g.add_merge(n[0], n[1])
#             for out in self.edges_out:
#                 for n in accepted_signals:
#                     out.activate(n)
#         self.active = bool(self.activations)


class SymmetricPairMergeNode(MergeNode):
    def activate(self, n, source=None):
        right_signal = ctrl.words.current_item.signal
        accepted_signals = []
        for e in self.edges_in:
            if e.activations and isinstance(e.start, FeatureNode):
                for head_signal_in, arg_signal_in in e.activations:
                    if arg_signal_in == right_signal:
                        accepted_signals.append((head_signal_in, arg_signal_in))
                    elif head_signal_in == right_signal:
                        accepted_signals.append((head_signal_in, arg_signal_in))
        print('  Nodes: accepted signals at symmetric merge: ', accepted_signals)
        print('  Nodes: n: ', n)
        if n in accepted_signals:
            self.activations.append(n)
            print(f'  Nodes: at {self.id} adding pair merge {n[0]}<->?{n[1]} where {n[0]} is -')
            ctrl.g.add_adjunction(n[0], n[1])
            for out in self.edges_out:
                for n in accepted_signals:
                    out.activate(n)
        self.active = bool(self.activations)


# class PairMergeNode(MergeNode):
#     # Viimeksi jäi epäselväksi onko meillä tarve erilliselle Mergeille vasemmalle ja oikealle, vai riittääkö
#     # symmetrinen merge ja symmetrinen parimerge, ja asymmetria tulisi signaalien järjestyksen kautta. Nykyiset
#     # mergejen laukaisijat eivät välitä suunnasta. Sen sijaan että olisi esivalintaa mitkä elementit ovat
#     # mergettävissä, nyt vaikea (laskennallinen) osuus tulisi siitä että mahdollisten mergejen vyyhdistä valitaan
#     # 'optimaalisin'. Vaikka noodi on symmetrinen, eli samaa noodia käytetään mergettäessä vasemmalle tai oikealle,
#     # se on kuitenkin asymmetrinen lopputulokseltaan, eli negatiivisen piirteen omistajasta tulee pää, positiivisen
#     # piirteen omistajasta argumentti.
#     # Tähän liittyi se, että parimergen käynnistävät piirteet voisi muuttaa tuttuun negatiivisen ja positiivisen
#     # piirteen tarkistamiseen, mutta pitää silti erillään niillä olisi silloin joku eri merkki, vaikka '-'.
#     def activate(self, n):
#         if n not in self.activations:
#             right_signal = ctrl.words.current_item.signal
#             if right_signal not in n:
#                 return
#             for e in self.edges_in:
#                 if e.activations:
#                     print('incoming pair merge activations: ', e.activations)
#                     print('from source: ', e.start)
#             print('activating adj merge with n: ', n)
#             self.activations.append(n)
#             print(f'at {self.id} adding pair merge ', n)
#             ctrl.g.add_adjunction(n[0], n[1])
#             for out in self.edges_out:
#                 out.activate(n)
#         self.active = bool(self.activations)


class MergeOkNode(Node):
    def activate(self, n, source=None):
        if n not in self.activations:
            self.activations.append(n)
        self.active = bool(self.activations)
