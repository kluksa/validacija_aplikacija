import logging
import os
from datetime import timedelta

import numpy as np
import pandas as pd
from PyQt4 import QtGui, QtCore

class ExportWorker(QtCore.QObject):
    pass

def export_frame(frame, folder, fname):
    fname = os.path.normpath(os.path.join(folder, fname))
    frame.to_csv(fname, sep=';')


def export_korekcije(dokument, fname):
    if fname:
        frejmKor = dokument._corr_df
        # izbaci zadnji red (za dodavanje stvari...)
        frejmKor = frejmKor.iloc[:-1, :]
        # drop nepotrebne stupce (remove/calc placeholderi)
        frejmKor.drop(['remove', 'calc'], axis=1, inplace=True)

        if not fname.endswith('.csv'):
            fname += '.csv'
        # os... sastavi imena fileova
        folder, name = os.path.split(fname)
        export_frame(dokument.koncModel.datafrejm, folder, "podaci_" + name)
        export_frame(dokument.zeroModel.datafrejm, folder, "zero_" + name)
        export_frame(dokument.spanModel.datafrejm, folder, "span_" + name)
        export_frame(frejmKor, folder, "korekcijski_parametri_" + name)
        return True
    return False


class DownloadPodatakaWorker(QtCore.QObject):
    greska_signal = QtCore.pyqtSignal(str)
    progress_signal = QtCore.pyqtSignal(int)
    gotovo_signal = QtCore.pyqtSignal(dict)
    u_tijeku_signal = QtCore.pyqtSignal()

    def __init__(self, rest, parent=None):
        super(self.__class__, self).__init__()
        self.restRequest = rest
        self.aktivan = False

    def set(self, kanal, od, do):
        self.kanal = kanal
        self.od = od
        self.do = do
        self.ndays = int((do - od).days)

    def run(self):
        if self.aktivan:
            self.u_tijeku_signal.emit()
            return

        try:
            rezultat = {}
            self.aktivan = True
            self.status_bits = self.restRequest.get_status_map()
            broj_u_satu = self.restRequest.get_broj_u_satu(self.kanal)
            zero_df = pd.DataFrame()
            span_df = pd.DataFrame()
            mjerenja_df = pd.DataFrame()
            for d in range(0, self.ndays):
                dan = (self.od + timedelta(d)).strftime('%Y-%m-%d')
                mjerenja = self.restRequest.get_sirovi(self.kanal, dan)
                [zero, span] = self.restRequest.get_zero_span(self.kanal, dan, 1)
                zero_df = zero_df.append(zero)
                span_df = span_df.append(span)
                mjerenja_df = mjerenja_df.append(mjerenja)
                self.progress_signal.emit(int(100 * d / self.ndays))

            if 3600 % broj_u_satu != 0:
                logging.error("Frekvencija mjerenja nije cijeli broj sekundi", exc_info=True)
                raise NotIntegerFreq()
            frek = str(int(3600 / broj_u_satu)) + "S"

            fullraspon = pd.date_range(start=self.od, end=self.do, freq=frek)

            mjerenja_df = mjerenja_df.reindex(fullraspon)
            mjerenja_df = self.sredi_missing_podatke(mjerenja_df)
            rezultat['mjerenja'] = mjerenja_df
            rezultat['zero'] = zero_df
            rezultat['span'] = span_df
            self.gotovo_signal.emit(rezultat)
        except Exception as err:
            logging.error(str(err), exc_info=True)
            self.greska_signal.emit(str(err))
        finally:
            self.aktivan = False

    def sredi_missing_podatke(self, frejm):
        # indeks svi konc nan
        i0 = np.isnan(frejm['koncentracija'])
        i1 = np.isnan(frejm['status'])
        # indeks konc i status su nan
        i1 = (np.isnan(frejm['koncentracija'])) & (np.isnan(frejm['status']))
        # indeks konc je nan, status nije
        i2 = (np.isnan(frejm['koncentracija'])) & ([not m for m in np.isnan(frejm['status'])])
        i2 = i0 & ~ i1

        frejm.loc[i0 & i1, 'status'] = 32768
        frejm.loc[i2, 'status'] = [self._bor_value(m, 32768) for m in frejm.loc[i2, 'status']]
        frejm.loc[i0, 'flag'] = -1
        return frejm

    def _bor_value(self, status, val):
        try:
            return int(status) | int(val)
        except Exception:
            return 32768

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

    def _status_int_to_string(self, sint):
        if np.isnan(sint):
            return 'Status nije definiran'
        sint = int(sint)
        rez = self._statusLookup.get(sint, None)  # see if value exists
        if rez is None:
            rez = self._check_status_flags(sint)  # calculate
            self._statusLookup[sint] = rez  # store value for future lookup
        return rez


class NotIntegerFreq(Exception):
    pass
