#!/usr/bin/python3
# -*- coding: utf-8 -*-

import sys

from PyQt4 import QtGui

from app.view import mainwindow
import  argparse
import app.model.konfig_objekt



def main(argv):
    app = QtGui.QApplication(argv)
    gui = mainwindow.MainWindow()
    gui.setWindowTitle('Validacija podataka')
    gui.showMaximized()
    gui.handle_login()
    sys.exit(app.exec_())


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Validacija podataka')
    parser.add_argument('--development', help="Ucitava razvojnu konfiguraciju", action="store_true")
    args = parser.parse_args()

    app.model.konfig_objekt.config.development=args.development

    main(sys.argv)
    #TODO! agregator treba updejtat da igrnorira flagove
    #TODO! provjeri prebacivanje flagova
    #TODO! ENUM ili neki drugi objekt za prijevod statusa
    #TODO! usporedne kanale... NO2, NOx, NO..
