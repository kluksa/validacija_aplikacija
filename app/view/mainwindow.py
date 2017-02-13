# -*- coding: utf-8 -*-
import logging
from datetime import timedelta

from PyQt4 import QtGui, QtCore, uic
from requests.exceptions import RequestException

import app.model.dokument
from app.control.rest_comm import RESTZahtjev, DataReaderAndCombiner, MockZahtjev
from app.model.konfig_objekt import config, GrafKonfig
from app.model.qtmodels import GumbDelegate
from app.view import auth_login
from app.view import kanal_dijalog
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
        self.data_reader = DataReaderAndCombiner(self.restRequest)
        self.progress_bar = ProgressBar()

        self.kanal = None
        self.vrijemeOd = None
        self.vrijemeDo = None

        self.dataDisplay.setModel(self.dokument.koncModel)
        self.korekcijaDisplay.setModel(self.dokument.korekcijaModel)

        self.sredi_delegate_za_tablicu()

        self.program_mjerenja_dlg = kanal_dijalog.KanalDijalog()
        self.download_podataka_worker = DownlodadPodatakaWorker(self.restRequest, self.dokument)

        # custom persistent delegates...
        # TODO! triple click fail... treba srediti persistent editor na cijeli stupac
        # self.korekcijaDisplay.setItemDelegateForColumn(4, GumbDelegate(self))


        self.setup_connections()

    def primjeni_korekciju(self):
        try:
            QtGui.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
            self.dokument.primjeni_korekciju()
            # naredi ponovno crtanje
            self.draw_graf()
        except Exception as err:
            msg = "General exception. \n\n{0}".format(str(err))
            logging.error(str(err), exc_info=True)
            QtGui.QApplication.restoreOverrideCursor()
            QtGui.QMessageBox.warning(QtGui.QWidget(), 'Problem', msg)
        finally:
            QtGui.QApplication.restoreOverrideCursor()

    def export_korekcije(self):
        try:
            QtGui.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
            # REVIEW model se serijalizira, a ne serizalizira ga GUI kontroler
            fname = QtGui.QFileDialog.getSaveFileName(self,
                                                      "export korekcije")
            self.dokument.spremi_se(fname)

        except Exception as err:
            msg = "General exception. \n\n{0}".format(str(err))
            logging.error(str(err), exc_info=True)
            QtGui.QApplication.restoreOverrideCursor()
            QtGui.QMessageBox.warning(QtGui.QWidget(), 'Problem', msg)
        finally:
            QtGui.QApplication.restoreOverrideCursor()

    def sredi_delegate_za_tablicu(self):
        model = self.korekcijaDisplay.model()
        self.korekcijaDisplay.setItemDelegateForColumn(4, GumbDelegate(self))
        for red in range(0, model.rowCount()):
            self.korekcijaDisplay.closePersistentEditor(model.index(red, 4))
            self.korekcijaDisplay.openPersistentEditor(model.index(red, 4))

    def setup_connections(self):
        self.action_quit.triggered.connect(self.close)
        # gumbi za add/remove/edit parametre korekcije i primjenu korekcije

        self.buttonUcitaj.clicked.connect(self.ucitaj_podatke2)
        self.buttonExport.clicked.connect(self.export_korekcije)
        self.buttonPrimjeniKorekciju.clicked.connect(self.primjeni_korekciju)
        # quit
        self.connect(self,
                     QtCore.SIGNAL('terminate_app'),
                     self.close)

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

        self.connect(self.kanvas,
                     QtCore.SIGNAL('table_select_podatak(PyQt_PyObject)'),
                     self.zoom_to_model_timestamp)

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

    def close_event(self, event):
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
            self.dokument.postavi_program_mjerenja(self.restRequest.get_programe_mjerenja())
            self.program_mjerenja_dlg.set_program(self.dokument.treeModelProgramaMjerenja)
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

    #
    # def ucitaj_podatke(self):
    #     """ucitavanje koncentracija, zero i span podataka"""
    #     try:
    #         if self.program_mjerenja_dlg.exec_():
    #             [self.kanal, self.vrijemeOd, self.vrijemeDo] = self.program_mjerenja_dlg.get_izbor()
    #         else:
    #             return
    #         # spinning cursor...
    #         QtGui.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
    #         # dohvati frejmove
    #         self.pokupi_podatke(self.kanal, self.vrijemeOd, self.vrijemeDo)
    #
    #         tpl = self.data_reader.get_data(self.kanal, self.vrijemeOd, self.vrijemeDo)
    #         master_konc_frejm, master_zero_frejm, master_span_frejm = tpl
    #         # spremi frejmove u dokument #TODO! samo 1 level...
    #         self.dokument.koncModel.datafrejm = master_konc_frejm
    #         self.dokument.zeroModel.datafrejm = master_zero_frejm
    #         self.dokument.spanModel.datafrejm = master_span_frejm
    #         # set clean modela za korekcije u dokument
    #         self.dokument.korekcijaModel.datafrejm = pd.DataFrame(columns=['vrijeme', 'A', 'B', 'Sr', 'remove'])
    #         # TODO! sredi opis i drugi update gui labela
    #         od = str(master_konc_frejm.index[0])
    #         do = str(master_konc_frejm.index[-1])
    #         self.dokument.set_kanal_info_string(self.kanal, od, do)
    #
    #         self.update_opis_grafa(self.dokument.koncModel.opis)
    #         self.update_konc_labels(('n/a', 'n/a', 'n/a'))
    #         self.update_zero_labels(('n/a', 'n/a', 'n/a'))
    #         self.update_span_labels(('n/a', 'n/a', 'n/a'))
    #         # predavanje (konc, zero, span) modela kanvasu za crtanje (primarni trigger za clear & redraw)
    #         self.set_data_models_to_canvas(self.dokument.koncModel,
    #                                        self.dokument.zeroModel,
    #                                        self.dokument.spanModel)
    #
    #     except (AssertionError, RequestException) as e1:
    #         msg = "Problem kod dohvaćanja minutnih podataka.\n\n{0}".format(str(e1))
    #         logging.error(str(e1), exc_info=True)
    #         QtGui.QApplication.restoreOverrideCursor()
    #         self.update_opis_grafa("n/a")
    #         QtGui.QMessageBox.warning(QtGui.QWidget(), 'Problem', msg)
    #     except Exception as e2:
    #         msg = "General exception. \n\n{0}".format(str(e2))
    #         logging.error(str(e2), exc_info=True)
    #         QtGui.QApplication.restoreOverrideCursor()
    #         self.update_opis_grafa("n/a")
    #         QtGui.QMessageBox.warning(QtGui.QWidget(), 'Problem', msg)
    #     finally:
    #         QtGui.QApplication.restoreOverrideCursor()

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
        ndays = int((self.dokument.vrijeme_do - self.dokument.vrijeme_od).days)
        self.progress_bar.setRange(0, ndays + 1)
        self.download_podataka_worker.set(self.dokument.aktivni_kanal, self.dokument.vrijeme_od, ndays)
        self.progress_bar.show()
        self.download_podataka_worker.start()

    def ucitavanje_progress(self, n):
        self.progress_bar.setValue(n)

    def ucitavanje_gotovo(self):
        self.progress_bar.close()
        QtGui.QApplication.restoreOverrideCursor()


class DownlodadPodatakaWorker(QtCore.QThread):
    def __init__(self, rest, dokument, parent=None):
        super(DownlodadPodatakaWorker, self).__init__()
        self.restRequest = rest
        self.dokument = dokument

    def set(self, kanal, od, ndays):
        self.kanal = kanal
        self.od = od
        self.ndays = ndays

    def run(self):
        for d in range(1, self.ndays):
            dan = (self.od + timedelta(d)).strftime('%Y-%m-%d')
            mjerenja = self.restRequest.get_sirovi(self.kanal, dan)
            [zero, span] = self.restRequest.get_zero_span(self.kanal, dan, 1)
            self.dokument.appendMjerenja(mjerenja)
            self.dokument.appendZero(zero)
            self.dokument.appendSpan(span)

            self.emit(QtCore.SIGNAL("ucitavanjeProgress(PyQt_PyObject)"), d)
        self.emit(QtCore.SIGNAL("ucitavanjeGotovo"), d)
        # emiriraj update padataka


class ProgressBar(QtGui.QProgressBar):
    def __init__(self, parent=None):
        super(QtGui.QProgressBar, self).__init__(parent)
        self.setWindowTitle('Load status:')
        self.setGeometry(300, 300, 200, 40)
