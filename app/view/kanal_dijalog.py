# -*- coding: utf-8 -*-
from PyQt4 import QtGui, QtCore, uic

BASE_KANAL_DIJALOG, FORM_KANAL_DIJALOG = uic.loadUiType('./app/view/ui_files/kanal_dijalog.ui')


class KanalDijalog(BASE_KANAL_DIJALOG, FORM_KANAL_DIJALOG):
    """izbor kanala i vremenskog raspona"""

    def __init__(self, dokument, parent=None):
        super(BASE_KANAL_DIJALOG, self).__init__(parent)
        self.setupUi(self)

        self.drvo = dokument.treeModelProgramaMjerenja
        self.izabraniKanal = None

        self.treeView.setModel(self.drvo)
        self.treeView.clicked.connect(self.resolve_tree_click)


        if od:
            datum = QtCore.QDate(od.year, od.month, od.day)
            self.kalendarOd.setSelectedDate(datum)
        if do:
            datum = QtCore.QDate(do.year, do.month, do.day)
            self.kalendarDo.setSelectedDate(datum)

    def accept(self):
        od = self.kalendarOd.selectedDate().toPyDate()
        do = self.kalendarDo.selectedDate().toPyDate()
        timeRaspon = (do - od).days
        if timeRaspon < 1:
            QtGui.QMessageBox.warning(self, 'Problem', 'Vremenski raspon nije dobro zadan')
            return
        elif self.izabraniKanal is None:
            QtGui.QMessageBox.warning(self, 'Problem', 'Program mjerenja nije zadan')
            return
        else:
            self.done(self.Accepted)

    def ucitaj_podatke(self):
        """ucitavanje koncentracija, zero i span podataka"""
        try:
            # spinning cursor...
            QtGui.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
            # dohvati frejmove

            tpl = self.data_reader.get_data(self.kanal, self.vrijemeOd, self.vrijemeDo)
            master_konc_frejm, master_zero_frejm, master_span_frejm = tpl
            # spremi frejmove u dokument #TODO! samo 1 level...
            self.dokument.koncModel.datafrejm = master_konc_frejm
            self.dokument.zeroModel.datafrejm = master_zero_frejm
            self.dokument.spanModel.datafrejm = master_span_frejm
            # set clean modela za korekcije u dokument
            self.dokument.korekcijaModel.datafrejm = pd.DataFrame(columns=['vrijeme', 'A', 'B', 'Sr', 'remove'])
            # TODO! sredi opis i drugi update gui labela
            od = str(master_konc_frejm.index[0])
            do = str(master_konc_frejm.index[-1])
            self.dokument.set_kanal_info_string(self.kanal, od, do)

            self.update_opis_grafa(self.dokument.koncModel.opis)
            self.update_konc_labels(('n/a', 'n/a', 'n/a'))
            self.update_zero_labels(('n/a', 'n/a', 'n/a'))
            self.update_span_labels(('n/a', 'n/a', 'n/a'))
            # predavanje (konc, zero, span) modela kanvasu za crtanje (primarni trigger za clear & redraw)
            self.set_data_models_to_canvas(self.dokument.koncModel,
                                           self.dokument.zeroModel,
                                           self.dokument.spanModel)
        except (AssertionError, RequestException) as e1:
            msg = "Problem kod dohvaćanja minutnih podataka.\n\n{0}".format(str(e1))
            logging.error(str(e1), exc_info=True)
            QtGui.QApplication.restoreOverrideCursor()
            self.update_opis_grafa("n/a")
            QtGui.QMessageBox.warning(QtGui.QWidget(), 'Problem', msg)
        except Exception as e2:
            msg = "General exception. \n\n{0}".format(str(e2))
            logging.error(str(e2), exc_info=True)
            QtGui.QApplication.restoreOverrideCursor()
            self.update_opis_grafa("n/a")
            QtGui.QMessageBox.warning(QtGui.QWidget(), 'Problem', msg)
        finally:
            QtGui.QApplication.restoreOverrideCursor()


    def resolve_tree_click(self, x):
        item = self.drvo.getItem(x)  # dohvati specificni objekt pod tim indeksom
        self.izabraniKanal = item._data[2]  # TODO! losa implementacija

    def get_izbor(self):
        od = self.kalendarOd.selectedDate().toPyDate()  # .strftime('%Y-%m-%d')
        do = self.kalendarDo.selectedDate().toPyDate()  # .strftime('%Y-%m-%d')
        return self.izabraniKanal, od, do
