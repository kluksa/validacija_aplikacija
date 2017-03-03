from PyQt4 import QtCore, QtGui
from app.view.abcalc import ABKalkulator
import logging
import pandas as pd
import numpy as np


class KorekcijaTablica(QtGui.QTableView):


    def __init__(self, parent = None):
        super(KorekcijaTablica, self).__init__(parent)
        self.setModel(KorekcijaFrameModel())
        self.sredi_delegate_za_tablicu()
        self.model().update_persistent_delegate.connect(self.sredi_delegate_za_tablicu)

    def sredi_delegate_za_tablicu(self):
        model = self.model()
        self.setItemDelegateForColumn(4, GumbDelegate(self))
        self.setItemDelegateForColumn(5, CalcGumbDelegate(self))
        for red in range(0, model.rowCount()):
            self.closePersistentEditor(model.index(red, 4))
            self.closePersistentEditor(model.index(red, 5))
            self.openPersistentEditor(model.index(red, 4))
            self.openPersistentEditor(model.index(red, 5))


class KorekcijaFrameModel(QtCore.QAbstractTableModel):

    update_persistent_delegate = QtCore.pyqtSignal()

    def __init__(self,  frejm=None, parent=None):
        QtCore.QAbstractTableModel.__init__(self, parent)
        self._dummydata = {'vrijeme': '', 'A': np.NaN, 'B': np.NaN, 'Sr': np.NaN, 'remove': '', 'calc': ''}
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
    def datafrejm(self, df):
        if isinstance(df, pd.core.frame.DataFrame):
            self._dataFrejm = df[self._expectedCols]  # reodrer / crop columns
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
            raise TypeError('Not a pandas DataFrame object'.format(type(df)))

    def set_ab_for_row(self, red, a, b):
        self._dataFrejm.iloc[red, 1] = a
        self._dataFrejm.iloc[red, 2] = b

        self.layoutChanged.emit()
        self.update_persistent_delegate.emit()
#        self.emit(QtCore.SIGNAL('update_persistent_delegate'))

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
            # do the sort
            self.layoutChanged.emit()
            self.update_persistent_delegate.emit()
#            self.emit(QtCore.SIGNAL('update_persistent_delegate'))
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
            # self.emit(QtCore.SIGNAL('update_persistent_delegate'))
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
            # self.emit(QtCore.SIGNAL('update_persistent_delegate'))
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
        view = self.sender().parent().parent()  # tableview
        model = view.model()  # model unutar table view-a
        indeks = view.indexAt(self.sender().pos())
#        gui = view.parent().parent()  # gui insatnca
        ab = self.get_AB_values()
        if ab:
            model.set_ab_for_row(indeks.row(), ab[0], ab[1])
            self.commitData.emit(self.sender())

    def get_AB_values(self):
        dijalogAB = ABKalkulator()
        if dijalogAB.exec_():
            return dijalogAB.AB
        else:
            return None

