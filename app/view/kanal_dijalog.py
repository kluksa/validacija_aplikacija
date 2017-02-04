# -*- coding: utf-8 -*-
from PyQt4 import QtGui, QtCore, uic

BASE_KANAL_DIJALOG, FORM_KANAL_DIJALOG = uic.loadUiType('./app/view/ui_files/kanal_dijalog.ui')


class KanalDijalog(BASE_KANAL_DIJALOG, FORM_KANAL_DIJALOG):
    """izbor kanala i vremenskog raspona"""

    def __init__(self, drvo, od=None, do=None, parent=None):
        super(BASE_KANAL_DIJALOG, self).__init__(parent)
        self.setupUi(self)

        self.drvo = drvo
        self.izabraniKanal = None

        self.treeView.setModel(self.drvo)
        self.treeView.clicked.connect(self.resolve_tree_click)

        if od:
            datum = QtCore.QDate(od.year, od.month, od.day)
            self.kalendarOd.setSelectedDate(datum)
        if do:
            datum = QtCore.QDate(do.year, do.month, do.day)
            self.kalendarDo.setSelectedDate(datum)

    def accept(self):
        od = self.kalendarOd.selectedDate().toPyDate()
        do = self.kalendarDo.selectedDate().toPyDate()
        timeRaspon = (do - od).days
        if timeRaspon < 1:
            QtGui.QMessageBox.warning(self, 'Problem', 'Vremenski raspon nije dobro zadan')
            return
        elif self.izabraniKanal is None:
            QtGui.QMessageBox.warning(self, 'Problem', 'Program mjerenja nije zadan')
            return
        else:
            self.done(self.Accepted)

    def resolve_tree_click(self, x):
        item = self.drvo.getItem(x)  # dohvati specificni objekt pod tim indeksom
        self.izabraniKanal = item._data[2]  # TODO! losa implementacija

    def get_izbor(self):
        od = self.kalendarOd.selectedDate().toPyDate()  # .strftime('%Y-%m-%d')
        do = self.kalendarDo.selectedDate().toPyDate()  # .strftime('%Y-%m-%d')
        return self.izabraniKanal, od, do
