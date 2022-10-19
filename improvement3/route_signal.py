from enum import Enum


class Relation(Enum):
    SIGNAL = 0
    HEAD = 1
    PART = 2
    ADJUNCT = 3


class RouteSignal:
    def __init__(self, source=None, relation=Relation.SIGNAL, signal=None, li=None):
        """ source: where this route is coming from,
         target: where this route is going to.
         the first part of a route has no source or target but it has a signal and li that it represents.
         """
        self.source = source
        self.relation = relation
        self.li = li
        self.signal = signal
        if self.source:
            print(f'creating RS from {self.source} to {self.li}-{self.signal}, ({self.relation.name})')
        else:
            print(f'creating RS {self.li}-{self.signal} ({self.relation.name})')

    def __contains__(self, item):
        return item == self.signal or (self.source and (item == self.source or item in self.source))

    def __eq__(self, other):
        if not isinstance(other, RouteSignal):
            return self.signal == other
        return self.relation == other.relation and self.signal == other.signal and self.source == other.source

    def __str__(self):
        if self.relation == Relation.SIGNAL:
            return str(self.signal)
        elif self.relation == Relation.HEAD:
            return f'({self.source}->{self.signal})'
        elif self.relation == Relation.PART:
            return f'{self.signal}.{self.source}'
        elif self.relation == Relation.ADJUNCT:
            return f'{self.source}=={self.signal}'

    def __repr__(self):
        return str(self)

    def head_first(self):
        if not self.source:
            return True
        if self.signal and self.source:
            return self.signal < self.source.signal

    def words(self):
        if not self.source:
            return self.li.word
        source_words = self.source.words()
        if head_first := self.head_first():
            first = self.li.word
            second = source_words
        else:
            first = source_words
            second = self.li.word
        if self.relation == Relation.HEAD:
            return f'({first}<-{second})' if head_first else f'({first}->{second})'
        elif self.relation == Relation.PART:
            return f'{first}.{second}' if head_first else f'{first}.{second}'
        elif self.relation == Relation.ADJUNCT:
            return f'{first}<=={second}' if head_first else f'{first}==>{second}'

    def find_label(self):
        if self.relation == Relation.ADJUNCT:
            if self.head_first():
                return f'{self.li.word}+{self.source.find_label()}'
            return f'{self.source.find_label()}+{self.li.word}'
        return self.li.word

    def tree(self):
        if not self.source:
            return self.li.word
        source_tree = self.source.tree()
        label = self.find_label()
        if self.head_first():
            return f'[.{label} {self.li.word} {source_tree}]'
        return f'[.{label} {source_tree} {self.li.word}]'

    # onko ainoa paikka jossa aukko sallitaan sellainen jossa sananosa annetaan verbille argumentiksi ja se
    # sananosa ei voi toimia pääsanana muille rakenteille?
    # Jos noin, niin miten toimisi rakenne 'kuinka paljon Pekka maksoi?' 'kuinka uuden auton Pekka osti?'
    # niissä voisi olla että kuinka1.kuinka'2<-paljon3 ja kuinka1.kuinka'2<-uuden3=auton4
    # Tuossa tulee se, että tuo wh ja wh' täytyy pitää erillään niin kauan kun niitä rakennetaan,
    # jotta wh' voi toimia liitoksen kohteena (argumenttina tai pääsanana noille). Toisaalta wh' ei saa olla
    # irrallinen liian pitkään eikä olla saatavilla kaikissa konteksteissa. Mitenkähän se rajautuu?
    # 1. 'Kenelle Pekka joka lähetti kirjeen meni nukkumaan' <-- ei voi tehdä tulkintaa että 'kirjeen kenelle'.
    # 2. 'Kenelle Pekka näki Merjan, joka lähetti kirjeen' <-- ei voi tehdä tulkintaa että 'kirjeen kenelle'.
    # 3. 'Kenelle Pekka näki Merjan lähettävän kirjeen' <-- voi tehdä tulkinnan 'kirjeen kenelle'
    # Helpointa olisi jos voisi todeta että relatiivilause ei ole tuossa vaiheessa vielä liitetty alisteiseksi
    # päälauseelle ja siksi siirtymä olisi mahdoton aukon takia. Siinä on ongelmana että tuota liittämistä ei voi
    # nyt erottaa niistä liitoksista joissa haluamme tunnistaa että tässä ollaan tekemässä yhtenäistä rakennetta.

    # Huomataan että on joitain rakenteita jotka muistuttavat relatiivirakenteita, mutta joissa sallitaan kysymyksen
    # viittaus sisälle: Mitä Pekka tiesi että Merja etsi? Tuossa on se ero, että siinä ei itsessään ole siirtyvää
    # sananosaa. Voisi olla siirtyvät sananosat jotenkin erilaisia kuin sananosat yleensä. Se auttaisi myös rajaamaan
    # mahdollisia yhteyksiä.
    #
    # Sananosa joka voi liikkua estää myös toisen sananosan liikkumisen sen yli. Kun rakenteet perustuvat yhteyksiin
    # sen säännön totetuttaminen vaatii vähän outoutta. Se on outo, koska se sääntö on riippumaton rakenteesta,
    # kun taas normaalisti sanan yhteys on sen naapurirakenteeseen, mutta se on moniselitteinen tilanne koska emme
    # tiedä mitkä ovat naapurirakenteita ennenkuin rakenteet voidaan rakentaa. Siirtyvä elementti synnyttää vähemmän
    # vaihtoehtoja kuin elementti jonka pitäisi viitata vain naapuriinsa.

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

    def signals_excluding_movers(self):
        if self.relation == Relation.SIGNAL:
            if self.li.is_free_to_move():
                return set()
            return {self.signal}
        return self.target.signals_excluding_movers() | self.source.signals_excluding_movers()

    def signals_in_order(self):
        if self.relation == Relation.SIGNAL:
            return [self.signal]
        return self.target.signals_in_order() + self.source.signals_in_order()

    def clumped_signals_in_order(self, part_map: dict):
        if self.relation == Relation.SIGNAL:
            return [part_map[self.signal]]
        return self.target.clumped_signals_in_order(part_map) + self.source.clumped_signals_in_order(part_map)

    def cost(self, part_map: dict):
        """ part_map is mapping from signal indices to word indices, so that eg. if "sanoi", "sanoi'", "eilen" are
        signals 1, 2, 3 then their word indices are 0, 0, 1. Word parts belonging to the same word have same word
        index. This prevents multipart words from causing additional costs on movement. """
        if self.relation == Relation.SIGNAL:
            return 0
        source_word = self.source.find_word()
        if source_word.li.is_word_head():
            source = part_map[source_word.signal]
            target = part_map[self.target.find_word().signal]  # min(self.target.signals())
            min_edge = part_map[min(self.source.signals())]
            max_edge = part_map[max(self.source.signals())]
            cost = min(abs(target - source), abs(target - min_edge), abs(target - max_edge))
            if cost > 0:
                cost -= 1
            #print(target, (min_edge, source, max_edge), cost)
            fine_cost = abs(self.target.find_word().signal - self.source.find_word().signal)
            if fine_cost > 1:
                cost += (fine_cost - 1) / 10
        else:
            cost = 0
        return cost + self.target.cost(part_map) + self.source.cost(part_map)

    def compatible_with(self, other):
        return not self.signals() & other.signals()

    # Route building -- this is kind of external logic that should be eventually implemented without relying to
    # RouteSignals and their kind of procedural computation.

    def continue_routes(self, li, signal, part_map=None):
        def _is_part_of_route(_signal, route):
            if not route:
                return False
            return _signal in route

        def get_previous_part():
            if li.lex_parts and (part_index := li.lex_parts.index(li)):
                return li.lex_parts[part_index - 1]

        def close_enough(other):
            # self is argument, other is head
            # Eli sääntö olisi että jos argumentti B etsii päätä A niin sopiva A on sellainen jonka hallitsema rakenne
            # on B:n hallitseman rakenteen vieressä jommallakummalla puolella.
            # Kun tätä käytetään, other ei saisi olla yksittäinen sananosa, vaan sen pitäisi olla reitti jotta
            # tiedetään mitkä osat ovat alisteisia sille.
            # Meneekö tuo oikein päin? Onko other:lla alisteisia osia? On, jos meillä on esimerkiksi kolmiosainen
            # verbi Pekka ostaa Merjalle kukkia, niin siinä halutaan käyttää 'ostaa Merjalle' kun arvioidaan onko
            # 'kukkia' verbin vieressä. Missä kohtaa parserointia tämä tieto olisi saatavilla? Pitää mennä
            # walk_routes_up_from -metodiin selvittämään tätä.
            print(f'close enough: arg: {li} rs: {self} {self.signals()} head: {other} {other.signal} {other.li}')
            return True

        def close_enough_old(other):
            USE_WORD_PARTS = True
            # self is argument, other is head
            # Eli sääntö olisi että jos argumentti B etsii päätä A niin sopiva A on sellainen jonka hallitsema rakenne on B:n
            # hallitseman rakenteen vieressä jommallakummalla puolella.
            print(f'  close_enough? {li.word=} {other=}, {self=}, {self.source=}, rs.words()="{self.words()}", '
                  f'rs.signals()'
                  f'={self.signals()}'
                  f' rs.find_head()={self.find_head()}, {other.signal=}')
            print('    rs.source.find_head=', self.source and self.source.find_head())
            if other.li.is_free_to_move():
                print('    can be used, other is mover')
                return True
            rs_signals = self.signals_excluding_movers()
            if not rs_signals:
                print('    can be used, is mover')
                return True
            if USE_WORD_PARTS:
                rs_min = part_map[min(rs_signals)]
                rs_max = part_map[max(rs_signals)]
                w_signal = part_map[signal]
                w_other = part_map[other.signal]
            else:
                rs_min = min(rs_signals)
                rs_max = max(rs_signals)
                w_signal = signal
                w_other = other.signal
            if (w_other == rs_min or w_other == rs_max) and not other.li.is_free_to_move():
                print(f'    already part of the same structure, arg: {li.word}-{signal}({rs_min}-{w_signal}'
                      f'-{rs_max}) head: {other} ({w_other})')
                return False
            if w_other == rs_min - 1 or w_other == rs_max + 1:
                print(f'    other is next to rs construction, ok')
                return True
            elif rs_min < w_other < rs_max:
                print(f'    other is within rs construction, is this ok?')
                return True
            print(f'    too far away, arg: {li.word}-{signal}({rs_min}-{w_signal}-{rs_max}) head: {other}'
                  f'({w_other}) (return True anyway)')
            return True

        if prev_part := get_previous_part(): # and not self.is_free_to_move():
            if not _is_part_of_route(signal - 1, self):
                new_rs = RouteSignal(source=self, target=prev_part.rs, relation=Relation.PART)
                prev_part.li.walk_all_routes_up_from(new_rs)
            if not li.is_free_to_move():
                print("Stop processing for word part ", li)
                return

        for edge in li.adjunctions:
            if edge.start.signal == signal:
                other_adjunct = edge.end
                if not _is_part_of_route(other_adjunct.signal, self) and close_enough(other_adjunct):
                    assert not {other_adjunct.signal} & self.signals()
                    print('doing adjunct,', li, ' walking up target ', other_adjunct.signal, ' edge: ', edge)
                    new_rs = RouteSignal(source=self, target=other_adjunct.rs, relation=Relation.ADJUNCT)
                    other_adjunct.li.walk_all_routes_up_from(new_rs)
        for edge in li.head_edges:
            head = edge.end
            if not _is_part_of_route(head.signal, self) and close_enough(head):
                new_rs = RouteSignal(source=self, target=head.rs, relation=Relation.HEAD)
                head.li.walk_all_routes_up_from(new_rs)

    def walk_all_routes_up_from(self, li): #relation, source=None, target_signal=None, part_map=None):
        # muistetaan se metafora että kulkiessaan reittiä ylös muurahaiset kirjoittavat noodiin mistä tulivat,
        # tähänastisen reittinsä. Jos wp:lle kirjoitetaan monia pitkiä reittejä, se saattaa tarkoittaa että tämä on
        # koko lauseen pääsana.

        # Reitin pohjimmainen jäsen kertoo siis sen, mistä reitti sai alkunsa -- jostakin argumentista.
        # Reitin viimeinen jäsen on se sana minne tämä reitti päädytään kirjoittamaan.
        #
        # Jos reitti jatkaa jo olemassaolevaa reittiä kyse on tilanteesta jossa esim. sanojen 1 ja 2 jälkeen
        # reittiä ei voitu tehdä pitemmälle, mutta kun tuli sana 4 niin se mahdollisti uuden pitemmän reitin ja
        # nyt se [1, 2] korvataan sillä uudella.
        #
        # Hm, ylläoleva ei oikein toimi ajatuksena. Kun reitti aina päättyy nykyiseen wp:hen, niin ei voi olla
        # tällä wp:llä toista reittiä joka olisi sisältynyt uuteen reittiin: vanha: [...x, wp] ja uusi: [...x, y,
        # wp]
        #
        # Taitaa olla että reitin jatkamiseen liittyvä vertailu tehtiin vain väärinpäin, unohtui tuo metafora
        # joka piti muistaa. Reitti kun esitetään listana, jossa viimeinen elementti on tämä
        # tämänhetkinen wp ja jos reittiä jatketaan, sitä pitäisi jatkaa listan alusta. Käännetäänpä vertailu.

        # J: Jos olemme argumentissa A niin säilötäänkö tänne reitteihin reitit tästä eteenpäin vai reitit tänne?
        # K: Reitit tänne.
        # target on aina yksinkertainen signaali, source voi olla
        # J: jos on kaksi instanssia samasta sanasta, niin miten erotetaan kumman reittejä jatketaan?

        # siinä kohtaa kun li:lle lisätään uusi reitti olisi mahdollisuus vertailla onko uusi reitti yhteensopiva
        # vanhojen kanssa ja luoda mahdolliset yhdistelmät.

        # 'Merja who he saw admiring him' tuottaa vaikeuksia, koska siinä "who'" siirtyy ja paikassa johon se siirtyy
        # se toimii sekä argumenttina että pääsanana joka ottaa argumentteja. Tuo että se ottaa omia argumentteja
        # tapahtuu paikassa johon se on siirtynyt, mikä vihjaisi että siirtyminen tapahtuu enemmän oikeasti kuin
        # tähän mennessä olen olettanut. Vaihtoehtoja olisi että on joku laskennallinen välimuoto, jossa "who'" on
        # lähimpänä äskeisen argumentiiksi ottamisen jäljiltä, tai että tapa jolla sanat etsivät sitä mille ne ovat
        # argumentteja on aina kantamaltaan riittävä selvitäkseen näistä.

        # 'Who does Pekka admire' päätyy tulkintaan, jossa "who'" on does:n subjekti ja Pekka admire:n objekti. Tämä
        # estyisi jos "admire'" ei voisi ottaa argumenttia edestään, ellei se ole liikkuva. Eli jos on "Pekka1 admire2
        # admire'3" niin 1->3 on liian pitkä matka. Ei auta vaikka 2 on samaa sanaa kuin 3. Joitakin toisia
        # tilanteita varten on laitettu laskenta jossa sananosia ei lasketa etäisyyttä laskiessa, mutta tässä kohtaa
        # sillä keinoin saisi syntymään tarvittavan esteen. Ei, tämä ei toimi. Parempi este olisi jos who does Pekka
        # admire ei suostu yhdistämään does - admire, koska välissä on Pekka. Pitää saada [.does does Pekka] admire
        # jotta ovat tarpeeksi lähellä. Tässä taas on pulmana että yhdistäminen onnistuisi sen jälkeen kun on tehty [
        # .admire Pekka admire]. Tarkistuksen täytyisi olla luonteeltaan epäsymmetristä.

        # 15.10. 2022 Jatkaessamme reittiä pitäisi arvioida onko tietty noodi hyvä kohde reitin jatkamiselle. Noodi
        # ei kuitenkaan itsessään vielä riitä tämän arvion tekemiseen, pitäisi myös tietää mitä reittejä noodilla on.

        new_routes = [self]
        if self.relation == Relation.ADJUNCT:
            print('at adjunct ', self, ' it has source: ', self.source, ' and target: ', self.target)
            other_li = self.source.find_head().li
            if self not in other_li.routes_up:
                other_li.routes_up.append(self)
                print('sharing adjunct to source head: ', self.source.find_head(), other_li.routes_up)
        if self.source:
            # taustaa: olemme saapumassa tähän noodiin (self-target-signal) source-noodista. Tämä source saattaa olla
            # osa pitempää ketjua. Source voi olla vaikka "ihailee'-4" ja tämä target on "ihailee-3". On kuitenkin
            # toisia reittejä jotka myös päätyvät tähän 'ihailee-3' kuten "Pekka-2" ja nämä reitit ovat yhteensopivia
            # tämän kanssa.

            # Kysymys nyt on pitääkö näitä käsitellä molempiin suuntiin, niin että meillä on 3.4 ja halutaan liittää
            # siihen 2->3, vai riittääkö että on 2->3 johon halutaan liittää 3.4. Tilanne jossa sananosat on
            # jo yhdistetty ja halutaan mutkistaa sananosan argumenttirakennetta syntyy aina jos edellisen sananosan
            # argumentti tulee joskus myöhemmin. Jos on vaikka 1.2 niin jos argumentti 1:lle on 3 niin silloin se
            # pitää ujuttaa mukaan kun 1.2 on jo tehty.
            # Mutta ei sen tarvitsisi koska se tekisi 1.2 -yhteyden uudestaan päästyään tuohon kohtaan. Ei,
            # kyllä tarvitsee koska oikeasti kyseessä on 2.1 yhteys, 1 on target ja 2 on source. Se ei jatkaessaan
            # rakentamista tekisi 1.2 yhteyttä, se yhteys tehdään 2:n toimesta.
            # Mutta miksi esimerkkilauseeni ei tarvitse tätä tilannetta? Hoituuko tuo sillä että uudelleenlasketaan
            # aiempia reittejä ja sovelletaan tuota toista tapausta?
            # Jatkokysymys: onko nyt tuo reittien uudelleenlaskenta tarpeen vai riittäisikö näillä korvaussäännöillä
            # puuhaaminen?
            # Tarve aiemman reitin uudelleenlaskennalle syntyy siitä, että aiempi elementti voi käyttää uudempaa
            # elementtiä kohteena/päänä. Jos tuon korjaisi tapauskohtaiseksi niin silloin tämä polkujen kulkeminen
            # pitäisi tehdä kaksisuuntaiseksi, kulkea kohteesta/päästä aiempaan elementtiin. Se olisi neuraalisesti
            # vaativa, helpompi olettaa että reitit 'sykkivät' niin että uuden reitin avautuminen tulee huomattua.

            # jos on vaikka 4->3 ja ..2.3 niin pitäisi olla mahdollista yhdistää ne reitiksi 2.(4->3)
            # samaten jos on 4->3 ja 2==3 niin pitäisi tulla myös (4->2==3)
            # muut yhdistelmät ovat mielettömiä.
            #
            # Mutta sen jälkeen pitäisi voida nähdä (4->2==3) niin, että sen pää on 3 tai 2. Nyt bugittaa kun
            # jatkaa vain tapauksista joissa pää on 2.

            # Seuraavaksi pitäisi estää tulkinta "[.saw' [.Merja Merja [.who who [.saw who' saw]]] saw']" jossa saw'
            # ottaa aiemman lauseen argumentiksi. Miksei siinä ole realisoitunut saw.saw'?

            # Tuossa tapauksessa ollaan tulossa jälkimmäisestä saw':sta ja sillä on kaikki ne rakenteet jotka sillä
            # pitää olla. Sillä ei ole muuta vaihtoehtoa kuin edetä saw:iin.

            # Miten on tarkoitus selvitä tilanteesta
            for old_rs in li.routes_up:
                # print('checking old rs ', old_rs, ' vs new rs ', rs)
                # Vanha tapaus: 2.3, uusi rs 4->3, haluttu tulema 2.(4->3)
                # ilmeisesti tätä ei tarvita
                # if old_rs.relation == Relation.PART and rs.relation == Relation.HEAD and rs.compatible_with(
                #         old_rs.source):
                #     new_rs = RouteSignal(source=old_rs.source, target=rs, relation=Relation.PART)
                #     if new_rs not in new_routes:
                #         if new_rs not in self.routes_up:
                #             print(f'{target_signal}: case 1, old word part relation: combine existing {old_rs} '
                #                   f'={old_rs.source} and current {rs} creating {new_rs}, {new_rs.words()}')
                #             #raise hell
                #         new_routes.append(new_rs)
                # Vanha tapaus: 4->3, uusi 2.3, haluttu tulema 2.(4->3)
                if self.relation == Relation.PART and old_rs.relation == Relation.HEAD and old_rs.compatible_with(
                        self.source):
                    new_rs = RouteSignal(source=self.source, target=old_rs, relation=Relation.PART)
                    if new_rs not in new_routes:
                        if new_rs not in li.routes_up:
                            print(f'{self.target_signal}: case 2, new word part relation: combine existing {old_rs} '
                                  f'={old_rs.source} and current {self} creating {new_rs}, {new_rs.words()}')
                        new_routes = [new_rs]
                        #new_routes.append(new_rs)
                # Vanha tapaus 2==3, uusi 4->3, haluttu tulema 4->2==3
                # ilmeisesti tätä ei tarvita
                # if old_rs.relation == Relation.ADJUNCT and rs.relation == Relation.HEAD and rs.compatible_with(
                #         old_rs.source) and False:
                #     new_rs = RouteSignal(source=old_rs.source, target=rs, relation=Relation.ADJUNCT)
                #     if new_rs not in new_routes:
                #         if new_rs not in self.routes_up:
                #             print(f'{target_signal}: case 3, old adjunct relation: combine existing {old_rs} '
                #                   f'={old_rs.source} and current {rs} creating {new_rs}, {new_rs.words()}')
                #         new_routes.append(new_rs)
                # Vanha tapaus 4->3, uusi 2==3, haluttu tulema 4->2==3
                elif self.relation == Relation.ADJUNCT and old_rs.relation == Relation.HEAD and \
                        old_rs.compatible_with(self.source):
                    new_rs = RouteSignal(source=self.source, target=old_rs, relation=Relation.ADJUNCT)
                    if new_rs not in new_routes:
                        if new_rs not in li.routes_up:
                            print(f'{self.target_signal}: case 4, new adjunct relation: combine existing {old_rs} '
                                  f'={old_rs.source} and current {self} creating {new_rs}, {new_rs.words()}')
                        new_routes.append(new_rs)
        real_new_routes = [route for route in new_routes if route not in li.routes_up]
        if real_new_routes:
            print(f'{self.target_signal}: adding routes')
        for rs in real_new_routes:
            print(f'  {self.target_signal}: {self}')
        li.routes_up += real_new_routes
        for rs in new_routes:
            if rs.relation == Relation.ADJUNCT:
                if rs.target_signal == rs.source.find_head().signal:
                    other_wp = rs.target.find_head()
                else:
                    other_wp = rs.source.find_head()
                print('would do adjunct, this: ', rs.target_signal, ', source head: ', rs.source.find_head().signal,
                      ' target head: ', rs.target.find_head().signal)
                print('continue routes ', rs, other_wp)
                other_wp.rs.continue_routes(other_wp.li, other_wp.signal)
            print('continue route ', rs, rs.target_signal)
            rs.continue_routes(rs, rs.target_signal)

