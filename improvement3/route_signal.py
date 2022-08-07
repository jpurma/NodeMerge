from enum import Enum


class Relation(Enum):
    SIGNAL = 0
    HEAD = 1
    PART = 2
    ADJUNCT = 3


class RouteSignal:
    def __init__(self, source=None, target=None, relation=Relation.SIGNAL, signal=None, li=None):
        self.source = source
        self.target = target
        self.relation = relation
        self.li = li
        self.signal = signal

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
            return f'{self.target}.{self.source}'
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
            if self.relation == Relation.PART:
                return self.source.find_head()
            return self.target.find_head()
        return self

    def find_word(self):
        if self.target:
            if self.relation == Relation.PART:
                return self.source.find_head()
            return self.target.find_head()
        return self

    def head_first(self):
        if not self.source:
            return True
        if self.target and self.source:
            return self.target < self.source

    def words(self):
        if self.li:
            return self.li.word
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
        if self.li:
            return self.li.word
        if self.relation == Relation.ADJUNCT:
            if self.head_first():
                return f'{self.target.find_label()}+{self.source.find_label()}'
            else:
                return f'{self.source.find_label()}+{self.target.find_label()}'
        elif self.target:
            return self.target.find_label()

    def tree(self):
        if self.li:
            return self.li.word
        target_tree = self.target.tree()
        source_tree = self.source.tree()
        label = self.find_label()
        if self.head_first():
            return f'[.{label} {target_tree} {source_tree}]'
        return f'[.{label} {source_tree} {target_tree}]'

    def coverage(self):
        return len(self.signals())

    def arg_count(self):
        return len(self.arg_signals())

    def arg_signals(self):
        if self.relation == Relation.SIGNAL:
            return set()
        elif self.relation == Relation.HEAD:
            return {str(self.source)} | self.source.arg_signals() | self.target.arg_signals()
        return self.source.arg_signals() | self.target.arg_signals()

    def signals(self):
        if self.relation == Relation.SIGNAL:
            return {self.signal}
        return self.target.signals() | self.source.signals()

    def signals_in_order(self):
        if self.relation == Relation.SIGNAL:
            return [self.signal]
        return self.target.signals_in_order() + self.source.signals_in_order()

    def cost(self, part_map: dict):
        """ part_map is mapping from signal indices to word indices, so that eg. if "sanoi", "sanoi'", "eilen" are
        signals 1, 2, 3 then their word indices are 0, 0, 1. Word parts belonging to the same word have same word
        index. This prevents multipart words from causing additional costs on movement. """
        if self.relation == Relation.SIGNAL:
            return 0
        target = self.target.find_word().signal  # min(self.target.signals())
        source = self.source.find_word().signal
        min_edge = min(self.source.signals())
        max_edge = max(self.source.signals())
        cost = min(abs(target - source), abs(target - min_edge), abs(target - max_edge))
        if cost > 0:
            cost -= 1
        print(target, (min_edge, source, max_edge), cost)
        fine_cost = abs(self.target.find_word().signal - self.source.find_word().signal)
        if fine_cost > 1 and False:
            cost += (fine_cost - 1) / 10
        return cost + self.target.cost(part_map) + self.source.cost(part_map)

    def cost_map(self, part_map: dict):
        """ part_map is mapping from signal indices to word indices, so that eg. if "sanoi", "sanoi'", "eilen" are
        signals 1, 2, 3 then their word indices are 0, 0, 1. Word parts belonging to the same word have same word
        index. This prevents multipart words from causing additional costs on movement. """
        if self.relation == Relation.SIGNAL:
            return 0
        target = part_map[self.target.find_word().signal]  # min(self.target.signals())
        source = part_map[self.source.find_word().signal]
        min_edge = part_map[min(self.source.signals())]
        max_edge = part_map[max(self.source.signals())]
        cost = min(abs(target - source), abs(target - min_edge), abs(target - max_edge))
        if cost > 0:
            cost -= 1
        print(target, (min_edge, source, max_edge), cost)
        fine_cost = abs(self.target.find_word().signal - self.source.find_word().signal)
        if fine_cost > 1 and False:
            cost += (fine_cost - 1) / 10
        return cost + self.target.cost(part_map) + self.source.cost(part_map)


    def compatible_with(self, other):
        return not self.signals() & other.signals()
