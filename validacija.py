#!/usr/bin/python3
# -*- coding: utf-8 -*-

import sys
from PyQt4 import QtGui
from app.control import controler


def main(argv):
    app = QtGui.QApplication(argv)
    runner = controler.Kontroler()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main(sys.argv)
    #TODO! flag LDL nikako se ne smije flagirati sa >0
    #TODO! agregator treba updejtat da igrnorira flagove
    #TODO! provjeri prebacivanje flagova
    #TODO! ENUM ili neki drugi objekt za prijevod statusa