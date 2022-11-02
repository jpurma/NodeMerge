from enum import Enum


class Relation(Enum):
    SIGNAL = 0
    PART = 1
    ARG = 2
    ADJUNCT = 3


def includes(route, part):
    if part is route['ITEM']:
        return True
    if 'PART' in route and includes(route['PART'], part):
        return True
    if 'ARG' in route and includes(route['ARG'], part):
        return True
    if 'ADJUNCT' in route and includes(route['ADJUNCT'], part):
        return True
    return False


def is_neighbor(signals, signal):
    if not signals:
        return True
    return signal == max(signals) + 1 or signal == min(signals) - 1


def collect_signals(route, signals=None):
    if not signals:
        signals = set()
    for key, value in route.items():
        if key == 'ITEM':
            signals.add(value.signal)
        else:
            collect_signals(value, signals)
    return signals


def tree(route):
    label = str(route['ITEM'])
    this = label
    if 'PART' in route:
        this = f"[.{label} {route['ITEM']} {tree(route['PART'])}]"
    if 'ADJ' in route:
        label = f"{label}+{route['ADJ']['ITEM']}"
        this = f"[.{label} {route['ITEM']} {tree(route['ADJ'])}]"

    if 'ARG' in route:
        if route['ITEM'].signal < route['ARG']['ITEM'].signal:
            return f"[.{label} {this} {tree(route['ARG'])}]"
        else:
            return f"[.{label} {tree(route['ARG'])} {this}]"
    else:
        return this


def collect_arg_signals(route):
    signals = set()

    def _collect_arg_signals(route, arg):
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
    if (('ARG' in route and 'ARG' in other_route) or
       ('PART' in route and 'PART' in other_route) or
       ('ADJUNCT' in route and 'ADJUNCT' in other_route)):
        return True
    if not route_signals:
        route_signals = collect_arg_signals(route)
    return route_signals & collect_arg_signals(other_route)


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

    def governed_area(self, complex_route):
        return collect_signals(complex_route)

    # {'ARG': [Pekka-1], 'PART': [admires'-3, {'ARG': Merja-4}]}

    # {'ITEM': admires-2, 'ARG': {'ITEM': Pekka-1}, 'PART': {'ITEM': admires'-3, 'ARG': {'ITEM': Merja-4}}}
    def add_new_route(self, route, wp_list):
        combinations = [route]
        print('added route: ', route)
        if route and route not in self.li.routes_down:
            route_signals = collect_arg_signals(route)
            for other_route in self.li.routes_down:
                if routes_overlap(route, other_route, route_signals):
                    continue
                new_combination = route | other_route
                print('new combination: ', new_combination)
                combinations.append(new_combination)
            for route_combo in combinations:
                if route_combo not in self.li.routes_down:
                    self.li.routes_down.append(route_combo)
                self.walk_all_routes_up(route_combo, wp_list)

    def walk_all_routes_up(self, route, wp_list):

        # Palataan siihen intuitioon että reitit ovat haarautumattomia matoja pohjalta ylös, ja reitit ovat
        # yhdistettävissä jos ne ovat keskenään ristiriidattomia. Jos reitti on vaikka ABCDEF ja toinen reitti ABCDEG
        # (alku on reitin yläpää, eli tuo kuvaisi rakennelmaa jonka pääsana on A), niin haluamme että tehdessä
        # reittiä ABCDEG ei tarvitsisi tehdä uudestaan reittiä ABCDE, koska kohdassa E se olisi jo tunnettu
        # tuosta aiemmasta ABCDEF -reitistä.

        # Kun reittiä aloitetaan pohjalta, alimmaisen olion reitti on tyhjä. Seuraava askel saa argumentiksi
        # tähänastisen reitin. Ensimmäisen askeleen jälkeen se on olio ja yhteys joka näitä yhdisti.

        # Selkeyden vuoksi yritetään pitää nyt erillään reitin luominen ja reittien yhdistäminen.

        lex_part_index = self.li.lex_parts.index(self.li)
        if lex_part_index and not self.li.is_free_to_move():
            wp = wp_list.word_parts[self.signal - 2]  # this is previous word part as signals start at 1
            if  not includes(route, wp):
                wp.add_new_route({'ITEM': wp, Relation.PART.name: route}, wp_list)

        for edge in self.li.head_edges:
            # pitäisi todeta että edge.head:n hallitsema alue ulottuu self:n hallitseman alueen naapuriksi.
            # route pitäisi ymmärtää laajemmin, niin että se kattaa myös yhdistelmät
            if edge.head.li.is_free_to_move() or self.li.is_free_to_move() or is_neighbor(
                    self.governed_area(route), edge.head.signal):
                if not includes(route, edge.head) and route['ITEM'].signal not in collect_arg_signals(route):
                    edge.head.add_new_route({'ITEM': edge.head, Relation.ARG.name: route}, wp_list)

        for edge in self.li.adjunctions:
            if is_neighbor(self.governed_area(route), edge.start.signal):
                if not includes(route, edge.start):
                    edge.start.add_new_route({'ITEM': edge.start, Relation.ADJUNCT.name: route}, wp_list)

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
        current_parts = self.word_parts[-1].li.lex_parts or [self.word_parts[-1].li]
        return [part for part in self.word_parts if part.li not in current_parts]
