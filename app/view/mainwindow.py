# -*- coding: utf-8 -*-
import datetime
from PyQt4 import QtGui, QtCore, uic
from app.view import auth_login
from app.view.canvas import GrafDisplayWidget
from app.view import korekcija_dijalog
from app.view.abcalc import ABKalkulator
from app.model.qtmodels import GumbDelegate, CalcGumbDelegate

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
        self.setup_connections()


    def sredi_delegate_za_tablicu(self):
        model = self.korekcijaDisplay.model()
        self.korekcijaDisplay.setItemDelegateForColumn(4, GumbDelegate(self))
        self.korekcijaDisplay.setItemDelegateForColumn(5, CalcGumbDelegate(self))
        for red in range(0, model.rowCount()):
            self.korekcijaDisplay.closePersistentEditor(model.index(red, 4))
            self.korekcijaDisplay.closePersistentEditor(model.index(red, 5))
            self.korekcijaDisplay.openPersistentEditor(model.index(red, 4))
            self.korekcijaDisplay.openPersistentEditor(model.index(red, 5))

    def get_current_x_zoom_range(self):
        return self.kanvas.get_xzoom_range()

    def set_current_x_zoom_range(self, x):
        self.kanvas.set_xzoom_range(x)

    def get_AB_values(self):
        self.dijalogAB = ABKalkulator()
        response = self.dijalogAB.exec_()
        if response:
            return self.dijalogAB.AB
        else:
            return None

    def setup_connections(self):
        self.action_quit.triggered.connect(self.close)
        # gumbi za add/remove/edit parametre korekcije i primjenu korekcije
        self.buttonUcitaj.clicked.connect(self.handle_ucitaj)
        self.buttonExport.clicked.connect(self.handle_export)
        self.buttonPrimjeniKorekciju.clicked.connect(self.handle_primjeni_korekciju)
        self.buttonSerialize.clicked.connect(self.handle_spremi_dokument)
        self.buttonUnserialize.clicked.connect(self.handle_load_dokument)
        self.buttonExportAgregirane.clicked.connect(self.handle_export_agregiranih)

        self.connect(self.kanvas,
                     QtCore.SIGNAL('graf_is_modified(PyQt_PyObject)'),
                     self.update_labele_obuhvata)
        # TODO! lose ali brzi fix
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
        vrijeme, val, kor = tpl
        self.koncValLabel.setText(str(val))
        self.koncTimeLabel.setText(str(vrijeme))
        self.koncKorLabel.setText(str(kor))

    def update_zero_labels(self, tpl):
        vrijeme, val, kor = tpl
        self.zeroValLabel.setText(str(val))
        self.zeroTimeLabel.setText(str(vrijeme))
        self.zeroKorLabel.setText(str(kor))

    def update_span_labels(self, tpl):
        vrijeme, val, kor = tpl
        self.spanValLabel.setText(str(val))
        self.spanTimeLabel.setText(str(vrijeme))
        self.spanKorLabel.setText(str(kor))

    def update_labele_obuhvata(self, mapa):
        ocekivano = mapa['ocekivano']
        mjerenja = mapa['broj_mjerenja']
        korekcija = mapa['broj_korektiranih']
        ispodNula = mapa['ispod_nula']
        ispodLDL = mapa['ispod_LDL']
        obuhvat = round((100 * korekcija / ocekivano), 2)
        # update gui elements
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

    def handle_export_agregiranih(self):
        self.emit(QtCore.SIGNAL('export_satno_agregiranih'))

    def handle_primjeni_korekciju(self):
        self.emit(QtCore.SIGNAL('primjeni_korekciju'))

    def handle_spremi_dokument(self):
        self.emit(QtCore.SIGNAL('serijaliziraj_dokument'))

    def handle_load_dokument(self):
        self.emit(QtCore.SIGNAL('unserijaliziraj_dokument'))

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
            # silent pass, error happens when None or out of bounds point is selected
            pass

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
            # overwite graf konfig file...
            self.cfgGraf.save_to_file()
            event.accept()
            self.emit(QtCore.SIGNAL('gui_terminated'))
        else:
            event.ignore()
