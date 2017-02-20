import app.model.dto as dto


class DTOParser:
    class Vrsta:
        JSON, XML = range(2)

    def parser_factory(self, key):
        if key == "odgovornoTijeloId":
            return OdgovornoTijeloParser(self.vrsta)
        elif key == "metodaId":
            return MetodaParser(self.vrsta)
        elif key == "mjerneJediniceId":
            return MjerneJediniceParser(self.vrsta)
        elif key == 'komponentaId':
            return KomponentaParser(self.vrsta)
        elif key == 'postajaId':
            return PostajaParser(self.vrsta)
        elif key == 'programMjerenjaId':
            return ProgramMjerenjaParser(self.vrsta)
        else:
            raise NotImplementedError

    def __init__(self, vrsta):
        parseri = [self.parseJson]
        self.vrsta = vrsta
        self.parse = parseri[vrsta]


class ProgramMjerenjaParser(DTOParser):
    def parseJson(self, json):
        m = dto.ProgramMjerenja()
        m.id = json['id']
        m.komponenta = self.parser_factory('komponentaId').parse(json['komponentaId'])
        m.metoda = self.parser_factory('metodaId').parse(json['metodaId']) if json['metodaId'] is not None else None
        m.pocetak_mjerenja = json['pocetakMjerenja']
        m.postaja = self.parser_factory('postajaId').parse(json['postajaId'])
        m.prikaz_web = json['prikazWeb']
        m.usporedno = json['usporednoMjerenje']
        return m


class PostajaParser(DTOParser):
    def parseJson(self, json):
        m = dto.Postaja()
        m.geogr_duzina = json['geogrDuzina']
        m.geogr_sirina = json['geogrSirina']
        m.id = json['id']
        m.kratka_oznaka = json['kratkaOznaka']
        m.nacionalna_oznaka = json['nacionalnaOznaka']
        m.nadmorska_visina = json['nadmorskaVisina']
        m.naziv_postaje = json['nazivPostaje']
        m.odgovorno_tijelo = self.parser_factory('odgovornoTijeloId').parseJson(json['odgovornoTijeloId'])
        m.oznaka_postaje = json['oznakaPostaje']
        return m


class KomponentaParser(DTOParser):
    def parseJson(self, json):
        m = dto.Komponenta()
        m.eol_oznaka = json['eolOznaka']
        m.formula = json['formula']
        m.id = json['id']
        m.iso_oznaka = json['isoOznaka']
        m.izrazeno_kao = json['izrazenoKao']
        m.konv_v_u_m = json['konvVUM']
        m.mjerne_jedinice = self.parser_factory('mjerneJediniceId').parseJson(json['mjerneJediniceId'])
        m.naziv = json['naziv']
        m.naziv_eng = json['nazivEng']
        m.vrsta_komponente = json['vrstaKomponente']
        return m


class MjerneJediniceParser(DTOParser):
    def parseJson(self, json):
        m = dto.MjerneJedinice()
        m.id = json['id']
        m.oznaka = json['oznaka']
        return m


class MetodaParser(DTOParser):
    def parseJson(self, json):
        m = dto.Metoda()
        m.id = json['id']
        m.naziv = json['naziv']
        return m


class OdgovornoTijeloParser(DTOParser):
    def parseJson(self, json):
        m = dto.OdgovornoTijelo()
        m.adresa = json['adresa']
        m.naziv = json['naziv']
        m.email = json['email']
        m.fax = json['fax']
        m.telefon = json['telefon']
        return m


if __name__ == '__main__':
    xml = """<programMjerenjas>
    <programMjerenja>
        <id>40</id>
        <komponentaId>
            <eolOznaka>4</eolOznaka>
            <formula>PM2.5</formula>
            <id>259</id>
            <isoOznaka>39</isoOznaka>
            <izrazenoKao></izrazenoKao>
            <konvVUM>1.0</konvVUM>
            <mjerneJediniceId>
                <id>1</id>
                <oznaka>ug/m3</oznaka>
            </mjerneJediniceId>
            <naziv>lebdece cestice (&lt;2.5um)</naziv>
            <nazivEng>Particulate matter &lt; 2.5 um (aerosol)</nazivEng>
            <vrstaKomponente>75</vrstaKomponente>
        </komponentaId>
        <metodaId>
            <id>7</id>
            <naziv>Ortogonalno svjetlosno raspršenje</naziv>
        </metodaId>
        <pocetakMjerenja>2012-01-01T00:00:00+01:00</pocetakMjerenja>
        <postajaId>
            <geogrDuzina>16.1129</geogrDuzina>
            <geogrSirina>43.0296</geogrSirina>
            <id>20</id>
            <kratkaOznaka>humv</kratkaOznaka>
            <nacionalnaOznaka>HUM01</nacionalnaOznaka>
            <nadmorskaVisina>574</nadmorskaVisina>
            <nazivPostaje>Hum (Vis)</nazivPostaje>
            <odgovornoTijeloId>
                <adresa>Grič 3</adresa>
                <EMail>kakvoca_Zraka@cirus.dhz.hr</EMail>
                <fax></fax>
                <id>1</id>
                <naziv>DHMZ</naziv>
                <odgovornaOsoba>Pero Perić</odgovornaOsoba>
                <telefon>01 4565 123</telefon>
            </odgovornoTijeloId>
            <oznakaPostaje>RH0118</oznakaPostaje>
        </postajaId>
        <prikazWeb>true</prikazWeb>
        <usporednoMjerenje>0</usporednoMjerenje>
    </programMjerenja>
    </programMjerenjas>
    """

    json_string = """
    {   "id":40,
        "usporednoMjerenje":0,
        "pocetakMjerenja":1325372400000,
        "zavrsetakMjerenja":null,
        "prikazWeb":true,
        "metodaId":
            {"id":7,
            "naziv":"Ortogonalno svjetlosno raspršenje",
            "norma":null,
            "zeroDriftAbsolut":null,
            "spanDriftRelativ":null},
        "komponentaId":{
            "id":259,
            "eolOznaka":4,
            "isoOznaka":"39",
            "formula":"PM2.5",
            "naziv":"lebdece cestice (<2.5um)",
            "izrazenoKao":"",
            "vrstaKomponente":"K",
            "konvVUM":1.0,
            "nazivEng":"Particulate matter < 2.5 um (aerosol)",
            "prosijekTijekom":null,
            "mjerneJediniceId":{
                "id":1,
                "oznaka":"ug/m3"
            }
        },
        "postajaId":{
            "id":20,
            "nazivPostaje":"Hum (Vis)",
            "nazivLokacije":null,
            "nacionalnaOznaka":"HUM01",
            "oznakaPostaje":"RH0118",
            "netAdresa":null,
            "geogrDuzina":16.1129,
            "geogrSirina":43.0296,
            "nadmorskaVisina":574,
            "nutsOznaka":null,
            "stanovnistvo":null,
            "kratkaOznaka":"humv",
            "odgovornoTijeloId":{
                "id":1,
                "naziv":"DHMZ",
                "odgovornaOsoba":"Pero Perić",
                "adresa":"Grič 3",
                "telefon":"01 4565 123",
                "fax":"",
                "internetAdresa":null,
                "email":"kakvoca_Zraka@cirus.dhz.hr"
            },
            "podrucjeId":null,
            "reprezentativnostId":null,
            "vrstaPostajeIzvorId":null,
            "prometnePostajeSvojstva":null,
            "industrijskePostajeSvojstva":null
        }
    }
    """
    #    ppp = fields.List(ProgramMjerenja).parse(xml)
    import json

    js = json.loads(json_string)
    fac = ProgramMjerenjaParser(DTOParser.Vrsta.JSON)
    programi = fac.parse(js)
    print(programi)
