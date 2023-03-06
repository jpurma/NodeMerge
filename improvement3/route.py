from ctrl import ctrl
from edges import LexEdge
from route_signal import RouteSignal

BREAKPOINT = 0

SIGNAL_TREE = False

ARGUMENT = 'argument'
ADJUNCTION = 'adjunction'
PART = 'part'


class Route:
    """ A route is one possible parse of a sentence, composed of other routes. A route is more like a computational
    representation of parse for this stage where I don't know what is required for a parse, so it has lots of
    superfluous information available.  """
    def __init__(self, parent, wp=None, part=None, arg=None, adjunct=None, cost=1):
        self.parent = parent
        if wp:
            self.wp = wp
            self.part = None
            self.arg = None
            self.adjuncts = []
            self.signals = {wp.signal}
            self.movers = {wp.signal} if self.wp.li.is_free_to_move() else set()
            self.cost = 0
            self.arg_signals = set()
        else:
            self.wp = parent.wp
            self.part = parent.part
            self.arg = parent.arg
            self.adjuncts = list(parent.adjuncts)
            self.signals = set(parent.signals)
            self.movers = set(parent.movers)
            self.cost = parent.cost
            self.arg_signals = set(parent.arg_signals)
        if part:
            self.part = part
            self.signals |= part.signals
            self.movers |= part.movers
            self.arg_signals |= part.arg_signals
            self.cost += part.cost
        if arg:
            self.arg = arg
            self.signals |= arg.signals
            if arg.can_move():
                self.movers |= arg.signals
                self.movers.add(self.wp.signal)
            self.arg_signals.add(arg.wp.signal)
            self.movers |= arg.movers
            self.arg_signals |= arg.arg_signals
            self.cost += arg.cost
        if adjunct:
            self.adjuncts.append(adjunct)
            self.signals |= adjunct.signals
            self.movers |= adjunct.movers
            self.arg_signals |= adjunct.arg_signals
            self.cost += adjunct.cost
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

    def can_move(self):
        if self.wp.li.is_free_to_move():
            return True
        if self.arg and self.arg.can_move():
            return True
        for adj in self.adjuncts:
            if adj.can_move():
                return True

    def collect_arg_signals(self, arg_signals=None, at_arg=False):
        if arg_signals is None:
            arg_signals = set()

        if at_arg:
            arg_signals.add(self.wp.signal)
        if self.arg:
            self.arg.collect_arg_signals(arg_signals, at_arg=True)
        if self.part:
            self.part.collect_arg_signals(arg_signals)
        if self.adjuncts:
            for adjunct in self.adjuncts:
                adjunct.collect_arg_signals(arg_signals)
        return arg_signals

    def __str__(self):
        return self.print_route()

    def __repr__(self):
        return f'Route({self.print_route()})'

    def print_route(self, can_move=False):
        can_move = can_move or self.can_move()
        #this = f'{self.wp.li.word}/{self.wp.signal}' if can_move else str(self.wp)
        this = str(self.wp)
        if self.adjuncts:
            for adjunct in self.adjuncts:
                if self.wp.signal < adjunct.wp.signal:
                    this = f"({this}+{adjunct.print_route(can_move=can_move)})"
                else:
                    this = f"({adjunct.print_route(can_move=can_move)}+{this})"
        if self.arg:
            if self.wp.signal < self.arg.wp.signal: # and not self.wp.li.is_free_to_move():
                this = f"({this}<-{self.arg.print_route(can_move=can_move)})"
            else:
                this = f"({self.arg.print_route(can_move=can_move)}->{this})"
        if self.part:
            this = f"{this}.{self.part.print_route(can_move=can_move)}"
        return this

    def tree(self):
        if SIGNAL_TREE:
            return self.signal_tree()
        else:
            return self.label_tree()

    def signal_tree(self):
        def joined(listlike):
            return '-'.join(str(l) for l in listlike)

        def _build_label(adjunct):
            a_label = [adjunct.wp.signal]
            for other_adjunct in adjunct.adjuncts:
                adjunct_labels = _build_label(other_adjunct)
                if adjunct.wp.signal < other_adjunct.wp.signal:
                    a_label += adjunct_labels
                else:
                    a_label = adjunct_labels + a_label
            return a_label

        label = [self.wp.signal if not self.can_move() else f'{self.wp.signal}M']
        this = str(self.wp)
        if self.part:
            this = f"[.{joined(label + list(self.part.signals))} {self.wp}" \
                   f" {self.part.signal_tree()}]"
        if self.adjuncts:
            for adjunct in self.adjuncts:
                if self.wp.signal < adjunct.wp.signal:
                    label += _build_label(adjunct)
                    this = f"[.{joined(label)} {this} {adjunct.signal_tree()}]"
                else:
                    label = _build_label(adjunct) + label
                    this = f"[.{joined(label)} {adjunct.signal_tree()} {this}]"
        if self.arg:
            if self.wp.signal < self.arg.wp.signal:
                if self.wp.li.is_free_to_move():
                    return f"[.{joined(self.signals)} {self.arg.signal_tree()} {this}]"
                return f"[.{joined(self.signals)} {this} {self.arg.signal_tree()}]"
            else:
                return f"[.{joined(self.signals)} {self.arg.signal_tree()} {this}]"
        if not (self.part or self.adjuncts):
            return str(self.wp)
        else:
            return this

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

    def adjunct_agrees(self, other_route):
        def disagreement(pos_feat, adj_feats, other_pos_feats):
            return pos_feat.sign == '' and pos_feat.name in adj_feats and pos_feat not in other_pos_feats

        # other route provides head where we are adjuncting to.
        # disagree if head has already been adjuncted by something and feature is not same as we are adjuncting with
        other_route_adj_feats = {feat.name for feat in other_route.wp.li.feats if feat.sign == '-'}
        for adjunct in other_route.adjuncts:
            if any(pos_feat for pos_feat in adjunct.wp.li.feats if disagreement(pos_feat, other_route_adj_feats,
                                                                                self.wp.li.feats)):
                print(f'''       other route {other_route} (head: {other_route.wp}) has positive adjunct {adjunct
                } 
{[pos_feat for pos_feat in adjunct.wp.li.feats if disagreement(pos_feat, other_route_adj_feats, self.wp.li.feats)]
                } which are not in my feats: {self.wp.li.feats}''')
                return False
        my_adj_feats = {feat.name for feat in self.wp.li.feats if feat.sign == '-'}
        for adjunct in self.adjuncts:
            if any(pos_feat for pos_feat in adjunct.wp.li.feats if disagreement(pos_feat, my_adj_feats,
                                                                                other_route.wp.li.feats)):
                print(f'''       self {self} (head: {self.wp}) has positive adjunct {adjunct
                } 
{[pos_feat for pos_feat in adjunct.wp.li.feats if disagreement(pos_feat, my_adj_feats, other_route.wp.li.feats)]
                } which are not in other_route feats: {other_route.wp.li.feats}''')
                return False

        print('      adjuncts agree: ', self, other_route)
        return True

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
            #if higher.high in higher.movers:
            #    return False
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
            return
        if self.routes_overlap(other_route):
            print(f'  {self.sg}: routes overlap: ', self, other_route)
            print(f'  {self.sg}: self:{self.signals} other:{other_route.signals}')
            print(f'  {self.sg}: self arg signals:{self.collect_arg_signals()} other arg signals:'
                  f'{other_route.collect_arg_signals()}')
            # assert set(list(sorted(self.signals))[1:]) & other_route.signals
            return
        elif type == ARGUMENT:
            if self.arg:
                return
            new_combination = Route(self, arg=other_route, cost=cost)
        elif type == ADJUNCTION:
            new_combination = Route(self, adjunct=other_route, cost=cost)
        elif type == PART:
            if self.part:
                return
            new_combination = Route(self, part=other_route, cost=cost)
        else:
            return
        if new_combination not in self.wp.li.routes_down:
            same_signals = [rd for rd in self.wp.li.routes_down if rd.signals == new_combination.signals]
            if same_signals and False:
                print(f'  {self.sg}:skipping this because there is already route with same signals: ',
                      new_combination.signals)
            else:
                print(f'  {self.sg}: ({type}) add_new_route: {self} (head: {self.wp})')
                print(f'  {self.sg}:               {other_route}')
                print(f'  {self.sg}:            => {new_combination}')
                print(f'  {self.sg}:  new combination for {self.wp}: {new_combination.print_route()}')
                print(f'  {self.sg}:    based on {self.print_route()} and {other_route.print_route()}')
                new_combination.add_route_edges()
                print('append route: ', new_combination)
                self.wp.li.routes_down.append(new_combination)
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

        if self not in self.wp.li.routes_down:
            print(f' {self.sg}: adding simple route: ', self)
            same_signals = [rd for rd in self.wp.li.routes_down if rd.signals == self.signals]
            if same_signals:
                print(f' {self.sg}: skipping this because there is already route with same signals: ', self.signals)
            else:
                print('append route: ', self)
                self.wp.li.routes_down.append(self)

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
                    # print('    skipping route because it already has arg')
                    continue
                print(f'      {self.sg}: head has route to combine with: ', other_route, other_route.route_signal)
                print('       are neighbors? ', self, self.route_signal, edge.head, other_route,
                      other_route.route_signal)
                if cost := self.are_neighbors(other_route):
                    print('        yes')
                    # print(f'  -> arg route from {self.wp} to {edge.head} in context of '
                    #  f'{other_route.print_route()}')
                    other_route.add_new_route(self, ARGUMENT, cost)

        print(f'   {self.sg}: checking adj routes from {self}  ({self.wp})')
        for edge in self.wp.li.adjunct_to:
            other = edge.end
            print(f'     this {self.wp} in {self} could be adjunct for {other}')
            if other.signal in self.signals:
                print('     other is already part of this route: ', other, self)
                continue
            for other_route in other.li.routes_down:
                if other != other_route.wp:
                    #print('   skip adjunction, other route has different wp to edge.start: ', edge, other_route.wp)
                    continue
                print('     are neighbors? ', self, self.route_signal, other, other_route, other_route.route_signal)
                if cost := self.are_neighbors(other_route):
                    print('      yes')
                    if not self.adjunct_agrees(other_route):
                        print('     satisfied adjunct in ', other_route, ' disagrees with proposed adjunction: ', self.wp)
                        continue
                    print(f'     <-> adj route from {other} to {edge.end} in context of {other_route.print_route()}')
                    other_route.add_new_route(self, ADJUNCTION, cost)

        wp = min([self.wp] + [route.wp for route in self.adjuncts])
        print(f'   {self.sg}: checking part routes from {self}  ({wp})')
        for edge in wp.li.edges_in:
            if isinstance(edge, LexEdge) and wp.signal - 1 in edge.activations:
                prev_wp = ctrl.words.word_parts[wp.signal - 2]
                for other_route in prev_wp.li.routes_down:
                    if prev_wp == other_route.wp:
                        other_route.add_new_route(self, PART)

        print(f' {self.sg}: done checking routes from {self}')
        if ctrl.g.counter == BREAKPOINT:
            print('**** at breakpoint ****')
