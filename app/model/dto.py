import dexml
from dexml import fields

"""
Ovo su DTO klase koje odgovaraju entityjima
"""


class OdgovornoTijelo(dexml.Model):
    class meta:
        tagname = 'odgovornoTijeloId'

    # id = fields.Integer(tagname='id')
    adresa = fields.String(tagname='adresa')
    naziv = fields.String(tagname='naziv')
    # odgovorna_osoba = fields.String(tagname='odgovornaOsoba')
    email = fields.String(tagname='EMail')
    fax = fields.String(tagname='fax')
    telefon = fields.String(tagname='telefon')


class Metoda(dexml.Model):
    class meta:
        tagname = 'metodaId'

    id = fields.Integer(tagname='id')
    naziv = fields.String(tagname='naziv')


class MjerneJedinice(dexml.Model):
    class meta:
        tagname = 'mjerneJediniceId'

    id = fields.Integer(tagname='id')
    oznaka = fields.String(tagname='oznaka')


class Komponenta(dexml.Model):
    class meta:
        tagname = 'komponentaId'

    eol_oznaka = fields.String(tagname='eolOznaka')
    formula = fields.String(tagname='formula')
    id = fields.Integer(tagname='id')
    iso_oznaka = fields.String(tagname='isoOznaka')
    izrazeno_kao = fields.String(tagname='izrazenoKao')
    konv_v_u_m = fields.Float(tagname='konvVUM')
    mjerne_jedinice = fields.Model(MjerneJedinice)
    naziv = fields.String(tagname='naziv')
    naziv_eng = fields.String(tagname='nazivEng')
    vrsta_komponente = fields.Integer(tagname='vrstaKomponente')


class Postaja(dexml.Model):
    class meta:
        tagname = 'postajaId'

    geogr_duzina = fields.Float(tagname='geogrDuzina')
    geogr_sirina = fields.Float(tagname='geogrSirina')
    id = fields.Integer(tagname='id')
    kratka_oznaka = fields.String(tagname='kratkaOznaka')
    nacionalna_oznaka = fields.String(tagname='nacionalnaOznaka')
    nadmorska_visina = fields.Integer(tagname='nadmorskaVisina')
    naziv_postaje = fields.String(tagname='nazivPostaje')
    # odgovorno_tijelo = fields.Model(OdgovornoTijelo)
    oznaka_postaje = fields.String(tagname='oznakaPostaje')


class ProgramMjerenja(dexml.Model):
    class meta:
        tagname = 'programMjerenja'

    id = fields.Integer(tagname='id')
    komponenta = fields.Model(Komponenta)
    metoda = fields.Model(Metoda, tagname='metodaId')
    pocetak_mjerenja = fields.String(tagname='pocetakMjerenja')
    postaja = fields.Model(Postaja, tagname='postajaId')
    prikaz_web = fields.String(tagname='prikazWeb')
    usporedno = fields.Integer(tagname='usporednoMjerenje')


class ProgramMjerenjaNox(ProgramMjerenja):
    id_no = None
    id_no2 = None
    komponenta_no = None
    komponenta_no2 = None

    def __init__(self, program):
        super(ProgramMjerenja, self).__init__()
        self.metoda = program.metoda
        self.pocetak_mjerenja = program.pocetak_mjerenja
        self.postaja = program.postaja
        self.prikaz_web = program.prikaz_web
        self.usporedno = program.usporedno
        self.dodaj_program(program)

    def dodaj_program(self, program):
        if program.komponenta.formula == 'NO':
            self.id_no = program.id
            self.komponenta_no = program.komponenta
        elif program.komponenta.formula == 'NOx':
            self.id = program.id
            self.komponenta = program.komponenta
        elif program.komponenta.formula == 'NO2':
            self.id_no2 = program.id
            self.komponenta_no2 = program.komponenta
