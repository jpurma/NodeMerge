
class RouteSignal:
    """ RouteSignal is a minimal representation of Route that should eventually replace Route. Parsing should be
    possible by doing computation in nodes with RouteSignals representing the parse states."""
    def __init__(self, route, part, arg, adjunct):
        self.route = route
        self.head = route.wp.signal
        if route.parent:
            self.low = route.parent.rs.low
            self.high = route.parent.rs.high
            self.movers = set(route.parent.rs.movers)
            self.used_movers = set(route.parent.rs.used_movers)
        else:
            self.low = self.head
            self.high = self.head
            self.movers = {self.head} if route.wp.li.is_free_to_move() else set()
            self.used_movers = set()
        if part:
            print('     rs: adding part ', part.route, part, ' to ', route.parent, self)
            self.movers |= part.movers
            self.used_movers |= part.used_movers
            self.high = part.high
        if arg:
            print('     rs: adding argument ', arg.route, arg, ' to ', route.parent, self)
            if self.movers or arg.movers:
                print(' rs: arg w. mover:', self.movers, arg.movers, arg.route.wp, route.wp)
            if self.head in self.movers:
                self.movers.remove(self.head)
                self.used_movers.add(self.head)
            self.movers -= arg.used_movers
            self.used_movers |= arg.used_movers
            if arg.head in self.movers:
                print('     rs: **** using and removing mover from self')
                self.movers.remove(arg.head)
                self.used_movers.add(arg.head)
            elif arg.head in arg.movers:
                print('     rs: ** merging mover argument, skip it from lowest count. arg: ', arg)
                self.used_movers.add(arg.head)
            else:
                self.low = min(self.low, arg.low)
            self.high = max(self.high, arg.high)
        if adjunct:
            print('     rs: adding adjunct ', adjunct.route, adjunct, ' to ', route.parent, self)
            self.low = min(self.low, adjunct.low)
            self.high = max(self.high, adjunct.high)
            if adjunct.movers:
                self.movers.add(self.head)
                print('     rs: adding ', self.head, ' to movers', self.movers)
        print('rs result: ', self)

    def __repr__(self):
        return f'<RouteSignal low:{self.low}, head: {self.head} high:{self.high}, movers:{self.movers}, ' \
               f'used:{self.used_movers}>'

    def is_lower_neighbor_due_movement_for(self, other):
        if self.head == other.head:
            return False
        if (self.head in self.movers  # 1. must be mover
              and self.high < other.low  # 2. must not be contained in where it is moved
              and self.head not in other.used_movers  # 3. mover must not be used
              and self.head not in other.movers):  # 4. mover must not be same structure (prob. not necessary because 2.)
            return True
        return False

    def are_neighbors(self, other):
        return self.is_lower_neighbor_of(other) or other.is_lower_neighbor_of(self)

    def is_lower_neighbor_of(self, other):
        if self.head == other.head:
            return False
        return self.high == other.low - 1

    def same_scope(self, other):
        return self.low == other.low and self.high == other.high and self.movers == other.movers and self.used_movers == other.used_movers

    def routes_overlap(self, other):
        if not other:
            return False
        if self.low < other.low:
            return self.high > other.low
        elif self.low > other.low:
            return self.low < other.high
        return False
