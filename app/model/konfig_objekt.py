# -*- coding: utf-8 -*-
import logging
import configparser
import matplotlib.colors as colors


def init(dev=False):
    if dev:
        pass


class Konfig:
    class Graph:
        def __init__(self, mapa):
            self.label = mapa['label']
            self.linestyle = mapa['linestyle']
            self.drawstyle = mapa['drawstyle']
            self.linewidth = float(mapa['linewidth'])
            self.color = self.color_from_str(mapa['color'])
            self.marker = mapa['marker']
            self.markersize = float(mapa['markersize'])
            self.markerfacecolor = self.color_from_str(mapa['markerfacecolor'])
            self.markeredgecolor = self.color_from_str(mapa['markeredgecolor'])

        def get_options(self):
            mapa = {'label': self.label, 'linestyle': self.linestyle, 'drawstyle': self.drawstyle,
                    'linewidth': self.linewidth, 'color': self.color, 'marker': self.marker,
                    'markersize': self.markersize, 'markerfacecolor': self.markerfacecolor,
                    'markeredgecolor': self.markeredgecolor}
            return mapa

        def color_from_str(self, out):
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
                    return None

        def postavi_opcije(self, line):
            if line is None:
                return
            self.label = line.get_label()
            self.linestyle = line.get_linestyle()
            self.drawstyle = line.get_drawstyle()
            self.linewidth = line.get_linewidth()
            self.color = line.get_color()
            self.marker = line.get_marker()
            self.markersize = line.get_markersize()
            self.markerfacecolor = line.get_markerfacecolor()
            self.markeredgecolor = line.get_markeredgecolor()

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

    def __init__(self, fname='validacija.ini'):
        self.fname = fname
        self._cfg = configparser.ConfigParser()
        self._cfg.read(self.fname)
        self.log = Konfig.Log(self._cfg['LOG_SETUP'])
        self.rest = Konfig.Rest(self._cfg['REST'])
        self.icons = Konfig.Icons(self._cfg['ICONS'])
        self.graf = {'KONC': {}}
        self.graf['KONC']['LDL'] = Konfig.Graph(self._cfg['KONC_LDL'])
        self.graf['KONC']['GOOD'] = Konfig.Graph(self._cfg['KONC_GOOD'])
        self.graf['KONC']['BAD'] = Konfig.Graph(self._cfg['KONC_BAD'])
        self.graf['KONC']['KOREKCIJA'] = Konfig.Graph(self._cfg['KONC_KOREKCIJA'])
        self.graf['KONC']['KOREKCIJA_BAD'] = Konfig.Graph(self._cfg['KONC_KOREKCIJA_BAD'])
        self.graf['KONC']['LEFT_LIMIT'] = Konfig.Graph(self._cfg['KONC_LEFT_LIMIT'])
        self.graf['KONC']['RIGHT_LIMIT'] = Konfig.Graph(self._cfg['KONC_RIGHT_LIMIT'])
        for zs in ['ZERO', 'SPAN']:
            self.graf[zs] = {}
            for komp in ['GOOD', 'BAD', 'LINE', 'KOREKCIJA', 'KOREKCIJA_BAD', 'TOP_LIMIT', 'LOW_LIMIT']:
                self.graf[zs][komp] = Konfig.Graph(self._cfg[zs + '_' + komp])
        self.development = False

    def save_to_file(self):
        for sec in self.graf:
            for sub in self.graf[sec]:
                for opt, val in self.graf[sec][sub].get_options().items():
                    self._cfg.set(sec + '_' + sub, opt, str(val))

        with open(self.fname, mode='w') as fajl:
            self._cfg.write(fajl)

    def get(self, section, option):
        return self._cfg.get(section, option)


config = Konfig()
