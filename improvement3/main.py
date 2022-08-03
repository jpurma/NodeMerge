from enum import Enum

from kivy.app import App
from kivy.uix.button import Button
from kivy.uix.widget import Widget
from kivy.core.window import Window
from nodes import *
from word_parts import WordPart, WordPartList

N_SIZE = 3
WIDTH = 1600
HEIGHT = 1024
LEXICON_PATH = 'lexicon.txt'
SENTENCES_PATH = 'sentences.txt'
SHOW_FULL_LEXICON = False


class Relation(Enum):
    SIGNAL = 0
    HEAD = 1
    PART = 2
    ADJUNCT = 3


class RouteSignal:
    def __init__(self, source=None, target=None, relation=Relation.SIGNAL, signal=None, word=''):
        self.source = source
        self.target = target
        self.relation = relation
        self.word = word
        self.signal = signal
        if source and target:
            assert not source.signals() & target.signals()

    def __contains__(self, item):
        if self.signal:
            return item == self.signal
        if self.target:
            if item == self.target:
                return True
            if item in self.target:
                return True
        if self.source:
            if item == self.source:
                return True
            if item in self.source:
                return True
        return False

    def __eq__(self, other):
        if not isinstance(other, RouteSignal):
            return self.signal == other
        return self.relation == other.relation and self.signal == other.signal and self.target == other.target and \
            self.source == other.source

    def __str__(self):
        if self.signal:
            return str(self.signal)
        if self.relation == Relation.HEAD:
            return f'({self.source}->{self.target})'
        elif self.relation == Relation.PART:
            return f'{self.source}.{self.target}'
        elif self.relation == Relation.ADJUNCT:
            return f'{self.source}=={self.target}'

    def __repr__(self):
        return str(self)

    def __lt__(self, other):
        head = self.find_head()
        if isinstance(other, RouteSignal):
            return head.signal < other.find_head().signal
        return head.signal < other

    def __gt__(self, other):
        head = self.find_head()
        if isinstance(other, RouteSignal):
            return head.signal > other.find_head().signal
        return head.signal > other

    def find_head(self):
        if self.target:
            return self.target.find_head()
        return self

    def head_first(self):
        if not self.source:
            return True
        if self.target and self.source:
            return self.target < self.source

    def words(self):
        if self.word:
            return self.word
        target_words = self.target.words()
        source_words = self.source.words()
        if head_first := self.head_first():
            first = target_words
            second = source_words
        else:
            first = source_words
            second = target_words
        if self.relation == Relation.HEAD:
            return f'({first}<-{second})' if head_first else f'({first}->{second})'
        elif self.relation == Relation.PART:
            return f'{first}.{second}' if head_first else f'{first}.{second}'
        elif self.relation == Relation.ADJUNCT:
            return f'{first}<=={second}' if head_first else f'{first}==>{second}'

    def find_label(self):
        if self.word:
            return self.word
        if self.relation == Relation.ADJUNCT:
            if self.head_first():
                return f'{self.target.find_label()}+{self.source.find_label()}'
            else:
                return f'{self.source.find_label()}+{self.target.find_label()}'
        elif self.target:
            return self.target.find_label()

    def tree(self):
        if self.word:
            return self.word
        target_tree = self.target.tree()
        source_tree = self.source.tree()
        label = self.find_label()
        if self.head_first():
            return f'[.{label} {target_tree} {source_tree}]'
        return f'[.{label} {source_tree} {target_tree}]'

    def coverage(self):
        return len(self.signals())

    def signals(self):
        if self.relation == Relation.SIGNAL:
            return {self.signal}
        return self.target.signals() | self.source.signals()

    def signals_in_order(self):
        if self.relation == Relation.SIGNAL:
            return [self.signal]
        return self.target.signals_in_order() + self.source.signals_in_order()

    def cost(self):
        if self.relation == Relation.SIGNAL:
            return 0
        target = self.target.find_head().signal  # min(self.target.signals())
        source = self.source.find_head().signal
        min_edge = min(self.source.signals())
        max_edge = max(self.source.signals())
        cost = min(abs(target - source), abs(target - min_edge), abs(target - max_edge)) - 1
        #print(target, source, min_edge, max_edge, cost)
        cost += (abs(self.source.find_head().signal - self.target.find_head().signal) - 1) / 10.0
        return cost + self.target.cost() + self.source.cost()

    def compatible_with(self, other):
        return not self.signals() & other.signals()


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
        keyboard = Window.request_keyboard(self.handle_keyup, self)
        keyboard.bind(on_key_up=self.handle_keyup)

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
            self.activate_current_words()
        if self.words.is_last():
            self.compute_minimal_route()
        self.update_canvas()

    def next_sentence(self):
        self.current_sentence_index += 1
        if self.current_sentence_index == len(self.sentences):
            self.current_sentence_index = 0
        self._reset_sentence()

    def prev_sentence(self):
        self.current_sentence_index -= 1
        if self.current_sentence_index < 0 :
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
        self.words = WordPartList(sentence.split(), self.lexicon)
        self.words.pick_first()
        self.update_sentence()

    def draw_grammar(self):
        row = 1
        row_height = HEIGHT / 5
        self.merge = self.add(SymmetricMergeNode, 'M(A<?>B)')  # A→B
        self.merge.set_pos(WIDTH / 2 - 256, row * row_height)
        self.merge_pair = self.add(SymmetricPairMergeNode, 'M(A<->B)')
        self.merge_pair.set_pos(WIDTH / 2 + 256, row * row_height)
        self.merge_ok = self.add(MergeOkNode, 'OK')
        self.merge_ok.set_pos(100, HEIGHT / 2)

        row += 2
        for n, cat_node in enumerate(self.categories):
            cat_node.set_pos(WIDTH / (len(self.categories) + 1) * (n + 1), row * row_height)
        self.merge.connect(self.merge_ok)
        self.merge_pair.connect(self.merge_ok)
        row += 1
        y_shift = -100
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

    def activate_current_words(self):
        lefts = list(reversed(self.words.prev_items))
        #closest = self.words.closest_item
        right = self.words.current_item
        right.li.activate(right.signal)
        #closest.li.activate(closest.signal)
        for left in reversed(lefts):
            left.li.activate(left.signal)
        print(f'*** activate {lefts}+{right}')
        self.update_canvas()


    def compute_minimal_route(self):
        """ mitenkäs etsitään täydellinen, mutta ekonomisin reitti jos tarjotut yhteydet ovat

        1. sanoin <> 3
        2. että -> 1
        3. kiihkeästi <> 1, <> 5
        4. Pekka -> 5
        5. ihailee -> 2, <> 3
        6. Merjaa -> 5, -> 1
        
        Jotenkin pitäisi olla selvä että 1<>3 on huonompi suhde kuin 3<>5. 2:ssa alkaa jotain joka keskeytyy jos 3 on
        osa 1:tä. 
        
        Tiedän että paras reitti olisi 1<-2 3 4->5((<>3)->2)<-6
        
        Etäisyys elementin ja toisen elementin välillä on etäisyys elementin ja toisen elementin lähimmän sen 
        hallitseman lapsen välillä. Eli jos on [.A A B] C  niin etäisyys A:n ja C:n välillä on 1, koska B on A:n 
        hallitsema ja B:n ja C:n välinen etäisyys on 1.  
        """

        def get_previous_part(wp):
            if wp.li.lex_parts and (part_index := wp.li.lex_parts.index(wp.li)):
                return WordPart(wp.li.lex_parts[part_index - 1], wp.signal - 1)

        def fetch_real_word_part(_wp_signal):
            return self.words.word_parts[_wp_signal - 1]

        def _is_part_of_route(signal, route):
            if not route:
                return False
            return signal in route

        def _walk_all_routes_up_from(relation, source=None, target_signal=None):
            # muistetaan se metafora että kulkiessaan reittiä ylös muurahaiset kirjoittavat noodiin mistä tulivat,
            # tähänastisen reittinsä. Jos wp:lle kirjoitetaan monia pitkiä reittejä, se saattaa tarkoittaa että tämä on
            # koko lauseen pääsana.

            # Reitin pohjimmainen jäsen kertoo siis sen, mistä reitti sai alkunsa -- jostakin argumentista.
            # Reitin viimeinen jäsen on se sana minne tämä reitti päädytään kirjoittamaan.
            #
            # Jos reitti jatkaa jo olemassaolevaa reittiä kyse on tilanteesta jossa esim. sanojen 1 ja 2 jälkeen
            # reittiä ei voitu tehdä pitemmälle, mutta kun tuli sana 4 niin se mahdollisti uuden pitemmän reitin ja
            # nyt se [1, 2] korvataan sillä uudella.
            #
            # Hm, ylläoleva ei oikein toimi ajatuksena. Kun reitti aina päättyy nykyiseen wp:hen, niin ei voi olla
            # tällä wp:llä toista reittiä joka olisi sisältynyt uuteen reittiin: vanha: [...x, wp] ja uusi: [...x, y,
            # wp]
            #
            # Taitaa olla että reitin jatkamiseen liittyvä vertailu tehtiin vain väärinpäin, unohtui tuo metafora
            # joka piti muistaa. Reitti kun esitetään listana, jossa viimeinen elementti on tämä
            # tämänhetkinen wp ja jos reittiä jatketaan, sitä pitäisi jatkaa listan alusta. Käännetäänpä vertailu.

            # J: Jos olemme argumentissa A niin säilötäänkö tänne reitteihin reitit tästä eteenpäin vai reitit tänne?
            # K: Reitit tänne.
            # target on aina yksinkertainen signaali, source voi olla
            # J: jos on kaksi instanssia samasta sanasta, niin miten erotetaan kumman reittejä jatketaan?

            # siinä kohtaa kun li:lle lisätään uusi reitti olisi mahdollisuus vertailla onko uusi reitti yhteensopiva
            # vanhojen kanssa ja luoda mahdolliset yhdistelmät.

            wp = fetch_real_word_part(target_signal)
            target_rs = RouteSignal(relation=Relation.SIGNAL, word=wp.li.word, signal=target_signal)
            if relation == Relation.SIGNAL:
                rs = target_rs
            else:
                rs = RouteSignal(source=source, target=target_rs, relation=relation)
                assert not source.signals() & target_rs.signals()
            new_routes = []
            if rs not in wp.li.routes_up:
                new_routes.append(rs)
            if relation == Relation.ADJUNCT:
                print('at adjunct ', rs, ' it has source: ', rs.source, ' and target: ', rs.target)
                other_wp = fetch_real_word_part(rs.source.find_head().signal)
                if rs not in other_wp.li.routes_up:
                    other_wp.li.routes_up.append(rs)
                    print('sharing adjunct to source head: ', rs.source.find_head(), other_wp.li.routes_up)
            if source:
                # jos on vaikka 4->3 ja ..2.3 niin pitäisi olla mahdollista yhdistää ne reitiksi 2.(4->3)
                # samaten jos on 4->3 ja 2==3 niin pitäisi tulla myös (4->2==3)
                # muut yhdistelmät ovat mielettömiä.
                #
                # Mutta sen jälkeen pitäisi voida nähdä (4->2==3) niin, että sen pää on 3 tai 2. Nyt bugittaa kun
                # jatkaa vain tapauksista joissa pää on 2.
                for old_rs in wp.li.routes_up:
                    #print('checking old rs ', old_rs, ' vs new rs ', rs)
                    if old_rs.relation == Relation.PART and rs.relation == Relation.HEAD and rs.compatible_with(
                            old_rs.source):
                        new_rs = RouteSignal(source=old_rs.source, target=rs, relation=old_rs.relation)
                        if new_rs not in wp.li.routes_up and new_rs not in new_routes:
                            print('case 1: adding queer part rs: ', new_rs, 'merging: ', old_rs, rs)
                            new_routes.append(new_rs)
                    elif rs.relation == Relation.PART and old_rs.relation == Relation.HEAD and old_rs.compatible_with(
                            rs.source):
                        new_rs = RouteSignal(source=rs.source, target=old_rs, relation=rs.relation)
                        if new_rs not in wp.li.routes_up and new_rs not in new_routes:
                            print('case 2: adding queer part rs: ', new_rs, 'merging: ', old_rs, rs)
                            new_routes.append(new_rs)
                    if old_rs.relation == Relation.ADJUNCT and rs.relation == Relation.HEAD and rs.compatible_with(
                            old_rs.source):
                        print('making rs with source ', old_rs.source, ' and target ', rs)
                        new_rs = RouteSignal(source=old_rs.source, target=rs, relation=old_rs.relation)
                        if new_rs not in wp.li.routes_up and new_rs not in new_routes:
                            print('case 3. adding queer adj rs: ', new_rs, 'merging: ', old_rs, rs)
                            new_routes.append(new_rs)
                    elif rs.relation == Relation.ADJUNCT and old_rs.relation == Relation.HEAD and \
                            old_rs.compatible_with(rs.source):
                        new_rs = RouteSignal(source=rs.source, target=old_rs, relation=rs.relation)
                        if new_rs not in wp.li.routes_up and new_rs not in new_routes:
                            print('case 4: adding queer adj rs: ', new_rs, 'merging: ', old_rs, rs)
                            new_routes.append(new_rs)

            wp.li.routes_up += new_routes
            if new_routes:
                print(f'adding {len(new_routes)} new routes')
            for rs in new_routes:
                if rs.relation == Relation.ADJUNCT:
                    if wp.signal == rs.source.find_head().signal:
                        other_signal = rs.target.find_head().signal
                    else:
                        other_signal = rs.source.find_head().signal
                    print('would do adjunct, this: ', wp.signal, ', source head: ', rs.source.find_head().signal,
                          ' target head: ', rs.target.find_head().signal)
                    other_wp = fetch_real_word_part(other_signal)
                    print('continue routes ', rs, other_wp)
                    _continue_routes(rs, other_wp)
                _continue_routes(rs, wp)

        def _continue_routes(rs, wp):
            if prev_part := get_previous_part(wp):
                if not _is_part_of_route(prev_part.signal, rs):
                    _walk_all_routes_up_from(Relation.PART, source=rs, target_signal=prev_part.signal)

            for edge in wp.li.adjunctions:
                if edge.start == wp:
                    other_adjunct = edge.end
                    if not _is_part_of_route(other_adjunct.signal, rs):
                        assert not {other_adjunct.signal} & rs.signals()
                        print('doing adjunct,', rs, ' walking up target ', other_adjunct.signal, ' edge: ', edge)
                        _walk_all_routes_up_from(Relation.ADJUNCT, source=rs, target_signal=other_adjunct.signal)

            for edge in wp.li.head_edges:
                head = edge.end
                if not _is_part_of_route(head.signal, rs):
                    _walk_all_routes_up_from(Relation.HEAD, source=rs, target_signal=head.signal)

            #print('routes at ', wp.li, ' : ', wp.li.routes_up)
            #print('added route: ', rs)


        print('compute minimal route')
        for word_part in self.words.word_parts:
            print('assign routes_up=[] for ', word_part)
            word_part.li.routes_up = []

        for word_part in self.words.word_parts:
            print(f'*** {word_part.signal} ***')
            _walk_all_routes_up_from(Relation.SIGNAL, target_signal=word_part.signal)

        signals = {_wp.signal for _wp in self.words.word_parts}
        sortable = []
        for word_part in self.words.word_parts:
            print(f'ooo routes up to highest heads from {word_part}:')
            for route in word_part.li.routes_up:
                if route.coverage() == len(signals):
                    cost = route.cost()
                    sortable.append((cost, route))
                    print('  ', route)
                    print('    ', route.words())
                    print('    ', route.tree())
                    print(f'     coverage: {int(route.coverage() / len(signals) * 100)}% cost: {cost}')
                else:
                    print('  ', route.signals_in_order())
        sortable.sort()
        if sortable:
            route = sortable[0][1]
            print('***** best parse: ')
            print('  ', route)
            print('    ', route.words())
            print('    ', route.tree())
            print('    ', route.signals_in_order())
            print(f'     coverage: {int(route.coverage() / len(signals) * 100)}% cost: {route.cost()}')


class NetworkApp(App):
    def build(self):
        g = Network()
        ctrl.post_initialize(g)
        g.build()
        return g


if __name__ == '__main__':
    NetworkApp().run()
