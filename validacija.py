#!/usr/bin/python3
# -*- coding: utf-8 -*-

import logging
import sys

from PyQt4 import QtGui

from app.model import dokument
from app.model import konfig_objekt
from app.view import mainwindow


class Validacija():
    def __init__(self):
        self.konfig = konfig_objekt.MainKonfig('konfig_params.cfg')
        self.graf_konfig = konfig_objekt.GrafKonfig('graf_params.cfg')
        self.setup_logging()

    def setup_logging(self):
        """Inicijalizacija loggera"""
        try:
            logging.basicConfig(level=self.konfig.logLvl,
                                filename=self.konfig.logFile,
                                filemode=self.konfig.logMode,
                                format='{levelname}:::{asctime}:::{module}:::{funcName}:::LOC:{lineno}:::{message}',
                                style='{')
        except Exception as err:
            print('Pogreska prilikom konfiguracije loggera.')
            print(str(err))
            raise SystemExit('Kriticna greska, izlaz iz aplikacije.')


    def run(self, argv):

        app = QtGui.QApplication(argv)
        gui = mainwindow.MainWindow(self.konfig, self.graf_konfig, dokument.Dokument())
        gui.show()
        gui.handle_login()
        sys.exit(app.exec_())


if __name__ == '__main__':
    Validacija().run(sys.argv)
