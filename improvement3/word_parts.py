from ctrl import ctrl

SIGNAL_TREE = True

class Route:
    def __init__(self, wp, part=None, arg=None, adjuncts=None):
        self.wp = wp
        self.part = part
        self.arg = arg
        if isinstance(adjuncts, list):
            self.adjuncts = adjuncts
        else:
            self.adjuncts = [adjuncts] if adjuncts else []
        self.signals = {wp.signal}
        self.movers = {wp.signal} if self.wp.li.is_free_to_move() else set()
        self.arg_signals = set()
        if self.part:
            self.signals |= self.part.signals
            self.movers |= self.part.movers
            self.arg_signals |= self.part.arg_signals
        if self.arg:
            self.signals |= self.arg.signals
            if self.arg.can_move():
                self.movers |= self.arg.signals
                self.movers.add(self.wp.signal)
            self.arg_signals.add(self.arg.wp.signal)
            self.movers |= self.arg.movers
            self.arg_signals |= self.arg.arg_signals
        if self.adjuncts:
            for adjunct in self.adjuncts:
                self.signals |= adjunct.signals
                self.movers |= adjunct.movers
                self.arg_signals |= adjunct.arg_signals
        self.signals = set(sorted(list(self.signals)))

    def __eq__(self, other):
        if not isinstance(other, Route):
            return False
        return self.wp == other.wp and self.part == other.part and self.arg == other.arg and self.adjuncts == other.adjuncts

    @property
    def sg(self):
        return self.wp.signal

    def includes(self, part):
        if part is self.wp:
            return True
        if self.part and self.part.includes(part):
            return True
        if self.arg and self.arg.includes(part):
            return True
        if self.adjuncts:
            if any(adj.includes(part) for adj in self.adjuncts):
                return True
        return False

    def can_move(self):
        if self.wp.li.is_free_to_move():
            return True
        if self.arg and self.arg.can_move():
            return True
        for adj in self.adjuncts:
            if adj.can_move():
                return True

    def collect_arg_signals(self, arg_signals=None, at_arg=False):
        if arg_signals is None:
            arg_signals = set()

        if at_arg:
            arg_signals.add(self.wp.signal)
        if self.arg:
            self.arg.collect_arg_signals(arg_signals, at_arg=True)
        if self.part:
            self.part.collect_arg_signals(arg_signals)
        if self.adjuncts:
            for adjunct in self.adjuncts:
                adjunct.collect_arg_signals(arg_signals)
        return arg_signals

    def __str__(self):
        return self.print_route()

    def __repr__(self):
        return f'Route({self.print_route()})'

    def print_route(self, can_move=False):
        can_move = can_move or self.can_move()
        this = f'{self.wp.li.word}/{self.wp.signal}' if can_move else str(self.wp)
        if self.adjuncts:
            for adjunct in self.adjuncts:
                if self.wp.signal < adjunct.wp.signal:
                    this = f"({this}+{adjunct.print_route(can_move=can_move)})"
                else:
                    this = f"({adjunct.print_route(can_move=can_move)}+{this})"
        if self.arg:
            if self.wp.signal < self.arg.wp.signal and not self.wp.li.is_free_to_move():
                this = f"({this}<-{self.arg.print_route(can_move=can_move)})"
            else:
                this = f"({self.arg.print_route(can_move=can_move)}->{this})"
        if self.part:
            this = f"{this}.{self.part.print_route(can_move=can_move)}"
        return this

    def tree(self):
        if SIGNAL_TREE:
            return self.signal_tree()
        else:
            return self.label_tree()

    def signal_tree(self):
        def joined(listlike):
            return '-'.join(str(l) for l in listlike)

        def _build_label(adjunct):
            a_label = [adjunct.wp.signal]
            for other_adjunct in adjunct.adjuncts:
                adjunct_labels = _build_label(other_adjunct)
                if adjunct.wp.signal < other_adjunct.wp.signal:
                    a_label += adjunct_labels
                else:
                    a_label = adjunct_labels + a_label
            return a_label

        label = [self.wp.signal]
        this = str(self.wp)
        if self.part:
            this = f"[.{joined(label + list(self.part.signals))} {self.wp}" \
                   f" {self.part.signal_tree()}]"
        if self.adjuncts:
            for adjunct in self.adjuncts:
                if self.wp.signal < adjunct.wp.signal:
                    label += _build_label(adjunct)
                    this = f"[.{joined(label)} {this} {adjunct.signal_tree()}]"
                else:
                    label = _build_label(adjunct) + label
                    this = f"[.{joined(label)} {adjunct.signal_tree()} {this}]"
        if self.arg:
            if self.wp.signal < self.arg.wp.signal:
                if self.wp.li.is_free_to_move():
                    return f"[.{joined(self.signals)} {self.arg.signal_tree()} {this}]"
                return f"[.{joined(self.signals)} {this} {self.arg.signal_tree()}]"
            else:
                return f"[.{joined(self.signals)} {self.arg.signal_tree()} {this}]"
        if not (self.part or self.adjuncts):
            return str(self.wp)
        else:
            return this

    def label_tree(self):
        def _build_label(adjunct):
            a_label = [str(adjunct.wp)]
            for other_adjunct in adjunct.adjuncts:
                adjunct_labels = _build_label(other_adjunct)
                if adjunct.wp.signal < other_adjunct.wp.signal:
                    a_label += adjunct_labels
                else:
                    a_label = adjunct_labels + a_label
            return a_label

        label = str(self.wp)
        this = label
        if self.part:
            this = f"[.{label} {self.wp} {self.part.label_tree()}]"
        if self.adjuncts:
            for adjunct in self.adjuncts:
                if self.wp.signal < adjunct.wp.signal:
                    label = f"{label}+{_build_label(adjunct)}"
                    this = f"[.{label} {this} {adjunct.label_tree()}]"
                else:
                    label = f"{_build_label(adjunct)}+{label}"
                    this = f"[.{label} {adjunct.label_tree()} {this}]"
        if self.arg:
            if self.wp.signal < self.arg.wp.signal and not self.wp.li.is_free_to_move():
                return f"[.{label} {this} {self.arg.label_tree()}]"
            else:
                return f"[.{label} {self.arg.label_tree()} {this}]"
        else:
            return this

    def routes_overlap(self, other_route):
        if not other_route:
            return False
        if self == other_route:
            #print('it is the same route')
            return True
        if self.arg and other_route.arg:
            print('   very similar routes due args: ', self, other_route)
            return True
        if self.signals & other_route.signals != {self.wp.signal}:
            #print('   both use same signals: ', self, other_route, self.signals & other_route.signals)
            return True

    def add_route_edges(self):
        if self.arg:
            for origin in self.arg.signals:
                ctrl.g.add_route_edge(self.arg.wp, self.wp, origin)
        for adj in self.adjuncts:
            for origin in adj.signals:
                ctrl.g.add_route_edge(adj.wp, self.wp, origin)
        if self.part:
            for origin in self.part.signals:
                ctrl.g.add_route_edge(self.part.wp, self.wp, origin)

    def are_neighbors(self, other, other_route):
        other_signals = other_route.signals - other_route.movers

        if not other_signals:
            print('    no other signals: ', other_signals, other_route.signals, other_route.movers)
            return True
        if self.signals & other_route.signals:
            print('    not neighbors, signals overlap: ', self.signals & other_route.signals)
            return False
        #print('are neighbors? ', self.wp, movers, self.signals, other, other_movers, other_route.signals)
        #if other_route.wp.lex_part_signals() & self.signals:
        #    print('    reject because neighbors are part of same word')
        #    return False
        if self.can_move():
            if self.wp.signal < other.signal or True:
                #print(f'    "{self.wp}" (self) is free to move in route {self}')
                return True
            else:
                return False
        if other_route.can_move():
            if self.wp.signal > other.signal or True:
                #print(f'    "{other}" (other) is free to move in route {other_route}')
                return True
            else:
                return False
        if self.wp.signal < other.signal:
            print('<< wp.signal is less than other.signal, they should match at top of wp.signals + 1 and bottom of '
                  'other')
            my_signal = max(self.signals) + 1
            other_signal = min(other_signals)
        else:
            print('>> wp.signal is greater than other.signal, they should match at bottom of wp.signals - 1')
            signals = {signal for signal in self.signals if signal > other.signal}
            my_signal = min(signals) - 1
            other_signal = max(other_signals)

        # löytyykö välissä olevista signaaleista reittiä joka ei ole ristiriitainen näiden tarkasteltavien reittien
        # kanssa ja joka on kokonaan liikkuva?
        # se on kömpelö tarkistus tehdä, saako sen mitenkään elegantimmin?
        print(f'  {self.sg}: my_signal: {my_signal} other_signal: {other_signal}')
        return my_signal == other_signal

    def add_new_route(self, other_route, wp_list):
        if self == other_route:
            return
        if self.routes_overlap(other_route):
            print(f'  {self.sg}: routes overlap: ', self, other_route)
            print(f'  {self.sg}: self:{self.signals} other:{other_route.signals}')
            print(f'  {self.sg}: self arg signals:{self.collect_arg_signals()} other arg signals:'
                  f'{other_route.collect_arg_signals()}')
            # assert set(list(sorted(self.signals))[1:]) & other_route.signals
            return
        #assert not other_route or (self.wp == other_route.wp)
        #assert self.arg != other_route.arg or self.adjuncts != other_route.adjuncts or self.part != other_route.part
        new_combination = Route(
            wp=self.wp,
            part=self.part or other_route.part,
            arg=self.arg or other_route.arg,
            adjuncts=self.adjuncts + other_route.adjuncts)
        if new_combination not in self.wp.li.routes_down:
            same_signals = [rd for rd in self.wp.li.routes_down if rd.signals == new_combination.signals]
            if same_signals:
                print(f'  {self.sg}:skipping this because there is already route with same signals: ',
                      new_combination.signals)
            else:
                print(f'  {self.sg}:add_new_route: {self} (head: {self.wp})')
                print(f'  {self.sg}:               {other_route}')
                print(f'  {self.sg}:            => {new_combination}')
                print(f'  {self.sg}:  new combination for {self.wp}: {new_combination.print_route()}')
                print(f'  {self.sg}:    based on {self.print_route()} and {other_route.print_route()}')
                new_combination.add_route_edges()
                self.wp.li.routes_down.append(new_combination)
        new_combination.walk_all_routes_up(wp_list)

    def walk_all_routes_up(self, wp_list):

        # Palataan siihen intuitioon että reitit ovat haarautumattomia matoja pohjalta ylös, ja reitit ovat
        # yhdistettävissä jos ne ovat keskenään ristiriidattomia. Jos reitti on vaikka ABCDEF ja toinen reitti ABCDEG
        # (alku on reitin yläpää, eli tuo kuvaisi rakennelmaa jonka pääsana on A), niin haluamme että tehdessä
        # reittiä ABCDEG ei tarvitsisi tehdä uudestaan reittiä ABCDE, koska kohdassa E se olisi jo tunnettu
        # tuosta aiemmasta ABCDEF -reitistä.

        # Kun reittiä aloitetaan pohjalta, alimmaisen olion reitti on tyhjä. Seuraava askel saa argumentiksi
        # tähänastisen reitin. Ensimmäisen askeleen jälkeen se on olio ja yhteys joka näitä yhdisti.

        # Selkeyden vuoksi yritetään pitää nyt erillään reitin luominen ja reittien yhdistäminen.
        #print('walking all routes up from ', self.wp, ' with route ', self.print_route())
        print(f' {self.sg}: walking all routes up from: ', self.print_route())

        if self not in self.wp.li.routes_down:
            print(f' {self.sg}: adding simple route: ', self.print_route())
            same_signals = [rd for rd in self.wp.li.routes_down if rd.signals == self.signals]
            if same_signals:
                print(f' {self.sg}: skipping this because there is already route with same signals: ', self.signals)
            else:
                self.wp.li.routes_down.append(self)

        for edge in self.wp.li.adjunctions:
            if edge.start == self.wp:
                continue
            other = edge.start
            for other_route in other.li.routes_down:
                if other != other_route.wp:
                    continue
                if self.are_neighbors(other, other_route):
                    #print(f'  <-> adj route from {other} to {edge.end} in context of {other_route.print_route()}')
                    other_route.add_new_route(Route(wp=other, adjuncts=self), wp_list)

        print(f'{self.sg}:* checking head routes from {self}  ({self.wp})')
        for edge in self.wp.li.head_edges:
            # pitäisi todeta että edge.head:n hallitsema alue ulottuu self:n hallitseman alueen naapuriksi.
            # route pitäisi ymmärtää laajemmin, niin että se kattaa myös yhdistelmät
            print(f' {self.sg}: checking routes to head {edge.head} w. {len(edge.head.li.routes_down)} routes to '
                  f'combine with')
            for other_route in edge.head.li.routes_down:
                print(f'  {self.sg}: head has route to combine with: ', other_route)
                if edge.head != other_route.wp:
                    print('  skipping route because they have different heads: ', edge.head, other_route,
                          other_route.wp)
                    continue
                #print('  are neighbors? ', self, edge.head, other_route)
                if self.are_neighbors(edge.head, other_route):
                    #print('   yes')
                    #print(f'  -> arg route from {self.wp} to {edge.head} in context of '
                    #  f'{other_route.print_route()}')
                    other_route.add_new_route(Route(wp=edge.head, arg=self), wp_list)

        lex_part_index = self.wp.li.lex_parts.index(self.wp.li)
        if lex_part_index and not self.wp.li.is_free_to_move():
            print(
                f' {self.sg}: checking word part routes because we are in lex_part_index {lex_part_index} and not mover')
            prev_wp = None
            prev_moves = True
            prev_wp_signal = self.wp.signal - 2  # this is previous word part as signals start at 1
            # liikkujakaan ei voi olla rakenteessa kuin kerran, joten ei laiteta sitä PART-suhteella
            # alkuperäiselle paikalleen
            while prev_moves and prev_wp_signal >= self.wp.signal - lex_part_index - 1:
                prev_wp = wp_list.word_parts[prev_wp_signal]
                prev_moves = prev_wp.li.is_free_to_move()
                prev_wp_signal -= 1
            if not (prev_moves or self.includes(prev_wp)):
                for other_route in prev_wp.li.routes_down:
                    if prev_wp != other_route.wp:
                        continue
                    if not Route(wp=prev_wp, part=self).routes_overlap(other_route):
                        other_route.add_new_route(Route(wp=prev_wp, part=self), wp_list)
                    #else:
                    #    print('  skipping route to word part because it overlaps with other route: ', other_route)
            else:
                print(f'   {self.sg}:do not combine word parts because other is mover part: ', self.wp, prev_wp)
        print(f'{self.sg}: done checking routes from {self}')


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

    def lex_part_signals(self):
        lex_part_index = self.li.lex_parts.index(self.li)
        return {i for i in range(self.signal - lex_part_index, self.signal)}

    def mover_signals(self):
        signals = set()
        lex_part_index = self.li.lex_parts.index(self.li)
        if lex_part_index + 1 == len(self.li.lex_parts):
            return signals
        for i, lex_part in enumerate(self.li.lex_parts[lex_part_index + 1:], 1):
            if lex_part.is_free_to_move():
                signals.add(self.signal + i)
            else:
                return signals
        return signals

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
