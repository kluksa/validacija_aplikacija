# -*- coding: utf-8 -*-
import os
import pickle

import pandas

from app.model import qtmodels


class Dokument(object):
    """Sto instanca ove klase treba raditi ???
    1. čuva dataframeove sa podacima, zero, span
    2. čuva dataframe sa koeficijentima
    3. primijeni korekciju na podatke

    - Stablo sa programom je model vezan uz kanal_dijalog, dakle nije mu mjesto u dokumentu
    - od, do, aktivni program mogu biti ovdje, a mogu biti i kanal_dijalog-u
    """
    def __init__(self):
        # nested dict mjerenja
        self.programi = []
        # empty tree model programa mjerenja
        self._treeModelProgramaMjerenja = None

        # modeli za prikaz podataka
        self._koncModel = qtmodels.KoncFrameModel()
        self._zeroModel = qtmodels.ZeroSpanFrameModel('zero')
        self._spanModel = qtmodels.ZeroSpanFrameModel('span')
        self._korekcijaModel = qtmodels.KorekcijaFrameModel()
        self.sirovi = pandas.DataFrame()
        self.zero = pandas.DataFrame()
        self.span = pandas.DataFrame()

        self.aktivni_kanal = None
        self.vrijeme_od = None
        self.vrijeme_do = None

    def appendMjerenja(self, df):
        self.sirovi.append(df)

    def appendSpan(self, df):
        self.span.append(df)

    def appendZero(self, df):
        self.zero.append(df)

    def spremi_se(self, fajlNejm):
        # TODO funkcionalnost spremanja staviti u zasebni objekt koji onda (de)serijalizira dokument. Ovo je privremeno da pocistim kontroler
        frejmPodaci = self.dokument.koncModel.datafrejm
        frejmZero = self.dokument.zeroModel.datafrejm
        frejmSpan = self.dokument.spanModel.datafrejm

        # os... sastavi imena fileova
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

    @property
    def treeModelProgramaMjerenja(self):
        """Qt tree model za izbor kanala"""
        return self._treeModelProgramaMjerenja

    @property
    def koncModel(self):
        """Qt table model sa koncentracijama"""
        return self._koncModel

    @property
    def zeroModel(self):
        """Qt table model sa zero vrijednostima"""
        return self._zeroModel

    @property
    def spanModel(self):
        """Qt table model sa span vrijednostima"""
        return self._spanModel

    @property
    def korekcijaModel(self):
        """Qt table model sa tockama za korekciju"""
        return self._korekcijaModel

    def get_pickleBinary(self, fname):
        mapa = {'kanal': self.aktivni_kanal,
                'od': self.vrijeme_od,
                'do': self.vrijeme_do,
                'koncFrejm': self.koncModel.datafrejm,
                'zeroFrejm': self.zeroModel.datafrejm,
                'spanFrejm': self.spanModel.datafrejm,
                'korekcijaFrejm': self.korekcijaModel.datafrejm,
                'programiMjerenja': self.programi}
        return pickle.dumps(mapa)

    def set_pickleBinary(self, binstr):
        mapa = pickle.loads(binstr)
        self.koncModel.datafrejm = mapa['koncFrejm']
        self.zeroModel.datafrejm = mapa['zeroFrejm']
        self.spanModel.datafrejm = mapa['spanFrejm']
        self.korekcijaModel.datafrejm = mapa['korekcijaFrejm']
        self.vrijeme_od = mapa['od']
        self.vrijeme_do = mapa['do']
        self.aktivni_kanal = mapa['kanal']
        self.postavi_program_mjerenja(mapa['programiMjerenja'])
        # TODO! emit request za redraw

    def primjeni_korekciju(self):
        """pokupi frejmove, primjeni korekciju i spremi promjenu"""
        self.koncModel.datafrejm = self.korekcijaModel.primjeni_korekciju_na_frejm(self.koncModel.datafrejm)
        self.zeroModel.datafrejm = self.korekcijaModel.primjeni_korekciju_na_frejm(self.zeroModel.datafrejm)
        self.spanModel.datafrejm = self.korekcijaModel.primjeni_korekciju_na_frejm(self.spanModel.datafrejm)

    def postavi_program_mjerenja(self, programi):
        # sredjivanje povezanih kanala (NOx grupa i PM grupa)
 #       for kanal in self._kanali:
 #           pomocni = self._get_povezane_kanale(kanal)
 #           for i in pomocni:
 #               self._kanali[kanal]['povezaniKanali'].append(i)
 #           # sortiraj povezane kanale, predak je bitan zbog radio buttona
 #           lista = sorted(self._kanali[kanal]['povezaniKanali'])
 #           self._kanali[kanal]['povezaniKanali'] = lista

        self.programi = programi
        drvo = qtmodels.TreeItem(['stanice', None, None, None], parent=None)
        pomocna_mapa = {}
        for pm in programi:
            if pm.postaja.id not in pomocna_mapa:
                pomocna_mapa[pm.postaja.id] = qtmodels.PostajaItem(pm.postaja, parent=drvo)
                drvo.appendChild(pomocna_mapa[pm.postaja.id])
            postaja = pomocna_mapa[pm.postaja.id]
            postaja.appendChild(qtmodels.ProgramMjerenjaItem(pm, parent=postaja))

        drvo.sort_children()
        self._treeModelProgramaMjerenja = qtmodels.ModelDrva(drvo)

    def _get_povezane_kanale(self, kanal):
        """
        Za zadani kanal, ako je formula kanala unutar nekog od setova,
        vrati sve druge kanale na istoj postaji koji takodjer pripadaju istom
        setu (NOx i PM).

        npr. ako je izabrani kanal Desinic NO, funkcija vraca id mjerenja za
        NO2 i NOx sa Desinica (ako postoje)
        """
        setovi = [('NOx', 'NO', 'NO2'), ('PM10', 'PM1', 'PM2.5')]
        output = set()
        postaja = self._kanali[kanal]['postajaId']
        formula = self._kanali[kanal]['komponentaFormula']
        usporednoMjerenje = self._kanali[kanal]['usporednoMjerenje']
        ciljaniSet = None
        for kombinacija in setovi:
            if formula in kombinacija:
                ciljaniSet = kombinacija
                break
        # ako kanal ne pripada setu povezanih...
        if ciljaniSet is None:
            return output

        for pmid in self._kanali:
            if self._kanali[pmid]['postajaId'] == postaja and pmid != kanal:
                if self._kanali[pmid]['komponentaFormula'] in ciljaniSet:
                    # usporedno mjerenje se mora poklapati...
                    if self._kanali[pmid]['usporednoMjerenje'] == usporednoMjerenje:
                        output.add(pmid)
        return output
