class WordPart:
    def __init__(self, li, signal):
        self.li = li
        self.signal = signal

    def __str__(self):
        return f'{self.li.id}-{self.signal}'

    def __repr__(self):
        return str(self)

    def __lt__(self, other):
        return isinstance(other, WordPart) and (self.signal < other.signal)

    def __eq__(self, other):
        return isinstance(other, WordPart) and (self.signal == other.signal)

    def __hash__(self):
        return hash((self.li.id, self.signal))

    def lex_part_signals(self):
        lex_part_index = self.li.lex_parts.index(self.li)
        return {i for i in range(self.signal - lex_part_index, self.signal)}

    def lex_part_signals_without_movers(self):
        lex_part_index = self.li.lex_parts.index(self.li)
        return {index - lex_part_index + self.signal for index, li in enumerate(self.li.lex_parts) if not
            li.is_free_to_move()}

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
        # self.closest_item = self.current_item
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
        # current_parts = self.word_parts[-1].li.lex_parts or [self.word_parts[-1].li]
        # return [part for part in self.word_parts if part.li not in current_parts]
        return self.word_parts[:-1]
