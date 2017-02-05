# -*- coding: utf-8 -*-
import datetime
import json
import logging

import numpy as np
import pandas as pd
import requests
from PyQt4 import QtGui
from requests.auth import HTTPBasicAuth

from app.control.adapteri import PodatakAdapter, ProgramMjerenjaAdapter, ZeroSpanAdapter


class DataReaderAndCombiner(object):
    """
    klasa za read podataka sa resta. Cita dan po dan, updatea progress bar i spaja dnevne
    frejmove u jedan izlazni.

    reader : RestZahtjev objekt
    statusi : mapa {statusBit : status}
    """

    def __init__(self, reader):
        self.citac = reader
        # lookup tablica za opis statusa {broj statusa[int] : string asociranih flagova [str]}
        self._statusLookup = {}
        self._status_bits = {}

    def get_data(self, kanal, od, do):
        """
        in:
        -kanal: id kanala mjerenja
        -od: datetime.datetime (pocetak)
        -do: datetime.datetime (kraj)
        """
        try:
            # dohvati status bit info
            self._status_bits = self.citac.get_statusMap()
            # prazni frejmovi u koje ce se spremati podaci
            master_konc_frm = pd.DataFrame()
            master_zero_frm = pd.DataFrame()
            master_span_frm = pd.DataFrame()
            # definiraj raspon podataka
            time_raspon = (do - od).days
            if time_raspon < 1:
                raise ValueError('Vremenski raspon manji od dana nije dozvoljen')
            # napravi progress bar i postavi ga...
            self.progress = QtGui.QProgressBar()
            self.progress.setWindowTitle('Load status:')
            self.progress.setRange(0, time_raspon + 1)
            self.progress.setGeometry(300, 300, 200, 40)
            self.progress.show()
            # ucitavanje frejmova koncentracija, zero, span
            for d in range(1, time_raspon + 1):
                dan = (od + datetime.timedelta(d)).strftime('%Y-%m-%d')
                konc_frejm = self.citac.get_sirovi(kanal, dan)
                zero_frejm, span_frejm = self.citac.get_zero_span(kanal, dan, 1)
                # append dnevne frejmove na glavni ako imaju podatke
                if len(konc_frejm):
                    master_konc_frm = master_konc_frm.append(konc_frejm)
                if len(zero_frejm):
                    master_zero_frm = master_zero_frm.append(zero_frejm)
                if len(span_frejm):
                    master_span_frm = master_span_frm.append(span_frejm)
                # advance progress bar
                self.progress.setValue(d)
            self.progress.close()
            # broj podataka u satu...
            try:
                frek = int(np.floor(60 / self.citac.get_broj_u_satu(kanal)))
            except Exception as err:
                logging.error(str(err), exc_info=True)
                # default na minutni period
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
            # konverzija status int to string za koncentracijski frejm
            statstr = [self._statusInt_to_statusString(i) for i in master_konc_frm.loc[:, 'status']]
            master_konc_frm.loc[:, 'statusString'] = statstr
            # reindex koncentracijski data zbog rupa u podacima (ako nedostaju rubni podaci)
            master_konc_frm = master_konc_frm.reindex(fullraspon)
            # output frejmove
            return master_konc_frm, master_zero_frm, master_span_frm
        except Exception as err:
            logging.error(str(err), exc_info=True)
            if hasattr(self, 'progress'):
                self.progress.close()
            raise Exception('Problem kod ucitavanja podataka') from err

    def _check_bit(self, broj, bit_position):
        """
        Pomocna funkcija za testiranje statusa
        Napravi temporary integer koji ima samo jedan bit vrijednosti 1 na poziciji
        bit_position. Napravi binary and takvog broja i ulaznog broja.
        Ako oba broja imaju bit 1 na istoj poziciji vrati True, inace vrati False.
        """
        if bit_position is not None:
            temp = 1 << int(bit_position)  # left shift bit za neki broj pozicija
            if int(broj) & temp > 0:  # binary and izmjedju ulaznog broja i testnog broja
                return True
            else:
                return False

    def _check_status_flags(self, broj):
        """
        provjeri stauts integera broj dekodirajuci ga sa hash tablicom
        {bit_pozicija:opisni string}. Vrati string opisa.
        """
        flaglist = []
        for key, value in self._status_bits.items():
            if self._check_bit(broj, key):
                flaglist.append(value)
        opis = ",".join(flaglist)
        return opis

    def _statusInt_to_statusString(self, sint):
        if np.isnan(sint):
            return 'Status nije definiran'
        sint = int(sint)
        rez = self._statusLookup.get(sint, None)  # see if value exists
        if rez is None:
            rez = self._check_status_flags(sint)  # calculate
            self._statusLookup[sint] = rez  # store value for future lookup
        return rez


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

    def logmein(self, auth):
        self.user, self.pswd = auth

    def logmeout(self):
        self.user, self.pswd = ('', '')

    def get_broj_u_satu(self, programMjerenjaId):
        """
        Metoda dohvaca minimalni broj podataka u satu za neki programMjerenjaID.
        Output je integer
        """
        url = self.program_url + '/podaci/' + str(programMjerenjaId)
        head = {"accept": "application/json"}
        out = json.loads(self._get_request(url, '', head))
        return int(out['brojUSatu'])

    def get_statusMap(self):
        """
        Metoda dohvaca podatke o statusima sa REST servisa
        vraca mapu (dictionary):
        {broj bita [int] : opisni string [str]}
        """
        head = {"accept": "application/json"}
        json_str = self._get_request(self.status_map_url, '', head)
        x = json.loads(json_str)
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
        url = self.sirovi_podaci_url + '/' + str(programMjerenjaId) + '/' + datum
        payload = {"id": "getPodaci", "name": "GET", "broj_dana": 1}
        head = {"accept": "application/json"}
        frejm = self.podatak_adapter.adaptiraj(self._get_request(url, payload, head))
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
        # dat = datum.strftime('%Y-%m-%d')
        url = self.zero_span_podaci_url + '/' + str(programMjerenja) + '/' + datum
        payload = {"id": "getZeroSpanLista", "name": "GET", "broj_dana": int(kolicina)}
        head = {"accept": "application/json"}
        zero, span = self.zs_adapter.adaptiraj(self._get_request(url, payload, head))
        return zero, span

    def get_programe_mjerenja(self):
        """
        Metoda salje zahtjev za svim programima mjerenja prema REST servisu.
        Uz pomoc funkcije parse_xml, prepakirava dobivene podatke u mapu
        'zanimljivih' podataka. Vraca (nested) dictionary programa mjerenja ili
        prazan dictionary u slucaju pogreske prilikom rada.

        -bitno za test login funkcionalnosti... bogatiji report
        """
        head = {"accept": "application/xml"}
        payload = {"id": "findAll", "name": "GET"}
        out = self.program_adapter.adaptiraj(self._get_request(self.program_url, payload, head))
        return out

    def _get_request(self, url, params, headers):
        r = requests.get(url,
                         params=params,
                         timeout=39.1,
                         headers=headers,
                         auth=HTTPBasicAuth(self.user, self.pswd))
        msg = 'status={0} , reason={1}, url={2}'.format(str(r.status_code), str(r.reason), url)
        assert r.ok is True, msg
        return r.text

    def upload_json_minutnih(self, program_mjerenja_id=None, jstring=None, datum=None):
        """
        Spremanje minutnih podataka na REST servis.
        ulazni parametrni su:
        -programMjerenjaId : program mjerenja id
        -jstring : json string minutnih podataka koji se treba uploadati
        -datum : datum
        """
        url = self.sirovi_podaci_url + '/' + str(program_mjerenja_id) + '/' + datum
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
                         auth=HTTPBasicAuth(self.user, self.pswd))
        msg = 'status={0} , reason={1}, url={2}'.format(str(r.status_code), str(r.reason), url)
        assert r.ok is True, msg
        return True
