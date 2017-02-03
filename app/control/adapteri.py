import pandas as pd
import numpy as np
import xml.etree.ElementTree as Et

class MalformedJSONException(Exception):
    '''Iznimka kada ne valja ulazni JSON'''


class Adapter:


    def __init__(self):
        self.obavezni_json_stupci = []

    def _provjeri(self, json, obavezni_json_stupci):
        if len(json.columns) < len(obavezni_json_stupci):
            raise MalformedJSONException('JSON ima manje stupaca od obaveznog broja')
        for stupac in obavezni_json_stupci:
            if stupac not in json.columns:
                raise MalformedJSONException('Nedostaje stupac ' + stupac)


class ZeroSpanAdapter(Adapter):


    def __init__(self):
        super(Adapter,self).__init__()
        self.obavezni_json_stupci = ['vrsta', 'vrijeme', 'vrijednost', 'minDozvoljeno', 'maxDozvoljeno']
        self.frame_stupci = ['vrijednost', 'korekcija', 'minDozvoljeno', 'maxDozvoljeno', 'A', 'B', 'Sr', 'LDL']

    def _napravi_frame(self, frame):
        frame = frame.set_index(frame['vrijeme'])
        frame.index = [i.round('Min') for i in frame.index]
        frame = frame[frame['vrijednost'] > -998.0]
        frame.drop(['vrijeme', 'vrsta'], inplace=True, axis=1)
        frame = pd.concat([frame, pd.DataFrame(columns=['korekcija', 'A', 'B', 'Sr', 'LDL'])])
        return frame[self.frame_stupci]

    def adapt(self, x):
        #       try:
        frejm = pd.read_json(x, orient='records', convert_dates=['vrijeme'])
        self._provjeri(frejm, self.obavezni_json_stupci)
        zero_frejm = self._napravi_frame(frejm[frejm['vrsta'] == 'Z'])
        zero_frejm.rename(columns={'vrijednost': 'zero'}, inplace=True)
        span_frejm = self._napravi_frame(frejm[frejm['vrsta'] == 'S'])
        span_frejm.rename(columns={'vrijednost': 'span'}, inplace=True)
        return zero_frejm, span_frejm


# except Exception:
# ovo ne valja. Korisnik treba znati da je došlo do greške, a ne zakopati tu informaciju u log file
#            logging.error('Fail kod parsanja json stringa:\n' + str(x), exc_info=True)
#            spanFrejm = pd.DataFrame(columns=self.expectedColsSpan)
#            zeroFrejm = pd.DataFrame(columns=self.expectedColsZero)
#            return zeroFrejm, spanFrejm


class PodatakAdapter(Adapter):
    def __init__(self):
        self.frame_stupci = ['koncentracija', 'korekcija', 'flag', 'statusString',
                             'status', 'id', 'A', 'B', 'Sr', 'LDL']
        self.obavezni_json_stupci = ['vrijeme', 'id', 'vrijednost', 'statusString', 'valjan',
                                     'statusInt', 'nivoValidacije']

    def adaptiraj_ulazni_json(self, json):
        """
        Funkcija je zaduzena da konvertira ulazni json string (x) u pandas frejm
        """
        #        try:
        df = pd.read_json(json, orient='records', convert_dates=['vrijeme'])
        self._provjeri(df, self.obavezni_json_stupci)
        df = df.set_index(df['vrijeme'])
        df.drop(['vrijeme', 'nivoValidacije'], inplace=True, axis=1)
        rename_map = {'vrijednost': 'koncentracija',
                      'valjan': 'flag',
                      'statusInt': 'status'}
        df.rename(columns=rename_map, inplace=True)
        df['koncentracija'] = df['koncentracija'].map(lambda x: x if x > -999 else np.Nan)
        df['flag'] = df['flag'].map(lambda x: 1 if x else -1)
        df = pd.concat([df, pd.DataFrame(columns=['korekcija', 'A', 'B', 'Sr', 'LDL'])])
        # REVIEW sto je ovo?????????????????????
        df['statusString'] = df['statusString']
        # reorder
        df = df[self.frame_stupci]
        return df


# except (ValueError, TypeError, AssertionError):
#            logging.error('Fail kod parsanja json stringa:\n' + str(x), exc_info=True)
#            df = pd.DataFrame(columns=self.expectedColsKonc)
#            return df


class ProgramMjerenjaAdapter:
    def adapt(self, x):
        """
        Parsira xml sa programima mjerenja preuzetih sa rest servisa,

        output: (nested) dictionary sa bitnim podacima. Primarni kljuc je program
        mjerenja id, sekundarni kljucevi su opisni (npr. 'komponentaNaziv')
        """
        rezultat = {}
        root = Et.fromstring(x)
        for programMjerenja in root:
            i = int(programMjerenja.find('id').text)
            rezultat[i] = {
                'postajaId': int(programMjerenja.find('.postajaId/id').text),
                'postajaNaziv': programMjerenja.find('.postajaId/nazivPostaje').text,
                'komponentaId': programMjerenja.find('.komponentaId/id').text,
                'komponentaNaziv': programMjerenja.find('.komponentaId/naziv').text,
                'komponentaMjernaJedinica': programMjerenja.find('.komponentaId/mjerneJediniceId/oznaka').text,
                'komponentaFormula': programMjerenja.find('.komponentaId/formula').text,
                'usporednoMjerenje': programMjerenja.find('usporednoMjerenje').text,
                'konvVUM': float(programMjerenja.find('.komponentaId/konvVUM').text),  # konverizijski volumen,
                'povezaniKanali': [i]}
        return rezultat
