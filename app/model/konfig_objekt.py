# -*- coding: utf-8 -*-
import logging
import configparser
import matplotlib.colors as colors


class Konfig:
    class Log:
        LOG_LEVELS = {'DEBUG': logging.DEBUG,
                      'INFO': logging.INFO,
                      'WARNING': logging.WARNING,
                      'ERROR': logging.ERROR,
                      'CRITICAL': logging.CRITICAL}

        def __init__(self, log_dict):
            self.level = self.LOG_LEVELS[log_dict['lvl']]
            self.mode = log_dict['mode']
            self.file = log_dict['file']

    class Rest:
        def __init__(self, mapa):
            self.program_mjerenja_url = mapa['program_mjerenja']
            self.sirovi_podaci_url = mapa['sirovi_podaci']
            self.status_map_url = mapa['status_map']
            self.zero_span_podaci_url = mapa['zero_span_podaci']

    class Icons:
        def __init__(self, mapa):
            self.span_select_icon = mapa['spanSelectIcon']
            self.x_zoom_icon = mapa['xZoomIcon']

    def __init__(self):
        self._cfg = self.read_config(['konfig_params.cfg', 'graf_params.cfg'])
        self.log = Konfig.Log(self._cfg['LOG_SETUP'])
        self.rest = Konfig.Rest(self._cfg['REST'])
        self.icons = Konfig.Icons(self._cfg['ICONS'])

    def read_config(self, datoteke):
        cfg = configparser.ConfigParser()
        for d in datoteke:
            cfg.read(d)
        return cfg


config = Konfig()


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
        elif option in ['markersize', 'linewidth']:
            return float(out)  # force float values for sizes
        else:
            return out

    def set_konfig_option(self, section, option, val):
        self.cfg.set(section, option, value=str(val))
