# -*- coding: utf-8 -*-
import logging
import os
from datetime import timedelta

import numpy as np
import pandas as pd
from PyQt4 import QtGui, QtCore, uic
from requests.exceptions import RequestException

import app.model.dokument
from app.control.rest_comm import RESTZahtjev, MockZahtjev
from app.control.satniagregator import SatniAgregator
from app.model.konfig_objekt import config, GrafKonfig
from app.model.qtmodels import GumbDelegate, CalcGumbDelegate
from app.view import auth_login
from app.view import kanal_dijalog
from app.view.abcalc import ABKalkulator
from app.view.canvas import GrafDisplayWidget

MAIN_BASE, MAIN_FORM = uic.loadUiType('./app/view/ui_files/mainwindow.ui')


class MainWindow(MAIN_BASE, MAIN_FORM):
    def __init__(self, parent=None):
        super(MAIN_BASE, self).__init__(parent)
        self.cfgGraf = GrafKonfig('graf_params.cfg')
        #        util.setup_logging(config.log.file, config.log.level, config.log.mode)
        self.setupUi(self)
        self.dokument = app.model.dokument.Dokument()

        self.toggle_logged_in_state(False)
        self.kanvas = GrafDisplayWidget(config.icons.span_select_icon,
                                        config.icons.x_zoom_icon, self.cfgGraf)
        self.grafLayout.addWidget(self.kanvas)

        # dependency injection kroz konstruktor je puno bolji pattern od slanja konfig objekta

        if True:
            self.restRequest = MockZahtjev()
        else:
            self.restRequest = RESTZahtjev(config.rest.program_mjerenja_url,
                                           config.rest.sirovi_podaci_url,
                                           config.rest.status_map_url,
                                           config.rest.zero_span_podaci_url)

            # self.restRequest = RESTZahtjev(self.cfg.cfg['REST') #.restProgramMjerenja, self.cfg.restSiroviPodaci,
            # self.cfg.restStatusMap, self.cfg.restZeroSpanPodaci)

        self.progress_bar = QtGui.QProgressBar()
        self.progress_bar.setWindowTitle('Load status:')
        self.progress_bar.setGeometry(300, 300, 200, 40)
        self.progress_bar.setRange(0, 100)

        self.dataDisplay.setModel(self.dokument.koncModel)
        self.korekcijaDisplay.setModel(self.dokument.korekcijaModel)

        self.sredi_delegate_za_tablicu()

        self.program_mjerenja_dlg = kanal_dijalog.KanalDijalog()
        self.download_podataka_worker = DownloadPodatakaWorker(self.restRequest)

        # custom persistent delegates...
        # TODO! triple click fail... treba srediti persistent editor na cijeli stupac
        # self.korekcijaDisplay.setItemDelegateForColumn(4, GumbDelegate(self))
        self.satniAgregator = SatniAgregator()
        self.setup_connections()

    def primjeni_korekciju(self):
        try:
            QtGui.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
            self.dokument.primjeni_korekciju()
            # naredi ponovno crtanje
            xraspon = self.get_current_x_zoom_range()
            self.draw_graf()
            self.set_current_x_zoom_range(xraspon)
        except Exception as err:
            msg = "General exception. \n\n{0}".format(str(err))
            logging.error(str(err), exc_info=True)
            QtGui.QApplication.restoreOverrideCursor()
            QtGui.QMessageBox.warning(QtGui.QWidget(), 'Problem', msg)
        finally:
            QtGui.QApplication.restoreOverrideCursor()

    def export_korekcije(self):
        print('NOT IMPLEMENTED SA RESTOM')
        try:
            QtGui.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)

            frejmPodaci = self.dokument.koncModel.datafrejm
            frejmZero = self.dokument.zeroModel.datafrejm
            frejmSpan = self.dokument.spanModel.datafrejm
            frejmKor = self.dokument.korekcijaModel.datafrejm
            # izbaci zadnji red (za dodavanje stvari...)
            frejmKor = frejmKor.iloc[:-1, :]
            # drop nepotrebne stupce (remove/calc placeholderi)
            frejmKor.drop(['remove', 'calc'], axis=1, inplace=True)

            fajlNejm = QtGui.QFileDialog.getSaveFileName(self,
                                                         "export korekcije")
            if fajlNejm:
                if not fajlNejm.endswith('.csv'):
                    fajlNejm = fajlNejm + '.csv'
                # os... sastavi imena fileova
                folder, name = os.path.split(fajlNejm)
                podName = "podaci_" + name
                zeroName = "zero_" + name
                spanName = "span_" + name
                korName = "korekcijski_parametri_" + name
                podName = os.path.normpath(os.path.join(folder, podName))
                zeroName = os.path.normpath(os.path.join(folder, zeroName))
                spanName = os.path.normpath(os.path.join(folder, spanName))
                korName = os.path.normpath(os.path.join(folder, korName))
                frejmPodaci.to_csv(podName, sep=';')
                frejmZero.to_csv(zeroName, sep=';')
                frejmSpan.to_csv(spanName, sep=';')
                frejmKor.to_csv(korName, sep=';')
                QtGui.QApplication.restoreOverrideCursor()
                msg = 'Podaci su uspjesno spremljeni\ndata={0}\nzero={1}\nspan={2}\nParametri={3}'.format(podName,
                                                                                                          zeroName,
                                                                                                          spanName,
                                                                                                          korName)
                QtGui.QMessageBox.information(QtGui.QWidget(), 'Info', msg)
            else:
                pass  # canceled
        except Exception as err:
            msg = "General exception. \n\n{0}".format(str(err))
            logging.error(str(err), exc_info=True)
            QtGui.QApplication.restoreOverrideCursor()
            QtGui.QMessageBox.warning(QtGui.QWidget(), 'Problem', msg)
        finally:
            QtGui.QApplication.restoreOverrideCursor()

    def export_satno_agregiranih(self):
        try:
            fajlNejm = QtGui.QFileDialog.getSaveFileName(self,
                                                         "export satno agregiranih")
            if fajlNejm:
                if not fajlNejm.endswith('.csv'):
                    fajlNejm = fajlNejm + '.csv'
                frejm = self.dokument.koncModel.datafrejm
                broj_u_satu = self.restRequest.get_broj_u_satu(self.dokument.aktivniKanal)
                output = self.satniAgregator.agregiraj(frejm, broj_u_satu)
                QtGui.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
                output.to_csv(fajlNejm)
                QtGui.QApplication.restoreOverrideCursor()
                msg = 'Podaci su uspjesno spremljeni\nagregirani={0}'.format(fajlNejm)
                QtGui.QMessageBox.information(QtGui.QWidget(), 'Info', msg)
            else:
                pass  # canceled
        except Exception as err:
            logging.error(str(err), exc_info=True)
            QtGui.QApplication.restoreOverrideCursor()
        finally:
            QtGui.QApplication.restoreOverrideCursor()

    def spremanje_podataka_u_file(self):
        """spremanje podataka u file"""
        try:
            # get file sa save
            fajlNejm = QtGui.QFileDialog.getSaveFileName(self,
                                                         "Spremi podatke")
            if fajlNejm:
                if not fajlNejm.endswith('.dat'):
                    fajlNejm = fajlNejm + '.dat'
                # spinning cursor...
                QtGui.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)

                bstr = self.dokument.get_pickleBinary()
                with open(fajlNejm, 'wb') as fn:
                    fn.write(bstr)

                QtGui.QApplication.restoreOverrideCursor()
                msg = 'Podaci su uspjesno spremljeni\nfile={0}'.format(str(fajlNejm))
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

                self.update_opis_grafa(self.dokument.koncModel.opis)
                self.update_konc_labels(('n/a', 'n/a', 'n/a'))
                self.update_zero_labels(('n/a', 'n/a', 'n/a'))
                self.update_span_labels(('n/a', 'n/a', 'n/a'))

                # predavanje (konc, zero, span) modela kanvasu za crtanje (primarni trigger za clear & redraw)
                self.set_data_models_to_canvas(self.dokument.koncModel,
                                               self.dokument.zeroModel,
                                               self.dokument.spanModel)
                self.sredi_delegate_za_tablicu()

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
        self.buttonSerialize.clicked.connect(self.handle_spremi_dokument)
        self.buttonUnserialize.clicked.connect(self.handle_load_dokument)
        self.buttonExportAgregirane.clicked.connect(self.handle_export_agregiranih)
        # gumbi za add/remove/edit parametre korekcije i primjenu korekcije

        self.buttonUcitaj.clicked.connect(self.ucitaj_podatke2)
        self.buttonExport.clicked.connect(self.export_korekcije)
        self.buttonPrimjeniKorekciju.clicked.connect(self.primjeni_korekciju)
        # quit
        self.connect(self,
                     QtCore.SIGNAL('terminate_app'),
                     self.close)
        self.connect(self,
                     QtCore.SIGNAL('initiate_login(PyQt_PyObject)'),
                     self.log_in)

        # # load in novih podataka sa REST-a
        # self.connect(self.gui,
        #              QtCore.SIGNAL('ucitaj_minutne'),
        #              self.ucitavanje_podataka_sa_resta)

        # navigacija graf-tablica sa podacima
        self.connect(self.kanvas,
                     QtCore.SIGNAL('table_select_podatak(PyQt_PyObject)'),
                     self.zoom_to_model_timestamp)

        # # primjena korekcije
        # self.connect(self.gui,
        #              QtCore.SIGNAL('primjeni_korekciju'),
        #              self.primjeni_korekciju)
        # export korekcije
        self.connect(self,
                     QtCore.SIGNAL('export_korekcije'),
                     self.export_korekcije)
        # serijalizacija dokumenta
        self.connect(self,
                     QtCore.SIGNAL('serijaliziraj_dokument'),
                     self.spremanje_podataka_u_file)
        # unserijalizacija dokumenta
        self.connect(self,
                     QtCore.SIGNAL('unserijaliziraj_dokument'),
                     self.ucitavanje_podataka_iz_filea)
        # export satno agregiranih
        self.connect(self,
                     QtCore.SIGNAL('export_satno_agregiranih'),
                     self.export_satno_agregiranih)





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


        self.connect(self.dokument.korekcijaModel,
                     QtCore.SIGNAL('update_persistent_delegate'),
                     self.sredi_delegate_za_tablicu)

        self.connect(self.download_podataka_worker,
                     QtCore.SIGNAL('ucitavanjeProgress(PyQt_PyObject)'), self.ucitavanje_progress)
        self.connect(self.download_podataka_worker,
                     QtCore.SIGNAL('ucitavanjeGotovo'), self.ucitavanje_gotovo)

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
        dijalog = auth_login.DijalogLoginAuth()
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

                # REVIEW ovo je besmisleno. Zbog 3 linije koda imaš dupli exception handling

    def init_program_mjerenja(self):
        try:
            QtGui.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
            ####
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

    def ucitaj_podatke2(self):
        if self.program_mjerenja_dlg.exec_():
            self.dokument.vrijeme_od = self.program_mjerenja_dlg.vrijemeOd
            self.dokument.vrijeme_do = self.program_mjerenja_dlg.vrijemeDo
            self.dokument.aktivni_kanal = self.program_mjerenja_dlg.izabraniKanal
        else:
            return

        self.update_konc_labels(('n/a', 'n/a', 'n/a'))
        self.update_zero_labels(('n/a', 'n/a', 'n/a'))
        self.update_span_labels(('n/a', 'n/a', 'n/a'))
        self.update_opis_grafa(self.set_kanal_info_string(self.dokument.aktivni_kanal,
                                                          self.dokument.vrijeme_od, self.dokument.vrijeme_do))

        QtGui.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
        self.download_podataka_worker.set(self.dokument.aktivni_kanal, self.dokument.vrijeme_od,
                                          self.dokument.vrijeme_do)
        self.progress_bar.show()
        self.download_podataka_worker.start()

    def ucitavanje_progress(self, n):
        self.progress_bar.setValue(n)

    def ucitavanje_gotovo(self):
        self.progress_bar.close()
        QtGui.QApplication.restoreOverrideCursor()
        self.dokument.koncModel.datafrejm = self.download_podataka_worker.mjerenja_df
        self.dokument.zeroModel.datafrejm = self.download_podataka_worker.zero_df
        self.dokument.spanModel.datafrejm = self.download_podataka_worker.span_df
        # set clean modela za korekcije u dokument
        self.dokument.korekcijaModel.datafrejm = pd.DataFrame(columns=['vrijeme', 'A', 'B', 'Sr', 'remove', 'calc'])
        self.set_data_models_to_canvas(self.dokument.koncModel,
                                       self.dokument.zeroModel,
                                       self.dokument.spanModel)


class DownloadPodatakaWorker(QtCore.QThread):
    ucitavanje_gotovo_signal = QtCore.SIGNAL("ucitavanjeGotovo")
    ucitavanje_progress_signal = QtCore.SIGNAL("ucitavanjeProgress(PyQt_PyObject)")
    ucitavanje_u_tijeku_signal = QtCore.SIGNAL("ucitavanjeUTijeku")
    ucitavanje_neuspjelo_signal = QtCore.SIGNAL("ucitavanjeNeuspjelo")

    def __init__(self, rest, parent=None):
        super(self.__class__, self).__init__()
        self.restRequest = rest
        self.zero_df = None
        self.span_df = None
        self.mjerenja_df = None
        self.aktivan = False

    def set(self, kanal, od, do):
        self.kanal = kanal
        self.od = od
        self.do = do
        self.ndays = int((do - od).days)

    def run(self):
        if self.aktivan:
            self.emit(DownloadPodatakaWorker.ucitavanje_u_tijeku_signal)
            return
        try:
            self.aktivan = True
            self.status_bits = self.restRequest.get_status_map()
            broj_u_satu = self.restRequest.get_broj_u_satu(self.kanal)
            self.zero_df = pd.DataFrame()
            self.span_df = pd.DataFrame()
            self.mjerenja_df = pd.DataFrame()
            for d in range(0, self.ndays):
                dan = (self.od + timedelta(d)).strftime('%Y-%m-%d')
                mjerenja = self.restRequest.get_sirovi(self.kanal, dan)
                [zero, span] = self.restRequest.get_zero_span(self.kanal, dan, 1)
                self.zero_df = self.zero_df.append(zero)
                self.span_df = self.zero_df.append(span)
                self.mjerenja_df = self.mjerenja_df.append(mjerenja)
                self.emit(DownloadPodatakaWorker.ucitavanje_progress_signal, int(100 * d / self.ndays))

            if 3600 % broj_u_satu != 0:
                logging.error("Frekvencija mjerenja nije cijeli broj sekundi", exc_info=True)
                raise NotIntegerFreq()
            frek = str(int(3600 / broj_u_satu)) + "S"

            fullraspon = pd.date_range(start=self.od, end=self.do, freq=frek)

            self.mjerenja_df = self.mjerenja_df.reindex(fullraspon)
            self.mjerenja_df = self.sredi_missing_podatke(self.mjerenja_df)

            self.emit(DownloadPodatakaWorker.ucitavanje_gotovo_signal)
        except Exception as err:
            logging.error(str(err), exc_info=True)
            self.emit(DownloadPodatakaWorker.ucitavanje_neuspjelo_signal)
        finally:
            self.aktivan = False

    def sredi_missing_podatke(self, frejm):
        # indeks svi konc nan
        i0 = np.isnan(frejm['koncentracija'])
        i1 = np.isnan(frejm['status'])
        # indeks konc i status su nan
        i1 = (np.isnan(frejm['koncentracija'])) & (np.isnan(frejm['status']))
        # indeks konc je nan, status nije
        i2 = (np.isnan(frejm['koncentracija'])) & ([not m for m in np.isnan(frejm['status'])])
        i2 = i0 & ~ i1

        frejm.loc[i0 & i1, 'status'] = 32768
        frejm.loc[i2, 'status'] = [self._bor_value(m, 32768) for m in frejm.loc[i2, 'status']]
        frejm.loc[i0, 'flag'] = -1
        return frejm

    def _bor_value(self, status, val):
        try:
            return int(status) | int(val)
        except Exception:
            return 32768


class NotIntegerFreq(Exception):
    pass
