from nodes import NegFeatureNode


class WordPart:
    def __init__(self, li, signal):
        self.li = li
        self.signal = signal

    def __str__(self):
        return f'{self.li.id}-{self.signal}'

    def __repr__(self):
        return str(self)

    def __eq__(self, other):
        return isinstance(other, WordPart) and (self.li == other.li) and (self.signal == other.signal)

    def __hash__(self):
        return hash((self.li.id, self.signal))


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

    def collect_previous_items_old(self):
        """ Otetaankin kaikki jotta selvitään tilanteista joissa parempi ehdokas tiettyyn rooliin tulee myöhemmin,
        kuten 'Pekka sanoi että ihailee Merja luontoa' -- järkeily miksi tarvitaan kaikki menee niin, että jos meillä
        olisi tässä heuristiikkaa estämässä tiettyjä elementtejä niin sikäli kun se heuristiikka pohjautuu yhteyksiin
        jotka on rakennettu, niin nämä rakennetut yhteydet saattavat olla vääriä hypoteeseja joten niihin ei voi
        luottaa, eikä siten koko heuristiikan tulokseen. Se jättää kyllä mahdolliseksi sellaiset heuristiikat
        jotka perustuvat vain sanojen ominaisuuksiin.
        """

        def is_unsatisfied_blocker(b_part: WordPart):
            for e in b_part.li.edges_out:
                if isinstance(e.end, NegFeatureNode) and e.end.sign == '-' and not e.end.activated_at(b_part.signal):
                    return True

        def collect_adj_parts(adj_part, adj_parts):
            adj_parts.add(adj_part)
            for e in adj_part.li.adjunctions:
                if e.end == adj_part:
                    collect_adj_parts(e.start, adj_parts)

        def collect_complex_parts(c_parts):
            prev_li_parts = None
            for c_part in set(c_parts):
                if c_part.li.lex_parts is not prev_li_parts:
                    c_parts |= set(self.get_lex_parts(c_part))
                    prev_li_parts = c_part.li.lex_parts

        part_stack = list(self.word_parts)
        prev_items = []
        current = part_stack.pop()
        args = set()
        inner_parts = current.li.lex_parts
        related_parts = set()
        while part_stack:
            part = part_stack.pop()
            if part not in related_parts:
                related_parts = set()
                collect_adj_parts(part, related_parts)
                #collect_complex_parts(related_parts)
                print(f'related parts for {part}: ', related_parts)
                for related_part in related_parts:
                    if [head_edge for head_edge in related_part.li.head_edges if head_edge.arg == related_part]:
                        print(f'found one part being arg {related_part}, adding all related parts as args: ', related_parts)
                        args |= related_parts
            if part.li in inner_parts and False:
                continue
            else:
                inner_parts = part.li.lex_parts
                if part not in args or True:
                    prev_items.append(part)
            # if is_unsatisfied_blocker(part):
            #    break

        print(f'current {current}, known args: ', args)
        return prev_items
