import json
import math
import socket
from operator import attrgetter

from kivy.app import App
from kivy.uix.button import Button
from kivy.uix.widget import Widget
from kivy.core.window import Window

from improvement4.edges import RouteEdge
from nodes import *
from signaler import Signaler
from route import Route

N_SIZE = 3
WIDTH = 2048
HEIGHT = 1600
LEXICON_PATH = 'lexicon.txt'
SENTENCES_PATH = 'sentences.txt'
SHOW_FULL_LEXICON = False

IP, PORT = '127.0.0.1', 62236

Window.size = WIDTH / 2, HEIGHT / 2

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
        self.merge = None
        self.merge_pair = None
        self.merge_ok = None
        self.signaler = None
        self.route_mode = False
        self.ongoing_sentence = ""
        self.ongoing_sentence_label = Label(text="")
        self.ongoing_sentence_label.x = WIDTH / 2
        self.ongoing_sentence_label.y = 100
        self.sentence_row_y = 0
        self.kataja_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
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
        self.route_mode_button = Button(text='Routes /\nNetwork', font_size=14)
        self.route_mode_button.x = WIDTH - 120
        self.route_mode_button.y = 10
        self.add_widget(self.route_mode_button)
        self.route_mode_button.on_press = self.toggle_route_mode
        self.counter = 0

        keyboard = Window.request_keyboard(self.handle_keyup, self)
        keyboard.bind(on_key_up=self.handle_keyup)
        Window.bind(on_request_close=self.on_request_close)

    def on_request_close(self, *args):
        if self.kataja_socket:
            # Sockets should be closed on garbage collection, probably this is not necessary
            self.kataja_socket.close()

    def handle_keyup(self, window, keycode):
        if keycode:
            if keycode[1] == 'right':
                self.next_word()
            elif keycode[1] == 'down':
                self.next_sentence()
            elif keycode[1] == 'up':
                self.prev_sentence()

    def clear_grammar(self):
        self.nodes = {}
        self.edges = {}
        self.lexicon = {}
        self.features = {}
        self.categories = []
        self.merge = None
        self.merge_pair = None
        self.merge_ok = None

    def toggle_route_mode(self):
        self.route_mode = not self.route_mode
        if self.route_mode:
            self.draw_sentence_circle()
        else:
            self.draw_sentence_row()
        self.update_canvas()

    def update_canvas(self, *args):
        self.canvas.clear()
        self.clear_widgets()
        if self.route_mode:
            for edge in self.edges.values():
                if edge.draw_in_route_mode:
                    edge.draw()
        else:
            for edge in self.edges.values():
                if edge.draw_in_feature_mode:
                    edge.draw()
        if self.route_mode:
            for node in self.nodes.values():
                if node.draw_in_route_mode:
                    node.draw()
        else:
            for node in self.nodes.values():
                if node.draw_in_feature_mode:
                    node.draw()
        if self.route_mode:
            for node in self.nodes.values():
                if node.draw_in_route_mode:
                    node.add_label()
        else:
            for node in self.nodes.values():
                if node.draw_in_feature_mode:
                    node.add_label()
        self.add_widget(self.next_button)
        self.add_widget(self.next_sen_button)
        self.add_widget(self.ongoing_sentence_label)
        self.add_widget(self.route_mode_button)

    def merge_signals(self, old_signal, new_signal):
        for node in self.nodes.values():
            node.merge_activations(old_signal, new_signal)
            if isinstance(node, LexicalNode):
                for route in node.routes_down:
                    #if route.wp.signal == old_signal:
                    route.rs.merge_signals(old_signal, new_signal)

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
                        word = f"{word}'"
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

    def get_wp(self, signal):
        for wp in self.signaler.word_parts:
            if wp.signal == signal:
                return wp

    def get_first_wp(self, signal):
        for wp in self.signaler.word_parts:
            if wp.signal == signal:
                return wp

    def get_last_wp(self, signal):
        for wp in reversed(self.signaler.word_parts):
            if wp.signal == signal:
                return wp

    def add_merge(self, head_signal, arg_signal):
        if head_signal < arg_signal or True:
            head = self.get_first_wp(head_signal)
            arg = self.get_first_wp(arg_signal)
        else:
            head = self.get_first_wp(head_signal)
            arg = self.get_last_wp(arg_signal)
        if head and arg:
            LexicalNode.add_merge(head, arg)

    def add_adjunction(self, first_signal, second_signal):
        head = self.get_wp(first_signal)
        adj = self.get_wp(second_signal)
        if head and adj:
            LexicalNode.add_adjunction(head, adj)

    def update_sentence(self, text=""):
        if not text:
            text = f'{self.current_sentence_index + 1}/{len(self.sentences)}. ' + self.sentences[
                self.current_sentence_index]
        self.ongoing_sentence = text
        self.ongoing_sentence_label.text = self.ongoing_sentence

    def send(self, data):
        if self.kataja_socket:
            try:
                self.kataja_socket = socket.create_connection((IP, PORT))
                self.kataja_socket.send(str(data).encode('utf-8'))
                self.kataja_socket.close()
                return True
            except ConnectionRefusedError:
                self.kataja_socket = None

    def reset(self):
        self.signaler.reset()
        self.counter = 0
        for edge in list(self.edges.values()):
            if isinstance(edge, (MergeEdge, AdjunctEdge, RouteEdge)):
                del self.edges[edge.id]
        for node in self.nodes.values():
            node.reset()
            if isinstance(node, LexicalNode):
                node.head_edges.clear()
                node.arg_edges.clear()
                node.adjunctions.clear()
                node.adjunct_to.clear()
                node.routes_down.clear()
                node.route_edges.clear()
        self.clear_activations()

    def decay_signals(self):
        for edge in self.edges.values():
            edge.decay()
        for node in self.nodes.values():
            node.decay()

    def next_word(self):
        if not self.signaler:
            return
        if self.signaler.current_item.signal == 1:
            self.update_canvas()
            leaf_constituent = Route(None, wp=self.signaler.current_item)
            leaf_constituent.wp.li.routes_down.append(leaf_constituent)
        if self.signaler.pick_next():
            self.update_sentence(' '.join([wp.li.id for wp in self.signaler.word_parts]))
        else:
            self.reset()
            self.signaler.pick_first()
            self.update_sentence()
        print()
        print(f'** Activating {self.signaler.current_item} ***')
        if self.signaler.can_merge():
            self.decay_signals()
            self.signaler.activate_current_words()
            self.update_canvas()
        print()
        print(f'*** Handling {self.signaler.current_item} ***')
        leaf_constituent = Route(None, wp=self.signaler.current_item)
        leaf_constituent.wp.li.routes_down.append(leaf_constituent)
        leaf_constituent.walk_all_routes_up()
        """
        for wp in self.signaler.word_parts[:-1]:
            print()
            print(f' *** Revisiting {wp} ***')
            print(f' routes to walk: {wp.li.routes_down}')
            for route in wp.li.routes_down:
                if route.wp is wp and len(route) == 1:
                    route.walk_all_routes_up()

        for wp in self.signaler.word_parts:
            if wps_to_merge := self.should_merge_signals(wp):
                print(f'*** merging signals {wps_to_merge} -> {wp}')
                for wp_to_merge in wps_to_merge:
                    wp_to_merge.merged = True
                    self.merge_signals(wp_to_merge.signal, wp.signal)
                    wp_to_merge.signal = wp.signal
        """
        if self.signaler.is_last() and False:
            for wp in self.signaler.word_parts:
                print()
                print(f' *** Revisiting one last time: {wp} ***')
                print(f' routes to walk: {wp.li.routes_down}')
                for route in wp.li.routes_down:
                    if route.wp is wp and len(route) == 1:
                        route.walk_all_routes_up()

            print('****************************************')
            print('*                                      *')
            print('* Done parsing, now pick optimal route *')
            print('*                                      *')
            print('****************************************')
            self.pick_optimal_route()
        else:
            self.show_current_routes()
        self.update_canvas()

    def should_merge_signals(self, wp):
        my_routes = [r for r in wp.li.routes_down if r.wp.signal == wp.signal]
        wps_to_merge = set()
        if my_routes:
            top_route = my_routes[0]
            if top_route.arg and top_route.arg.wp.signal < wp.signal:
                print(f'sig_merge {top_route.arg.wp} -> {wp} because it is argument at route {top_route}')
                wps_to_merge.add(top_route.arg.wp)
                arg_part = top_route.arg.part
                while arg_part:
                    print(f'sig_merge {arg_part.wp} -> {wp} because it is part of merged argument')
                    wps_to_merge.add(arg_part.wp)
                    arg_part = arg_part.part
            if top_route.wp.merged and top_route.part and False:
                part = top_route.part
                while part:
                    if part.wp.signal != wp.signal:
                        print(f'sig_merge {part.wp} -> {wp} because it is my part')
                        wps_to_merge.add(part.wp)
                    part = part.part
            for adjunct in top_route.adjuncts:
                if adjunct.wp.signal != wp.signal:
                    print(f'sig_merge {adjunct.wp} -> {wp} because it is adjunct of this wp')
                    wps_to_merge.add(adjunct.wp)
        return wps_to_merge

    def next_sentence(self):
        self.current_sentence_index += 1
        if self.current_sentence_index == len(self.sentences):
            self.current_sentence_index = 0
        self._reset_sentence()

    def prev_sentence(self):
        self.current_sentence_index -= 1
        if self.current_sentence_index < 0:
            self.current_sentence_index = len(self.sentences) - 1
        self._reset_sentence()

    def _reset_sentence(self):
        self.clear_activations()
        self.reset()
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
        self.signaler = Signaler(sentence.split(), self.lexicon)
        self.signaler.pick_first()
        self.update_sentence()

    def draw_grammar(self):
        row = 1
        row_height = HEIGHT / 6
        self.merge = self.add(SymmetricMergeNode, 'M(A<?>B)')  # A→B
        self.merge.set_pos(WIDTH / 2 - WIDTH / 8, row * row_height)
        self.merge_pair = self.add(SymmetricPairMergeNode, 'M(A<->B)')
        self.merge_pair.set_pos(WIDTH / 2 + WIDTH / 8, row * row_height)
        self.merge_ok = self.add(MergeOkNode, 'OK')
        self.merge_ok.set_pos(100, HEIGHT / 2)

        row += 2
        for n, cat_node in enumerate(self.categories):
            cat_node.set_pos(WIDTH / (len(self.categories) + 1) * (n + 1), row * row_height)
        self.merge.connect(self.merge_ok)
        self.merge_pair.connect(self.merge_ok)
        row += 1
        y_shift = row_height / -2
        sorted_features = sorted(self.features.values(), key=FeatureNode.sortable)
        for n, feat_node in enumerate(sorted_features):
            x = WIDTH / (len(self.features) + 1) * (n + 1)
            y = row * row_height + y_shift
            y_shift += 50
            if y_shift > 50:
                y_shift = -100
            if feat_node.sign == '=':
                feat_node.connect(self.merge)
                feat_node.connect_positive()
            elif feat_node.sign == '-':
                feat_node.connect(self.merge_pair)
                feat_node.connect_positive()
            feat_node.set_pos(x, y)
        row += 1
        print('row: ', row)
        self.sentence_row_y = row * row_height
        for n, lex_node in enumerate(self.lexicon.values()):
            lex_node.connect_lex_parts()
        if self.route_mode:
            self.draw_sentence_circle()
        else:
            self.draw_sentence_row()
        self.update_canvas()

    def draw_sentence_row(self):
        y_shift = 0
        for n, lex_node in enumerate(self.lexicon.values()):
            x = WIDTH / (len(self.lexicon) + 1) * (n + 1)
            y = self.sentence_row_y + y_shift
            y_shift += 20
            if y_shift > 60:
                y_shift = 0
            lex_node.set_pos(x, y)

    def draw_sentence_circle(self):
        for n, lex_node in enumerate(self.lexicon.values()):
            pi_step = (math.pi * 2 / len(self.lexicon)) * n + math.pi / 2
            x = (math.cos(pi_step) * (WIDTH / -2 * 0.8)) + WIDTH / 2
            y = (math.sin(pi_step) * (HEIGHT / 2 * 0.8)) + HEIGHT / 2 + HEIGHT / 20
            lex_node.set_pos(x, y)

    def build(self):
        self.sentences = [row.strip() for row in open(SENTENCES_PATH).readlines()
                          if row.strip() and not row.strip().startswith('#')]
        self.parse(self.sentences[self.current_sentence_index])

    def clear_activations(self):
        for node in self.nodes.values():
            node.activations = {}
            node.active = False
        for edge in self.edges.values():
            edge.activations = {}

    def show_current_routes(self):
        c = 0
        for word_part in self.signaler.word_parts:
            indent = ' ' * word_part.signal
            print(f'{indent}*** routes down from {word_part}: ({len(word_part.li.routes_down)})')
            for route in word_part.li.routes_down:
                c += 1
                if route.wp is not word_part:
                    continue
                print(f'{indent}{route.print_route()} {route.rs.low}-{route.rs.high}, '
                      f'movers: {route.rs.movers} used:{route.rs.used_movers} w:{route.weight}, order:{route.order}')
        print('routes total at this point: ', c)

    def pick_optimal_route(self):
        total_routes = 0
        good_routes = []
        for word_part in self.signaler.word_parts:
            indent = ' ' * word_part.signal
            print(f'{indent}*** routes down from {word_part}: ({len(word_part.li.routes_down)})')
            for route in word_part.li.routes_down:
                if route.wp is not word_part:
                    continue
                total_routes += 1
                print(f'{indent} {route.print_route()} {route.rs.low}-{route.rs.high}, '
                      f'{route.rs.movers} wp: {route.wp}, len: {len(route)}, '
                      f'signals: {len({wp.signal for wp in route.wps})}, '
                      f'used_movers: {route.rs.used_movers}, weight: {route.weight}, order: {route.order}')

                if len(route) == len(self.signaler.word_parts) and not route.rs.movers:
                    if route not in good_routes:
                        good_routes.append(route)
                    print(route.tree())

            print(f'{indent} routes len: {len(word_part.li.routes_down)}')

        if good_routes:
            good_route_strs = []
            good_routes.sort(key=attrgetter('size', 'weight'), reverse=True)
            for route in good_routes:
                good_route = route.tree()
                good_route_strs.append(good_route)
                good_route_strs.append("")
                print(route, route.rs, route.weight, route.order)

            if self.send(json.dumps(good_route_strs)):
                print(f'sent {len(good_routes)} good routes to kataja')
            else:
                print(f'found {len(good_routes)} good routes')
        print('total routes: ', total_routes)

    def add_route_edge(self, start, end, origin):
        if not RouteEdge.exists(start, end, origin):
            edge = RouteEdge(start, end, origin)
            if edge not in end.li.route_edges:
                end.li.route_edges.append(edge)


class NetworkApp(App):
    def build(self):
        g = Network()
        ctrl.post_initialize(g)
        g.build()
        return g


if __name__ == '__main__':
    NetworkApp().run()

