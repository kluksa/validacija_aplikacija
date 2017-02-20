# -*- coding: utf-8 -*-
import numpy as np
import pandas as pd


class SatniAgregator(object):
    def __init__(self):
        pass

    def helper_binary_or(self, x):
        if len(x) == 0:
            return 524288  # nema podataka - obuhvat satni los status
        result = 0
        for i in x:
            try:
                result |= int(i)
            except ValueError:
                pass
        return result

    def helper_average(self, x):
        if len(x) == 0:
            return -9999
        return np.mean(x)

    def test_valjanosti(self, x):
        if x < 32768 * 2:
            return True
        else:
            return False

    def agregiraj(self, frejm, broj_u_satu):
        """
        satna agregacija frejma

        frejm - pandas dataframe podataka (sa vremenskim indeksom)
        broj_u_satu - broj podataka u satu (za obuhvat)
        """
        expectedCols = ['mean', 'valjan', 'count', 'obuhvat', 'status']
        # 0. korak : pripremi output frejm
        agregirani = pd.DataFrame()

        # 1.korak : agregiraj sve statuse (binary or)
        agStatusi = frejm['status'].resample('H', closed='right', label='right').apply(self.helper_binary_or)
        agregirani['status'] = agStatusi

        # 2.korak : obuhvat i priprema podataka
        bezNanKonc = frejm[[not np.isnan(i) for i in frejm['korekcija']]]  # bez nan vrijednosti
        bezLosihFlagova = bezNanKonc[bezNanKonc['flag'] >= 0]  # samo flagovi >= 0
        bezLosihStatusa = bezLosihFlagova[bezLosihFlagova['status'] < 1024]  # samo statusi ispod 1024

        agCount = bezLosihStatusa['korekcija'].resample('H', closed='right', label='right').count()
        agregirani['count'] = agCount
        agregirani['obuhvat'] = 100 * agregirani['count'] / broj_u_satu

        # 3.korak : za los obuhvat <75% dodaj status 524288
        agregirani.loc[agregirani['obuhvat'] < 75, 'status'] = [(int(i) | 524288) for i in
                                                                agregirani.loc[agregirani['obuhvat'] < 75, 'status']]

        # 4.korak
        agAverage = bezLosihStatusa['korekcija'].resample('H', closed='right', label='right').apply(self.helper_average)
        agregirani['mean'] = agAverage

        # 5.korak sredi stupac valjan
        agregirani['valjan'] = [self.test_valjanosti(i) for i in agregirani['status']]
        agregirani = agregirani[expectedCols]
        return agregirani
