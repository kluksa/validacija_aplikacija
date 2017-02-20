# -*- coding: utf-8 -*-
import datetime
import json
import logging
import re

import numpy as np
import pandas as pd
import requests
from PyQt4 import QtGui
from requests.auth import HTTPBasicAuth

from app.control.adapteri import PodatakAdapter, ProgramMjerenjaAdapter, ZeroSpanAdapter


class MockZahtjev:
    def __init__(self, program_url='', sirovi_podaci_url='', status_map_url='',
                 zero_span_podaci_url='', auth=('', '')):
        self.zs_adapter = ZeroSpanAdapter()
        self.program_adapter = ProgramMjerenjaAdapter()
        self.podatak_adapter = PodatakAdapter()
        self.user = None
        self.pswd = None

    def logmein(self, auth):
        self.user, self.pswd = auth

    def get_broj_u_satu(self, program_mjerenja_id):
        with open("/home/kraljevic/PycharmProjects/validacija_aplikacija/test_resources/broj_u_satu.json",
                  "r") as myfile:
            data = myfile.readline()
        out = json.loads(data)
        return int(out['brojUSatu'])

    def get_status_map(self):
        with open("/home/kraljevic/PycharmProjects/validacija_aplikacija/test_resources/statusi.json", "r") as myfile:
            data = myfile.readline()
        x = json.loads(data)
        rezultat = {}
        for i in range(len(x)):
            rezultat[x[i]['i']] = x[i]['s']
        return rezultat

    def get_sirovi(self, program_mjerenja_id, datum):
        dd = datum[-2:]
        n = 1 + (int(datum[-2:]) - 6) % 10
        fname = "/home/kraljevic/PycharmProjects/validacija_aplikacija/test_resources/p" + str(n) + ".json"
        with open(fname, "r") as myfile:
            data = myfile.readline()
            re.sub("", "", data)
        frejm = self.podatak_adapter.adaptiraj(data)
        return frejm

    def get_zero_span(self, program_mjerenja_id, datum, kolicina):
        with open("/home/kraljevic/PycharmProjects/validacija_aplikacija/test_resources/zs.json", "r") as myfile:
            data = myfile.readline()
        zero, span = self.zs_adapter.adaptiraj(data)
        return zero, span

    def get_programe_mjerenja(self):
        with open("/home/kraljevic/PycharmProjects/validacija_aplikacija/test_resources/program.json", "r") as myfile:
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
        head = {"accept": "application/json"}
        out = json.loads(self._get_request(url, '', head))
        return int(out['brojUSatu'])

    def get_status_map(self):
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

    def get_sirovi(self, program_mjerenja, datum):
        """
        Za zadani program mjerenja (int) i datum (string, formata YYYY-MM-DD)
        dohvati sirove (minutne) podatke sa REST servisa.
        Output funkcije je json string.
        """
        url = self.sirovi_podaci_url + '/' + str(program_mjerenja.id) + '/' + datum
        payload = {"id": "getPodaci", "name": "GET", "broj_dana": 1}
        head = {"accept": "application/json"}
        frejm = self.podatak_adapter.adaptiraj(self._get_request(url, payload, head))
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
        head = {"accept": "application/json"}
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
                         auth=HTTPBasicAuth(self.user, self.pswd))
        msg = 'status={0} , reason={1}, url={2}'.format(str(r.status_code), str(r.reason), url)
        assert r.ok is True, msg
        return True
