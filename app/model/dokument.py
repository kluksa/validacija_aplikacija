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
        self.sirovi = self.sirovi.append(df)
        pass

    def appendSpan(self, df):
        self.span = self.span.append(df)
        pass

    def appendZero(self, df):
        self.zero = self.zero.append(df)
        pass

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
