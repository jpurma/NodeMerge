
test_lexicon = """
sopimus :: N:nom3sg adjL:D|a =T:a-inf
ihailla :: T:a-inf, v =N:prt =N:lla
#ihaili :: =N:nom3sg T:pst, =N:prt
sitä :: N:prt a:D|n
Merjaa :: N:prt adjL:D <N:gen a:n
#Minttua :: N:prt adjL:D <N:gen a:n
jonka :: adjL:n =T, N:acc
Pekka :: N:nom3sg n a:n
näki :: =N:nom3sg T:pst, =N:prt|acc
peruuntui :: =N:nom3sg T:pst
#ja :: adjL:D|n
#ei :: =N:nom3sg, =v adjL:advNeg
#enää :: a:advNeg
#rakasta :: v, =N:prt
#rakastaa :: =nom3sg T:pre, =N:prt
"""
sentence = "sopimus ihailla sitä Merjaa jonka Pekka näki peruuntui"


test_lexicon2 = """
Pekka :: N:nom3sg n a:n
ihaili :: =N:nom3sg T:pst, =N:prt
Merjaa :: N:prt adjL:D <N:gen a:n
ja :: adjL:D|n
Minttua :: N:prt adjL:D <N:gen a:n
"""

test_lexicon3 = """
Pekka :: N:nom3sg n a:n
teki :: T:pst =N:nom3sg, =N:acc|prt
hyvän :: a:acc|gen
sopimuksen :: N:acc adjL:acc|gen =T:a-inf
antaa :: T:a-inf =N:gen, v =N:acc|prt =N:lle =N:lla
avaimen :: N:acc adjL:acc|gen =T:a-inf
Merjalle :: N:lle
"""


test_lexicon = """
Pekka :: N:nom3sg a:n
sanoi :: T:pst =N:nom3sg, =N:acc|prt a:t
että :: adjL:n|t =T, N:pass
se :: N:nom3sg a:n
väite :: N:nom3sg a:n adjL:n
että1 :: adjL:n|t =T, N:pass
teoria :: N:nom3sg a:n adjL:n
kumoutui :: =N:pass T:pst, =N:nom3sg
hylättiin :: =N:pass T:pst, =N:nom3sg
"""
sentence = "Pekka sanoi että se että teoria kumoutui kumoutui"
sentence = "Pekka sanoi että se väite että1 teoria hylättiin kumoutui"
sentence = "Pekka sanoi että se väite että1 teoria kumoutui hylättiin"

test_lexicon = """
Pekka :: N:nom3sg a:n
sanoi :: T:pst =N:nom3sg, =N:prt =rel:että a:t
että :: rel:että adjL:n, N:pass
hylättiin :: =N:pass T:pst, =N:nom3sg
se :: N:nom3sg a:n
väite :: N:nom3sg a:n adjL:n, =rel:että 
että1 :: rel:että adjL:n
teoria :: N:nom3sg a:n adjL:n
kumoutui :: =N:pass T:pst, =N:nom3sg
"""
sentence = "Pekka sanoi että se väite että1 teoria kumoutui hylättiin"
sentence = "Pekka sanoi että hylättiin se väite että1 teoria kumoutui"
sentence = "hylättiin se väite että teoria kumoutui"
sentence = "Pekka sanoi että se väite hylättiin että teoria kumoutui"
sentence = "Pekka sanoi että se väite että teoria kumoutui hylättiin"
test_lexicon = """
Pekka :: N:nom3sg a:n
sanoi :: T:pst =N:nom3sg, =N:prt =rel:että a:t
että :: rel:että adjL:n, =T
se :: N:nom3sg a:n
väite :: N:nom3sg a:n adjL:n, =rel:että 
teoria :: N:nom3sg a:n adjL:n
kumoutui :: =N:pass T:pst, =N:nom3sg
hylättiin :: =N:pass T:pst, =N:nom3sg
"""


"""
minkä Merja muisti että Pekka oli unohtanut jos olisi niin että relatiivilauseella tai kysymyslauseella 
relatiivi/kysymyssana ei pyydä verbiä, vaan yhteys tulee vain ja ainoastaan siitä että sanaa käytetään myöhemmin 
lauseessa. 

minkälainen suhde on relatiivipronominin ja pääsanan välillä? Se on aina tiukasti (head, rel), väliin ei mahdu 
mitään. Tai mahtuu ehkä, "Sofia pieni, joka..." olettaen että Sofia on pääsana tässä. Järjestyksen pitää ainakin 
olla noin, ei onnistu jos on relatiivilause ensin ja sitten pääsana. Ei myöskään onnistu yhden sanan 
relatiivilauseet tai relatiivilauseet joissa relatiivipronominia ei käytetä. Yksinäiset relatiivipronominit kyllä 
onnistuvat lauseen alussa: 'Joka etsii puita voi löytää karhun', mutta ei lauseen sisällä '*Pekka etsi jota 
rakastaa' - ei onnistu vaikka sijamuodon perusteella relatiivipronomini sopisi kumpaankin lauseenosaan. Muistetaan 
myös, että relatiivipronominin ei tarvitse olla sijamuodoltaan sama kuin pääsanansa. Jos relatiivipronomini on 
kompleksi adjunkti 'jota :: a:rel, N:prt' niin silloin saavutetaan tuo läheltä kiinnittyminen pääsanaan, 
mutta puuttuu syy miksi relatiivilause tarvitsee verbin ja mikä estää sitä etsimästä argumentteja päälauseesta. 
Toimisiko se yleensä, jos 'X (X)' -rakenteen jälkeen ei voisi katsoa (X):ää edemmäksi? Jos 'X' on käytössä. 

Pitääkö käsitellä erilaisina tilanteet joissa X (X):ssä (X) on pää joka etsii argumenttia vai argumentti joka etsii
päätä? Jos se on pää joka etsii argumenttia tällä rajoituksella, niin 'ketä Merja rakastaa (rakastaa)' ei löydä 
'ketä', se ei pääse yli ensimmäisestä 'rakastaa'. Tämä tarvitaan. Jotenkin pitäisi kuitenkin estää ettei 
relatiivipronominin jälkeen etsitä siitä vasemmalle. Halutaan että kun on 'v<-Y+joka (joka)' niin (joka) ei voi 
tarttua v:hen. Sen pitäisi toteutua jo sillä että Y on v:n argumentti.  

Mitenkäs tämä: 'Pekka sanoi (sanoi) että (että) se väite että (että)

"sanoi1 (sanoi)2 että3 (että)4 hylättiin5": ongelma on miten estää ettei 'että3' ota edeltävää 'sanoi1' 
argumentiksi vaan malttaa odottaa seuraavaan 'hylättiin'. 
"""

xtest_lexicon = """
Pekka :: N:nom3sg a:n
sanoi :: T:pst =N:nom3sg, =N:prt =rel:että a:t
että :: rel:että adjL:n, =T
Merja :: N:nom3sg a:n
rakasti :: T:pst =N:nom3sg, =N:prt a:t
Minttua :: N:prt a:n
"""
xsentence = "Pekka sanoi että Pekka sanoi että Merja rakasti Minttua"
