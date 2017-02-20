import logging
import os
from datetime import timedelta

import numpy as np
import pandas as pd
from PyQt4 import QtGui, QtCore


def export_frame(frame, fname):
    frame.to_csv(fname, sep=';')


def export_korekcije(dokument, fname):
    if fname:
        frejmPodaci = dokument.koncModel.datafrejm
        frejmZero = dokument.zeroModel.datafrejm
        frejmSpan = dokument.spanModel.datafrejm
        frejmKor = dokument.korekcijaModel.datafrejm
        # izbaci zadnji red (za dodavanje stvari...)
        frejmKor = frejmKor.iloc[:-1, :]
        # drop nepotrebne stupce (remove/calc placeholderi)
        frejmKor.drop(['remove', 'calc'], axis=1, inplace=True)

        if not fname.endswith('.csv'):
            fname += '.csv'
        # os... sastavi imena fileova
        folder, name = os.path.split(fname)
        podName = "podaci_" + name
        zeroName = "zero_" + name
        spanName = "span_" + name
        korName = "korekcijski_parametri_" + name
        podName = os.path.normpath(os.path.join(folder, podName))
        zeroName = os.path.normpath(os.path.join(folder, zeroName))
        spanName = os.path.normpath(os.path.join(folder, spanName))
        korName = os.path.normpath(os.path.join(folder, korName))
        frejmPodaci.to_csv(podName, sep=';')
        frejmZero.to_csv(zeroName, sep=';')
        frejmSpan.to_csv(spanName, sep=';')
        frejmKor.to_csv(korName, sep=';')
        return True
    return False


class DownloadProgressBar(QtGui.QProgressBar):
    def __init__(self, restRequest, parent=None):
        super(QtGui.QProgressBar, self).__init__(parent)
        self.setWindowTitle('Load status:')
        self.setGeometry(300, 300, 200, 40)
        self.setRange(0, 100)
        self.thread = QtCore.QThread()
        self.download_podataka_worker = DownloadPodatakaWorker(restRequest)
        self.download_podataka_worker.moveToThread(self.thread)
        self.download_podataka_worker.progress_signal.connect(self.ucitavanje_progress)
        self.download_podataka_worker.greska_signal.connect(self.ucitavanje_greska)
        self.download_podataka_worker.greska_signal.connect(self.thread.quit)
        self.download_podataka_worker.gotovo_signal.connect(self.thread.quit)
        self.thread.started.connect(self.download_podataka_worker.run)

    def ucitaj(self, aktivni_kanal, vrijeme_od, vrijeme_do):
        self.download_podataka_worker.set(aktivni_kanal, vrijeme_od, vrijeme_do)
        self.thread.start()
        self.show()

    def ucitavanje_progress(self, n):
        self.setValue(n)

    def ucitavanje_greska(self, err):
        QtGui.QMessageBox.warning(self, 'Pogreška', 'Učitavanje podataka nije uspjelo ' + str(err))
        self.close()


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
