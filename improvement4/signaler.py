from word_part import WordPart


class Signaler:
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

    def activate_current_words(self):
        lefts = list(reversed(self.prev_items))
        current = self.current_item
        print(f' Signaler: *** activate {lefts} & {current}')
        strength = 1.0
        current.li.activate(current.signal, strength=strength)
        # for left in list(reversed(lefts))[:2]:
        #    strength = strength * 0.9
        #    left.li.refresh_activation(left.signal, strength)
