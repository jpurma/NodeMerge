
class Signal:
    def __init__(self, parts, strength, outgoing=False, key=None):
        self.parts = parts
        self.strength = strength
        if key:
            self.key = key
        else:
            if len(parts) == 1:
                if outgoing:
                    self.key = str(parts[0]) + '>'
                else:
                    self.key = str(parts[0]) + '<'
            else:
                self.key = '-'.join(str(part) for part in parts)

    def __repr__(self):
        return f'S{self.key}:{self.strength}'

    def copy(self):
        return Signal(self.parts, self.strength, key=self.key)

    def weaken(self, loss):
        self.strength -= loss
        if self.strength <= 0:
            return None
        return self

    def is_outgoing(self):
        return self.key.endswith('>')

    def is_inwards(self):
        return self.key.endswith('<')

    def is_seeker(self):
        return len(self.parts) > 1

    def __eq__(self, other):
        if not isinstance(other, Signal):
            return False
        return other.key == self.key
