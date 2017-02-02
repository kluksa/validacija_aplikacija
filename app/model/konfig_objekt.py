# -*- coding: utf-8 -*-
import logging
import configparser
import matplotlib.colors as colors


class MainKonfig(object):
    def __init__(self, cfgFile, parent=None):
        self.cfg = configparser.ConfigParser()
        self.LOG_LEVELS = {'DEBUG': logging.DEBUG,
                           'INFO': logging.INFO,
                           'WARNING': logging.WARNING,
                           'ERROR': logging.ERROR,
                           'CRITICAL': logging.CRITICAL}
        try:
            self.cfg.read(cfgFile)
        except OSError:
            msg = 'Kriticna pogreska kod citanja konfig filea, izlaz iz aplikacije.'
            print(msg)
            logging.error(msg, exc_info=True)
            raise SystemExit(msg)

    # LOGGING
    @property
    def logFile(self):
        return self.cfg['LOG_SETUP']['file']

    @property
    def logMode(self):
        val = self.cfg['LOG_SETUP']['mode']
        if val in ['a', 'w']:
            return val
        else:
            return 'a'

    @property
    def logLvl(self):
        val = self.cfg['LOG_SETUP']['lvl']
        return self.LOG_LEVELS.get(val, logging.ERROR)

    # REST
    @property
    def restProgramMjerenja(self):
        return self.cfg['REST']['program_mjerenja']

    @property
    def restSiroviPodaci(self):
        return self.cfg['REST']['sirovi_podaci']

    @property
    def restStatusMap(self):
        return self.cfg['REST']['status_map']

    @property
    def restZeroSpanPodaci(self):
        return self.cfg['REST']['zero_span_podaci']

    # icons
    @property
    def spanSelectIcon(self):
        return self.cfg['ICONS']['spanSelectIcon']

    @property
    def xZoomIcon(self):
        return self.cfg['ICONS']['xZoomIcon']


class GrafKonfig(object):
    def __init__(self, cfgFile, parent=None):
        self.fajlname = cfgFile
        self.cfg = configparser.ConfigParser()
        try:
            self.cfg.read(cfgFile)
        except OSError:
            msg = 'Kriticna pogreska kod citanja konfig filea za grafove, izlaz iz aplikacije.'
            print(msg)
            logging.error(msg, exc_info=True)
            raise SystemExit(msg)

    def save_to_file(self):
        with open(self.fajlname, mode='w') as fajl:
            self.cfg.write(fajl)

    def get_konfig_option(self, section, option, fallback):
        out = self.cfg.get(section, option, fallback=fallback)
        if option in ['linecolor', 'markerfacecolor', 'markeredgecolor']:
            if "#" in out:
                # convert from hex
                return colors.hex2color(out)
            else:
                # tuple zagrade treba maknuti...
                rgba = out.replace('(', '')
                rgba = rgba.replace(')', '')
                rgba = rgba.split(sep=',')
                rgba = [float(i.strip()) for i in rgba]
                if len(rgba) in [3, 4]:
                    return tuple(rgba)
                else:
                    return fallback
        else:
            return out

    def set_konfig_option(self, section, option, val):
        self.cfg.set(section, option, value=str(val))
