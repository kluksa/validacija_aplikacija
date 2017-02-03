# -*- coding: utf-8 -*-
import datetime
from PyQt4 import QtGui, QtCore, uic
from app.view import auth_login
from app.view.canvas import GrafDisplayWidget
from app.model.qtmodels import GumbDelegate

MAIN_BASE, MAIN_FORM = uic.loadUiType('./app/view/ui_files/mainwindow.ui')
class MainWindow(MAIN_BASE, MAIN_FORM):
    def __init__(self, konfig, graf_opcije, parent=None):
        super(MAIN_BASE, self).__init__(parent)
        self.setupUi(self)
        self.cfg = konfig
        self.cfgGraf = graf_opcije
        self.toggle_logged_in_state(False)
        self.kanvas = GrafDisplayWidget(self.cfg.spanSelectIcon, self.cfg.xZoomIcon, self.cfgGraf)
        self.grafLayout.addWidget(self.kanvas)

        #custom persistent delegates...
        #TODO! triple click fail... treba srediti persistent editor na cijeli stupac
        #self.korekcijaDisplay.setItemDelegateForColumn(4, GumbDelegate(self))

        self.setup_connections()

    def sredi_delegate_za_tablicu(self):
        model = self.korekcijaDisplay.model()
        self.korekcijaDisplay.setItemDelegateForColumn(4, GumbDelegate(self))
        for red in range(0, model.rowCount()):
            self.korekcijaDisplay.closePersistentEditor(model.index(red, 4))
            self.korekcijaDisplay.openPersistentEditor(model.index(red, 4))

    def setup_connections(self):
        self.action_quit.triggered.connect(self.close)
        #gumbi za add/remove/edit parametre korekcije i primjenu korekcije
        self.buttonUcitaj.clicked.connect(self.handle_ucitaj)
        self.buttonExport.clicked.connect(self.handle_export)
        self.buttonPrimjeniKorekciju.clicked.connect(self.handle_primjeni_korekciju)

        self.connect(self.kanvas,
                     QtCore.SIGNAL('graf_is_modified(PyQt_PyObject)'),
                     self.update_labele_obuhvata)

        #TODO! lose ali brzi fix
        self.connect(self.kanvas.figure_canvas,
                     QtCore.SIGNAL('update_konc_label(PyQt_PyObject)'),
                     self.update_konc_labels)

        self.connect(self.kanvas.figure_canvas,
                     QtCore.SIGNAL('update_zero_label(PyQt_PyObject)'),
                     self.update_zero_labels)

        self.connect(self.kanvas.figure_canvas,
                     QtCore.SIGNAL('update_span_label(PyQt_PyObject)'),
                     self.update_span_labels)

    def update_opis_grafa(self, opis):
        self.labelOpisGrafa.setText(opis)

    def update_konc_labels(self, tpl):
        vrijeme, val = tpl
        self.koncValLabel.setText(str(vrijeme))
        self.koncTimeLabel.setText(str(val))

    def update_zero_labels(self, tpl):
        vrijeme, val = tpl
        self.zeroValLabel.setText(str(vrijeme))
        self.zeroTimeLabel.setText(str(val))

    def update_span_labels(self, tpl):
        vrijeme, val = tpl
        self.spanValLabel.setText(str(vrijeme))
        self.spanTimeLabel.setText(str(val))

    def update_labele_obuhvata(self, mapa):
        ocekivano = mapa['ocekivano']
        mjerenja = mapa['broj_mjerenja']
        korekcija = mapa['broj_korektiranih']
        ispodNula =  mapa['ispod_nula'] #TODO!
        ispodLDL = mapa['ispod_LDL']
        obuhvat = round((100 * korekcija / ocekivano), 2)
        #update gui elements
        self.ocekivanoLabel.setText(str(ocekivano))
        self.mjerenjaLabel.setText(str(mjerenja))
        self.korekcijaLabel.setText(str(korekcija))
        self.obuhvatLabel.setText(str(obuhvat))
        self.ispodNulaLabel.setText(str(ispodNula))
        self.ispodLDLLabel.setText(str(ispodLDL))

    def handle_login(self):
        dijalog = auth_login.DijalogLoginAuth()
        if dijalog.exec_():
            creds = dijalog.get_credentials()
            self.emit(QtCore.SIGNAL('initiate_login(PyQt_PyObject)'), creds)
        else:
            raise SystemExit('login canceled, QUIT')

    def toggle_logged_in_state(self, x):
        """Aktiviranje akcija ovisno o loginu, x je boolean"""
        self.action_login.setEnabled(not x)
        self.action_logout.setEnabled(x)
        self.action_ucitaj.setEnabled(x)
        self.action_export.setEnabled(x)

    def handle_logout(self):
        self.emit(QtCore.SIGNAL('initiate_logout'))

    def handle_ucitaj(self):
        self.emit(QtCore.SIGNAL('ucitaj_minutne'))

    def handle_export(self):
        self.emit(QtCore.SIGNAL('export_korekcije'))

    def handle_primjeni_korekciju(self):
        self.emit(QtCore.SIGNAL('primjeni_korekciju'))

    def draw_graf(self):
        self.kanvas.crtaj()

    def set_data_models_to_canvas(self, konc, zero, span):
        """
        setter modela za koncentraciju, zero i span u kanvas modela
        """
        self.kanvas.set_models(konc, zero, span)

    def zoom_to_model_timestamp(self, red):
        try:
            self.dataDisplay.selectRow(red)
        except (TypeError, LookupError):
            #silent pass, error happens when None or out of bounds point is selected
            pass

#    def zoom_to_relevant_korekcija(self, x):
#        """x je pandas timestamp"""
#        model = self.korekcijaDisplay.model()
#        indeks = model.get_relevantni_red(x)
#        if indeks != None:
#            self.korekcijaDisplay.selectRow(indeks)
#
#    def dodaj_parametar_korekcije(self):
#        #defaulti
#        mapa = {'time':datetime.datetime.now(), 'A':1.0, 'B':0.0, 'Sr':3.33}
#        dijalog = korekcija_dijalog.KorekcijaDijalog(mapa)
#        if dijalog.exec_():
#            parametri = dijalog.get_izbor()
#            model = self.korekcijaDisplay.model()
#            model.add_row(parametri)
#
#    def makni_selektirani_parametar_korekcije(self):
#        red = self.korekcijaDisplay.selectionModel().selectedRows()
#
#        if len(red):
#            x = red[0].row()
#            model = self.korekcijaDisplay.model()
#            model.remove_row(x)
#
#    def edit_selektirani_parametar_korekcije(self):
#        red = self.korekcijaDisplay.selectionModel().selectedRows()
#        if len(red):
#            x = red[0].row()
#            model = self.korekcijaDisplay.model()
#            mapa = model.get_row_dict(x)
#            dijalog = korekcija_dijalog.KorekcijaDijalog(mapa)
#            if dijalog.exec_():
#                parametri = dijalog.get_izbor()
#                parametri['red'] = x
#                model.edit_row(parametri)

    def closeEvent(self, event):
        """
        Overloadani signal za gasenje aplikacije. Dodatna potvrda za izlaz.
        """
        reply = QtGui.QMessageBox.question(
            self,
            'Potvrdi izlaz:',
            'Da li ste sigurni da hocete ugasiti aplikaciju?',
            QtGui.QMessageBox.Yes,
            QtGui.QMessageBox.No)
        if reply == QtGui.QMessageBox.Yes:
            #overwite graf konfig file...
            self.cfgGraf.save_to_file()
            event.accept()
            self.emit(QtCore.SIGNAL('gui_terminated'))
        else:
            event.ignore()
