#!/usr/bin/python3
# -*- coding: utf-8 -*-

import sys
from PyQt4 import QtGui
from app.view import mainwindow
from app.model import dokument
from app.model.konfig_objekt import Konfig


if __name__ == '__main__':
    Konfig.read_config(['konfig_params.cfg', 'graf_params.cfg'])
    app = QtGui.QApplication(sys.argv)
    gui = mainwindow.MainWindow(dokument.Dokument())
    gui.setWindowTitle('Validacija podataka')
    gui.showMaximized()
    gui.handle_login()
    sys.exit(app.exec_())
