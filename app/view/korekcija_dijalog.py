# -*- coding: utf-8 -*-
from PyQt4 import QtCore, uic

# REVIEW zasto je ovaj fajl tu. Ova funkcionalnost vise ne postoji dakle treba biti izbrisano
BASE_KOREKCIJA_DIJALOG, FORM_KOREKCIJA_DIJALOG = uic.loadUiType('./app/view/ui_files/korekcija_dijalog.ui')


class KorekcijaDijalog(BASE_KOREKCIJA_DIJALOG, FORM_KOREKCIJA_DIJALOG):
    def __init__(self, argmap, parent=None):
        """
        init sa mapom korekcijskih parametara
        {'time':datetime, 'A':float, 'B':float, 'Sr':float}
        """
        super(BASE_KOREKCIJA_DIJALOG, self).__init__(parent)
        self.setupUi(self)

        self.argmap = argmap
        # convert from python datetime to qtcore datetime object
        pdt = self.argmap['time']
        tajm = QtCore.QDateTime(pdt.year, pdt.month, pdt.day, pdt.hour, pdt.minute)
        # set initial values
        self.dateTimeEdit.setDateTime(tajm)
        self.doubleSpinBoxA.setValue(self.argmap['A'])
        self.doubleSpinBoxB.setValue(self.argmap['B'])
        self.doubleSpinBoxSr.setValue(self.argmap['Sr'])
        # connections
        self.dateTimeEdit.dateTimeChanged.connect(self.modifyTime)
        self.doubleSpinBoxA.valueChanged.connect(self.modifyA)
        self.doubleSpinBoxB.valueChanged.connect(self.modifyB)
        self.doubleSpinBoxSr.valueChanged.connect(self.modifySr)

    def modifyTime(self, x):
        # x je QDateTime
        self.argmap['time'] = x.toPyDateTime()

    def modifyA(self, x):
        # x je float
        self.argmap['A'] = x

    def modifyB(self, x):
        # x je float
        self.argmap['B'] = x

    def modifySr(self, x):
        # x je float
        self.argmap['Sr'] = x

    def get_izbor(self):
        return self.argmap
