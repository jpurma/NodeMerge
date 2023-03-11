
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

    def neighbors_due_movement(self, other):
        if self.head == other.head:
            return False
        if self.head < other.head:
            lower = self
            higher = other
        else:
            lower = other
            higher = self
        if (lower.head in lower.movers
              and lower.high < higher.low
              and not lower.movers & higher.movers):
            print('           *** mover -based neighbor: ', self, other)
            for route in higher.route.wp.li.routes_down:
                if route.rs.used_movers & lower.movers:
                    print('           reject mover ', lower, ' because it has better use for that mover: ', route)
                    return False
            return True
        return False

    def are_neighbors(self, other):
        if self.head == other.head:
            return False
        if self.head < other.head:
            lower = self
            higher = other
        else:
            lower = other
            higher = self
        return lower.high == higher.low - 1

    def routes_overlap(self, other):
        if not other:
            return False
        if self.low < other.low:
            return self.high > other.low
        elif self.low > other.low:
            return self.low < other.high
        return False
