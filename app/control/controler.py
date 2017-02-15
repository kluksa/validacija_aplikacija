# -*- coding: utf-8 -*-
from PyQt4 import QtGui, QtCore


class Kontroler(QtGui.QWidget):
    def __init__(self, parent=None):
        super(Kontroler, self).__init__(parent=None)


        self.setup_connections()

    def setup_connections(self):
        pass

    def kickstart_gui(self):
        # set modele u odgovarajuce tablice
        self.gui.dataDisplay.setModel(self.dokument.koncModel)
        self.gui.korekcijaDisplay.setModel(self.dokument.korekcijaModel)

        self.gui.sredi_delegate_za_tablicu()
        self.connect(self.dokument.korekcijaModel,
                     QtCore.SIGNAL('update_persistent_delegate'),
                     self.gui.sredi_delegate_za_tablicu)
        #login
        self.gui.handle_login()


