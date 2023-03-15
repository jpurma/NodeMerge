from operator import attrgetter

from ctrl import ctrl
from edges import LexEdge
from route_signal import RouteSignal

BREAKPOINT = 0

ARGUMENT = 'argument'
LONG_DISTANCE_ARGUMENT = 'ld_argument'
ADJUNCTION = 'adjunction'
PART = 'part'


class Route:
    """ A route is one possible parse of a sentence, composed of other routes. A route is more like a computational
    representation of parse for this stage where I don't know what is required for a parse, so it has lots of
    superfluous information available.  """
    def __init__(self, parent, wp=None, part=None, arg=None, adjunct=None):
        self.parent = parent
        self.size = 0
        if wp:
            self.wp = wp
            self.part = None
            self.arg = None
            self.adjuncts = []
            self.size = 1
        else:
            self.wp = parent.wp
            self.part = parent.part
            self.arg = parent.arg
            self.adjuncts = list(parent.adjuncts)
            self.size = parent.size
        if part:
            self.part = part
            self.size += part.size
        if arg:
            self.arg = arg
            self.size += arg.size
        if adjunct:
            self.adjuncts.append(adjunct)
            self.size += adjunct.size
        self.weight = 0
        self.rs = RouteSignal(self, part and part.rs, arg and arg.rs, adjunct and adjunct.rs)

    def __eq__(self, other):
        if self is other:
            return True
        if not isinstance(other, Route):
            return False
        return self.wp == other.wp and self.part == other.part and self.arg == other.arg and self.adjuncts == other.adjuncts

    def __len__(self):
        return self.size

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

    def __str__(self):
        return self.print_route()

    def __repr__(self):
        return f'Route({self.print_route()})'

    def print_route(self):
        this = str(self.wp)
        if self.adjuncts:
            for adjunct in self.adjuncts:
                if self.wp.signal < adjunct.wp.signal:
                    this = f"({this}<+{adjunct})"
                else:
                    this = f"({adjunct}+>{this})"
        if self.arg:
            if self.wp.signal < self.arg.wp.signal:
                this = f"({this}<-{self.arg})"
            else:
                this = f"({self.arg}->{this})"
        if self.part:
            this = f"{this}.{self.part}"
        return this

    def tree(self):
        def _build_label(adjunct):
            a_label = str(adjunct.wp)
            for other_adjunct in adjunct.adjuncts:
                adjunct_labels = _build_label(other_adjunct)
                if adjunct.wp.signal < other_adjunct.wp.signal:
                    a_label += '<+' + adjunct_labels
                else:
                    a_label = adjunct_labels + '+>' + a_label
            return a_label

        label = str(self.wp)
        this = label
        if self.part:
            this = f"[.{label} {self.wp} {self.part.tree()}]"
        if self.adjuncts:
            for adjunct in self.adjuncts:
                if self.wp.signal < adjunct.wp.signal:
                    label = f"{label}<+{_build_label(adjunct)}"
                    this = f"[.{label} {this} {adjunct.tree()}]"
                else:
                    label = f"{_build_label(adjunct)}+>{label}"
                    this = f"[.{label} {adjunct.tree()} {this}]"
        if self.arg:
            if self.wp.signal < self.arg.wp.signal and not self.wp.li.is_free_to_move():
                return f"[.{label} {this} {self.arg.tree()}]"
            else:
                return f"[.{label} {self.arg.tree()} {this}]"
        else:
            return this

    def add_route_edges(self):
        if self.arg:
            for origin in range(self.arg.rs.low, self.arg.rs.high + 1):
                ctrl.g.add_route_edge(self.arg.wp, self.wp, origin)
        for adj in self.adjuncts:
            for origin in range(adj.rs.low, adj.rs.high + 1):
                ctrl.g.add_route_edge(adj.wp, self.wp, origin)
        if self.part:
            for origin in range(self.part.rs.low, self.part.rs.high + 1):
                ctrl.g.add_route_edge(self.part.wp, self.wp, origin)

    def add_new_route(self, other_route, type=''):
        new_combination = None
        if self == other_route:
            return
        elif self.rs.routes_overlap(other_route.rs):
            return
        elif self.rs.used_movers & other_route.rs.used_movers:
            return
        elif type == ARGUMENT:
            if self.arg:
                return
            elif other_route.rs.head in other_route.rs.movers:
                return
            elif other_route.rs.head in self.rs.used_movers:
                return
            elif other_route.rs.head in self.rs.movers:
                return
            # Avoid splitting words
            elif other_route.rs.head < self.rs.head and self.wp.li.lex_parts.index(self.wp.li):
                return
            elif other_route.rs.are_neighbors(self.rs):
                new_combination = Route(self, arg=other_route)
        elif type == LONG_DISTANCE_ARGUMENT:
            if self.arg:
                return
            elif other_route.rs.is_lower_neighbor_due_movement_for(self.rs):
                print('long distance argument: ', other_route, self)
                new_combination = Route(self, arg=other_route)
            elif self.rs.is_lower_neighbor_due_movement_for(other_route.rs):
                print('reversed long distance argument: ', other_route, self)
                new_combination = Route(self, arg=other_route)
        elif type == ADJUNCTION:
            if other_route.rs.are_neighbors(self.rs):
                new_combination = Route(self, adjunct=other_route)
        elif type == PART:
            if self.part:
                return
            new_combination = Route(self, part=other_route)
        if not new_combination:
            return
        old_combination = None
        for combination in self.wp.li.routes_down:
            if combination == new_combination:
                old_combination = combination
                break
            elif combination.rs.same_scope(new_combination.rs):
                old_combination = combination
                break
        if old_combination:
            old_combination.weight += 1
            old_combination.walk_all_routes_up()
        else:
            print(f'  {self.sg}: ({type}) add_new_route: {self} ({self.rs})')
            print(f'  {self.sg}:               {other_route} ({other_route.rs})')
            print(f'  {self.sg}:            => {new_combination}')
            print(f'  {self.sg}:  new combination: {new_combination} ({new_combination.rs})')
            new_combination.add_route_edges()
            new_combination.weight = self.weight + other_route.weight
            self.wp.li.routes_down.insert(0, new_combination)
            self.wp.li.routes_down.sort(key=attrgetter('size', 'weight'), reverse=True)
            new_combination.walk_all_routes_up()

    def walk_all_routes_up(self):
        ctrl.g.counter += 1
        print(f'------ {ctrl.g.counter} ------')
        print(f' {self.sg}: walking all routes up from: ', self)
        for edge in self.wp.li.head_edges:
            for other_route in edge.head.li.routes_down:
                if edge.head == other_route.wp:
                    other_route.add_new_route(self, ARGUMENT)

        wp = min([self.wp] + [route.wp for route in self.adjuncts])
        for edge in wp.li.edges_in:
            if isinstance(edge, LexEdge) and wp.signal - 1 in edge.activations:
                prev_wp = ctrl.words.word_parts[wp.signal - 2]
                for other_route in prev_wp.li.routes_down:
                    if prev_wp == other_route.wp:
                        other_route.add_new_route(self, PART)

        for edge in self.wp.li.adjunct_to:
            if edge.start != self.wp:
                continue
            other = edge.end
            if self.rs.low <= other.signal <= self.rs.high:
                continue
            for other_route in other.li.routes_down:
                if other == other_route.wp:
                    other_route.add_new_route(self, ADJUNCTION)

        for edge in self.wp.li.head_edges:
            for other_route in edge.head.li.routes_down:
                if edge.head == other_route.wp:
                    other_route.add_new_route(self, LONG_DISTANCE_ARGUMENT)

        print(f' {self.sg}: done checking routes from {self}')
        if ctrl.g.counter == BREAKPOINT:
            print('**** at breakpoint ****')
