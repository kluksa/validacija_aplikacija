# -*- coding: utf-8 -*-
import logging
import os

import pandas as pd
from PyQt4 import QtGui, QtCore, uic
from requests.exceptions import RequestException

from app.control.rest_comm import get_comm_object
from app.control.satniagregator import SatniAgregator
from app.model.dokument import Dokument
from app.model.konfig_objekt import config, GrafKonfig
from app.model.qtmodels import KoncTableModel
from app.view.auth_login import DijalogLoginAuth
from app.view.canvas import GrafDisplayWidget
from app.view.input_output import DownloadPodatakaWorker
from app.view.kanal_dijalog import KanalDijalog
import app.view.input_output as input_output
201
MAIN_BASE, MAIN_FORM = uic.loadUiType('./app/view/ui_files/mainwindow.ui')


class MainWindow(MAIN_BASE, MAIN_FORM):
    def __init__(self, parent=None):
        super(MAIN_BASE, self).__init__(parent)
        self.cfgGraf = GrafKonfig('graf_params.cfg')
        self.setupUi(self)
        self.dokument = Dokument()

        self.toggle_logged_in_state(False)
        self.kanvas = GrafDisplayWidget(config.icons.span_select_icon,
                                        config.icons.x_zoom_icon, self.cfgGraf)
        self.grafLayout.addWidget(self.kanvas)

        # dependency injection kroz konstruktor je puno bolji pattern od slanja konfig objekta
        self.restRequest = get_comm_object(config)

        self.progress_bar = DownloadProgressBar(self.restRequest)

        self.program_mjerenja_dlg = KanalDijalog()

        # TODO! triple click fail... treba srediti persistent editor na cijeli stupac
        # self.korekcijaDisplay.setItemDelegateForColumn(4, GumbDelegate(self))
        self.satniAgregator = SatniAgregator()
        self.setup_connections()

    def setup_connections(self):
        self.action_quit.triggered.connect(self.close)
        # gumbi za add/remove/edit parametre korekcije i primjenu korekcije
        self.buttonExport.clicked.connect(self.on_export_korekcije)
        self.buttonSerialize.clicked.connect(self.spremanje_podataka_u_file)
        self.buttonUnserialize.clicked.connect(self.ucitavanje_podataka_iz_filea)
        self.buttonExportAgregirane.clicked.connect(self.export_satno_agregiranih)
        self.buttonUcitaj.clicked.connect(self.ucitaj_podatke)
        self.buttonPrimjeniKorekciju.clicked.connect(self.on_primjeni_korekciju)

        self.progress_bar.download_podataka_worker.gotovo_signal.connect(self.ucitavanje_gotovo)
        self.dokument.novi_podaci.connect(self.update_svega)
        self.korekcijaDisplay.model().dataChanged.connect(self.handle_korekcija_change)


        # navigacija graf-tablica sa podacima
        self.connect(self.kanvas.figure_canvas,
                     QtCore.SIGNAL('table_select_podatak(PyQt_PyObject)'),
                     self.zoom_to_model_timestamp)
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

    def on_primjeni_korekciju(self):
        try:
            QtGui.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
            self.dokument.set_korekcija(self.korekcijaDisplay.model().datafrejm)
            self.dokument.primjeni_korekciju()
            # naredi ponovno crtanje
            xraspon = self.get_current_x_zoom_range()
            self.kanvas.crtaj()
            self.set_current_x_zoom_range(xraspon)
        except Exception as err:
            msg = "General exception. \n\n{0}".format(str(err))
            logging.error(str(err), exc_info=True)
            QtGui.QApplication.restoreOverrideCursor()
            QtGui.QMessageBox.warning(QtGui.QWidget(), 'Problem', msg)
        finally:
            QtGui.QApplication.restoreOverrideCursor()

    def on_export_korekcije(self):
        fajlNejm = QtGui.QFileDialog.getSaveFileName(self,
                                                     "export korekcije")
        if fajlNejm:
            if not fajlNejm.endswith('.csv'):
                fajlNejm += '.csv'

            try:
                QtGui.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
                input_output.export_korekcije(self.dokument, fajlNejm)

            except Exception as err:
                msg = "General exception. \n\n{0}".format(str(err))
                logging.error(str(err), exc_info=True)
                QtGui.QApplication.restoreOverrideCursor()
                QtGui.QMessageBox.warning(QtGui.QWidget(), 'Problem', msg)
            finally:
                QtGui.QApplication.restoreOverrideCursor()


    def export_satno_agregiranih(self):
        fajlNejm = QtGui.QFileDialog.getSaveFileName(self,
                                                     "export satno agregiranih")
        if fajlNejm:
            if not fajlNejm.endswith('.csv'):
                fajlNejm += '.csv'
            try:
                QtGui.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
                frejm = self.dokument.koncModel.datafrejm
                broj_u_satu = self.restRequest.get_broj_u_satu(self.dokument.aktivni_kanal)
                output = self.satniAgregator.agregiraj(frejm, broj_u_satu)
                output.to_csv(fajlNejm)
                QtGui.QApplication.restoreOverrideCursor()
                msg = 'Podaci su uspjesno spremljeni\nagregirani={0}'.format(fajlNejm)
                QtGui.QMessageBox.information(QtGui.QWidget(), 'Info', msg)
            except Exception as err:
                msg = "General exception. \n\n{0}".format(str(err))
                logging.error(str(err), exc_info=True)
                QtGui.QMessageBox.warning(QtGui.QWidget(), 'Problem', msg)
            finally:
                QtGui.QApplication.restoreOverrideCursor()

    def ucitavanje_podataka_iz_filea(self):
        """ucitavanje podataka iz prethodno spremljenog filea"""
        try:
            # get file za load
            fajlNejm = QtGui.QFileDialog.getOpenFileName(self,
                                                         "Ucitaj podatke")
            if fajlNejm:
                # spinning cursor...
                QtGui.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)

                with open(fajlNejm, 'rb') as fn:
                    bstr = fn.read()
                    self.dokument.set_pickleBinary(bstr)
                self.korekcijaDisplay.model().datafrejm = self.dokument._corr_df

                self.update_konc_labels(('n/a', 'n/a', 'n/a'))
                self.update_zero_labels(('n/a', 'n/a', 'n/a'))
                self.update_span_labels(('n/a', 'n/a', 'n/a'))


                QtGui.QApplication.restoreOverrideCursor()
                msg = 'Podaci su uspjesno ucitani\nfile={0}'.format(str(fajlNejm))
                QtGui.QMessageBox.information(QtGui.QWidget(), 'Info', msg)
            else:
                pass  # canceled
        except Exception as err:
            msg = "General exception. \n\n{0}".format(str(err))
            logging.error(str(msg), exc_info=True)
            QtGui.QApplication.restoreOverrideCursor()
            self.update_opis_grafa("n/a")
            QtGui.QMessageBox.warning(QtGui.QWidget(), 'Problem', msg)
        finally:
            QtGui.QApplication.restoreOverrideCursor()



    def spremanje_podataka_u_file(self):
        """spremanje podataka u file"""

        # get file sa save
        self.dokument.set_korekcija(self.korekcijaDisplay.model().datafrejm)
        fajlNejm = QtGui.QFileDialog.getSaveFileName(self,
                                                     "Spremi podatke")
        if fajlNejm:
            if not fajlNejm.endswith('.dat'):
                fajlNejm += '.dat'
            # spinning cursor...
            QtGui.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
            try:
                bstr = self.dokument.get_pickleBinary()
                with open(fajlNejm, 'wb') as fn:
                    fn.write(bstr)

                QtGui.QApplication.restoreOverrideCursor()
                msg = 'Podaci su uspjesno spremljeni\nfile={0}'.format(str(fajlNejm))
                QtGui.QMessageBox.information(QtGui.QWidget(), 'Info', msg)
            except Exception as err:
                msg = "General exception. \n\n{0}".format(str(err))
                logging.error(str(msg), exc_info=True)
                self.update_opis_grafa("n/a")
                QtGui.QMessageBox.warning(QtGui.QWidget(), 'Problem', msg)
            finally:
                QtGui.QApplication.restoreOverrideCursor()


    def get_current_x_zoom_range(self):
        return self.kanvas.get_xzoom_range()

    def set_current_x_zoom_range(self, x):
        self.kanvas.set_xzoom_range(x)

    def handle_korekcija_change(self):
        self.dokument.set_korekcija(self.korekcijaDisplay.model().datafrejm)

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
        ispod_nula = mapa['ispod_nula']  # TODO!
        ispod_l_d_l = mapa['ispod_LDL']
        obuhvat = round((100 * korekcija / ocekivano), 2)
        # update gui elements
        self.ocekivanoLabel.setText(str(ocekivano))
        self.mjerenjaLabel.setText(str(mjerenja))
        self.korekcijaLabel.setText(str(korekcija))
        self.obuhvatLabel.setText(str(obuhvat))
        self.ispodNulaLabel.setText(str(ispod_nula))
        self.ispodLDLLabel.setText(str(ispod_l_d_l))

    def handle_login(self):
        dijalog = DijalogLoginAuth()
        if dijalog.exec_():
            creds = dijalog.get_credentials()
            self.log_in(creds)
        else:
            raise SystemExit('login canceled, QUIT')

    def toggle_logged_in_state(self, x):
        """Aktiviranje akcija ovisno o loginu, x je boolean"""
        self.action_login.setEnabled(not x)
        self.action_logout.setEnabled(x)
        self.action_ucitaj.setEnabled(x)
        self.action_export.setEnabled(x)

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

    def log_in(self, x):
        try:
            self.restRequest.logmein(x)
            self.init_program_mjerenja()
            self.toggle_logged_in_state(True)
        except Exception as err:
            logging.error(str(err), exc_info=True)
            logging.error('logging out')
            # try again loop
            odgovor = QtGui.QMessageBox.question(self,
                                                 'Ponovi login',
                                                 'Neuspješan login, želite li probati ponovo?',
                                                 QtGui.QMessageBox.Ok | QtGui.QMessageBox.No)
            if odgovor == QtGui.QMessageBox.Ok:
                self.handle_login()
            else:
                QtGui.QApplication.quit()

    def init_program_mjerenja(self):
        try:
            QtGui.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
            self.program_mjerenja_dlg.set_program(self.restRequest.get_programe_mjerenja())
        except (AssertionError, RequestException) as e1:
            msg = "Problem kod dohvaćanja podataka o mjerenjima.\n\n{0}".format(str(e1))
            logging.error(str(e1), exc_info=True)
            QtGui.QApplication.restoreOverrideCursor()
            QtGui.QMessageBox.warning(QtGui.QWidget(), 'Problem', msg)
            raise Exception from e1
        except Exception as e2:
            msg = "General exception. \n\n{0}".format(str(e2))
            logging.error(str(e2), exc_info=True)
            QtGui.QApplication.restoreOverrideCursor()
            QtGui.QMessageBox.warning(QtGui.QWidget(), 'login error', msg)
            raise Exception from e2
        finally:
            QtGui.QApplication.restoreOverrideCursor()

    def set_kanal_info_string(self, kanal, od, do):
        out = "{0}: {1} | {2} ({3}) | OD: {4} | DO: {5}".format(
            kanal.id,
            kanal.postaja.naziv_postaje,
            kanal.komponenta.formula,
            kanal.komponenta.mjerne_jedinice.oznaka,
            od,
            do)
        return out

    def ucitaj_podatke(self):
        if self.program_mjerenja_dlg.exec_():
            self.dokument.vrijeme_od = self.program_mjerenja_dlg.vrijemeOd
            self.dokument.vrijeme_do = self.program_mjerenja_dlg.vrijemeDo
            self.dokument.aktivni_kanal = self.program_mjerenja_dlg.izabraniKanal

            self.update_konc_labels(('n/a', 'n/a', 'n/a'))
            self.update_zero_labels(('n/a', 'n/a', 'n/a'))
            self.update_span_labels(('n/a', 'n/a', 'n/a'))
            self.update_opis_grafa(self.set_kanal_info_string(self.dokument.aktivni_kanal,
                                                              self.dokument.vrijeme_od, self.dokument.vrijeme_do))
            QtGui.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
            self.progress_bar.ucitaj(self.dokument.aktivni_kanal, self.dokument.vrijeme_od,
                                              self.dokument.vrijeme_do)

    def ucitavanje_u_tijeku(self):
        QtGui.QMessageBox.warning(self, 'Učitavanje u tijeku',
                                  'Ne mogu učitati nove podatke dok ne zavši već započeto učitavanje')

    def ucitavanje_gotovo(self, result):
        self.progress_bar.close()
        QtGui.QApplication.restoreOverrideCursor()
        self.dokument.prihvat_podataka(result)

    def update_svega(self):
# ovo je lose i prilicno rudimentarno
        self.update_opis_grafa(self.dokument.koncModel.opis)
        self.kanvas.set_models(self.dokument.koncModel,
                                       self.dokument.zeroModel,
                                       self.dokument.spanModel)
        self.dataDisplay.setModel(KoncTableModel(self.dokument._konc_df))


class DownloadProgressBar(QtGui.QProgressBar):
    def __init__(self, restRequest, parent=None):
        super(QtGui.QProgressBar, self).__init__(parent)
        self.setWindowTitle('Load status:')
        self.setGeometry(300, 300, 200, 40)
        self.setRange(0, 100)
        self.thread = QtCore.QThread()
        self.download_podataka_worker = DownloadPodatakaWorker(restRequest)
        self.download_podataka_worker.moveToThread(self.thread)
        self.download_podataka_worker.progress_signal.connect(self.ucitavanje_progress)
        self.download_podataka_worker.greska_signal.connect(self.ucitavanje_greska)
        self.download_podataka_worker.greska_signal.connect(self.thread.quit)
        self.download_podataka_worker.gotovo_signal.connect(self.thread.quit)
        self.thread.started.connect(self.download_podataka_worker.run)

    def ucitaj(self, aktivni_kanal, vrijeme_od, vrijeme_do):
        self.download_podataka_worker.set(aktivni_kanal, vrijeme_od, vrijeme_do)
        self.thread.start()
        self.show()

    def ucitavanje_progress(self, n):
        self.setValue(n)

    def ucitavanje_greska(self, err):
        QtGui.QMessageBox.warning(self, 'Pogreška', 'Učitavanje podataka nije uspjelo ' + str(err))
        self.close()


