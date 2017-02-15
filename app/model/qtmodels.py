# -*- coding: utf-8 -*-
import copy
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
class KoncFrameModel(QtCore.QAbstractTableModel):
    """
    properties
    .datafrejm - frejm sa podacima
    .opis - "Postaja , naziv formula ( mjerna jedinica )"
    .kanalMeta - mapa metapodataka o kanalu
    .timestep - vremenski razmak izmedju podataka
    """

    def __init__(self, frejm=None, parent=None):
        QtCore.QAbstractTableModel.__init__(self, parent)
        # TODO! hardcoding = bad...
        self._expectedCols = ['koncentracija', 'korekcija', 'flag', 'statusString',
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
        statstr = [self._statusInt_to_statusString(i) for i in frejm.loc[:,'status']]
        frejm.loc[:,'statusString'] = statstr
        return frejm

    @property
    def datafrejm(self):
        # TODO ZASTO kopirati????
        return self._dataFrejm.copy()

    @datafrejm.setter
    def datafrejm(self, x):
        if isinstance(x, pd.core.frame.DataFrame):
            #TODO!
            self._dataFrejm = x[self._expectedCols]  # reodrer / crop columns
            indeksKorekcijaIspodLDL = self._dataFrejm['korekcija'] < self._dataFrejm['LDL']
            indeksKorekcijaIznadLDL = self._dataFrejm['korekcija'] >= self._dataFrejm['LDL']
            self._dataFrejm.loc[indeksKorekcijaIspodLDL, 'status'] = [(int(i) | 2048) for i in self._dataFrejm.loc[indeksKorekcijaIspodLDL, 'status']]
            self._dataFrejm.loc[indeksKorekcijaIznadLDL, 'status'] = [(int(i) & (~2048)) for i in self._dataFrejm.loc[indeksKorekcijaIznadLDL, 'status']]
            #TODO! extra flag ako ispod ldl
            self._dataFrejm.loc[indeksKorekcijaIspodLDL, 'flag'] = -1
            #sredi status string
            self._dataFrejm = self.sredi_status_stringove(self._dataFrejm)
            self.layoutChanged.emit()
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
    def kanalMeta(self):
        # TODO koji K???? Zašto pobogu deep copy?
        return copy.deepcopy(self._kanalMeta)

    @kanalMeta.setter
    def kanalMeta(self, x):
        if isinstance(x, dict):
            self._kanalMeta = copy.deepcopy(x)
        else:
            raise TypeError('{0} . Not a dictionary.'.format(type(x)))

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
            minC = np.nanmin(slajs['koncentracija'])
            maxC = np.nanmax(slajs['koncentracija'])
            minK = np.nanmin(slajs['korekcija'])
            maxK = np.nanmax(slajs['korekcija'])
            ymin = np.nanmin([minC, minK])
            ymax = np.nanmax([maxC, maxK])
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

    def promjeni_flag(self, argDict):
        """promjena flaga na intervalu, argDict je dict [od, do, noviFlag]"""
        od = argDict['od']
        do = argDict['do']
        fl = argDict['noviFlag']
        self._dataFrejm.loc[od:do, 'flag'] = fl
        if fl < 0:
            self._dataFrejm.loc[od:do, 'status'] = [(int(i) | 1024) for i in self._dataFrejm.loc[od:do, 'status']]
        else:
            self._dataFrejm.loc[od:do, 'status'] = [(int(i) & (~1024)) for i in self._dataFrejm.loc[od:do, 'status']]

        #TODO! LDL se ne smije proglasiti ok... nikad
        ldlmask = [self._check_for_ldl(i) for i in self._dataFrejm.loc[:, 'status']]
        self._dataFrejm.loc[ldlmask, 'flag'] = -1

        self._dataFrejm = self.sredi_status_stringove(self._dataFrejm)
        self.layoutChanged.emit()

    def _check_for_ldl(self, x):
        #TODO! helper funkcija... mora na bolji nacin
        x = int(x)
        if x | 2048 == x:
            return True
        else:
            return False

    def update_korekciju_i_ldl(self, kor, ldl, a, b, sr):
        # TODO!
        self._dataFrejm['korekcija'] = kor
        self._dataFrejm['LDL'] = ldl
        self._dataFrejm['A'] = a
        self._dataFrejm['B'] = b
        self._dataFrejm['Sr'] = sr
        self.layoutChanged.emit()

    # QT functionality
    def rowCount(self, parent=QtCore.QModelIndex()):
        return len(self._dataFrejm)

    def columnCount(self, parent=QtCore.QModelIndex()):
        return 6

    def flags(self, index):
        if index.isValid():
            return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable

    def data(self, index, role):
        if not index.isValid():
            return None
        row = index.row()
        col = index.column()
        if role == QtCore.Qt.DisplayRole:
            value = self._dataFrejm.iloc[row, col]
            if col == 0:
                return str(round(value, 3))  # koncentracija
            elif col == 1:
                return str(round(value, 3))  # korekcija
            elif col == 3:
                return value  # status string
            else:
                return str(value)

    def headerData(self, section, orientation, role):
        if orientation == QtCore.Qt.Vertical:
            if role == QtCore.Qt.DisplayRole:
                return str(self._dataFrejm.index[section].strftime('%Y-%m-%d %H:%M:%S'))
        if orientation == QtCore.Qt.Horizontal:
            if role == QtCore.Qt.DisplayRole:
                return str(self._dataFrejm.columns[section])

    def _check_bit(self, broj, bit_position):
        """
        Pomocna funkcija za testiranje statusa
        Napravi temporary integer koji ima samo jedan bit vrijednosti 1 na poziciji
        bit_position. Napravi binary and takvog broja i ulaznog broja.
        Ako oba broja imaju bit 1 na istoj poziciji vrati True, inace vrati False.
        """
        if bit_position != None:
            temp = 1 << int(bit_position) #left shift bit za neki broj pozicija
            if int(broj) & temp > 0: # binary and izmjedju ulaznog broja i testnog broja
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
        rez = self._statusLookup.get(sint, None) #see if value exists
        if rez == None:
            rez = self._check_status_flags(sint) #calculate
            self._statusLookup[sint] = rez #store value for future lookup
        return rez

################################################################################
################################################################################
class ZeroSpanFrameModel(QtCore.QAbstractTableModel):
    """
    properties
    .datafrejm - frejm sa podacima
    """

    def __init__(self, tip, frejm=None, parent=None):
        # TODO! hardcoding = bad...
        QtCore.QAbstractTableModel.__init__(self, parent)
        self._expectedCols = [str(tip), 'korekcija', 'minDozvoljeno',
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
            self.layoutChanged.emit()
        else:
            raise TypeError('Not a pandas DataFrame object'.format(type(x)))

    @property
    def bad_index(self):
        ispod = self._dataFrejm.loc[:, 'korekcija'] < self._dataFrejm.loc[:, 'minDozvoljeno']
        preko = self._dataFrejm.loc[:, 'korekcija'] > self._dataFrejm.loc[:, 'maxDozvoljeno']
        krivi = [i or j for i, j in zip(ispod, preko)]
        return krivi

    @property
    def good_index(self):
        krivi = self.bad_index
        dobri = [not i for i in krivi]
        return dobri

    @property
    def rasponi(self):
        indeks = self._dataFrejm.index
        ispod = self._dataFrejm.loc[:, 'korekcija'] < self._dataFrejm.loc[:, 'minDozvoljeno']
        preko = self._dataFrejm.loc[:, 'korekcija'] > self._dataFrejm.loc[:, 'maxDozvoljeno']
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

    def get_najblizu_vrijednost(self, tajm):
        """getter najblize vijednosti zero ili span vremenskom indeksu tajm (pd.tslib.Timestamp)"""
        manji = self._dataFrejm[self._dataFrejm.index <= tajm]
        if len(manji):
            t1 = manji.index[-1]
            v1 = manji.loc[t1, self._expectedCols[0]]
            v1k = manji.loc[t1, 'korekcija']
        else:
            t1 = None
            v1 = None
            v1k = None
        # svi veci od tajm
        veci = self._dataFrejm[self._dataFrejm.index > tajm]
        if len(veci):
            t2 = veci.index[0]
            v2 = veci.loc[t2, self._expectedCols[0]]
            v2k = manji.loc[t1, 'korekcija']
        else:
            t2 = None
            v2 = None
            v2k = None

        if t1 != None and t2 == None:
            return t1, v1, v1k
        elif t1 == None and t2 != None:
            return t2, v2, v2k
        elif t1 == None and t2 == None:
            return 'n/a', 'n/a', 'n/a'
        else:
            d1 = (tajm - t1).total_seconds()
            d2 = (t2 - tajm).total_seconds()
            if d1 > d2:
                return t2, v2, v2k
            else:
                return t1, v1, v1k

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

    def update_korekciju_i_ldl(self, kor, ldl, a, b, sr):
        # TODO!
        self._dataFrejm['korekcija'] = kor
        self._dataFrejm['LDL'] = ldl
        self._dataFrejm['A'] = a
        self._dataFrejm['B'] = b
        self._dataFrejm['Sr'] = sr
        self.layoutChanged.emit()

    # QT functionality
    def rowCount(self, parent=QtCore.QModelIndex()):
        return len(self._dataFrejm)

    def columnCount(self, parent=QtCore.QModelIndex()):
        return 4

    def flags(self, index):
        if index.isValid():
            return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable

    def data(self, index, role):
        if not index.isValid():
            return None
        row = index.row()
        col = index.column()
        if role == QtCore.Qt.DisplayRole:
            value = self._dataFrejm.iloc[row, col]
            return str(round(value, 3))

    def headerData(self, section, orientation, role):
        if orientation == QtCore.Qt.Vertical:
            if role == QtCore.Qt.DisplayRole:
                return str(self._dataFrejm.index[section].strftime('%Y-%m-%d %H:%M:%S'))
        if orientation == QtCore.Qt.Horizontal:
            if role == QtCore.Qt.DisplayRole:
                return str(self._dataFrejm.columns[section])


################################################################################
################################################################################
class KorekcijaFrameModel(QtCore.QAbstractTableModel):
    def __init__(self, frejm=None, parent=None):
        QtCore.QAbstractTableModel.__init__(self, parent)
        self._dummydata = {'vrijeme': '', 'A': np.NaN, 'B': np.NaN, 'Sr': np.NaN, 'remove': '', 'calc':''}
        self._expectedCols = ['vrijeme', 'A', 'B', 'Sr', 'remove', 'calc']
        self._dataFrejm = pd.DataFrame(columns=self._expectedCols)
        if frejm is None:
            frejm = pd.DataFrame(columns=self._expectedCols)
        self.datafrejm = frejm

    @property
    def datafrejm(self):
        # TODO zašto kopija????
        return self._dataFrejm.copy()

    @datafrejm.setter
    def datafrejm(self, x):
        if isinstance(x, pd.core.frame.DataFrame):
            self._dataFrejm = x[self._expectedCols]  # reodrer / crop columns
            # dodaj prazan red na kraj
            red = pd.DataFrame(data=self._dummydata,
                               columns=self._expectedCols,
                               index=[len(self._dataFrejm)])
            self._dataFrejm = self._dataFrejm.append(red)
            self.sort(0, QtCore.Qt.AscendingOrder)
            # reindex
            self._dataFrejm.reset_index()
            self.layoutChanged.emit()
        else:
            raise TypeError('Not a pandas DataFrame object'.format(type(x)))

    def set_AB_for_row(self, red, a, b):
        self._dataFrejm.iloc[red, 1] = a
        self._dataFrejm.iloc[red, 2] = b

        self.layoutChanged.emit()
        self.emit(QtCore.SIGNAL('update_persistent_delegate'))

    def calc_ldl_values(self, frejm):
        # TODO zasto ovdje??? LDL bi se trebao racunati u dokumentu. Ovo je samo GUI kontroler
        """dohvati ldl vrijednosti..."""
        sr = frejm['Sr']
        A = frejm['A']
        ldl = (-3.3 * sr) / A
        frejm['LDL'] = ldl
        return frejm

    def primjeni_korekciju_na_frejm(self, frejm):
        # TODO zasto ovdje???? Ovo bi trebao raditi dokument. Ovo je najobicnija kontrola od tablice
        """primjena korekcije na zadani frejm..."""
        # pripremi frejm korekcije za rad
        df = self._dataFrejm.copy()
        # izbaci zadnji red (za dodavanje stvari...)
        df = df.iloc[:-1, :]
        TEST1  = len(df) # broj redova tablice
        # sort
        df.dropna(axis=0, inplace=True)
        df.sort_values(['vrijeme'], inplace=True)
        df = df.set_index(df['vrijeme'])
        #drop stupce koji su pomocni
        df.drop(['remove', 'calc', 'vrijeme'], axis=1, inplace=True)
        df['A'] = df['A'].astype(float)
        df['B'] = df['B'].astype(float)
        df['Sr'] = df['Sr'].astype(float)

        TEST2  = len(df) # broj redova tablice bez n/a
        if TEST1 != TEST2:
            raise ValueError('Parametri korekcije nisu dobro ispunjeni')
        if (not len(df)) or (not len(frejm)):
            # korekcija nije primjenjena jer je frejm sa parametrima prazan ili je sam frejm prazan
            return frejm
        try:
            zadnjiIndeks = list(df.index)[-1]
            # sredi interpolaciju dodaj na kraj podatka zadnju vrijednost
            krajPodataka = frejm.index[-1]
            df.loc[krajPodataka, 'A'] = df.loc[zadnjiIndeks, 'A']
            df.loc[krajPodataka:, 'B'] = df.loc[zadnjiIndeks, 'B']
            df.loc[krajPodataka:, 'Sr'] = df.loc[zadnjiIndeks, 'Sr']
            # interpoliraj na minutnu razinu
            savedSr = df['Sr']
            df = df.resample('Min').interpolate()
            # sredi Sr da bude skokovit
            for i in range(len(savedSr) - 1):
                ind1 = savedSr.index[i]
                ind2 = savedSr.index[i + 1]
                val = savedSr.iloc[i]
                df.loc[ind1:ind2, 'Sr'] = val
            df = self.calc_ldl_values(df)
            df = df.reindex(frejm.index)  # samo za definirane indekse...
            # slozi podatke u input frejm
            frejm['A'] = df['A']
            frejm['B'] = df['B']
            frejm['Sr'] = df['Sr']
            frejm['LDL'] = df['LDL']
            # izracunaj korekciju i apply
            korekcija = frejm.iloc[:, 0] * frejm.loc[:, 'A'] + frejm.loc[:, 'B']
            frejm['korekcija'] = korekcija
            return frejm
        except Exception as err:
            logging.error(str(err), exc_info=True)
            QtGui.QMessageBox.warning(QtGui.QWidget(), 'Problem', 'Problem kod racunanja korekcije')
            return frejm

    # QT functionality
    def rowCount(self, parent=QtCore.QModelIndex()):
        return len(self._dataFrejm)

    def columnCount(self, parent=QtCore.QModelIndex()):
        return 6

    def flags(self, index):
        if index.isValid():
            return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEditable

    def sort(self, col, order):
        """
        Sort tablicu prema broju stupca i redosljedu (QtCore.Qt.AscendingOrder
        ili QtCore.Qt.DescendingOrder).

        Dozvoljeno je samo sortiranje 0 stupca (vrijeme) i samo u
        uzlaznom nacinu
        """
        if col == 0 and order == QtCore.Qt.AscendingOrder:
            self.layoutAboutToBeChanged.emit()
            self._dataFrejm.iloc[-1, 0] = pd.NaT
            self._dataFrejm = self._dataFrejm.sort_values('vrijeme')
            self._dataFrejm.iloc[-1, 0] = ''
            #do the sort
            self.layoutChanged.emit()
            self.emit(QtCore.SIGNAL('update_persistent_delegate'))
        else:
            pass

    def insertRows(self, position, rows=1, index=QtCore.QModelIndex()):
        try:
            self.beginInsertRows(QtCore.QModelIndex(),
                                 position,
                                 position + rows - 1)
            # uguraj index u frejm na kraj
            red = pd.DataFrame(data=self._dummydata,
                               columns=self._expectedCols,
                               index=[len(self._dataFrejm)])
            self._dataFrejm = self._dataFrejm.append(red)
            self._dataFrejm = self._dataFrejm.reindex()

            self.endInsertRows()
            self.layoutChanged.emit()
            self.sort(0, QtCore.Qt.AscendingOrder)
            #self.emit(QtCore.SIGNAL('update_persistent_delegate'))
            return True
        except Exception as err:
            logging.error(str(err), exc_info=True)
            return False

    def removeRows(self, position, rows=1, index=QtCore.QModelIndex()):
        try:
            if position == self.rowCount() - 1:
                # clear red...
                for col in range(len(self._dataFrejm.columns)):
                    self._dataFrejm.iloc[-1, col] = ''
                self.layoutChanged.emit()
                return False  # nemoj maknuti zadnji red NIKADA!
            self.beginRemoveRows(QtCore.QModelIndex(),
                                 position,
                                 position + rows - 1)
            # drop row...
            self._dataFrejm.drop(self._dataFrejm.index[position], inplace=True)
            self._dataFrejm = self._dataFrejm.reindex()

            self.endRemoveRows()
            self.layoutChanged.emit()
            self.sort(0, QtCore.Qt.AscendingOrder)
            #self.emit(QtCore.SIGNAL('update_persistent_delegate'))
            return True
        except Exception as err:
            logging.error(str(err), exc_info=True)
            return False

    def setData(self, index, value, role=QtCore.Qt.EditRole):
        if not index.isValid():
            return False
        red = index.row()
        stupac = index.column()
        try:
            if stupac == 0:
                # NaT fix
                if value == "":
                    return False
                ts = pd.to_datetime(value)
                self._dataFrejm.iloc[red, stupac] = ts
                # sort index
                self._dataFrejm.sort_index()

                # napravi novi redak ako se editira zadnji redak u tablici
                if red == self.rowCount() - 1:
                    self.insertRows(123123)  # dummy positional argument
            elif stupac in [1, 2, 3]:
                self._dataFrejm.iloc[red, stupac] = float(value)
            else:
                self._dataFrejm.iloc[red, stupac] = str(value)

            self.dataChanged.emit(QtCore.QModelIndex(), QtCore.QModelIndex())
            if stupac == 0:
                self.sort(0, QtCore.Qt.AscendingOrder)
            return True
        except Exception as err:
            logging.error(str(err), exc_info=True)
            return False

    def data(self, index, role):
        if not index.isValid():
            return None
        row = index.row()
        col = index.column()
        if role == QtCore.Qt.DisplayRole or role == QtCore.Qt.EditRole:
            val = self._dataFrejm.iloc[row, col]
            if col == 0:
                if isinstance(val, pd.tslib.Timestamp):
                    return str(val.strftime('%Y-%m-%d %H:%M:%S'))
                else:
                    return str(val)
            else:
                return str(val)

    def headerData(self, section, orientation, role):
        if orientation == QtCore.Qt.Vertical:
            if role == QtCore.Qt.DisplayRole:
                return str(section)
        if orientation == QtCore.Qt.Horizontal:
            if role == QtCore.Qt.DisplayRole:
                return str(self._dataFrejm.columns[section])


################################################################################
################################################################################
class GumbDelegate(QtGui.QItemDelegate):
    def __init__(self, parent):
        QtGui.QItemDelegate.__init__(self, parent)

    def createEditor(self, parent, option, index):
        gumb = QtGui.QPushButton('X', parent=parent)
        gumb.clicked.connect(self.delete_or_clear_row)
        return gumb

    def setEditorData(self, editor, index):
        pass

    def setModelData(self, editor, model, index):
        pass
        # model.setData(index, editor.text())

    def delete_or_clear_row(self, ind):
        # glupo do bola, ali radi za sada
        view = self.sender().parent().parent()
        model = view.model()
        indeks = view.indexAt(self.sender().pos())
        model.removeRows(indeks.row())
        self.commitData.emit(self.sender())


class CalcGumbDelegate(QtGui.QItemDelegate):
    def __init__(self, parent):
        QtGui.QItemDelegate.__init__(self, parent)

    def createEditor(self, parent, option, index):
        gumb = QtGui.QPushButton('AB', parent=parent)
        gumb.clicked.connect(self.calculate_AB_for_row)
        return gumb

    def setEditorData(self, editor, index):
        pass

    def setModelData(self, editor, model, index):
        pass
        # model.setData(index, editor.text())

    def calculate_AB_for_row(self, x):
        # glupo do bola, ali radi za sada
        view = self.sender().parent().parent() #tableview
        model = view.model() #model unutar table view-a
        indeks = view.indexAt(self.sender().pos())
        gui = view.parent().parent() #gui insatnca
        ab = gui.get_AB_values()
        if ab:
            model.set_AB_for_row(indeks.row(), ab[0], ab[1])
            self.commitData.emit(self.sender())
