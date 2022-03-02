from io import StringIO

from kivy.app import App
from kivy.uix.button import Button
from kivy.uix.widget import Widget
from nodes import *
from word_parts import WordPart, WordPartList

from lexicon import test_lexicon, sentence

N_SIZE = 3
WIDTH = 1600
HEIGHT = 1024


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
            node.reset()
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
        g = Network()
        ctrl.post_initialize(g)
        g.build()
        g.parse(sentence)
        return g


if __name__ == '__main__':
    NetworkApp().run()
