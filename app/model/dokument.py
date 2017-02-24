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

    def __init__(self):
        # nested dict mjerenja
        self.programi = []
        # empty tree model programa mjerenja

        # modeli za prikaz podataka
        self._koncModel = qtmodels.KoncFrameModel()
        self._zeroModel = qtmodels.ZeroSpanFrameModel('zero')
        self._spanModel = qtmodels.ZeroSpanFrameModel('span')
        self._korekcijaModel = qtmodels.KorekcijaFrameModel()

        self.aktivni_kanal = None
        self.vrijeme_od = None
        self.vrijeme_do = None

        self._konc_df = None
        self._zero_df = None
        self._span_df = None
        self._corr_df = None

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

    @property
    def korekcijaModel(self):
        """Qt table model sa tockama za korekciju"""
        return self._korekcijaModel

    def get_pickleBinary(self):
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

    def primjeni_korekciju_na_frejm(self, df):
        """primjena korekcije na zadani frejm..."""

        tdf  = pd.DataFrame(index=df.index).join(self._corr_df, how='outer')
        df = df.join(tdf[['A','B']].interpolate(method='time')).join(tdf[['Sr']].fillna(method='ffill'))
        df['korekcija'] = df.iloc[:,0] * df['A'] + df['B']
        df['LDL'] = 3.33*df['Sr']/df['A']

        # pripremi frejm korekcije za rad
        df = self._dataFrejm.copy()
        # izbaci zadnji red (za dodavanje stvari...)
        df = df.iloc[:-1, :]
        TEST1 = len(df)  # broj redova tablice
        # sort

        # radimo samo sa privatnim podacima, pa nema potrebe za validacijom
        # 1. spojimo koncentracijski df sa df korekcijskim faktorima
        # 2. interpoliramo korekcijske faktore
        # 3. odrežemo datframe na [od, do]
        # 4. primijenimo korekciju


        df.dropna(axis=0, inplace=True)
        df.sort_values(['vrijeme'], inplace=True)
        df = df.set_index(df['vrijeme'])
        # drop stupce koji su pomocni
        df.drop(['remove', 'calc', 'vrijeme'], axis=1, inplace=True)
        df['A'] = df['A'].astype(float)
        df['B'] = df['B'].astype(float)
        df['Sr'] = df['Sr'].astype(float)

        TEST2 = len(df)  # broj redova tablice bez n/a
        if TEST1 != TEST2:
            raise ValueError('Parametri korekcije nisu dobro ispunjeni')
        if (not len(df)) or (not len(frejm)):
            # korekcija nije primjenjena jer je frejm sa parametrima prazan ili je sam frejm prazan
            return frejm
        try:
            zadnji_indeks = list(df.index)[-1]
            # sredi interpolaciju dodaj na kraj podatka zadnju vrijednost
            kraj_podataka = frejm.index[-1]
            df.loc[kraj_podataka, 'A'] = df.loc[zadnji_indeks, 'A']
            df.loc[kraj_podataka:, 'B'] = df.loc[zadnji_indeks, 'B']
            df.loc[kraj_podataka:, 'Sr'] = df.loc[zadnji_indeks, 'Sr']
            # interpoliraj na minutnu razinu
            saved_sr = df['Sr']
            df = df.resample('Min').interpolate()
            # sredi Sr da bude skokovit
            for i in range(len(saved_sr) - 1):
                ind1 = saved_sr.index[i]
                ind2 = saved_sr.index[i + 1]
                val = saved_sr.iloc[i]
                df.loc[ind1:ind2, 'Sr'] = val
            df = self.calc_ldl_values(df)
            df = df.reindex(frejm.index)  # samo za definirane indekse...
            # slozi podatke u input frejm
            frejm['A'] = df['A']
            frejm['B'] = df['B']
            frejm['Sr'] = df['Sr']
            frejm['LDL'] = df['LDL']
            # izracunaj korekciju i apply
            korekcija = frejm.iloc[:, 0] * frejm.loc[:, 'A'] + frejm.loc[:, 'B']
            frejm['korekcija'] = korekcija
            return frejm
        except Exception as err:
            logging.error(str(err), exc_info=True)
            QtGui.QMessageBox.warning(QtGui.QMessageBox(), 'Problem', 'Problem kod racunanja korekcije')
            return frejm
