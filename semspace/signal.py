
class Signal:
    def __init__(self, parts, strength, key=None):
        self.parts = parts
        self.strength = strength
        self.trace_strength = 0
        self.key = key or '-'.join(str(part) for part in parts)

    def __repr__(self):
        return f'S{self.parts}:{self.strength}'

    def copy(self):
        return Signal(self.parts, self.strength, self.key)

    def weaken(self, loss):
        self.strength -= loss
        if self.strength <= 0:
            return None
        return self

    def __eq__(self, other):
        if not isinstance(other, Signal):
            return False
        return other.key == self.key

    def __hash__(self):
        multip = 1
        sum = 0
        for part in self.parts:
            sum += multip * part
            multip *= 100
        return sum
