from enum import Enum
from ctrl import ctrl

class Relation(Enum):
    SIGNAL = 0
    PART = 1
    ARG = 2
    ADJUNCT = 3


def includes(route, part):
    if not route:
        return False
    if part is route['ITEM']:
        return True
    if 'PART' in route and includes(route['PART'], part):
        return True
    if 'ARG' in route and includes(route['ARG'], part):
        return True
    if 'ADJUNCT' in route:
        adjunct = route['ADJUNCT']
        if isinstance(adjunct, list):
            if any(includes(adj, part) for adj in adjunct):
                return True
        else:
            if includes(adjunct, part):
                return True
    return False


def collect_signals(route, signals=None):
    if not signals:
        signals = set()
    if isinstance(route, list):
        for item in route:
            collect_signals(item, signals)
    else:
        for key, value in route.items():
            if key == 'ITEM':
                signals.add(value.signal)
            else:
                collect_signals(value, signals)
    # print('signals in route: ', route, signals)
    return signals


def collect_signals_and_movers(route, movers=None, signals=None, at_arg=False):
    if signals is None:
        signals = set()
    if movers is None:
        movers = set()
    if isinstance(route, list):
        for item in route:
            collect_signals_and_movers(item, movers, signals, False)
    else:
        for key, value in route.items():
            if key == 'ITEM':
                if not (at_arg and value.li.is_free_to_move()):
                    signals.add(value.signal)
                else:
                    movers.add(value.signal)
            elif key == 'ARG':
                collect_signals_and_movers(value, movers, signals, True)
            else:
                collect_signals_and_movers(value, movers, signals, False)
    return movers, signals


def print_route(route):
    if not route:
        return ''
    this = route['ITEM']
    if 'ADJUNCT' in route:
        adjuncts = route['ADJUNCT']
        if not isinstance(adjuncts, list):
            adjuncts = [adjuncts]
        for adjunct in adjuncts:
            if route['ITEM'].signal < adjunct['ITEM'].signal:
                this = f"({this}+{print_route(adjunct)})"
            else:
                this = f"({print_route(adjunct)}+{this})"
    if 'ARG' in route:
        if route['ITEM'].signal < route['ARG']['ITEM'].signal and not route['ITEM'].li.is_free_to_move():
            this = f"({this}<-{print_route(route['ARG'])})"
        else:
            this = f"({print_route(route['ARG'])}->{this})"
    if 'PART' in route:
        this = f"{this}.{print_route(route['PART'])}"
    return this


def tree(route):
    def joined(listlike):
        return '-'.join(str(l) for l in listlike)

    def _build_label(adjunct):
        item = adjunct['ITEM']
        more_adjuncts = adjunct.get('ADJUNCT', None)
        a_label = [item.signal]
        if more_adjuncts:
            adjunct_labels = _build_label(more_adjuncts)
            return a_label + adjunct_labels if item.signal < more_adjuncts['ITEM'].signal else adjunct_labels + a_label
        return a_label

    label = [route['ITEM'].signal]
    this = str(route['ITEM'])
    if 'PART' in route:
        this = f"[.{joined(label + list(collect_signals(route['PART'])))} {route['ITEM']}" \
               f" {tree(route['PART'])}]"
    if 'ADJUNCT' in route:
        adjuncts = route['ADJUNCT']
        if not isinstance(adjuncts, list):
            adjuncts = [adjuncts]
        for adjunct in adjuncts:
            if route['ITEM'].signal < adjunct['ITEM'].signal:
                label += _build_label(adjunct)
                this = f"[.{joined(label)} {this} {tree(adjunct)}]"
            else:
                label = _build_label(adjunct) + label
                this = f"[.{joined(label)} {tree(adjunct)} {this}]"
    if 'ARG' in route:
        if route['ITEM'].signal < route['ARG']['ITEM'].signal:
            if route['ITEM'].li.is_free_to_move():
                print('free to move case here:', collect_signals(route['ARG']), route['ITEM'], route['ARG']['ITEM'])
                return f"[.{joined(collect_signals(route))} {tree(route['ARG'])} {this}]"
            return f"[.{joined(collect_signals(route))} {this} {tree(route['ARG'])}]"
        else:
            print('ARG goes left: ', collect_signals(route['ARG']), route['ITEM'], route['ARG']['ITEM'],
                  collect_signals(route))
            return f"[.{joined(collect_signals(route))} {tree(route['ARG'])} {this}]"
    if 'PART' not in route and 'ADJUNCT' not in route:
        return str(route['ITEM'])
    else:
        return this

def tree_o(route):
    def _build_label(adjunct):
        item = adjunct['ITEM']
        more_adjuncts = adjunct.get('ADJUNCT', None)
        a_label = str(item)
        if more_adjuncts:
            if item.signal < more_adjuncts['ITEM'].signal:
                return f'({a_label}+{_build_label(more_adjuncts)})'
            return f'({_build_label(more_adjuncts)}+{a_label})'
        return a_label

    label = str(route['ITEM'])
    this = label
    if 'PART' in route:
        this = f"[.{label} {route['ITEM']} {tree(route['PART'])}]"
    if 'ADJUNCT' in route:
        adjuncts = route['ADJUNCT']
        if not isinstance(adjuncts, list):
            adjuncts = [adjuncts]
        for adjunct in adjuncts:
            if route['ITEM'].signal < adjunct['ITEM'].signal:
                label = f"{label}+{_build_label(adjunct)}"
                this = f"[.{label} {this} {tree(adjunct)}]"
            else:
                label = f"{_build_label(adjunct)}+{label}"
                this = f"[.{label} {tree(adjunct)} {this}]"
    if 'ARG' in route:
        if route['ITEM'].signal < route['ARG']['ITEM'].signal and not route['ITEM'].li.is_free_to_move():
            return f"[.{label} {this} {tree(route['ARG'])}]"
        else:
            return f"[.{label} {tree(route['ARG'])} {this}]"
    else:
        return this


def collect_arg_signals(route):
    signals = set()

    def _collect_arg_signals(route, arg):
        if isinstance(route, list):
            for item in route:
                _collect_arg_signals(item, arg)
        else:
            for key, value in route.items():
                if key == 'ITEM':
                    if arg:
                        signals.add(value.signal)
                elif key == 'ARG':
                    _collect_arg_signals(value, True)
                else:
                    _collect_arg_signals(value, False)
    _collect_arg_signals(route, False)
    return signals


def routes_overlap(route, other_route, route_signals=None):
    def same_adjuncts(adjuncts, other_adjuncts):
        a_set = {adj['ITEM'] for adj in adjuncts} if isinstance(adjuncts, list) else {adjuncts['ITEM']}
        b_set = {adj['ITEM'] for adj in other_adjuncts} if isinstance(other_adjuncts, list) else {other_adjuncts['ITEM']}
        return a_set & b_set

    if not other_route:
        return False
    if (('ARG' in route and 'ARG' in other_route) or
       ('PART' in route and 'PART' in other_route) or
       ('ADJUNCT' in route and 'ADJUNCT' in other_route and same_adjuncts(route['ADJUNCT'], other_route['ADJUNCT']))):
        #print('       routes overlap: two elements fill the same role')
        return True
    if not route_signals:
        route_signals = collect_arg_signals(route)
    #route_signals.add(route['ITEM'].signal)
    return route_signals & collect_arg_signals(other_route)


def check_that_no_duplicates(route):
    def collect_signals(route_part):
        if isinstance(route_part, list):
            for rp in route_part:
                collect_signals(rp)
            return
        signal = route_part['ITEM'].signal
        if signal in signals:
            print('found signal twice: ', route_part['ITEM'])
            #raise hell
        signals.add(route_part['ITEM'].signal)
        if 'ARG' in route_part:
            collect_signals(route_part['ARG'])
        if 'ADJ' in route_part:
            collect_signals(route_part['ADJ'])
        if 'PART' in route_part:
            collect_signals(route_part['PART'])
    signals = set()
    collect_signals(route)


class WordPart:
    def __init__(self, li, signal):
        self.li = li
        self.signal = signal

    def __str__(self):
        return f'{self.li.id}-{self.signal}'

    def __repr__(self):
        return str(self)

    def __eq__(self, other):
        return isinstance(other, WordPart) and (self.signal == other.signal)

    def __hash__(self):
        return hash((self.li.id, self.signal))

    def are_neighbors(self, route, other, other_route, consider_movers=True):
        movers, signals = collect_signals_and_movers(route)
        other_movers, other_signals = collect_signals_and_movers(other_route)
        if not other_signals:
            return True
        if (signals | movers) & (other_signals | other_movers):
            return False
        print('are neighbors? ', self, movers, signals, other, other_movers, other_signals)
        if other_route['ITEM'].lex_part_signals() & (signals | movers):
            #print('reject because neighbors are part of same word')
            return False
        # print(self.is_free_to_move_in_route(route), other.is_free_to_move_in_route(other_route))
        if self.li.is_free_to_move():
            if self.signal < other.signal:
                #print(f'   "{self}" (self) is free to move in route {route}')
                return True
            else:
                return False
        if other.li.is_free_to_move():
            if self.signal > other.signal:
                #print(f'   "{other}" (other) is free to move in route {other_route}')
                return True
            else:
                return False
        if self.signal < other.signal:
            extended_signals = signals | other_movers
            extended_signals.add(max(extended_signals) + 1)
        else:
            extended_signals = signals | movers
            extended_signals.add(min(extended_signals) - 1)
        print('      extended signals: ', extended_signals, '  overlap: ', extended_signals & other_signals)
        return extended_signals & other_signals

    def is_free_to_move_in_route(self, route):
        #print(f'is "{self}" free to move in route {route}?')
        pass

    def lex_part_signals(self):
        lex_part_index = self.li.lex_parts.index(self.li)
        return {i for i in range(self.signal - lex_part_index, self.signal)}

    def mover_signals(self):
        signals = set()
        lex_part_index = self.li.lex_parts.index(self.li)
        if lex_part_index + 1 == len(self.li.lex_parts):
            return signals
        for i, lex_part in enumerate(self.li.lex_parts[self.li.lex_parts.index(self.li) + 1:]):
            if lex_part.is_free_to_move():
                signals.add(self.signal + i)
            else:
                return signals
        return signals

    def add_route_edges(self, route):
        def collect_origins(route, prev_items):
            if 'ARG' in route:
                prev_items.add(route['ARG']['ITEM'])
                collect_origins(route['ARG'], prev_items)
            if 'ADJUNCT' in route:
                adjunct = route['ADJUNCT']
                if isinstance(adjunct, list):
                    for adj in adjunct:
                        prev_items.add(adj['ITEM'])
                        collect_origins(adj, prev_items)
                else:
                    prev_items.add(adjunct['ITEM'])
                    collect_origins(adjunct, prev_items)
            if 'PART' in route:
                prev_items.add(route['PART']['ITEM'])
                collect_origins(route['PART'], prev_items)
            return prev_items

        if 'ARG' in route:
            origins = collect_origins(route['ARG'], {route['ARG']['ITEM']})
            for origin in origins:
                ctrl.g.add_route_edge(route['ARG']['ITEM'], self, origin)

        if 'ADJUNCT' in route:
            adjunct = route['ADJUNCT']
            if isinstance(adjunct, list):
                for adj in adjunct:
                    origins = collect_origins(adj, {adj['ITEM']})
                    for origin in origins:
                        ctrl.g.add_route_edge(adj['ITEM'], self, origin)
            else:
                origins = collect_origins(adjunct, {adjunct['ITEM']})
                for origin in origins:
                    ctrl.g.add_route_edge(adjunct['ITEM'], self, origin)
        if 'PART' in route:
            origins = collect_origins(route['PART'], {route['PART']['ITEM']})
            for origin in origins:
                ctrl.g.add_route_edge(route['PART']['ITEM'], self, origin)

    # {'ITEM': admires-2, 'ARG': {'ITEM': Pekka-1}, 'PART': {'ITEM': admires'-3, 'ARG': {'ITEM': Merja-4}}}
    def add_new_route(self, route, other_route, wp_list):
        def bySignal(adj):
            return adj['ITEM'].signal

        route_signals = collect_arg_signals(route)
        if routes_overlap(route, other_route, route_signals):
            #print('  routes overlap: ', route, other_route)
            return
        assert not other_route or (route['ITEM'] == other_route['ITEM'])
        new_combination = route | other_route
        if other_route and 'ADJUNCT' in other_route and 'ADJUNCT' in route:
            adjunct = route['ADJUNCT']
            adjunct = adjunct if isinstance(adjunct, list) else [adjunct]
            other_adjunct = other_route['ADJUNCT']
            other_adjunct = other_adjunct if isinstance(other_adjunct, list) else [other_adjunct]
            new_adjuncts = adjunct + other_adjunct
            new_adjuncts.sort(key=bySignal)
            new_combination['ADJUNCT'] = new_adjuncts
        if new_combination not in self.li.routes_down:
            print('  add_new_route: ', route)
            print('                 ', other_route)
            print('              => ', route | other_route)
            print(f'    new combination for {self}: {print_route(new_combination)}')
            print(f'      based on {print_route(route)} and {print_route(other_route)}')
            self.add_route_edges(new_combination)
            check_that_no_duplicates(new_combination)
            self.li.routes_down.append(new_combination)

        self.walk_all_routes_up(new_combination, wp_list)

    def walk_all_routes_up(self, route, wp_list):

        # Palataan siihen intuitioon että reitit ovat haarautumattomia matoja pohjalta ylös, ja reitit ovat
        # yhdistettävissä jos ne ovat keskenään ristiriidattomia. Jos reitti on vaikka ABCDEF ja toinen reitti ABCDEG
        # (alku on reitin yläpää, eli tuo kuvaisi rakennelmaa jonka pääsana on A), niin haluamme että tehdessä
        # reittiä ABCDEG ei tarvitsisi tehdä uudestaan reittiä ABCDE, koska kohdassa E se olisi jo tunnettu
        # tuosta aiemmasta ABCDEF -reitistä.

        # Kun reittiä aloitetaan pohjalta, alimmaisen olion reitti on tyhjä. Seuraava askel saa argumentiksi
        # tähänastisen reitin. Ensimmäisen askeleen jälkeen se on olio ja yhteys joka näitä yhdisti.

        # Selkeyden vuoksi yritetään pitää nyt erillään reitin luominen ja reittien yhdistäminen.
        print('walking all routes up from ', self, ' with route ', print_route(route))

        if route not in self.li.routes_down:
            print('adding simple route: ', print_route(route))
            check_that_no_duplicates(route)
            self.li.routes_down.append(route)

        for edge in self.li.adjunctions:
            if edge.start == self:
                continue
            other = edge.start
            for other_route in other.li.routes_down or [{}]:
                if self.are_neighbors(route, other, other_route):
                    print(f'  <-> adj route from {other} to {edge.end} in context of {print_route(other_route)}')
                    other.add_new_route({'ITEM': other, Relation.ADJUNCT.name: route}, other_route, wp_list)

        for edge in self.li.head_edges:
            # pitäisi todeta että edge.head:n hallitsema alue ulottuu self:n hallitseman alueen naapuriksi.
            # route pitäisi ymmärtää laajemmin, niin että se kattaa myös yhdistelmät
            for other_route in edge.head.li.routes_down or [{}]:
                if not includes(route, edge.head) and route['ITEM'].signal not in collect_arg_signals(route):
                    if self.are_neighbors(route, edge.head, other_route):
                        print(f'  -> arg route from {route["ITEM"]} to {edge.head} in context of '
                              f'{print_route(other_route)}')
                        edge.head.add_new_route({'ITEM': edge.head, Relation.ARG.name: route}, other_route, wp_list)

        is_later_part = self.li.lex_parts.index(self.li)
        if is_later_part:
            wp = wp_list.word_parts[self.signal - 2]  # this is previous word part as signals start at 1
            this_moves = self.li.is_free_to_move()
            other_moves = wp.li.is_free_to_move()
            # liikkujakaan ei voi olla rakenteessa kuin kerran, joten ei laiteta sitä PART-suhteella
            # alkuperäiselle paikalleen
            if (this_moves and other_moves) or not (this_moves or other_moves) and not includes(route, wp):
                for other_route in wp.li.routes_down or [{}]:
                    print(f'  . part route from {print_route(route)} to {wp} in context of {print_route(other_route)}')
                    wp.add_new_route({'ITEM': wp, Relation.PART.name: route}, other_route, wp_list)

        # 25.10. 2022
        # nyt jos reitit on luotu niin miten esitetään reittien yhdistäminen? Tämä olisi jonkinlainen
        # permutaatio-ongelma.
        # AB
        # ACD
        # ACE
        #
        #  /B
        # A  /D
        #  \C
        #    \E
        # Pitäisi olla yksi lähtönoodi josta voi käydä kaikissa noodeissa joutumatta käymään missään kahdesti.
        # Tässä se summausnäkökulma oli että kussakin välinoodissa voi esittää permutaatiot siihen saapuneista
        # ristiriidattomista oksista. Se olisi eri joukko kuin routes_down, mutta se olisi aina isompi joukko kuin
        # routes_down. Jokainen reitti kuuluu siihen, mutta myös reittien ristiriitaiset yhdistelmät. Ne voisi kuvata
        # joukkoina. Oletetaan reitit:
        # ['ARG', Pekka-1]
        # ['PART', admires'-3]
        # ['PART', admires'-3, 'ARG', Pekka-1]
        # ['ARG', Merja-4]
        # ['PART', admires'-3, 'ARG', Merja-4]
        # Näiden permutaatiot olisivat näiden itsensä muodostamien yhden kokoisten joukkojen lisäksi:
        # 1. { ['ARG', Pekka-1], ['PART', admires'-3] }
        # 2. { ['ARG', Pekka-1], ['PART', admires'-3, 'ARG', Merja-4] }
        # 3. { ['ARG', Merja-4], ['PART', admires'-3] }
        # 4. { ['ARG', Merja-4], ['PART', admires'-3, 'ARG', Pekka-1] }
        # Näistä (2) ja (4) ovat hyviä koska ne kattavat kaikki 4 elementtiä. Pitäisi osoittaa myös että (2) on parempi
        # kuin (4). Olin jo päässyt siihen toteamukseen että yksittäisen mergen kautta ei voi vielä päätellä onko
        # tämä hyvä naapurusten välinen merge vai epäilyttävä etäisempi merge. Sen pystyy tekemään vain
        # derivaatiossa kun tietää mitkä elementit ovat päätyneet toistensa naapuriksi yhdistämällä välissä olevia
        # elementtejä itseensä. Tapauksessa 2 palaset ovat suoraviivaisesti toistensa naapureita. Tapauksessa 4 voi
        # rakentaa vaikeuksia sillä perusteella, että admires'-3 ja Pekka-1 ovat huonoja
        # naapureita koska niiden välissä oleva elementti admires-2 on admires'-3:n pää, joten admires'-3 ei hallitse
        # sen ja kohteen välissä olevia elementtejä. Onko se ongelma heti olemassa kun admires'3 yrittää yhteyttä
        # Pekka-1:een? On ainakin sitä myötä että PART-relaatio on pakollinen.
        #
        # 26.10.2022
        # Päästiin eilen siihen ajatukseen, mutta ei vielä toteutukseen, että permutaatiot on sittenkin parempi
        # laskea samalla kun reitit. Kahden elementin naapuruus ei perustu ainoastaan elementin lapsiin tietyllä
        # reitillä, vaan siinä voi olla myös toisen reitin lapsia. Yksinkertaisena esimerkkinä 'Pekka ihailee Merjaa'
        # koostuisi kahdesta reitistä joissa toisessa Pekka->ihailee ja toisessa ihailee.ihailee'<-Merjaa. Sitten jos
        # olisi kysyttävä olisiko tuota palasta edeltävä tai seuraava sana sen naapuri, pitäisi voida katsoa
        # molempia. Eli ei katsota molempia erikseen vaan katsotaan yhdistelmää.
        #
        # Mitä tuo walk_all_routes_up tarkoittaa suhteessa permutaatioihin?
        #
        # 6.11.2022
        # On ihan hyvä reitinmuodostus nyt. Seuraava haaste on adjunktit.


class WordPartList:
    def __init__(self, words, lexicon):
        self.original = words
        self.words_left = list(reversed(words))
        self.lexicon = lexicon
        self.word_parts = []
        self.current_item = None
        self.prev_items = []
        self.closest_item = None
        self.signal_count = sum([len(self.lexicon.get(x).lex_parts) for x in self.original])

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
        #self.closest_item = self.current_item
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

    def is_last(self):
        return self.current_item and (not self.words_left) and self.current_item.li.lex_parts[-1] is \
               self.current_item.li

    def can_merge(self):
        return self.prev_items and self.current_item

    def collect_previous_items(self):
        if len(self.word_parts) < 2:
            return []
        #current_parts = self.word_parts[-1].li.lex_parts or [self.word_parts[-1].li]
        #return [part for part in self.word_parts if part.li not in current_parts]
        return self.word_parts[:-1]
