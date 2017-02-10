#!/usr/bin/python3
# -*- coding: utf-8 -*-

import sys
from PyQt4 import QtGui
from app.view import mainwindow
from app.model import dokument
from app.model.konfig_objekt import Konfig


if __name__ == '__main__':
    app = QtGui.QApplication(sys.argv)
    gui = mainwindow.MainWindow()
    gui.setWindowTitle('Validacija podataka')
    gui.showMaximized()
    gui.handle_login()
    sys.exit(app.exec_())
