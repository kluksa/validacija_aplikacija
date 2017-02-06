# -*- coding: utf-8 -*-
from PyQt4 import QtGui, uic

BASE_KANAL_DIJALOG, FORM_KANAL_DIJALOG = uic.loadUiType('./app/view/ui_files/kanal_dijalog.ui')


class KanalDijalog(BASE_KANAL_DIJALOG, FORM_KANAL_DIJALOG):
    """izbor kanala i vremenskog raspona"""

    def __init__(self, parent=None):
        super(BASE_KANAL_DIJALOG, self).__init__(parent)
        self.setModal(True)
        self.setupUi(self)
        self.izabraniKanal = None
        self.drvo = None


    def set_program(self, drvo):
        self.drvo = drvo
        self.treeView.setModel(drvo)

    def accept(self):
        od = self.kalendarOd.selectedDate().toPyDate()
        do = self.kalendarDo.selectedDate().toPyDate()
        indexes = self.treeView.selectedIndexes()
        if len(indexes) > 0:
            index = indexes[0]
            item = self.drvo.getItem(index)
            self.izabraniKanal = item._data[2]

        timeRaspon = (do - od).days
        if timeRaspon < 1:
            QtGui.QMessageBox.warning(self, 'Problem', 'Vremenski raspon nije dobro zadan')
            return
        elif self.izabraniKanal is None:
            QtGui.QMessageBox.warning(self, 'Problem', 'Program mjerenja nije zadan')
            return
        else:
            self.done(self.Accepted)

    def get_izbor(self):
        od = self.kalendarOd.selectedDate().toPyDate()  # .strftime('%Y-%m-%d')
        do = self.kalendarDo.selectedDate().toPyDate()  # .strftime('%Y-%m-%d')
        return self.izabraniKanal, od, do
