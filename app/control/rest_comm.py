# -*- coding: utf-8 -*-
import json
import requests
from app.control.adapteri import PodatakAdapter, ProgramMjerenjaAdapter, ZeroSpanAdapter

def get_comm_object(config):
    if config.development:
        return MockZahtjev()
    else:
        return RESTZahtjev(config.rest.program_mjerenja_url,
                                       config.rest.sirovi_podaci_url,
                                       config.rest.status_map_url,
                                       config.rest.zero_span_podaci_url)

class MockZahtjev:
    def __init__(self, program_url='', sirovi_podaci_url='', status_map_url='',
                 zero_span_podaci_url='', auth=('', '')):
        self.zs_adapter = ZeroSpanAdapter()
        self.program_adapter = ProgramMjerenjaAdapter()
        self.podatak_adapter = PodatakAdapter()
        self.user = None
        self.pswd = None
        self.basedir = '/home/kraljevic/razvoj/python/validacija_aplikacija/test_resources/'

    def logmein(self, auth):
        self.user, self.pswd = auth

    def get_broj_u_satu(self, program_mjerenja_id):
        with open(self.basedir + "/broj_u_satu.json",
                  "r") as myfile:
            data = myfile.readline()
        out = json.loads(data)
        return int(out['brojUSatu'])

    def get_status_map(self):
        with open(self.basedir + "/statusi.json", "r") as myfile:
            data = myfile.readline()
        x = json.loads(data)
        rezultat = {}
        for i in range(len(x)):
            rezultat[x[i]['i']] = x[i]['s']
        return rezultat

    def get_sirovi(self, program_mjerenja_id, datum):
        dd = datum[-2:]
        n = 1 + (int(datum[-2:]) - 6) % 10
        fname = self.basedir + "/p" + str(n) + ".json"
        with open(fname, "r") as myfile:
            data = myfile.readline()
        frejm = self.podatak_adapter.adaptiraj(data)
        return frejm

    def get_zero_span(self, program_mjerenja_id, datum, kolicina):
        with open(self.basedir + "/zs.json", "r") as myfile:
            data = myfile.readline()
        zero, span = self.zs_adapter.adaptiraj(data)
        return zero, span

    def get_programe_mjerenja(self):
        with open(self.basedir + "/program.json", "r") as myfile:
            data = myfile.readline()
        out = self.program_adapter.adaptiraj(data)
        return out


class RESTZahtjev(object):
    """
    Klasa zaduzena za komunikaciju sa REST servisom
    """

    def __init__(self, program_url, sirovi_podaci_url, status_map_url, zero_span_podaci_url, auth=('', '')):
        self.logmein(auth)
        # ocekivani stupci u ooutputu
        self.program_url = program_url
        self.sirovi_podaci_url = sirovi_podaci_url
        self.status_map_url = status_map_url
        self.zero_span_podaci_url = zero_span_podaci_url
        self.zs_adapter = ZeroSpanAdapter()
        self.program_adapter = ProgramMjerenjaAdapter()
        self.podatak_adapter = PodatakAdapter()
        self.user = None
        self.pswd = None

    def logmein(self, auth):
        self.user, self.pswd = auth

    def get_broj_u_satu(self, program_mjerenja):
        """
        Metoda dohvaca minimalni broj podataka u satu za neki programMjerenjaID.
        Output je integer
        """
        url = self.program_url + '/podaci/' + str(program_mjerenja.id)
        out = json.loads(self._get_request(url, ''))
        return int(out['brojUSatu'])

    def get_status_map(self):
        """
        Metoda dohvaca podatke o statusima sa REST servisa
        vraca mapu (dictionary):
        {broj bita [int] : opisni string [str]}
        """
        json_str = self._get_request(self.status_map_url, '')
        x = json.loads(json_str)
        rezultat = {}
        for i in range(len(x)):
            rezultat[x[i]['i']] = x[i]['s']
        return rezultat

    def get_sirovi(self, program_mjerenja, datum):
        """
        Za zadani program mjerenja (int) i datum (string, formata YYYY-MM-DD)
        dohvati sirove (minutne) podatke sa REST servisa.
        Output funkcije je json string.
        """
        url = self.sirovi_podaci_url + '/' + str(program_mjerenja.id) + '/' + datum
        payload = {"broj_dana": 1}
        frejm = self.podatak_adapter.adaptiraj(self._get_request(url, payload))
        return frejm

    def get_zero_span(self, program_mjerenja, datum, kolicina):
        """
        Dohvati zero-span vrijednosti
        ulazni parametri su:
        -programMjerenja : integer, id programa mjerenja
        -datum : string formata 'YYYY-MM-DD'
        -kolicina : integer, broj dana koji treba dohvatiti

        Funkcija vraca json string sa trazenim podacima ili prazan string ako je
        doslo do problema prilikom rada.
        """
        # dat = datum.strftime('%Y-%m-%d')
        url = self.zero_span_podaci_url + '/' + str(program_mjerenja.id) + '/' + datum
        payload = {"broj_dana": int(kolicina)}
        zero, span = self.zs_adapter.adaptiraj(self._get_request(url, payload))
        return zero, span

    def get_programe_mjerenja(self):
        """
        Metoda salje zahtjev za svim programima mjerenja prema REST servisu.
        Uz pomoc funkcije parse_xml, prepakirava dobivene podatke u mapu
        'zanimljivih' podataka. Vraca (nested) dictionary programa mjerenja ili
        prazan dictionary u slucaju pogreske prilikom rada.

        -bitno za test login funkcionalnosti... bogatiji report
        """
        payload = {"id": "findAll", "name": "GET"}
        out = self.program_adapter.adaptiraj(self._get_request(self.program_url, {}))
        return out

    def _get_request(self, url, params ):
        r = requests.get(url,
                         params=params,
                         timeout=39.1,
                         headers={"accept": "application/json"},
                         auth=requests.auth.HTTPBasicAuth(self.user, self.pswd))
        if r.ok is not True:
            raise RESTException('status={0} , reason={1}, url={2}'.format(str(r.status_code), str(r.reason), url))
        return r.text

    def upload_json_minutnih(self, program_mjerenja=None, jstring=None, datum=None):
        """
        Spremanje minutnih podataka na REST servis.
        ulazni parametrni su:
        -programMjerenjaId : program mjerenja id
        -jstring : json string minutnih podataka koji se treba uploadati
        -datum : datum
        """
        url = self.sirovi_podaci_url + '/' + str(program_mjerenja.id) + '/' + datum
        payload = {"id": "putPodaci", "name": "PUT"}
        headers = {'Content-type': 'application/json'}
        if not isinstance(jstring, str):
            raise ValueError('Ulazni parametar nije tipa string.')
        if len(jstring) == 0:
            raise ValueError('Ulazni json string je prazan')
        r = requests.put(url,
                         params=payload,
                         data=jstring,
                         headers=headers,
                         timeout=39.1,
                         auth=requests.auth.HTTPBasicAuth(self.user, self.pswd))
        msg = 'status={0} , reason={1}, url={2}'.format(str(r.status_code), str(r.reason), url)
        if r.ok is not True:
            raise RESTException(msg)

class RESTException(Exception):
    def __init__(self, message):
        super(RESTException, self).__init__(message)

