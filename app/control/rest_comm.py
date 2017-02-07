# -*- coding: utf-8 -*-
import json
import logging
import requests
import datetime
import numpy as np
import pandas as pd
from requests.auth import HTTPBasicAuth
import xml.etree.ElementTree as ET
from PyQt4 import QtGui

class DataReaderAndCombiner(object):
    """
    klasa za read podataka sa resta. Cita dan po dan, updatea progress bar i spaja dnevne
    frejmove u jedan izlazni.

    reader : RestZahtjev objekt
    """
    def __init__(self, reader):
        self.citac = reader

    def get_data(self, kanal, od, do):
        """
        in:
        -kanal: id kanala mjerenja
        -od: datetime.datetime (pocetak)
        -do: datetime.datetime (kraj)
        """
        try:
            #dohvati status bit info
            #prazni frejmovi u koje ce se spremati podaci
            masterKoncFrejm = pd.DataFrame(columns=self.citac.expectedColsKonc)
            masterZeroFrejm = pd.DataFrame(columns=self.citac.expectedColsZero)
            masterSpanFrejm = pd.DataFrame(columns=self.citac.expectedColsSpan)
            #definiraj raspon podataka
            timeRaspon = (do - od).days
            if timeRaspon < 1:
                raise ValueError('Vremenski raspon manji od dana nije dozvoljen')
            #napravi progress bar i postavi ga...
            self.progress = QtGui.QProgressBar()
            self.progress.setWindowTitle('Load status:')
            self.progress.setRange(0, timeRaspon+1)
            self.progress.setGeometry(300, 300, 200, 40)
            self.progress.show()
            #ucitavanje frejmova koncentracija, zero, span
            for d in range(timeRaspon+1):
                dan = (od + datetime.timedelta(d)).strftime('%Y-%m-%d')
                koncFrejm = self.citac.get_sirovi(kanal, dan)
                zeroFrejm, spanFrejm = self.citac.get_zero_span(kanal, dan, 1)
                #append dnevne frejmove na glavni ako imaju podatke
                if len(koncFrejm):
                    masterKoncFrejm = masterKoncFrejm.append(koncFrejm)
                if len(zeroFrejm):
                    masterZeroFrejm = masterZeroFrejm.append(zeroFrejm)
                if len(spanFrejm):
                    masterSpanFrejm = masterSpanFrejm.append(spanFrejm)
                #advance progress bar
                self.progress.setValue(d)
            self.progress.close()
            #broj podataka u satu...
            try:
                frek = int(np.floor(60/self.citac.get_broj_u_satu(kanal)))
            except Exception as err:
                logging.error(str(err), exc_info=True)
                #default na minutni period
                frek = -1

            if frek <= 1:
                frek = 'Min'
                start = datetime.datetime.combine(od, datetime.time(0, 1, 0))
                kraj = do + datetime.timedelta(1)
            else:
                frek = str(frek) + 'Min'
                start = datetime.datetime.combine(od, datetime.time(0, 0, 0))
                kraj = do + datetime.timedelta(1)


            fullraspon = pd.date_range(start=start, end=kraj, freq=frek)
            #reindex koncentracijski data zbog rupa u podacima (ako nedostaju rubni podaci)
            masterKoncFrejm = masterKoncFrejm.reindex(fullraspon)
            #sredi satuse missing podataka
            masterKoncFrejm = self.sredi_missing_podatke(masterKoncFrejm)
            #output frejmove
            return masterKoncFrejm, masterZeroFrejm, masterSpanFrejm
        except Exception as err:
            logging.error(str(err), exc_info=True)
            if hasattr(self, 'progress'):
                self.progress.close()
            raise Exception('Problem kod ucitavanja podataka') from err

    def sredi_missing_podatke(self, frejm):
        #indeks svi konc nan
        i0 = np.isnan(frejm['koncentracija'])
        #indeks konc i status su nan
        i1 = (np.isnan(frejm['koncentracija']))&(np.isnan(frejm['status']))
        #indeks konc je nan, status nije
        i2 = (np.isnan(frejm['koncentracija']))&([not m for m in np.isnan(frejm['status'])])

        frejm.loc[i1, 'status'] = 32768
        frejm.loc[i2, 'status'] = [(int(m) | 32768) for m in frejm.loc[i2, 'status']]
        frejm.loc[i0, 'flag'] = -1000
        return frejm


class RESTZahtjev(object):
    """
    Klasa zaduzena za komunikaciju sa REST servisom
    """
    def __init__(self, konfig, auth=('','')):
        self.konfig = konfig
        self.logmein(auth)
        #ocekivani stupci u ooutputu
        self.expectedColsKonc = ['koncentracija', 'korekcija', 'flag', 'statusString',
                                 'status', 'id', 'A', 'B', 'Sr', 'LDL']
        self.expectedColsZero = ['zero', 'korekcija', 'minDozvoljeno',
                                 'maxDozvoljeno', 'A', 'B', 'Sr', 'LDL']
        self.expectedColsSpan = ['span', 'korekcija', 'minDozvoljeno',
                                 'maxDozvoljeno', 'A', 'B', 'Sr', 'LDL']

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
        out = self.parse_mjerenjaXML(r.text)
        return out

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
            #round off zero i spana na minutu
            zeroIndeksRounded = [i.round('Min') for i in zeroFrejm.index]
            spanIndeksRounded = [i.round('Min') for i in spanFrejm.index]
            zeroFrejm.index = zeroIndeksRounded
            spanFrejm.index = spanIndeksRounded
            # kontrola za besmislene vrijednosti (tipa -999)
            zeroFrejm = zeroFrejm[zeroFrejm['vrijednost'] > -998.0]
            spanFrejm = spanFrejm[spanFrejm['vrijednost'] > -998.0]
            #drop unused
            spanFrejm.drop(['vrijeme', 'vrsta'], inplace=True, axis=1)
            zeroFrejm.drop(['vrijeme', 'vrsta'], inplace=True, axis=1)
            #dodaj nan stupce
            spanFrejm['korekcija'] = np.NaN
            spanFrejm['A'] = np.NaN
            spanFrejm['B'] = np.NaN
            spanFrejm['Sr'] = np.NaN
            spanFrejm['LDL'] = np.NaN
            zeroFrejm['korekcija'] = np.NaN
            zeroFrejm['A'] = np.NaN
            zeroFrejm['B'] = np.NaN
            zeroFrejm['Sr'] = np.NaN
            zeroFrejm['LDL'] = np.NaN
            #rename zero i span
            spanFrejm.rename(columns={'vrijednost':'span'}, inplace=True)
            zeroFrejm.rename(columns={'vrijednost':'zero'}, inplace=True)
            #reorder columns
            spanFrejm = spanFrejm[self.expectedColsSpan]
            zeroFrejm = zeroFrejm[self.expectedColsZero]
            return zeroFrejm, spanFrejm
        except Exception:
            logging.error('Fail kod parsanja json stringa:\n'+str(x), exc_info=True)
            spanFrejm = pd.DataFrame(columns=self.expectedColsSpan)
            zeroFrejm = pd.DataFrame(columns=self.expectedColsZero)
            return zeroFrejm, spanFrejm

    def adaptiraj_ulazni_json(self, x):
        """
        Funkcija je zaduzena da konvertira ulazni json string (x) u pandas frejm
        """
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
            df['A'] = np.NaN #placeholder
            df['B'] = np.NaN #placeholder
            df['Sr'] = np.NaN #placeholder
            df['LDL'] = np.NaN #placeholder
            df['statusString'] = df['statusString']
            #drop unused columns
            df.drop(['vrijeme', 'nivoValidacije'], inplace=True, axis=1)
            #reorder
            df = df[self.expectedColsKonc]
            return df
        except (ValueError, TypeError, AssertionError):
            logging.error('Fail kod parsanja json stringa:\n'+str(x), exc_info=True)
            df = pd.DataFrame(columns=self.expectedColsKonc)
            return df

    def parse_mjerenjaXML(self, x):
        """
        Parsira xml sa programima mjerenja preuzetih sa rest servisa,

        output: (nested) dictionary sa bitnim podacima. Primarni kljuc je program
        mjerenja id, sekundarni kljucevi su opisni (npr. 'komponentaNaziv')
        """
        rezultat = {}
        root = ET.fromstring(x)
        for programMjerenja in root:
            i = int(programMjerenja.find('id').text)
            postajaId = int(programMjerenja.find('.postajaId/id').text)
            postajaNaziv = programMjerenja.find('.postajaId/nazivPostaje').text
            komponentaId = programMjerenja.find('.komponentaId/id').text
            komponentaNaziv = programMjerenja.find('.komponentaId/naziv').text
            komponentaMjernaJedinica = programMjerenja.find('.komponentaId/mjerneJediniceId/oznaka').text
            komponentaFormula = programMjerenja.find('.komponentaId/formula').text
            usporednoMjerenje = programMjerenja.find('usporednoMjerenje').text
            konvVUM = float(programMjerenja.find('.komponentaId/konvVUM').text) #konverizijski volumen
            #dodavanje mjerenja u dictionary
            rezultat[i] = {
                'postajaId':postajaId,
                'postajaNaziv':postajaNaziv,
                'komponentaId':komponentaId,
                'komponentaNaziv':komponentaNaziv,
                'komponentaMjernaJedinica':komponentaMjernaJedinica,
                'komponentaFormula':komponentaFormula,
                'usporednoMjerenje':usporednoMjerenje,
                'konvVUM':konvVUM,
                'povezaniKanali':[i]}
        return rezultat


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

