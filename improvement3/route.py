from operator import attrgetter

from ctrl import ctrl
from edges import LexEdge
from route_signal import RouteSignal

BREAKPOINT = 0
COMPLETE_ROUTES = False

ARGUMENT = 'argument'
ADJUNCTION = 'adjunction'
PART = 'part'


class Route:
    """ A route is one possible parse of a sentence, composed of other routes. A route is more like a computational
    representation of parse for this stage where I don't know what is required for a parse, so it has lots of
    superfluous information available.  """
    def __init__(self, parent, wp=None, part=None, arg=None, adjunct=None, cost=1):
        self.parent = parent
        self.size = 0
        if wp:
            self.wp = wp
            self.part = None
            self.arg = None
            self.adjuncts = []
            self.signals = {wp.signal}
            self.cost = 0
            self.size = 1
        else:
            self.wp = parent.wp
            self.part = parent.part
            self.arg = parent.arg
            self.adjuncts = list(parent.adjuncts)
            self.signals = set(parent.signals)
            self.cost = parent.cost
            self.size = parent.size
        if part:
            self.part = part
            self.signals |= part.signals
            self.cost += part.cost
            self.size += part.size
        if arg:
            self.arg = arg
            self.signals |= arg.signals
            self.cost += arg.cost
            self.size += arg.size
        if adjunct:
            self.adjuncts.append(adjunct)
            self.signals |= adjunct.signals
            self.cost += adjunct.cost
            self.size += adjunct.size
            #self.adjuncts.sort()
        self.signals = set(sorted(list(self.signals)))
        # Kokeillaan naapureiden laskemista reittiä tehdessä
        self.route_signal = RouteSignal(self, part, arg, adjunct)

    def __eq__(self, other):
        if self is other:
            return True
        if not isinstance(other, Route):
            return False
        return self.wp == other.wp and self.part == other.part and self.arg == other.arg and self.adjuncts == other.adjuncts

    def __lt__(self, other):
        if not isinstance(other, Route):
            return False
        if self.cost != other.cost:
            return self.cost < other.cost
        return self.wp.signal < other.wp.signal

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
                    this = f"({this}+{adjunct})"
                else:
                    this = f"({adjunct}+{this})"
        if self.arg:
            if self.wp.signal < self.arg.wp.signal: # and not self.wp.li.is_free_to_move():
                this = f"({this}<-{self.arg})"
            else:
                this = f"({self.arg}->{this})"
        if self.part:
            this = f"{this}.{self.part}"
        return this

    def tree(self):
        return self.label_tree()

    def label_tree(self):
        def _build_label(adjunct):
            a_label = str(adjunct.wp)
            for other_adjunct in adjunct.adjuncts:
                adjunct_labels = _build_label(other_adjunct)
                if adjunct.wp.signal < other_adjunct.wp.signal:
                    a_label += '+' + adjunct_labels
                else:
                    a_label = adjunct_labels + '+' + a_label
            return a_label

        label = str(self.wp)
        this = label
        if self.part:
            this = f"[.{label} {self.wp} {self.part.label_tree()}]"
        if self.adjuncts:
            for adjunct in self.adjuncts:
                if self.wp.signal < adjunct.wp.signal:
                    label = f"{label}+{_build_label(adjunct)}"
                    this = f"[.{label} {this} {adjunct.label_tree()}]"
                else:
                    label = f"{_build_label(adjunct)}+{label}"
                    this = f"[.{label} {adjunct.label_tree()} {this}]"
        if self.arg:
            if self.wp.signal < self.arg.wp.signal and not self.wp.li.is_free_to_move():
                return f"[.{label} {this} {self.arg.label_tree()}]"
            else:
                return f"[.{label} {self.arg.label_tree()} {this}]"
        else:
            return this

    def routes_overlap(self, other_route):
        if not other_route:
            return False
        print(self.route_signal, other_route.route_signal)
        if self.route_signal.low < other_route.route_signal.low:
            return self.route_signal.high > other_route.route_signal.low
        elif self.route_signal.low > other_route.route_signal.low:
            return self.route_signal.low < other_route.route_signal.high
        return False

    def add_route_edges(self):
        if self.arg:
            for origin in self.arg.signals:
                ctrl.g.add_route_edge(self.arg.wp, self.wp, origin)
        for adj in self.adjuncts:
            for origin in adj.signals:
                ctrl.g.add_route_edge(adj.wp, self.wp, origin)
        if self.part:
            for origin in self.part.signals:
                ctrl.g.add_route_edge(self.part.wp, self.wp, origin)

    def simple_neighborhood_check(self, other_route):
        if self.wp.signal == other_route.wp.signal:
            return False
        if self.wp.signal < other_route.wp.signal:
            lower = self.route_signal
            higher = other_route.route_signal
        else:
            lower = other_route.route_signal
            higher = self.route_signal

        if lower.high == higher.low - 1:
            return True
        elif (self.wp.signal in lower.movers or other_route.wp.signal in lower.movers) and lower.high < higher.low and\
                not lower.movers & higher.movers:
            print('*** mover -based neighbor: ', self, other_route)
            return True
        return False

    def are_neighbors(self, other_route):
        print('      simple check returns: ', self.simple_neighborhood_check(other_route))
        return self.simple_neighborhood_check(other_route)

    def add_new_route(self, other_route, type='', cost=1):
        if self == other_route:
            raise hell
            return
        if self.routes_overlap(other_route):
            print(f'  {self.sg}: routes overlap: ', self, other_route)
            print(f'  {self.sg}: self:{self.signals} other:{other_route.signals}')
            # assert set(list(sorted(self.signals))[1:]) & other_route.signals
            return
        elif type == ARGUMENT:
            if self.arg:
                raise hell
                return
            new_combination = Route(self, arg=other_route, cost=cost)
        elif type == ADJUNCTION:
            new_combination = Route(self, adjunct=other_route, cost=cost)
        elif type == PART:
            if self.part:
                raise hell
                return
            new_combination = Route(self, part=other_route, cost=cost)
        else:
            return
        if new_combination not in self.wp.li.routes_down:
            same_signals = [rd for rd in self.wp.li.routes_down if (
                    len(rd) > len(new_combination) and
                    rd.route_signal.low == new_combination.route_signal.low and
                    rd.route_signal.high == new_combination.route_signal.high and
                    len(rd.route_signal.movers) <= len(new_combination.route_signal.movers))]
            if same_signals:
                print(f'  {self.sg}:skipping this because there is already route with same signals: ',
                      new_combination.route_signal)
            else:
                print(f'  {self.sg}: ({type}) add_new_route: {self} (head: {self.wp})')
                print(f'  {self.sg}:               {other_route}')
                print(f'  {self.sg}:            => {new_combination}')
                print(f'  {self.sg}:  new combination for {self.wp}: {new_combination.print_route()}')
                print(f'  {self.sg}:    based on {self.print_route()} and {other_route.print_route()}')
                new_combination.add_route_edges()
                print('append route: ', new_combination)
                self.wp.li.routes_down.insert(0, new_combination)
                self.wp.li.routes_down.sort(key=attrgetter('size'), reverse=True)
                new_combination.walk_all_routes_up()

    def walk_all_routes_up(self):

        # Palataan siihen intuitioon että reitit ovat haarautumattomia matoja pohjalta ylös, ja reitit ovat
        # yhdistettävissä jos ne ovat keskenään ristiriidattomia. Jos reitti on vaikka ABCDEF ja toinen reitti ABCDEG
        # (alku on reitin yläpää, eli tuo kuvaisi rakennelmaa jonka pääsana on A), niin haluamme että tehdessä
        # reittiä ABCDEG ei tarvitsisi tehdä uudestaan reittiä ABCDE, koska kohdassa E se olisi jo tunnettu
        # tuosta aiemmasta ABCDEF -reitistä.

        # Kun reittiä aloitetaan pohjalta, alimmaisen olion reitti on tyhjä. Seuraava askel saa argumentiksi
        # tähänastisen reitin. Ensimmäisen askeleen jälkeen se on olio ja yhteys joka näitä yhdisti.

        # Selkeyden vuoksi yritetään pitää nyt erillään reitin luominen ja reittien yhdistäminen.
        # print('walking all routes up from ', self.wp, ' with route ', self.print_route())
        ctrl.g.counter += 1
        print(f'------ {ctrl.g.counter} ------')
        print(f' {self.sg}: walking all routes up from: ', self.print_route())

        print(f'   {self.sg}: checking head routes from {self}  ({self.wp}) {self.route_signal}')
        for edge in reversed(self.wp.li.head_edges):
            # pitäisi todeta että edge.head:n hallitsema alue ulottuu self:n hallitseman alueen naapuriksi.
            # route pitäisi ymmärtää laajemmin, niin että se kattaa myös yhdistelmät
            print(f'     {self.sg}: checking routes to head {edge.head} w. {len(edge.head.li.routes_down)} routes to '
                  f'combine with')
            for other_route in edge.head.li.routes_down:
                if edge.head != other_route.wp:
                    # print('  skipping route because they have different heads: ', edge.head, other_route,
                    #      other_route.wp)
                    continue
                if other_route.arg:
                    print(f'    skipping route {other_route} because it already has arg')
                    continue
                print(f'      {self.sg}: head has route to combine with: ', other_route, other_route.route_signal)
                print('       are neighbors? ', self, self.route_signal, edge.head, other_route,
                      other_route.route_signal)
                if cost := self.are_neighbors(other_route):
                    print('        yes')
                    # print(f'  -> arg route from {self.wp} to {edge.head} in context of '
                    #  f'{other_route.print_route()}')
                    other_route.add_new_route(self, ARGUMENT, cost)
                    if not COMPLETE_ROUTES:
                        break

        print(f'   {self.sg}: checking adj routes from {self}  ({self.wp})')
        for edge in self.wp.li.adjunct_to:
            other = edge.end
            print(f'     this {self.wp} in {self} could be adjunct for {other}, w. {len(other.li.routes_down)} routes')
            if self.route_signal.low <= other.signal <= self.route_signal.high:
                print('     other is already part of this route: ', other, self)
                continue
            for other_route in other.li.routes_down:
                if other != other_route.wp:
                    #print('   skip adjunction, other route has different wp to edge.start: ', edge, other_route.wp)
                    continue
                print('     are neighbors? ', self, self.route_signal, other, other_route, other_route.route_signal)
                if cost := self.are_neighbors(other_route):
                    print('      yes')
                    print(f'     <-> adj route from {other} to {edge.end} in context of {other_route.print_route()}')
                    other_route.add_new_route(self, ADJUNCTION, cost)
                    if not COMPLETE_ROUTES:
                        break

        wp = min([self.wp] + [route.wp for route in self.adjuncts])
        print(f'   {self.sg}: checking part routes from {self}  ({wp})')
        for edge in wp.li.edges_in:
            if isinstance(edge, LexEdge) and wp.signal - 1 in edge.activations:
                prev_wp = ctrl.words.word_parts[wp.signal - 2]
                for other_route in prev_wp.li.routes_down:
                    if prev_wp == other_route.wp and not other_route.part:
                        other_route.add_new_route(self, PART)
                        if not COMPLETE_ROUTES:
                            break

        print(f' {self.sg}: done checking routes from {self}')
        if ctrl.g.counter == BREAKPOINT:
            print('**** at breakpoint ****')
