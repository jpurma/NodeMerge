from kivy.app import App
from kivy.uix.button import Button
from kivy.uix.widget import Widget
from nodes import *
from word_parts import WordPart, WordPartList
from util import build_tree

N_SIZE = 3
WIDTH = 1600
HEIGHT = 1024
LEXICON_PATH = 'lexicon.txt'
SENTENCES_PATH = 'sentences.txt'
SHOW_FULL_LEXICON = False


class Network(Widget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.nodes = {}
        self.edges = {}
        self.lexicon = {}
        self.features = {}
        self.categories = []
        self.sentences = []
        self.current_sentence_index = 0
        self.merge_right = None
        self.merge_left = None
        self.merge_pair = None
        self.merge_ok = None
        self.words = None
        self.ongoing_sentence = ""
        self.ongoing_sentence_label = Label(text="")
        self.ongoing_sentence_label.x = WIDTH / 2
        self.ongoing_sentence_label.y = 100
        self.next_button = Button(text='Next step', font_size=14)
        self.next_button.x = 120
        self.next_button.y = 10
        self.add_widget(self.next_button)
        self.next_button.on_press = self.next_word
        self.next_sen_button = Button(text='Next sen', font_size=14)
        self.next_sen_button.x = 10
        self.next_sen_button.y = 10
        self.add_widget(self.next_sen_button)
        self.next_sen_button.on_press = self.next_sentence

    def clear_grammar(self):
        self.nodes = {}
        self.edges = {}
        self.lexicon = {}
        self.features = {}
        self.categories = []
        self.merge_right = None
        self.merge_left = None
        self.merge_pair = None
        self.merge_ok = None

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
        self.add_widget(self.next_sen_button)
        self.add_widget(self.ongoing_sentence_label)

    def read_lexicon(self, lexicon_file, append=False, only_these=None):
        if not append:
            self.lexicon.clear()
        new_lexicon = {}
        with open(lexicon_file) as lines:
            for line in lines:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                word, feats = line.split('::', 1)
                word = word.strip()
                if only_these and word not in only_these:
                    continue
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
                    new_lexicon[word] = lex_node
                    first = False
        if only_these:
            self.lexicon.clear()
            for word in only_these:
                lex_node = new_lexicon[word]
                self.lexicon[word] = lex_node
                if lex_node.lex_parts:
                    for part in lex_node.lex_parts:
                        self.lexicon[part.id] = part

        else:
            self.lexicon = new_lexicon

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

    def update_sentence(self, text=""):
        if not text:
            text = f'{self.current_sentence_index + 1}/{len(self.sentences)}. ' + self.sentences[
                self.current_sentence_index]
        self.ongoing_sentence = text
        self.ongoing_sentence_label.text = self.ongoing_sentence

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
        if self.words.pick_next():
            self.update_sentence(' '.join([wp.li.id for wp in self.words.word_parts]))
        else:
            self.reset()
            self.words.pick_first()
            self.update_sentence()

        self.clear_activations()
        if self.words.can_merge():
            self.activate()
        build_tree(self.words.word_parts)
        self.update_canvas()

    def next_sentence(self):
        self.clear_activations()
        self.reset()
        self.current_sentence_index += 1
        if self.current_sentence_index == len(self.sentences):
            self.current_sentence_index = 0
        self.parse(self.sentences[self.current_sentence_index])
        self.update_canvas()

    def add(self, node_class, label, *args, **kwargs):
        if label in self.nodes:
            return self.nodes[label]
        node = node_class(label, *args, **kwargs)
        self.nodes[label] = node
        return node

    def parse(self, sentence):
        if not SHOW_FULL_LEXICON:
            self.clear_grammar()
            self.read_lexicon(LEXICON_PATH, only_these=sentence.split())
            self.draw_grammar()
        elif not self.lexicon:
            self.read_lexicon(LEXICON_PATH)
            self.draw_grammar()
        self.words = WordPartList(sentence.split(), self.lexicon)
        self.words.pick_first()
        self.update_sentence()

    def draw_grammar(self):
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

        row += 2
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

    def build(self):
        self.sentences = [row.strip() for row in open(SENTENCES_PATH).readlines()
                          if row.strip() and not row.strip().startswith('#')]
        self.parse(self.sentences[self.current_sentence_index])

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
        return g


if __name__ == '__main__':
    NetworkApp().run()
