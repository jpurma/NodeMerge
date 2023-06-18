class WordPart:
    def __init__(self, li, signal):
        self.li = li
        self.signal = signal
        self.merged = False
        print('created word part ', self)

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
