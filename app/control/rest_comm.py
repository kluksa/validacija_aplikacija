# -*- coding: utf-8 -*-
import json
import logging
import requests
import numpy as np
import pandas as pd
from requests.auth import HTTPBasicAuth


class RESTZahtjev(object):
    """
    Klasa zaduzena za komunikaciju sa REST servisom
    """
    def __init__(self, konfig, auth=('','')):
        self.konfig = konfig
        self.logmein(auth)

    def logmein(self, auth):
        self.user, self.pswd = auth

    def logmeout(self):
        self.user, self.pswd = ('', '')

    def get_broj_u_satu(self, programMjerenjaId):
        """
        Metoda dohvaca minimalni broj podataka u satu za neki programMjerenjaID.
        Output je integer
        """
        url = "".join([self.konfig.restProgramMjerenja, '/podaci/',str(programMjerenjaId)])
        head = {"accept":"application/json"}
        r = requests.get(url,
                         timeout=15.1,
                         headers=head,
                         auth=HTTPBasicAuth(self.user, self.pswd))

        msg = 'status={0} , reason={1}, url={2}'.format(str(r.status_code), str(r.reason), url)
        assert r.ok == True, msg
        out = json.loads(r.text)
        print(r.text)
        return int(out['brojUSatu'])

    def get_statusMap(self):
        """
        Metoda dohvaca podatke o statusima sa REST servisa
        vraca mapu (dictionary):
        {broj bita [int] : opisni string [str]}
        """
        url = self.konfig.restStatusMap
        head = {"accept":"application/json"}
        r = requests.get(url,
                         timeout=15.1,
                         headers = head,
                         auth=HTTPBasicAuth(self.user, self.pswd))
        msg = 'status={0} , reason={1}, url={2}'.format(str(r.status_code), str(r.reason), url)
        assert r.ok == True, msg
        jsonStr = r.text
        x = json.loads(jsonStr)
        rezultat = {}
        for i in range(len(x)):
            rezultat[x[i]['i']] = x[i]['s']
        return rezultat

    def get_sirovi(self, programMjerenjaId, datum):
        """
        Za zadani program mjerenja (int) i datum (string, formata YYYY-MM-DD)
        dohvati sirove (minutne) podatke sa REST servisa.
        Output funkcije je json string.
        """
        url = "/".join([self.konfig.restSiroviPodaci, str(programMjerenjaId), datum])
        payload = {"id":"getPodaci", "name":"GET", "broj_dana":1}
        head = {"accept":"application/json"}
        r = requests.get(url,
                         params=payload,
                         timeout=39.1,
                         headers=head,
                         auth=HTTPBasicAuth(self.user, self.pswd))
        msg = 'status={0} , reason={1}, url={2}'.format(str(r.status_code), str(r.reason), url)
        assert r.ok == True, msg
        frejm = self.adaptiraj_ulazni_json(r.text)
        return frejm

    def get_zero_span(self, programMjerenja, datum, kolicina):
        """
        Dohvati zero-span vrijednosti
        ulazni parametri su:
        -programMjerenja : integer, id programa mjerenja
        -datum : string formata 'YYYY-MM-DD'
        -kolicina : integer, broj dana koji treba dohvatiti

        Funkcija vraca json string sa trazenim podacima ili prazan string ako je
        doslo do problema prilikom rada.
        """
        #dat = datum.strftime('%Y-%m-%d')
        url = "/".join([self.konfig.restZeroSpanPodaci, str(programMjerenja), datum])
        payload = {"id":"getZeroSpanLista", "name":"GET", "broj_dana":int(kolicina)}
        msg = 'get_zero_span pozvan sa parametrima: id={0}, datum={1}, brojdana={2}'.format(str(programMjerenja), str(datum), str(kolicina))
        head = {"accept":"application/json"}
        r = requests.get(url,
                         params=payload,
                         timeout=39.1,
                         headers=head,
                         auth=HTTPBasicAuth(self.user, self.pswd))
        msg = 'status={0} , reason={1}, url={2}'.format(str(r.status_code), str(r.reason), url)
        assert r.ok == True, msg
        zero, span = self.adaptiraj_zero_span_json(r.text)
        return zero, span

    def get_programe_mjerenja(self):
        """
        Metoda salje zahtjev za svim programima mjerenja prema REST servisu.
        Uz pomoc funkcije parse_xml, prepakirava dobivene podatke u mapu
        'zanimljivih' podataka. Vraca (nested) dictionary programa mjerenja ili
        prazan dictionary u slucaju pogreske prilikom rada.

        -bitno za test login funkcionalnosti... bogatiji report
        """
        url = self.konfig.restProgramMjerenja
        head = {"accept":"application/xml"}
        payload = {"id":"findAll", "name":"GET"}
        r = requests.get(url,
                         params=payload,
                         timeout=39.1,
                         headers=head,
                         auth=HTTPBasicAuth(self.user, self.pswd))
        msg = 'status={0} , reason={1}, url={2}'.format(str(r.status_code), str(r.reason), url)
        assert r.ok == True, msg
        return r.text

    def _valjan_conversion(self, x):
        if x:
            return 1
        else:
            return -1

    def _nan_conversion(self, x):
        if x > -99:
            return x
        else:
            return np.NaN

    def adaptiraj_zero_span_json(self, x):
        expectedColumns = ['vrijednost',
                           'korekcija',
                           'minDozvoljeno',
                           'maxDozvoljeno']
        try:
            frejm = pd.read_json(x, orient='records', convert_dates=['vrijeme'])
            assert 'vrsta' in frejm.columns, 'Nedostaje stupac vrsta'
            assert 'vrijeme' in frejm.columns, 'Nedostaje stupac vrijeme'
            assert 'vrijednost' in frejm.columns, 'Nedostaje stupac vrijednost'
            assert 'minDozvoljeno' in frejm.columns, 'Nedostaje stupac minDozvoljeno'
            assert 'maxDozvoljeno' in frejm.columns, 'Nedostaje stupac maxDozvoljeno'
            zeroFrejm = frejm[frejm['vrsta'] == "Z"]
            spanFrejm = frejm[frejm['vrsta'] == "S"]
            zeroFrejm = zeroFrejm.set_index(zeroFrejm['vrijeme'])
            spanFrejm = spanFrejm.set_index(spanFrejm['vrijeme'])
            # kontrola za besmislene vrijednosti (tipa -999)
            zeroFrejm = zeroFrejm[zeroFrejm['vrijednost'] > -998.0]
            spanFrejm = spanFrejm[spanFrejm['vrijednost'] > -998.0]
            #drop unused
            spanFrejm.drop(['vrijeme', 'vrsta'], inplace=True, axis=1)
            zeroFrejm.drop(['vrijeme', 'vrsta'], inplace=True, axis=1)
            #dodaj korekciju
            spanFrejm['korekcija'] = np.NaN
            zeroFrejm['korekcija'] = np.NaN
            #rename zero i span
            spanFrejm.rename(columns={'vrijednost':'span'}, inplace=True)
            zeroFrejm.rename(columns={'vrijednost':'zero'}, inplace=True)
            return zeroFrejm, spanFrejm
        except Exception:
            logging.error('Fail kod parsanja json stringa:\n'+str(x), exc_info=True)
            spanFrejm = pd.DataFrame(columns=expectedColumns)
            zeroFrejm = pd.DataFrame(columns=expectedColumns)
            spanFrejm.rename(columns={'vrijednost':'span'}, inplace=True)
            zeroFrejm.rename(columns={'vrijednost':'zero'}, inplace=True)
            return zeroFrejm, spanFrejm

    def adaptiraj_ulazni_json(self, x):
        """
        Funkcija je zaduzena da konvertira ulazni json string (x) u pandas frejm
        """
        expectedColumns = ['koncentracija',
                           'korekcija',
                           'flag',
                           'statusString',
                           'status',
                           'id']
        try:
            df = pd.read_json(x, orient='records', convert_dates=['vrijeme'])
            assert 'vrijeme' in df.columns, 'ERROR - Nedostaje stupac: "vrijeme"'
            assert 'id' in df.columns, 'ERROR - Nedostaje stupac: "id"'
            assert 'vrijednost' in df.columns, 'ERROR - Nedostaje stupac: "vrijednost'
            assert 'statusString' in df.columns, 'ERROR - Nedostaje stupac: "statusString"'
            assert 'valjan' in df.columns, 'ERROR - Nedostaje stupac: "valjan"'
            assert 'statusInt' in df.columns, 'ERROR - Nedostaje stupac: "statusInt"'
            assert 'nivoValidacije' in df.columns, 'Error - Nedostaje stupac: "nivoValidacije"'
            df = df.set_index(df['vrijeme'])
            renameMap = {'vrijednost':'koncentracija',
                         'valjan':'flag',
                         'statusInt':'status'}
            df.rename(columns=renameMap, inplace=True)
            df['koncentracija'] = df['koncentracija'].map(self._nan_conversion)
            df['flag'] = df['flag'].map(self._valjan_conversion)
            df['korekcija'] = np.NaN #placeholder
            df['statusString'] = df['statusString']
            #drop unused columns
            df.drop(['vrijeme', 'nivoValidacije'], inplace=True, axis=1)
            return df
        except (ValueError, TypeError, AssertionError):
            logging.error('Fail kod parsanja json stringa:\n'+str(x), exc_info=True)
            df = pd.DataFrame(columns=expectedColumns)
            return df

#    def upload_json_minutnih(self, programMjerenjaId=None, jstring=None, datum=None):
#        """
#        Spremanje minutnih podataka na REST servis.
#        ulazni parametrni su:
#        -programMjerenjaId : program mjerenja id
#        -jstring : json string minutnih podataka koji se treba uploadati
#        -datum : datum
#        """
#        url = "/".join([self.konfig.restSiroviPodaci, str(programMjerenjaId), datum])
#        payload = {"id":"putPodaci", "name":"PUT"}
#        headers = {'Content-type': 'application/json'}
#        if not isinstance(jstring, str):
#            raise ValueError('Ulazni parametar nije tipa string.')
#        if len(jstring) == 0:
#            raise ValueError('Ulazni json string je prazan')
#        r = requests.put(url,
#                         params=payload,
#                         data=jstring,
#                         headers=headers,
#                         timeout=39.1,
#                         auth=HTTPBasicAuth(self.user, self.pswd))
#        msg = 'status={0} , reason={1}, url={2}'.format(str(r.status_code), str(r.reason), url)
#        assert r.ok == True, msg
#        return True

