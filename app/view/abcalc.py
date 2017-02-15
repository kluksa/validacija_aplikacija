# -*- coding: utf-8 -*-
import sys
from PyQt4 import QtGui


class DoubleValidatedLineEdit(QtGui.QLineEdit):
    def __init__(self, val, parent=None):
        super(DoubleValidatedLineEdit, self).__init__(parent=parent)
        self.setValidator(QtGui.QDoubleValidator())  # set validation for double characters
        self.setText(str(val))


class ABKalkulator(QtGui.QDialog):
    def __init__(self, parent=None):
        QtGui.QDialog.__init__(self, parent=parent)
        self.setModal(False)
        self.setWindowTitle('Računanje A, B')
        # OUTPUT VARS
        self._AB = (1.0, 0.0)

        self.span0 = DoubleValidatedLineEdit(1.0, parent=self)
        self.span1 = DoubleValidatedLineEdit(1.0, parent=self)
        self.zero0 = DoubleValidatedLineEdit(0.0, parent=self)
        self.zero1 = DoubleValidatedLineEdit(0.0, parent=self)
        self.Aparam = DoubleValidatedLineEdit(1.0, parent=self)
        self.Bparam = DoubleValidatedLineEdit(0.0, parent=self)
        # result
        self.outputA = QtGui.QLabel('1.0')
        self.outputB = QtGui.QLabel('0.0')
        # gumbi
        self.gumbOK = QtGui.QPushButton('Ok')
        self.gumbCancel = QtGui.QPushButton('Cancel')

        gridlay = QtGui.QGridLayout()
        gridlay.addWidget(QtGui.QLabel('span 0 :'), 0, 0, 1, 1)
        gridlay.addWidget(self.span0, 0, 1, 1, 1)
        gridlay.addWidget(QtGui.QLabel('zero 0 :'), 0, 2, 1, 1)
        gridlay.addWidget(self.zero0, 0, 3, 1, 1)
        gridlay.addWidget(QtGui.QLabel('span 1 :'), 1, 0, 1, 1)
        gridlay.addWidget(self.span1, 1, 1, 1, 1)
        gridlay.addWidget(QtGui.QLabel('zero 1 :'), 1, 2, 1, 1)
        gridlay.addWidget(self.zero1, 1, 3, 1, 1)
        gridlay.addWidget(QtGui.QLabel('A :'), 2, 0, 1, 1)
        gridlay.addWidget(self.Aparam, 2, 1, 1, 1)
        gridlay.addWidget(QtGui.QLabel('B :'), 2, 2, 1, 1)
        gridlay.addWidget(self.Bparam, 2, 3, 1, 1)
        gridlay.addWidget(QtGui.QLabel('Out A'), 3, 0, 1, 1)
        gridlay.addWidget(self.outputA, 3, 1, 1, 1)
        gridlay.addWidget(QtGui.QLabel('Out B'), 3, 2, 1, 1)
        gridlay.addWidget(self.outputB, 3, 3, 1, 1)
        gridlay.addWidget(self.gumbOK, 5, 2, 1, 1)
        gridlay.addWidget(self.gumbCancel, 5, 3, 1, 1)
        self.setLayout(gridlay)

        self.gumbOK.clicked.connect(self.accept)
        self.gumbCancel.clicked.connect(self.reject)
        self.span0.textChanged.connect(self.racunaj_AB)
        self.span1.textChanged.connect(self.racunaj_AB)
        self.zero0.textChanged.connect(self.racunaj_AB)
        self.zero1.textChanged.connect(self.racunaj_AB)
        self.Aparam.textChanged.connect(self.racunaj_AB)
        self.Bparam.textChanged.connect(self.racunaj_AB)

    @property
    def AB(self):
        return self._AB

    @AB.setter
    def AB(self, x):
        self._AB = x

    def showEvent(self, event):
        self.reset_params()
        super(ABKalkulator, self).showEvent(event)

    def reset_params(self):
        self.span0.setText('1.0')
        self.span1.setText('1.0')
        self.zero0.setText('0.0')
        self.zero1.setText('0.0')
        self.Aparam.setText('1.0')
        self.Bparam.setText('0.0')
        self.outputA.setText('1.0')
        self.outputB.setText('0.0')

    def racunaj_AB(self):
        try:
            s0, s1 = float(self.span0.text()), float(self.span1.text())
            z0, z1 = float(self.zero0.text()), float(self.zero1.text())
            ab = (float(self.Aparam.text()), float(self.Bparam.text()))
            outA, outB = self.calcab(s0, s1, z0, z1, ab)
            self.AB = (outA, outB)
            self.outputA.setText(str(outA))
            self.outputB.setText(str(outB))
        except ValueError:
            self.AB = (None, None)
            self.outputA.setText('None')
            self.outputB.setText('None')

    def calcab(self, s0, s1, z0, z1, ab):
        a = (s0 - z0) / (s1 - z1)
        b = z0 - a * z1
        aa = a * ab[0]
        bb = ab[0] * b + ab[1]
        return aa, bb


if __name__ == '__main__':
    class TestProzor(QtGui.QWidget):
        def __init__(self, parent=None):
            QtGui.QWidget.__init__(self, parent=parent)

            self.theGumb = QtGui.QPushButton('click me...')
            self.theGumb.setCheckable(True)
            self.theGumb.toggled.connect(self.prikazi_dijalog)

            self.kalkulator = ABKalkulator(parent=self)

            lay = QtGui.QVBoxLayout()
            lay.addWidget(self.theGumb)
            self.setLayout(lay)

        def prikazi_dijalog(self, x):
            # self.kalkulator.show()
            # print('AB: ', self.kalkulator.AB)
            ok = self.kalkulator.exec_()
            if ok:
                print('AB: ', self.kalkulator.AB)
            else:
                print('canceled')


    app = QtGui.QApplication(sys.argv)
    aaa = TestProzor()
    aaa.show()
    sys.exit(app.exec_())
