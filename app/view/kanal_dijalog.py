# -*- coding: utf-8 -*-
from PyQt4 import QtGui, uic, QtCore

BASE_KANAL_DIJALOG, FORM_KANAL_DIJALOG = uic.loadUiType('./app/view/ui_files/kanal_dijalog.ui')


class KanalDijalog(BASE_KANAL_DIJALOG, FORM_KANAL_DIJALOG):
    """izbor kanala i vremenskog raspona"""

    def __init__(self, parent=None):
        super(BASE_KANAL_DIJALOG, self).__init__(parent)
        self.setModal(True)
        self.setupUi(self)
        self.izabraniKanal = None
        self.treeModel = None

    def set_program(self, drvo):
        self.treeModel = ProgramTreeModel(drvo)
        self.treeView.setModel(self.treeModel)

    def accept(self):
        self.vrijemeOd = self.kalendarOd.selectedDate().toPyDate()
        self.vrijemeDo = self.kalendarDo.selectedDate().toPyDate()
        indexes = self.treeView.selectedIndexes()
        if len(indexes) > 0:
            index = indexes[0]
            item = self.treeModel.getItem(index)
            self.izabraniKanal = item.itemData

        timeRaspon = (self.vrijemeDo - self.vrijemeOd).days
        if timeRaspon < 1:
            QtGui.QMessageBox.warning(self, 'Problem', 'Vremenski raspon nije dobro zadan')
            return
        elif self.izabraniKanal is None:
            QtGui.QMessageBox.warning(self, 'Problem', 'Program mjerenja nije zadan')
            return
        else:
            self.done(self.Accepted)


class TreeItem:
    def __init__(self, data, parent=None):
        self.parentItem = parent
        self.itemData = data
        self.childItems = []
        self.sorting_polje = data

    def sort_children(self):
        self.childItems = sorted(self.childItems, key=lambda item: item.sorting_polje)
        for child in self.childItems:
            child.sort_children()

    def appendChild(self, item):
        self.childItems.append(item)

    def child(self, row):
        return self.childItems[row]

    def child_count(self):
        return len(self.childItems)

    def parent(self):
        return self.parentItem

    def row(self):
        if self.parentItem:
            return self.parentItem.childItems.index(self)
        return 0

    def setData(self, data):
        self.itemData = data

    def columnCount(self):
        return len(self.itemData)

    def data(self, column):
        if column == 0:
            return self.itemData
        else:
            return None


class PostajaItem(TreeItem):
    def __init__(self, data, parent=None):
        super(self.__class__, self).__init__(data, parent)
        self.sorting_polje = self.itemData.naziv_postaje

    def columnCount(self):
        return 4

    def data(self, column):
        if column == 0:
            return self.itemData.naziv_postaje
        else:
            return None

    def sort_children(self):
        self.childItems = sorted(self.childItems, key=lambda item: item.sorting_polje)
        for child in self.childItems:
            child.sort_children()


class ProgramMjerenjaItem(TreeItem):
    def __init__(self, data, parent=None):
        super(self.__class__, self).__init__(data, parent)
        self.sorting_polje = self.itemData.id

    def columnCount(self):
        return 4

    def data(self, column):
        try:
            if column == 0:
                return self.itemData.id
            elif column == 1:
                return self.itemData.komponenta.formula
            elif column == 2:
                return self.itemData.usporedno
            elif column == 3:
                return self.itemData.komponenta.naziv

        except IndexError:
            return None


class ProgramTreeModel(QtCore.QAbstractItemModel):
    """
    Specificna implementacija QtCore.QAbstractItemModel, model nije editable!

    Za inicijalizaciju modela bitno je prosljediti root item neke tree strukture
    koja se sastoji od TreeItem instanci.
    """

    def __init__(self, data, parent=None):
        QtCore.QAbstractItemModel.__init__(self, parent)
        drvo = TreeItem(['stanice', None, None, None], parent=None)
        pomocna_mapa = {}
        for pm in data:
            if pm.postaja.id not in pomocna_mapa:
                pomocna_mapa[pm.postaja.id] = PostajaItem(pm.postaja, parent=drvo)
                drvo.appendChild(pomocna_mapa[pm.postaja.id])
            postaja = pomocna_mapa[pm.postaja.id]
            postaja.appendChild(ProgramMjerenjaItem(pm, parent=postaja))
        drvo.sort_children()
        self.rootItem = drvo

    def index(self, row, column, parent=QtCore.QModelIndex()):
        """
        funkcija vraca indeks u modelu za zadani red, stupac i parent
        """
        if parent.isValid() and parent.column() != 0:
            return QtCore.QModelIndex()

        parentItem = self.getItem(parent)
        childItem = parentItem.child(row)
        if childItem:
            # napravi index za red, stupac i child
            return self.createIndex(row, column, childItem)
        else:
            # vrati prazan QModelIndex
            return QtCore.QModelIndex()

    def getItem(self, index):
        """
        funckija vraca objekt pod indeksom index, ili rootItem ako indeks
        nije valjan
        """
        if index.isValid():
            item = index.internalPointer()
            if item:
                return item
        return self.rootItem

    def data(self, index, role=QtCore.Qt.DisplayRole):
        """
        primarni getter za vrijednost objekta
        za index i ulogu, vraca reprezentaciju view objektu
        """
        if not index.isValid():
            return None

        if role != QtCore.Qt.DisplayRole:
            return None
        item = self.getItem(index)

        return item.data(index.column())

    def rowCount(self, parent=QtCore.QModelIndex()):
        """
        vrati broj redaka (children objekata) za parent
        """
        parentItem = self.getItem(parent)
        return parentItem.child_count()

    def columnCount(self, parent=QtCore.QModelIndex()):
        """
        vrati broj stupaca (bitno za view)
        """
        if parent.isValid():
            return parent.internalPointer().columnCount()
        else:
            return self.rootItem.columnCount()

    def parent(self, index):
        """
        vrati parent od TreeItem objekta pod datim indeksom.
        Ako TreeItem name parenta, ili ako je indeks nevalidan, vrati
        defaultni QModelIndex (ostatak modela ga zanemaruje)
        """
        if not index.isValid():
            return QtCore.QModelIndex()

        childItem = self.getItem(index)
        parentItem = childItem.parent()
        if parentItem == self.rootItem:
            return QtCore.QModelIndex()
        else:
            return self.createIndex(parentItem.child_count(), 0, parentItem)

    def headerData(self, section, orientation, role):
        """
        headeri
        """
        headeri = ['Stanica/komponenta', 'Formula', 'Id', 'Usporedno']
        if orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.DisplayRole:
            return headeri[section]
        return None
