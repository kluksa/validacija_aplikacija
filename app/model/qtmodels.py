# -*- coding: utf-8 -*-
import logging

import numpy as np
import pandas as pd
from PyQt4 import QtGui, QtCore

################################################################################
################################################################################
"""
tree node object

self._parent --> referencira parent node (takodjer TreeItem objekt)
self._children --> LISTA djece (svi child itemi su TreeItem objekti)
self._data --> kontenjer koji sadrzi neke podatke (npr, lista, dict...)
"""


################################################################################
################################################################################
class KoncFrameModel(QtCore.QObject):
    """
    properties
    .datafrejm - frejm sa podacima
    .opis - "Postaja , naziv formula ( mjerna jedinica )"
    .kanalMeta - mapa metapodataka o kanalu
    .timestep - vremenski razmak izmedju podataka
    """

    def __init__(self, dokument, frejm=None, parent=None):
        QtCore.QObject.__init__(self, parent)
        # TODO! hardcoding = bad...
        self.dokument = dokument
        self._expectedCols = ['vrijednost', 'korekcija', 'flag', 'statusString',
                              'status', 'id', 'A', 'B', 'Sr', 'LDL']
        self._dataFrejm = pd.DataFrame(columns=self._expectedCols)
        self._opis = "Postaja , naziv formula ( mjerna jedinica )"
        self._kanalMeta = {}

        self._statusLookup = {}
        self._status_bits = {}

        if frejm is None:
            frejm = pd.DataFrame(columns=self._expectedCols)
        self.frejm = frejm

    def set_status_bits(self, x):
        self._status_bits = x

    def sredi_status_stringove(self, frejm):
        statstr = [self._status_int_to_string(i) for i in frejm.loc[:, 'status']]
        frejm.loc[:, 'statusString'] = statstr
        return frejm

    @property
    def datafrejm(self):
        # TODO ZASTO kopirati????
        return self._dataFrejm.copy()

    @datafrejm.setter
    def datafrejm(self, x):
        if isinstance(x, pd.core.frame.DataFrame):
            # TODO!
            self._dataFrejm = x[self._expectedCols]  # reodrer / crop columns
            indeks_korekcija_ispod_ldl = self._dataFrejm['korekcija'] < self._dataFrejm['LDL']
            indeks_korekcija_iznad_ldl = self._dataFrejm['korekcija'] >= self._dataFrejm['LDL']
            self._dataFrejm.loc[indeks_korekcija_ispod_ldl, 'status'] = [(int(i) | 2048) for i in self._dataFrejm.loc[
                indeks_korekcija_ispod_ldl, 'status']]
            self._dataFrejm.loc[indeks_korekcija_iznad_ldl, 'status'] = [(int(i) & (~2048)) for i in
                                                                         self._dataFrejm.loc[
                                                                             indeks_korekcija_iznad_ldl, 'status']]
            # TODO! extra flag ako ispod ldl
            self._dataFrejm.loc[indeks_korekcija_ispod_ldl, 'flag'] = -1
            # sredi status string
            self._dataFrejm = self.sredi_status_stringove(self._dataFrejm)
        # self.layoutChanged.emit()
        else:
            raise TypeError('Not a pandas DataFrame object'.format(type(x)))

    @property
    def opis(self):
        return self._opis

    @opis.setter
    def opis(self, x):
        if isinstance(x, str):
            self._opis = x
        else:
            raise TypeError('{0} . Not a string.'.format(type(x)))

    @property
    def timestep(self):
        try:
            indeksi = self._dataFrejm.index
            step = round((indeksi[1] - indeksi[0]).total_seconds(), 0)
            return step
        except Exception as err:
            logging.error(str(err), exc_info=True)

    @property
    def rasponi(self):
        if 'LDL' in self._dataFrejm.columns:
            indeks = self._dataFrejm.index
            ispod = self._dataFrejm.loc[:, 'korekcija'] < self._dataFrejm.loc[:, 'LDL']
            preko = self._dataFrejm.loc[:, 'korekcija'] > self._dataFrejm.loc[:, 'LDL']
            krivi = [i or j for i, j in zip(ispod, preko)]

            pos = 0
            out = []
            while pos < len(indeks):
                # get prvi True (prekoracenje)
                try:
                    loc1 = krivi.index(True, pos)
                    pos = loc1
                    # get prvi false nakon pronadjeng indeksa
                    try:
                        loc2 = krivi.index(False, pos)
                        pos = loc2
                        out.append((indeks[loc1], indeks[loc2]))
                    except ValueError:
                        # svi su krivi do kraja
                        loc2 = len(indeks) - 1
                        out.append((indeks[loc1], indeks[loc2]))
                        break
                except ValueError:
                    # nema prekoracenja, break iz while petlje
                    break
            return out
        else:
            return []

    def get_autoscale_y_range(self, t1, t2):
        """getter y raspona podataka izmedju vremena t1 i t2. Za raspon se promatraju
        samo podaci sa dobrim flagom (>0)"""
        slajs = self._dataFrejm[self._dataFrejm.index >= t1]
        slajs = slajs[slajs.index <= t2]
        slajs = slajs[slajs['flag'] >= 0]
        if len(slajs):
            min_c = np.nanmin(slajs['vrijednost'])
            max_c = np.nanmax(slajs['vrijednost'])
            min_k = np.nanmin(slajs['korekcija'])
            max_k = np.nanmax(slajs['korekcija'])
            ymin = np.nanmin([min_c, min_k])
            ymax = np.nanmax([max_c, max_k])
            return ymin, ymax
        else:
            return np.NaN, np.NaN

    def get_index_position(self, tajmstemp):
        """Za zadani pandas timestamp, vrati odgovarajuci broj reda"""
        try:
            indeksi = self._dataFrejm.index
            red = indeksi.get_loc(tajmstemp)
            return red
        except KeyError as err:
            logging.error(str(err), exc_info=True)

    def promjeni_flag(self, arg_dict):
        """promjena flaga na intervalu, argDict je dict [od, do, noviFlag]"""
        od = arg_dict['od']
        do = arg_dict['do']
        fl = arg_dict['noviFlag']
        self._dataFrejm.loc[od:do, 'flag'] = fl
        if fl < 0:
            self._dataFrejm.loc[od:do, 'status'] = [(int(i) | 1024) for i in self._dataFrejm.loc[od:do, 'status']]
        else:
            self._dataFrejm.loc[od:do, 'status'] = [(int(i) & (~1024)) for i in self._dataFrejm.loc[od:do, 'status']]

        # TODO! LDL se ne smije proglasiti ok... nikad
        ldlmask = [self._check_for_ldl(i) for i in self._dataFrejm.loc[:, 'status']]
        self._dataFrejm.loc[ldlmask, 'flag'] = -1

        self._dataFrejm = self.sredi_status_stringove(self._dataFrejm)
        self.layoutChanged.emit()

    def _check_for_ldl(self, x):
        # TODO! helper funkcija... mora na bolji nacin
        x = int(x)
        if x | 2048 == x:
            return True
        else:
            return False

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
        if rez is not None:
            rez = self._check_status_flags(sint)  # calculate
            self._statusLookup[sint] = rez  # store value for future lookup
        return rez


class KoncTableModel(QtCore.QAbstractTableModel):
    # QT functionality
    def __init__(self, data, parent=None):
        super(KoncTableModel, self).__init__(parent)
        self._dataFrejm = data

    def rowCount(self, parent=QtCore.QModelIndex()):
        return len(self._dataFrejm)

    def columnCount(self, parent=QtCore.QModelIndex()):
        return 5

    def data(self, index, role):
        if not index.isValid():
            return None
        row = index.row()
        col = index.column()
        if role == QtCore.Qt.DisplayRole:
            value = self._dataFrejm.iloc[row, col]
            if col == 0 or col == 1:
                return "{0:.2f}".format(value)  # koncentracija
            elif col == 2:
                return "{0:.0f}".format(value)  # status string
            elif col == 3:
                return value
            elif col == 4:
                return "{0:.0f}".format(value)
            else:
                return str(value)

    def headerData(self, section, orientation, role):
        if orientation == QtCore.Qt.Vertical:
            if role == QtCore.Qt.DisplayRole:
                return str(self._dataFrejm.index[section].strftime('%Y-%m-%d %H:%M:%S'))
        if orientation == QtCore.Qt.Horizontal:
            if role == QtCore.Qt.DisplayRole:
                return str(self._dataFrejm.columns[section])

    def flags(self, index):
        if index.isValid():
            return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable


################################################################################
################################################################################
class ZeroSpanFrameModel(QtCore.QObject):
    """
    properties
    .datafrejm - frejm sa podacima
    """

    def __init__(self, tip, dokument, frejm=None, parent=None):
        # TODO! hardcoding = bad...
        super().__init__(parent)
        self.dokument = dokument
        self._expectedCols = ['vrijednost', 'korekcija', 'minDozvoljeno',
                              'maxDozvoljeno', 'A', 'B', 'Sr', 'LDL']
        self._dataFrejm = pd.DataFrame(columns=self._expectedCols)
        if frejm is None:
            frejm = pd.DataFrame(columns=self._expectedCols)
        self.frejm = frejm

    @property
    def datafrejm(self):
        return self._dataFrejm.copy()

    @datafrejm.setter
    def datafrejm(self, x):
        if isinstance(x, pd.core.frame.DataFrame):
            self._dataFrejm = x[self._expectedCols]  # reodrer / crop columns
        # self.layoutChanged.emit()
        else:
            raise TypeError('Not a pandas DataFrame object'.format(type(x)))

    @property
    def bad_index(self):
        ispod = self._dataFrejm.loc[:, 'korekcija'] < self._dataFrejm.loc[:, 'minDozvoljeno']
        preko = self._dataFrejm.loc[:, 'korekcija'] > self._dataFrejm.loc[:, 'maxDozvoljeno']
        krivi = [i or j for i, j in zip(ispod, preko)]
        return krivi

    @property
    def rasponi(self):
        indeks = self._dataFrejm.index
        krivi = self.bad_index

        pos = 0
        out = []
        while pos < len(indeks):
            # get prvi True (prekoracenje)
            try:
                loc1 = krivi.index(True, pos)
                pos = loc1
                # get prvi false nakon pronadjeng indeksa
                try:
                    loc2 = krivi.index(False, pos)
                    pos = loc2
                    out.append((indeks[loc1], indeks[loc2]))
                except ValueError:
                    # svi su krivi do kraja
                    loc2 = len(indeks) - 1
                    out.append((indeks[loc1], indeks[loc2]))
                    break
            except ValueError:
                # nema prekoracenja, break iz while petlje
                break
        return out

    def get_autoscale_y_range(self, t1, t2):
        """getter y raspona podataka izmedju vremena t1 i t2"""
        slajs = self._dataFrejm[self._dataFrejm.index >= t1]
        slajs = slajs[slajs.index <= t2]
        if len(slajs):
            ymin = np.nanmin(slajs)
            ymax = np.nanmax(slajs)
            return ymin, ymax
        else:
            return np.NaN, np.NaN
