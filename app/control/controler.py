# -*- coding: utf-8 -*-
import os
import logging
import datetime
import numpy as np
import pandas as pd
from requests.exceptions import RequestException
from PyQt4 import QtGui, QtCore
import xml.etree.ElementTree as ET
from app.model import dokument
from app.model import konfig_objekt
from app.control.rest_comm import RESTZahtjev
from app.view import mainwindow
from app.view import kanal_dijalog


class Kontroler(QtGui.QWidget):
    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent=None)

        self.kanal = None
        self.vrijemeOd = None
        self.vrijemeDo = None

        self.konfig = konfig_objekt.MainKonfig('konfig_params.cfg')
        self.grafKonfig = konfig_objekt.GrafKonfig('graf_params.cfg')
        self.setup_logging()
        self.restRequest = RESTZahtjev(self.konfig)
        self.dokument = dokument.Dokument()

        self._statusMap = {} # bit status objasnjenje {broj bita [int] : opisni string [str]}
        self._statusLookup = {} # lookup tablica za opis statusa {broj statusa[int] : string asociranih flagova [str]}

        self.gui = mainwindow.MainWindow(self.konfig, self.grafKonfig)
        self.gui.show()
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
                     self.ucitaj_podatke_za_kanal_i_datum)
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

    def kickstart_gui(self):
        # set modele u odgovarajuce tablice
        self.gui.dataDisplay.setModel(self.dokument.koncModel)
        self.gui.korekcijaDisplay.setModel(self.dokument.korekcijaModel)

        self.gui.sredi_delegate_za_tablicu()
        self.connect(self.dokument.korekcijaModel,
                     QtCore.SIGNAL('update_persistent_delegate'),
                     self.gui.sredi_delegate_za_tablicu)
        # login
        self.gui.handle_login()

    def primjeni_korekciju(self):
        try:
            # TODO! za export svega....
            QtGui.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
            #dohvati relevantne modele
            model_korekcija = self.dokument.korekcijaModel
            modelZero = self.dokument.zeroModel
            modelSpan = self.dokument.spanModel
            modelKoncentracija = self.dokument.koncModel
            #sredi zero
            df = modelZero.datafrejm
            dfk = model_korekcija.get_frejm_za_korekciju(df.index)
            if len(dfk):
                korekcija = df.loc[:,'zero'] * dfk.loc[:,'A'] + dfk.loc[:,'B']
                ldl = dfk['LDL']
                a = dfk['A']
                b = dfk['B']
                sr = dfk['Sr']
            else:
                korekcija = np.repeat(np.NaN, len(df))
                ldl = np.repeat(np.NaN, len(df))
                a = np.repeat(np.NaN, len(df))
                b = np.repeat(np.NaN, len(df))
                sr = np.repeat(np.NaN, len(df))
            modelZero.update_korekciju_i_ldl(korekcija, ldl, a, b, sr)
            #sredi span
            df = modelSpan.datafrejm
            dfk = model_korekcija.get_frejm_za_korekciju(df.index)
            if len(dfk):
                korekcija = df.loc[:,'span'] * dfk.loc[:,'A'] + dfk.loc[:,'B']
                ldl = dfk['LDL']
                a = dfk['A']
                b = dfk['B']
                sr = dfk['Sr']
            else:
                korekcija = np.repeat(np.NaN, len(df))
                ldl = np.repeat(np.NaN, len(df))
                a = np.repeat(np.NaN, len(df))
                b = np.repeat(np.NaN, len(df))
                sr = np.repeat(np.NaN, len(df))
            modelSpan.update_korekciju_i_ldl(korekcija, ldl, a, b, sr)
            #sredi koncentraciju
            df = modelKoncentracija.datafrejm
            dfk = model_korekcija.get_frejm_za_korekciju(df.index)
            if len(dfk):
                korekcija = df.loc[:,'koncentracija'] * dfk.loc[:,'A'] + dfk.loc[:,'B']
                ldl = dfk['LDL']
                a = dfk['A']
                b = dfk['B']
                sr = dfk['Sr']
            else:
                korekcija = np.repeat(np.NaN, len(df))
                ldl = np.repeat(np.NaN, len(df))
                a = np.repeat(np.NaN, len(df))
                b = np.repeat(np.NaN, len(df))
                sr = np.repeat(np.NaN, len(df))
            modelKoncentracija.update_korekciju_i_ldl(korekcija, ldl, a, b, sr)
            #naredi ponovno crtanje
            self.gui.draw_graf()
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

            fajlNejm = QtGui.QFileDialog.getSaveFileName(self.gui,
                                                         "export korekcije")

            #os... sastavi imena fileova
            folder, name = os.path.split(fajlNejm)
            podName = "podaci_" + name
            zeroName = "zero_" + name
            spanName = "span_" + name
            podName = os.path.normpath(os.path.join(folder, podName))
            zeroName = os.path.normpath(os.path.join(folder, zeroName))
            spanName = os.path.normpath(os.path.join(folder, spanName))

            frejmPodaci.to_csv(podName, sep=';')
            frejmZero.to_csv(zeroName, sep=';')
            frejmSpan.to_csv(spanName, sep=';')
            print('FILES SAVED : ', podName, zeroName, spanName)
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
            mjerenjaXML = self.restRequest.get_programe_mjerenja()
            self.dokument.mjerenja = self._parse_mjerenjaXML(mjerenjaXML)
            self._statusMap = self.restRequest.get_statusMap()
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

    def ucitaj_podatke_za_kanal_i_datum(self):
        """ucitavanje koncentracija, zero i span podataka"""
        try:
            treemodel = self.dokument.treeModelProgramaMjerenja
            dijalog = kanal_dijalog.KanalDijalog(treemodel)
            if dijalog.exec_():
                self.kanal, self.vrijemeOd, self.vrijemeDo = dijalog.get_izbor()
            else:
                return

            raspon = (self.vrijemeDo - self.vrijemeOd).days
            if raspon < 1:
                raise ValueError('Vremenski raspon manji od dana nije dozvoljen')

            #data storage za ucitane podatke
            masterKoncFrejm = pd.DataFrame(columns=['koncentracija', 'korekcija', 'flag', 'statusString', 'status', 'id'])
            masterZeroFrejm = pd.DataFrame(columns=['zero', 'korekcija', 'minDozvoljeno', 'maxDozvoljeno'])
            masterSpanFrejm = pd.DataFrame(columns=['span', 'korekcija', 'minDozvoljeno', 'maxDozvoljeno'])
            #spinning cursor...
            QtGui.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)

            #PROGRESS BAR
            self.progress = QtGui.QProgressBar()
            self.progress.setWindowTitle('Load status:')
            self.progress.setRange(0, raspon+1)
            self.progress.setGeometry(300, 300, 200, 40)
            self.progress.show()

            #ucitavanje frejmova koncentracija, zero, span
            for d in range(raspon+1):
                dan = (self.vrijemeOd + datetime.timedelta(d)).strftime('%Y-%m-%d')
                koncFrejm = self.restRequest.get_sirovi(self.kanal, dan)
                zeroFrejm, spanFrejm = self.restRequest.get_zero_span(self.kanal, dan, 1)
                #append dnevne frejmove na glavni ako imaju podatke
                if len(koncFrejm):
                    masterKoncFrejm = masterKoncFrejm.append(koncFrejm)
                if len(zeroFrejm):
                    masterZeroFrejm = masterZeroFrejm.append(zeroFrejm)
                if len(spanFrejm):
                    masterSpanFrejm = masterSpanFrejm.append(spanFrejm)
                #advance progress bar
                self.progress.setValue(d)
            self.progress.close()
            #broj podataka u satu...
            try:
                frek = int(np.floor(60/self.restRequest.get_broj_u_satu(self.kanal)))
            except Exception as err:
                logging.error(str(err), exc_info=True)
                #default na minutni period
                frek = -1
            if frek <= 1:
                frek = 'Min'
                start = datetime.datetime.combine(self.vrijemeOd, datetime.time(0, 1, 0))
                kraj = self.vrijemeDo + datetime.timedelta(1)
            else:
                frek = str(frek) + 'Min'
                start = datetime.datetime.combine(self.vrijemeOd, datetime.time(0, 0, 0))
                kraj = self.vrijemeDo + datetime.timedelta(1)
            fullraspon = pd.date_range(start=start, end=kraj, freq=frek)
            #reindex koncentracijski data zbog rupa u podacima (ako nedostaju rubni podaci)
            masterKoncFrejm = masterKoncFrejm.reindex(fullraspon)
            #konverzija status int to string
            statstr = [self._statusInt_to_statusString(i) for i in masterKoncFrejm.loc[:,'status']]
            masterKoncFrejm.loc[:,'statusString'] = statstr

            self.dokument.koncModel.datafrejm = masterKoncFrejm
            self.dokument.zeroModel.datafrejm = masterZeroFrejm
            self.dokument.spanModel.datafrejm = masterSpanFrejm

            #spremanje metapodataka u model za koncentracije
            od = str(fullraspon[0])
            do = str(fullraspon[-1])
            self.dokument.koncModel.opis = self._get_kanal_info_string(self.kanal, od, do)
            self.dokument.koncModel.kanalMeta = self.dokument.mjerenja[self.kanal]
            #TODO! sredi opis kanala negdje na gui prozor...
            self.gui.update_opis_grafa(self.dokument.koncModel.opis)

            self.gui.update_konc_labels(('n/a','n/a'))
            self.gui.update_zero_labels(('n/a','n/a'))
            self.gui.update_span_labels(('n/a','n/a'))


            #set clean modela za korekcije u dokument
            self.dokument.korekcijaModel.datafrejm = pd.DataFrame(columns=['vrijeme', 'A', 'B', 'Sr', 'remove'])

            #predavanje (konc, zero, span) modela kanvasu za crtanje (primarni trigger za clear & redraw)
            self.gui.set_data_models_to_canvas(self.dokument.koncModel,
                                               self.dokument.zeroModel,
                                               self.dokument.spanModel)

        except (AssertionError, RequestException) as e1:
            msg = "Problem kod dohvaćanja minutnih podataka.\n\n{0}".format(str(e1))
            logging.error(str(e1), exc_info=True)
            if hasattr(self, "progress"):
                self.progress.close()
            QtGui.QApplication.restoreOverrideCursor()
            self.gui.update_opis_grafa("n/a")
            QtGui.QMessageBox.warning(QtGui.QWidget(), 'Problem', msg)
        except Exception as e2:
            msg = "General exception. \n\n{0}".format(str(e2))
            logging.error(str(e2), exc_info=True)
            if hasattr(self, "progress"):
                self.progress.close()
            QtGui.QApplication.restoreOverrideCursor()
            self.gui.update_opis_grafa("n/a")
            QtGui.QMessageBox.warning(QtGui.QWidget(), 'Problem', msg)
        finally:
            QtGui.QApplication.restoreOverrideCursor()

    def _get_kanal_info_string(self, kanal, od, do):
        """getter stringa za naslov grafa..."""
        mapa = self.dokument.mjerenja
        kid = str(kanal)
        postaja = mapa[kanal]['postajaNaziv']
        #naziv = mapa[kanal]['komponentaNaziv']
        formula = mapa[kanal]['komponentaFormula']
        mjernaJedinica = mapa[kanal]['komponentaMjernaJedinica']
        out = "{0}: {1} | {2} ({3}) | OD: {4} | DO: {5}".format(
            kid,
            postaja,
            formula,
            mjernaJedinica,
            od,
            do)
        return out

    def _check_bit(self, broj, bit_position):
        """
        Pomocna funkcija za testiranje statusa
        Napravi temporary integer koji ima samo jedan bit vrijednosti 1 na poziciji
        bit_position. Napravi binary and takvog broja i ulaznog broja.
        Ako oba broja imaju bit 1 na istoj poziciji vrati True, inace vrati False.
        """
        if bit_position != None:
            temp = 1 << int(bit_position) #left shift bit za neki broj pozicija
            if int(broj) & temp > 0: # binary and izmjedju ulaznog broja i testnog broja
                return True
            else:
                return False

    def _check_status_flags(self, broj):
        """
        provjeri stauts integera broj dekodirajuci ga sa hash tablicom
        {bit_pozicija:opisni string}. Vrati string opisa.
        """
        flaglist = []
        for key, value in self._statusMap.items():
            if self._check_bit(broj, key):
                flaglist.append(value)
        opis = ",".join(flaglist)
        return opis

    def _statusInt_to_statusString(self, sint):
        if np.isnan(sint):
            return 'Status nije definiran'
        sint = int(sint)
        rez = self._statusLookup.get(sint, None) #see if value exists
        if rez == None:
            rez = self._check_status_flags(sint) #calculate
            self._statusLookup[sint] = rez #store value for future lookup
        return rez

    def _parse_mjerenjaXML(self, x):
        """
        Parsira xml sa programima mjerenja preuzetih sa rest servisa,

        output: (nested) dictionary sa bitnim podacima. Primarni kljuc je program
        mjerenja id, sekundarni kljucevi su opisni (npr. 'komponentaNaziv')
        """
        rezultat = {}
        root = ET.fromstring(x)
        for programMjerenja in root:
            i = int(programMjerenja.find('id').text)
            postajaId = int(programMjerenja.find('.postajaId/id').text)
            postajaNaziv = programMjerenja.find('.postajaId/nazivPostaje').text
            komponentaId = programMjerenja.find('.komponentaId/id').text
            komponentaNaziv = programMjerenja.find('.komponentaId/naziv').text
            komponentaMjernaJedinica = programMjerenja.find('.komponentaId/mjerneJediniceId/oznaka').text
            komponentaFormula = programMjerenja.find('.komponentaId/formula').text
            usporednoMjerenje = programMjerenja.find('usporednoMjerenje').text
            konvVUM = float(programMjerenja.find('.komponentaId/konvVUM').text) #konverizijski volumen
            #dodavanje mjerenja u dictionary
            rezultat[i] = {
                'postajaId':postajaId,
                'postajaNaziv':postajaNaziv,
                'komponentaId':komponentaId,
                'komponentaNaziv':komponentaNaziv,
                'komponentaMjernaJedinica':komponentaMjernaJedinica,
                'komponentaFormula':komponentaFormula,
                'usporednoMjerenje':usporednoMjerenje,
                'konvVUM':konvVUM,
                'povezaniKanali':[i]}
        return rezultat


