#!/usr/bin/python3
# -*- coding: utf-8 -*-

import sys

from PyQt4 import QtGui

from app.view import mainwindow


def main(argv):
    app = QtGui.QApplication(sys.argv)
    gui = mainwindow.MainWindow()
    gui.setWindowTitle('Validacija podataka')
    gui.showMaximized()
    gui.handle_login()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main(sys.argv)
