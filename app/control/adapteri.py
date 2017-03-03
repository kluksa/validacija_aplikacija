import json

import numpy as np
import pandas as pd

import app.model.dto as dto
import app.model.dto_parser as dto_parser


class MalformedJSONException(Exception):
    """Iznimka kada ne valja ulazni JSON"""


class Adapter:
    def __init__(self):
        self.obavezni_json_stupci = []

    def adaptiraj(self, ulaz):
        raise NotImplementedError

    def _provjeri(self, data_frame, obavezni_json_stupci):
        d1 = len(data_frame.columns)
        d2 = len(obavezni_json_stupci)
        if len(data_frame.columns) < len(obavezni_json_stupci):
            raise MalformedJSONException('JSON ima manje stupaca od obaveznog broja')
        for stupac in obavezni_json_stupci:
            if stupac not in data_frame.columns:
                raise MalformedJSONException('Nedostaje stupac ' + stupac)
        return True


class ZeroSpanAdapter(Adapter):
    def __init__(self):
        super(Adapter, self).__init__()
        self.obavezni_json_stupci = ['vrsta', 'vrijeme', 'vrijednost', 'minDozvoljeno', 'maxDozvoljeno']
        self.frame_stupci = ['vrijednost', 'korekcija', 'minDozvoljeno', 'maxDozvoljeno', 'A', 'B', 'Sr', 'LDL']

    def _napravi_frame(self, frame: pd.DataFrame):
        frame = frame.set_index(frame['vrijeme'])
        frame.index = [i.round('Min') for i in frame.index]
        frame = frame[frame['vrijednost'] > -998.0]
        frame.drop(['vrijeme', 'vrsta'], inplace=True, axis=1)
        frame = pd.concat([frame, pd.DataFrame(columns=['korekcija', 'A', 'B', 'Sr', 'LDL'])])
        return frame[self.frame_stupci]

    def adaptiraj(self, ulaz):
        #       try:
        frejm = pd.read_json(ulaz, orient='records', convert_dates=['vrijeme'])
        if frejm.empty:
            return pd.DataFrame(columns=self.frame_stupci), pd.DataFrame(columns=self.frame_stupci)
        self._provjeri(frejm, self.obavezni_json_stupci)
        zero_frejm = self._napravi_frame(frejm[frejm['vrsta'] == 'Z'])
        span_frejm = self._napravi_frame(frejm[frejm['vrsta'] == 'S'])
        return zero_frejm, span_frejm


# except Exception:
# ovo ne valja. Korisnik treba znati da je došlo do greške, a ne zakopati tu informaciju u log file
#            logging.error('Fail kod parsanja json stringa:\n' + str(x), exc_info=True)
#            spanFrejm = pd.DataFrame(columns=self.expectedColsSpan)
#            zeroFrejm = pd.DataFrame(columns=self.expectedColsZero)
#            return zeroFrejm, spanFrejm


class PodatakAdapter(Adapter):
    def __init__(self):
        super().__init__()
        self.frame_stupci = ['vrijednost', 'korekcija', 'flag', 'statusString',
                             'status', 'id', 'A', 'B', 'Sr', 'LDL']
        self.obavezni_json_stupci = ['vrijeme', 'id', 'vrijednost', 'statusString', 'valjan',
                                     'statusInt', 'nivoValidacije']

    def adaptiraj(self, ulaz):
        """
        Funkcija je zaduzena da konvertira ulazni json string (x) u pandas frejm
        """
        #        try:
        df = pd.read_json(ulaz, orient='records')  # , convert_dates=['vrijeme'])
        if df.empty:
            return pd.DataFrame(columns=self.frame_stupci)
        df['vrijeme'] = pd.to_datetime(df['vrijeme'], unit='ms')
        self._provjeri(df, self.obavezni_json_stupci)
        df = df.set_index(df['vrijeme'])
        df.drop(['vrijeme', 'nivoValidacije'], inplace=True, axis=1)
        rename_map = {'valjan': 'flag',
                      'statusInt': 'status'}
        df.rename(columns=rename_map, inplace=True)
        df['vrijednost'] = df['vrijednost'].map(lambda x: x if x > -999 else np.NaN)
        df['flag'] = df['flag'].map(lambda x: 1 if x else -1)
        df = pd.concat([df, pd.DataFrame(columns=['korekcija', 'A', 'B', 'Sr', 'LDL'])])
        df = df[self.frame_stupci]
        return df


# except (ValueError, TypeError, AssertionError):
#            logging.error('Fail kod parsanja json stringa:\n' + str(x), exc_info=True)
#            df = pd.DataFrame(columns=self.expectedColsKonc)
#            return df


class ProgramMjerenjaAdapter:
    def adaptiraj(self, ulaz):
        """
        """
        parser = dto_parser.ProgramMjerenjaParser(dto_parser.DTOParser.Vrsta.JSON)
        rezultat = []
        nox = {}
        for pm in json.loads(ulaz):
            program = parser.parse(pm)
            if program.komponenta.formula in ['NO', 'NO2', 'NOx']:
                kljuc = str(program.postaja.id) + ":" + str(program.usporedno)
                if kljuc not in nox.keys():
                    p = dto.ProgramMjerenjaNox(program)
                    nox[kljuc] = p
                    rezultat.append(p)
                nox[kljuc].dodaj_program(program)
            else:
                rezultat.append(parser.parse(pm))
        return rezultat
