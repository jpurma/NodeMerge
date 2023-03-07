SIGNAL_TREE = False

ARGUMENT = 'argument'
ADJUNCTION = 'adjunction'
PART = 'part'


class RouteSignal:
    """ RouteSignal is a minimal representation of Route that should eventually replace Route. Parsing should be
    possible by doing computation in nodes with RouteSignals representing the parse states."""
    def __init__(self, route, part, arg, adjunct):
        # routesignal tapahtuu aina jossain noodissa, jolloin li on saatavilla siitä. signal on joko annettuna koska
        # ollaan kärjessä joka aktivoitui tai sitten tämä aktivoituu toisen RS:n toimesta jolloin se aktivoi tietyn
        # sopivan signaalin li:n signaaleista.
        # muista signaaleista tarvitaan ne, jotka ovat näkyvissä merge-kohteina argumenteille, adjunkteille tai
        # sananosille.
        # on epävarmaa tarvitaanko myös kaikki signaalit jotka tähän asti on kerätty: voi olla että tarvitaan jotta voi
        # todistaa että reitti kattaa kaikki noodit, vaikkakin se itse todistus on vaikea oikeuttaa ja toteuttaa
        # noodeilla. Voi myös olla että tarvitaan jottei noodia käytetä uudestaan.
        # tärkein kysymys on mitkä signaaleista ovat näkyvissä merge-kohteina.
        # näkyvissä kenelle? routesignal on yksi muurahainen joka on päässyt noodiin ja se etsii mihin mennä
        # seuraavaksi. sen oma routesignal sulkee joitakin vaihtoehtoja pois, koska siellä on jo käyty. Ei,
        # reitti mahdollistaa mihin mennä seuraavaksi koska reitti määrittelee sen mitkä signaalit ovat sen naapureita.
        # yksinkertaisimmassa tapauksessa reitti määrittäisi reunansa olemalla joukko vierekkäisiä noodeja {2, 3, 4}
        # jossa mahdolliset naapurit olisivat 1 ja 5. Ja tuollainen joukko olisi kuvattavissa (2, 4). Sitä mutkistaa
        # vähäsen adjunktit ja vähän enemmän liikkuvat elementit. Mutkistavatko adjunktit sitä? Ne ovat vielä
        # nuukempia sille ketä päästävät naapurikseen ja ne muodostuvat osaksi tuota naapurirakennetta. Joten
        # oletetaan että eivät mutkista. Miten liikkujat mutkistavat tuota? Liikkujat muodostavat oman mahdollisen
        # naapurinsa. Kun liikkuja kerää määreitä, mahdollinen naapuri siirtyy olemaan liikkujan reuna.
        #
        # - signaali johon ollaan saavuttu
        #
        if route.parent:
            self.low = route.parent.route_signal.low
            self.high = route.parent.route_signal.high
            self.movers = set(route.parent.route_signal.movers)
            self.used_movers = set(route.parent.route_signal.used_movers)
        else:
            self.low = route.wp.signal
            self.high = route.wp.signal
            self.movers = {route.wp.signal} if route.wp.li.is_free_to_move() else set()
            self.used_movers = set()
        if part:
            print('     rs: adding part ', part, part.route_signal, ' to ', route.parent, self)
            self.movers |= part.route_signal.movers
            self.used_movers |= part.route_signal.used_movers
            self.high = part.route_signal.high
        if arg:
            print('     rs: adding argument ', arg, arg.route_signal, ' to ', route.parent, self)
            if self.movers or arg.route_signal.movers:
                print(' rs: arg w. mover:', self.movers, arg.route_signal.movers, arg.wp, route.wp)
            self.movers -= arg.route_signal.used_movers
            self.used_movers |= arg.route_signal.used_movers
            if arg.wp.signal in self.movers:
                print('     rs: **** using and removing mover from self')
                self.movers.remove(arg.wp.signal)
                self.used_movers.add(arg.wp.signal)
            elif arg.wp.signal in arg.route_signal.movers:
                print('     rs: ** merging mover argument, skip it from lowest count. arg: ', arg.route_signal)
                self.used_movers.add(arg.wp.signal)
            else:
                self.low = min(self.low, arg.route_signal.low)
            self.high = max(self.high, arg.route_signal.high)
        if adjunct:
            print('     rs: adding adjunct ', adjunct, adjunct.route_signal, ' to ', route.parent, self)
            self.low = min(self.low, adjunct.route_signal.low)
            self.high = max(self.high, adjunct.route_signal.high)
            if adjunct.route_signal.movers:
                self.movers.add(route.wp.signal)
                print('     rs: adding ', route.wp.signal, ' to movers', self.movers)
        print('rs result: ', self)

    def __repr__(self):
        return f'<RouteSignal low:{self.low}, high:{self.high}, movers:{self.movers}, used:{self.used_movers}>'
