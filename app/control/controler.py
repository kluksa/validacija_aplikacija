# -*- coding: utf-8 -*-
import os
import logging
import datetime
import numpy as np
import pandas as pd
from requests.exceptions import RequestException
from PyQt4 import QtGui, QtCore
from app.model import dokument
from app.model import konfig_objekt
from app.control.rest_comm import RESTZahtjev, DataReaderAndCombiner
from app.view import mainwindow
from app.view import kanal_dijalog
from app.control.agregator import Agregator


class Kontroler(QtGui.QWidget):
    def __init__(self, parent=None):
        super(Kontroler, self).__init__(parent=None)

        self.kanal = None
        self.vrijemeOd = None
        self.vrijemeDo = None

        self.konfig = konfig_objekt.MainKonfig('konfig_params.cfg')
        self.grafKonfig = konfig_objekt.GrafKonfig('graf_params.cfg')
        self.setup_logging()
        self.restRequest = RESTZahtjev(self.konfig)
        self.restReader = DataReaderAndCombiner(self.restRequest)
        self.dokument = dokument.Dokument()
        self.satniAgregator = Agregator()

        self.gui = mainwindow.MainWindow(self.konfig, self.grafKonfig)
        self.gui.showMaximized()
        #self.gui.show()
        self.setup_connections()
        QtCore.QTimer.singleShot(0, self.kickstart_gui)

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

    def setup_connections(self):
        # quit
        self.connect(self.gui,
                     QtCore.SIGNAL('terminate_app'),
                     self.close)
        # login / logout
        self.connect(self.gui,
                     QtCore.SIGNAL('initiate_login(PyQt_PyObject)'),
                     self.log_in)
        self.connect(self.gui,
                     QtCore.SIGNAL('initiate_logout'),
                     self.log_out)
        # load in novih podataka sa REST-a
        self.connect(self.gui,
                     QtCore.SIGNAL('ucitaj_minutne'),
                     self.ucitavanje_podataka_sa_resta)
        # navigacija graf-tablica sa podacima
        self.connect(self.gui.kanvas,
                     QtCore.SIGNAL('table_select_podatak(PyQt_PyObject)'),
                     self.gui.zoom_to_model_timestamp)
        # primjena korekcije
        self.connect(self.gui,
                     QtCore.SIGNAL('primjeni_korekciju'),
                     self.primjeni_korekciju)
        # export korekcije
        self.connect(self.gui,
                     QtCore.SIGNAL('export_korekcije'),
                     self.export_korekcije)
        #serijalizacija dokumenta
        self.connect(self.gui,
                     QtCore.SIGNAL('serijaliziraj_dokument'),
                     self.spremanje_podataka_u_file)
        #unserijalizacija dokumenta
        self.connect(self.gui,
                     QtCore.SIGNAL('unserijaliziraj_dokument'),
                     self.ucitavanje_podataka_iz_filea)
        #export satno agregiranih
        self.connect(self.gui,
                     QtCore.SIGNAL('export_satno_agregiranih'),
                     self.export_satno_agregiranih)
        #load absr tablice (parametri za korekciju)
        self.connect(self.gui,
                     QtCore.SIGNAL('load_absr_tablicu'),
                     self.load_absr_tablicu_iz_filea)

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

    def primjeni_korekciju(self):
        try:
            QtGui.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
            self.dokument.primjeni_korekciju()
            #naredi ponovno crtanje
            xraspon = self.gui.get_current_x_zoom_range()
            self.gui.draw_graf()
            self.gui.set_current_x_zoom_range(xraspon)
        except Exception as err:
            msg = "General exception. \n\n{0}".format(str(err))
            logging.error(str(err), exc_info=True)
            QtGui.QApplication.restoreOverrideCursor()
            QtGui.QMessageBox.warning(QtGui.QWidget(), 'Problem', msg)
        finally:
            QtGui.QApplication.restoreOverrideCursor()

    def export_satno_agregiranih(self):
        try:
            fajlNejm = QtGui.QFileDialog.getSaveFileName(self.gui,
                                                         "export satno agregiranih")
            if fajlNejm:
                if not fajlNejm.endswith('.csv'):
                    fajlNejm = fajlNejm + '.csv'
                frejm = self.dokument.koncModel.datafrejm
                broj_u_satu = self.restRequest.get_broj_u_satu(self.dokument.aktivniKanal)
                output = self.satniAgregator.satno_agregiraj_frejm(frejm, broj_u_satu)
                QtGui.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
                output.to_csv(fajlNejm)
                QtGui.QApplication.restoreOverrideCursor()
                msg = 'Podaci su uspjesno spremljeni\nagregirani={0}'.format(fajlNejm)
                QtGui.QMessageBox.information(QtGui.QWidget(), 'Info', msg)
            else:
                pass #canceled
        except Exception as err:
            logging.error(str(err), exc_info=True)
            QtGui.QApplication.restoreOverrideCursor()
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

            fajlNejm = QtGui.QFileDialog.getSaveFileName(self.gui,
                                                         "export korekcije")
            if fajlNejm:
                if not fajlNejm.endswith('.csv'):
                    fajlNejm = fajlNejm + '.csv'
                #os... sastavi imena fileova
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
                msg = 'Podaci su uspjesno spremljeni\ndata={0}\nzero={1}\nspan={2}\nParametri={3}'.format(podName, zeroName, spanName, korName)
                QtGui.QMessageBox.information(QtGui.QWidget(), 'Info', msg)
            else:
                pass # canceled
        except Exception as err:
            msg = "General exception. \n\n{0}".format(str(err))
            logging.error(str(err), exc_info=True)
            QtGui.QApplication.restoreOverrideCursor()
            QtGui.QMessageBox.warning(QtGui.QWidget(), 'Problem', msg)
        finally:
            QtGui.QApplication.restoreOverrideCursor()

    def log_in(self, x):
        try:
            self.restRequest.logmein(x)
            self.init_mjerenja_from_rest()
            self.gui.toggle_logged_in_state(True)
        except Exception as err:
            logging.error(str(err), exc_info=True)
            logging.error('logging out')
            self.log_out()
            #try again loop
            odgovor = QtGui.QMessageBox.question(self.gui,
                                                 'Ponovi login',
                                                 'Neuspješan login, želite li probati ponovo?',
                                                 QtGui.QMessageBox.Ok | QtGui.QMessageBox.No)
            if odgovor == QtGui.QMessageBox.Ok:
                self.gui.handle_login()
            else:
                print('Gasim app')
                QtGui.QApplication.quit()


    def log_out(self):
        self.restRequest.logmeout()
        self.gui.toggle_logged_in_state(False)

    def init_mjerenja_from_rest(self):
        try:
            QtGui.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
            self.dokument.mjerenja = self.restRequest.get_programe_mjerenja()
            mapa = self.restRequest.get_statusMap()
            self.dokument.set_koncentracija_status_bits(mapa)
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

    def show_dijalog_za_izbor_kanala_i_datuma(self, od, do):
        treemodel = self.dokument.treeModelProgramaMjerenja
        dijalog = kanal_dijalog.KanalDijalog(treemodel, od=od, do=do)
        if dijalog.exec_():
            kanal, vrijemeOd, vrijemeDo = dijalog.get_izbor()
            return kanal, vrijemeOd, vrijemeDo

    def ucitavanje_podataka_sa_resta(self):
        """ucitavanje koncentracija, zero i span podataka sa REST servisa"""
        try:
            out = self.show_dijalog_za_izbor_kanala_i_datuma(self.vrijemeOd, self.vrijemeDo)
            if out:
                #nije cancel exit
                self.kanal, self.vrijemeOd, self.vrijemeDo = out
            else:
                return
            #spinning cursor...
            QtGui.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
            #dohvati frejmove
            tpl = self.restReader.get_data(self.kanal, self.vrijemeOd, self.vrijemeDo)
            #spremanje podataka o kanalu
            masterKoncFrejm, masterZeroFrejm, masterSpanFrejm = tpl
            #spremi frejmove u dokument #TODO! samo 1 level...
            self.dokument.koncModel.datafrejm = masterKoncFrejm
            self.dokument.zeroModel.datafrejm = masterZeroFrejm
            self.dokument.spanModel.datafrejm = masterSpanFrejm
            #set clean modela za korekcije u dokument
            self.dokument.korekcijaModel.datafrejm = pd.DataFrame(columns=['vrijeme', 'A', 'B', 'Sr', 'remove', 'calc'])
            # sredi opis i drugi update gui labela
            od = str(masterKoncFrejm.index[0])
            do = str(masterKoncFrejm.index[-1])
            self.dokument.set_kanal_info(self.kanal, od, do)
            self.gui.update_opis_grafa(self.dokument.koncModel.opis)
            self.gui.update_konc_labels(('n/a','n/a','n/a'))
            self.gui.update_zero_labels(('n/a','n/a','n/a'))
            self.gui.update_span_labels(('n/a','n/a','n/a'))
            #predavanje (konc, zero, span) modela kanvasu za crtanje (primarni trigger za clear & redraw)
            self.gui.set_data_models_to_canvas(self.dokument.koncModel,
                                               self.dokument.zeroModel,
                                               self.dokument.spanModel)
        except (AssertionError, RequestException) as e1:
            msg = "Problem kod dohvaćanja minutnih podataka.\n\n{0}".format(str(e1))
            logging.error(str(e1), exc_info=True)
            QtGui.QApplication.restoreOverrideCursor()
            self.gui.update_opis_grafa("n/a")
            QtGui.QMessageBox.warning(QtGui.QWidget(), 'Problem', msg)
        except Exception as e2:
            msg = "General exception. \n\n{0}".format(str(e2))
            logging.error(str(e2), exc_info=True)
            QtGui.QApplication.restoreOverrideCursor()
            self.gui.update_opis_grafa("n/a")
            QtGui.QMessageBox.warning(QtGui.QWidget(), 'Problem', msg)
        finally:
            QtGui.QApplication.restoreOverrideCursor()

    def spremanje_podataka_u_file(self):
        """spremanje podataka u file"""
        try:
            #get file sa save
            fajlNejm = QtGui.QFileDialog.getSaveFileName(self.gui,
                                                         "Spremi podatke")
            if fajlNejm:
                if not fajlNejm.endswith('.dat'):
                    fajlNejm = fajlNejm + '.dat'
                #spinning cursor...
                QtGui.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)

                bstr = self.dokument.get_pickleBinary()
                with open(fajlNejm, 'wb') as fn:
                    fn.write(bstr)

                QtGui.QApplication.restoreOverrideCursor()
                msg = 'Podaci su uspjesno spremljeni\nfile={0}'.format(str(fajlNejm))
                QtGui.QMessageBox.information(QtGui.QWidget(), 'Info', msg)
            else:
                pass # canceled
        except Exception as err:
            msg = "General exception. \n\n{0}".format(str(err))
            logging.error(str(msg), exc_info=True)
            QtGui.QApplication.restoreOverrideCursor()
            self.gui.update_opis_grafa("n/a")
            QtGui.QMessageBox.warning(QtGui.QWidget(), 'Problem', msg)
        finally:
            QtGui.QApplication.restoreOverrideCursor()

    def ucitavanje_podataka_iz_filea(self):
        """ucitavanje podataka iz prethodno spremljenog filea"""
        try:
            #get file za load
            fajlNejm = QtGui.QFileDialog.getOpenFileName(self.gui,
                                                         "Ucitaj podatke")
            if fajlNejm:
                #spinning cursor...
                QtGui.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)

                with open(fajlNejm, 'rb') as fn:
                    bstr = fn.read()
                    self.dokument.set_pickleBinary(bstr)

                self.gui.update_opis_grafa(self.dokument.koncModel.opis)
                self.gui.update_konc_labels(('n/a','n/a','n/a'))
                self.gui.update_zero_labels(('n/a','n/a','n/a'))
                self.gui.update_span_labels(('n/a','n/a','n/a'))

                #predavanje (konc, zero, span) modela kanvasu za crtanje (primarni trigger za clear & redraw)
                self.gui.set_data_models_to_canvas(self.dokument.koncModel,
                                                   self.dokument.zeroModel,
                                                   self.dokument.spanModel)
                self.gui.sredi_delegate_za_tablicu()

                QtGui.QApplication.restoreOverrideCursor()
                msg = 'Podaci su uspjesno ucitani\nfile={0}'.format(str(fajlNejm))
                QtGui.QMessageBox.information(QtGui.QWidget(), 'Info', msg)
            else:
                pass # canceled
        except Exception as err:
            msg = "General exception. \n\n{0}".format(str(err))
            logging.error(str(msg), exc_info=True)
            QtGui.QApplication.restoreOverrideCursor()
            self.gui.update_opis_grafa("n/a")
            QtGui.QMessageBox.warning(QtGui.QWidget(), 'Problem', msg)
        finally:
            QtGui.QApplication.restoreOverrideCursor()

    def load_absr_tablicu_iz_filea(self):
        try:
            #get file za load
            fajlNejm = QtGui.QFileDialog.getOpenFileName(self.gui,
                                                         "Ucitaj tablicu korekcijskih parametara")
            if fajlNejm:
                #spinning cursor...
                QtGui.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
                #TODO!
                frejm = pd.read_csv(fajlNejm,
                                    sep=';',
                                    index_col=0,
                                    parse_dates=['vrijeme'])
                #add button placeholder columns ['remove', 'calc']
                frejm['remove'] = ''
                frejm['calc'] = ''
                self.dokument.korekcijaModel.datafrejm = frejm
                self.primjeni_korekciju()
                QtGui.QApplication.restoreOverrideCursor()
                msg = 'Podaci su uspjesno ucitani\nfile={0}'.format(str(fajlNejm))
                QtGui.QMessageBox.information(QtGui.QWidget(), 'Info', msg)
            else:
                pass # canceled
        except Exception as err:
            msg = "General exception. \n\n{0}".format(str(err))
            logging.error(str(msg), exc_info=True)
            QtGui.QApplication.restoreOverrideCursor()
            self.gui.update_opis_grafa("n/a")
            QtGui.QMessageBox.warning(QtGui.QWidget(), 'Problem', msg)
        finally:
            QtGui.QApplication.restoreOverrideCursor()

