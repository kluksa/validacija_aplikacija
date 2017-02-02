# -*- coding: utf-8 -*-
from PyQt4 import uic

BASE_KANAL_DIJALOG, FORM_KANAL_DIJALOG = uic.loadUiType('./app/view/ui_files/kanal_dijalog.ui')
class KanalDijalog(BASE_KANAL_DIJALOG, FORM_KANAL_DIJALOG):
    """izbor kanala i vremenskog raspona"""
    def __init__(self, drvo, parent=None):
        super(BASE_KANAL_DIJALOG, self).__init__(parent)
        self.setupUi(self)

        self.drvo = drvo
        self.izabraniKanal = None

        self.treeView.setModel(self.drvo)
        self.treeView.clicked.connect(self.resolve_tree_click)

    def resolve_tree_click(self, x):
        item = self.drvo.getItem(x)  #dohvati specificni objekt pod tim indeksom
        self.izabraniKanal = item._data[2]  #TODO! losa implementacija

    def get_izbor(self):
        od = self.kalendarOd.selectedDate().toPyDate()#.strftime('%Y-%m-%d')
        do = self.kalendarDo.selectedDate().toPyDate()#.strftime('%Y-%m-%d')
        return self.izabraniKanal, od, do
