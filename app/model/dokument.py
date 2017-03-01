# -*- coding: utf-8 -*-
import os
import pickle
import pandas as pd

from app.model import qtmodels
from PyQt4 import QtCore

class Dokument(QtCore.QObject):
    """Sto instanca ove klase treba raditi ???
    1. čuva dataframeove sa podacima, zero, span
    2. čuva dataframe sa koeficijentima
    3. primijeni korekciju na podatke

    - Stablo sa programom je model vezan uz kanal_dijalog, dakle nije mu mjesto u dokumentu
    - od, do, aktivni program mogu biti ovdje, a mogu biti i kanal_dijalog-u
    """

    novi_podaci = QtCore.pyqtSignal()
    ucitani_dokument = QtCore.pyqtSignal()

    def __init__(self):
        super(self.__class__, self).__init__()
        # nested dict mjerenja
        self.program = None
        # empty tree model programa mjerenja

        # modeli za prikaz podataka
        self._koncModel = qtmodels.KoncFrameModel(self)
        self._zeroModel = qtmodels.ZeroSpanFrameModel('zero', self)
        self._spanModel = qtmodels.ZeroSpanFrameModel('span', self)


        self.aktivni_kanal = None
        self.vrijeme_od = None
        self.vrijeme_do = None
        self._konc_df = None
        self._zero_df = None
        self._span_df = None
        self._corr_df = None

    def prihvat_podataka(self, result):
        self._konc_df = result['mjerenja']
        self._zero_df = result['zero']
        self._span_df = result['span']
        self._koncModel.datafrejm = self._konc_df
        self._zeroModel.datafrejm = self._zero_df
        self._spanModel.datafrejm = self._span_df
        self.novi_podaci.emit()

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

    def set_korekcija(self, df):
        self._corr_df = df
        print("jesam")

    def get_pickleBinary(self):
        mapa = {'kanal': self.aktivni_kanal,
                'od': self.vrijeme_od,
                'do': self.vrijeme_do,
                'koncFrejm': self._konc_df,
                'zeroFrejm': self._zero_df,
                'spanFrejm': self._span_df,
                'korekcijaFrejm': self._corr_df,
                'programiMjerenja': self.program}
        return pickle.dumps(mapa)

    def set_pickleBinary(self, binstr):
        mapa = pickle.loads(binstr)
        self._corr_df = mapa['korekcijaFrejm']
        self.vrijeme_od = mapa['od']
        self.vrijeme_do = mapa['do']
        self.aktivni_kanal = mapa['kanal']
        self.program = mapa['programiMjerenja']
        self.prihvat_podataka(mapa)
        self.ucitani_dokument.emit()
        # TODO! emit request za redraw

    def primjeni_korekciju(self):
        """pokupi frejmove, primjeni korekciju i spremi promjenu"""
#        self.koncModel.datafrejm = self.korekcijaModel.primjeni_korekciju_na_frejm(self.koncModel.datafrejm)
#        self.zeroModel.datafrejm = self.korekcijaModel.primjeni_korekciju_na_frejm(self.zeroModel.datafrejm)
#        self.spanModel.datafrejm = self.korekcijaModel.primjeni_korekciju_na_frejm(self.spanModel.datafrejm)
        self._konc_df = self.primjeni_korekciju_na_frejm(self._konc_df)
        self._zero_df = self.primjeni_korekciju_na_frejm(self._zero_df)
        self._span_df = self.primjeni_korekciju_na_frejm(self._span_df)
        self._koncModel.datafrejm = self._konc_df
        self._zeroModel.datafrejm = self._zero_df
        self._spanModel.datafrejm = self._span_df
        self.novi_podaci.emit()

    def primjeni_korekciju_na_frejm(self, df):
        df = df.drop(['A','B','Sr'], axis=1)
        korr_df = self._corr_df.iloc[:-1, :]
        korr_df = korr_df.set_index(pd.DatetimeIndex(korr_df['vrijeme']))
        tdf = pd.DataFrame(index=df.index).join(korr_df, how='outer')
        tdf['A'] = pd.to_numeric(tdf['A'])
        tdf['B'] = pd.to_numeric(tdf['B'])
        tdf['Sr'] = pd.to_numeric(tdf['Sr'])
        df = df.join(tdf[['A', 'B']].interpolate(method='time').join(tdf[['Sr']].fillna(method='ffill')))
        df['korekcija'] = df.iloc[:, 0] * df['A'] + df['B']
        df['LDL'] = 3.33 * df['Sr'] / df['A']
        return df

