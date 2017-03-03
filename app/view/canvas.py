# -*- coding: utf-8 -*-
import datetime
import functools
import logging
import os

import matplotlib
import numpy as np
import pandas as pd
from PyQt4 import QtCore, QtGui
from matplotlib import gridspec
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt4agg import NavigationToolbar2QT as NavigationToolbar2
from matplotlib.figure import Figure
from matplotlib.widgets import SpanSelector

try:
    import matplotlib.backends.qt_editor.figureoptions as figureoptions
except ImportError as err:
    logging.error(str(err), exc_info=True)
    figureoptions = None


################################################################################
################################################################################
class ExpandedToolbar(NavigationToolbar2):
    """
    subklasa navigacijskog bara sa dodanim span select tool-om
    """
    toolitems = (
        ('Home', 'Reset original view', 'home', 'home'),
        ('Back', 'Back to  previous view', 'back', 'back'),
        ('Forward', 'Forward to next view', 'forward', 'forward'),
        (None, None, None, None),
        ('Toggle_span', 'Select horizontal span with left mouse', 'embed', 'toggle_span'),
        ('Pan', 'Pan axes with left mouse, zoom with right', 'move', 'pan'),
        ('Zoom', 'Zoom to rectangle', 'zoom_to_rect', 'zoom'),
        ('SpanZoom', 'Zoom horizontal region', 'horizontal zoom', 'toggle_hzoom'),
        (None, None, None, None),
        ('Subplots', 'Configure subplots', 'subplots', 'configure_subplots'),
        ('Save', 'Save the figure', 'filesave', 'save_figure'),
    )

    def __init__(self, canvas, parent, icon, callback, icon2, callback2, coordinates=False):
        """
        canvas - instanca canvasa povezanog sa toolbarom
        parent - parent toolbara
        icon - QtGui.QIcon ikona za span selector alat
        callback - funkcija koja radi span selection
        icon2 - QtGui.QIcon ikona za horizontalni span zoom alat
        callback2 - funkcija koja radi horizontalni span zoom
        """
        self.spanSelector = None
        self.spanSelectorIcon = icon
        self.spanSelectorCallback = callback
        self.spanZoomKonc = None
        self.spanZoomZero = None
        self.spanZoomSpan = None
        self.spanZoomIcon = icon2
        self.spanZoomCallback = callback2
        NavigationToolbar2.__init__(self, canvas, parent, coordinates=True)

    def pan(self, *args):
        """Activate the pan/zoom tool. pan with left button, zoom with right"""
        if self._active == 'PAN':
            self._active = None
            self.mode = ''
        else:
            self._active = 'PAN'
        if self._idPress is not None:
            self._idPress = self.canvas.mpl_disconnect(self._idPress)
            self.mode = ''
        if self._idRelease is not None:
            self._idRelease = self.canvas.mpl_disconnect(self._idRelease)
            self.mode = ''
        if self.spanSelector is not None:
            self.spanSelector = None
        if self.spanZoomKonc is not None:
            self.spanZoomKonc = None
            self.spanZoomZero = None
            self.spanZoomSpan = None
        if self._active:
            self._idPress = self.canvas.mpl_connect('button_press_event', self.press_pan)
            self._idRelease = self.canvas.mpl_connect('button_release_event', self.release_pan)
            self.mode = 'pan/zoom'
            # release span selector lock
            if self.canvas.widgetlock.isowner(self.spanSelector):
                self.canvas.widgetlock.release(self.spanSelector)
            self.canvas.widgetlock(self)
        else:
            self.canvas.widgetlock.release(self)
        for a in self.canvas.figure.get_axes():
            a.set_navigate_mode(self._active)
        self.set_message(self.mode)
        self._update_buttons_checked()

    def zoom(self, *args):
        """Activate zoom to rect mode"""
        if self._active == 'ZOOM':
            self._active = None
            self.mode = ''
        else:
            self._active = 'ZOOM'
        if self._idPress is not None:
            self._idPress = self.canvas.mpl_disconnect(self._idPress)
            self.mode = ''
        if self._idRelease is not None:
            self._idRelease = self.canvas.mpl_disconnect(self._idRelease)
            self.mode = ''
        if self.spanSelector is not None:
            self.spanSelector = None
        if self.spanZoomKonc is not None:
            self.spanZoomKonc = None
            self.spanZoomZero = None
            self.spanZoomSpan = None
        if self._active:
            self._idPress = self.canvas.mpl_connect('button_press_event', self.press_zoom)
            self._idRelease = self.canvas.mpl_connect('button_release_event', self.release_zoom)
            self.mode = 'zoom rect'
            # release span selector lock
            if self.canvas.widgetlock.isowner(self.spanSelector):
                self.canvas.widgetlock.release(self.spanSelector)
            self.canvas.widgetlock(self)
        else:
            self.canvas.widgetlock.release(self)
        for a in self.canvas.figure.get_axes():
            a.set_navigate_mode(self._active)
        self.set_message(self.mode)
        self._update_buttons_checked()

    def toggle_span(self):
        if self._active == 'SPAN':
            self._active = None
            self.mode = ''
        else:
            self._active = 'SPAN'
        if self._idPress is not None:
            self._idPress = self.canvas.mpl_disconnect(self._idPress)
            self.mode = ''
        if self._idRelease is not None:
            self._idRelease = self.canvas.mpl_disconnect(self._idRelease)
            self.mode = ''
        if self.spanSelector is not None:
            self.spanSelector = None
        if self.spanZoomKonc is not None:
            self.spanZoomKonc = None
            self.spanZoomZero = None
            self.spanZoomSpan = None
        if self._active:
            self.spanSelector = SpanSelector(self.canvas.axesC,
                                             self.spanSelectorCallback,
                                             direction='horizontal',
                                             button=1,
                                             useblit=True,
                                             rectprops=dict(alpha=0.3, facecolor='yellow'))
            self.mode = 'horizontal span selection'
            self.canvas.widgetlock.release(self)  # release other locks
            self.canvas.widgetlock.available(self.spanSelector)  # lock selector
        else:
            self.canvas.widgetlock.release(self.spanSelector)
        for a in self.canvas.figure.get_axes():
            a.set_navigate_mode(self._active)
        self.set_message(self.mode)
        self._update_buttons_checked()

    def toggle_hzoom(self):
        # push original view to stack if stack is empty
        if self._views.empty():
            self.push_current()
        if self._active == 'HZOOM':
            self._active = None
            self.mode = ''
        else:
            self._active = 'HZOOM'
        if self._idPress is not None:
            self._idPress = self.canvas.mpl_disconnect(self._idPress)
            self.mode = ''
        if self._idRelease is not None:
            self._idRelease = self.canvas.mpl_disconnect(self._idRelease)
            self.mode = ''
        if self.spanSelector is not None:
            self.spanSelector = None
        if self.spanZoomKonc is not None:
            self.spanZoomKonc = None
            self.spanZoomZero = None
            self.spanZoomSpan = None
        if self._active:
            self.spanZoomKonc = SpanSelector(self.canvas.axesC,
                                             self.spanZoomCallback,
                                             direction='horizontal',
                                             button=1,
                                             useblit=True,
                                             rectprops=dict(alpha=0.3, facecolor='orange'))

            self.spanZoomZero = SpanSelector(self.canvas.axesZ,
                                             self.spanZoomCallback,
                                             direction='horizontal',
                                             button=1,
                                             useblit=True,
                                             rectprops=dict(alpha=0.3, facecolor='orange'))

            self.spanZoomSpan = SpanSelector(self.canvas.axesS,
                                             self.spanZoomCallback,
                                             direction='horizontal',
                                             button=1,
                                             useblit=True,
                                             rectprops=dict(alpha=0.3, facecolor='orange'))
            self.mode = 'zoom to selected region'
            self.canvas.widgetlock.release(self)  # release other locks
            # release span Selector lock
            if self.canvas.widgetlock.isowner(self.spanSelector):
                self.canvas.widgetlock.release(self.spanSelector)
        else:
            self.canvas.widgetlock.release(self)
        for a in self.canvas.figure.get_axes():
            a.set_navigate_mode(self._active)
        self.set_message(self.mode)
        self._update_buttons_checked()

    def _update_buttons_checked(self):
        # sync button checkstates to match active mode
        self._actions['pan'].setChecked(self._active == 'PAN')
        self._actions['zoom'].setChecked(self._active == 'ZOOM')
        self._actions['toggle_span'].setChecked(self._active == 'SPAN')
        self._actions['toggle_hzoom'].setChecked(self._active == 'HZOOM')
        if self._active:
            self.canvas.set_tools_in_use(True)
        else:
            self.canvas.set_tools_in_use(False)

    def _init_toolbar(self):
        self.basedir = os.path.join(matplotlib.rcParams['datapath'], 'images')
        for text, tooltip_text, image_file, callback in self.toolitems:
            if text is None:
                self.addSeparator()
            elif text == 'Toggle_span':
                a = self.addAction(self.spanSelectorIcon, text, getattr(self, callback))
                a.setCheckable(True)
                a.setToolTip(tooltip_text)
                self._actions[callback] = a
            elif text == 'SpanZoom':
                a = self.addAction(self.spanZoomIcon, text, getattr(self, callback))
                a.setCheckable(True)
                a.setToolTip(tooltip_text)
                self._actions[callback] = a
            else:
                ikona = self._icon(image_file + '.png')
                a = self.addAction(ikona, text, getattr(self, callback))
                self._actions[callback] = a
                if callback in ['zoom', 'pan']:
                    a.setCheckable(True)
                if tooltip_text is not None:
                    a.setToolTip(tooltip_text)
        if figureoptions is not None:
            a = self.addAction(self._icon("qt4_editor_options.png"),
                               'Customize', self.edit_parameters)
            a.setToolTip('Edit curves line and axes parameters')
        self.buttons = {}
        # Add the x,y location widget at the right side of the toolbar
        # The stretch factor is 1 which means any resizing of the toolbar
        # will resize this label instead of the buttons.
        if self.coordinates:
            self.locLabel = QtGui.QLabel("", self)
            self.locLabel.setAlignment(
                QtCore.Qt.AlignRight | QtCore.Qt.AlignTop)
            self.locLabel.setSizePolicy(
                QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding,
                                  QtGui.QSizePolicy.Ignored))
            labelAction = self.addWidget(self.locLabel)
            labelAction.setVisible(True)
        # reference holder for subplots_adjust window
        self.adj_window = None

    if figureoptions is not None:
        def edit_parameters(self):
            allaxes = self.canvas.figure.get_axes()
            if len(allaxes) == 1:
                axes = allaxes[0]
            else:
                titles = []
                for axes in allaxes:
                    title = axes.get_title()
                    ylabel = axes.get_ylabel()
                    if title:
                        fmt = "%(title)s"
                        if ylabel:
                            fmt += ": %(ylabel)s"
                        fmt += " (%(axes_repr)s)"
                    elif ylabel:
                        fmt = "%(axes_repr)s (%(ylabel)s)"
                    elif hasattr(axes, "_CUSTOM_NAME"):
                        fmt = "%(CUSTOM_NAME)s"
                    else:
                        fmt = "%(axes_repr)s"
                    titles.append(fmt % dict(title=title,
                                             ylabel=ylabel,
                                             axes_repr=repr(axes),
                                             CUSTOM_NAME=axes._CUSTOM_NAME))
                item, ok = QtGui.QInputDialog.getItem(self, 'Customize',
                                                      'Select axes:', titles,
                                                      0, False)
                if ok:
                    axes = allaxes[titles.index(str(item))]
                else:
                    return
            figureoptions.figure_edit(axes, self)

    def clear_and_push_image_to_zoom_stack(self):
        """clear zoom stack and push current image (home)"""
        self._views.clear()
        self.push_current()


################################################################################
################################################################################
class Kanvas(FigureCanvas):
    def __init__(self, graf_opcije, parent=None, width=12, height=6, dpi=100):
        """
        Kanvas za grafove
        Span, Zero, Koncentracija...
        """
        self.cfgGraf = graf_opcije
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        FigureCanvas.__init__(self, self.fig)
        FigureCanvas.setSizePolicy(
            self,
            QtGui.QSizePolicy.Expanding,
            QtGui.QSizePolicy.Expanding)
        self.setParent(parent)
        # gridspec layout subplotova
        self.gs = gridspec.GridSpec(3, 1, height_ratios=[1, 1, 4])
        # defiincija pojedinih subplotova
        self.axesC = self.fig.add_subplot(self.gs[2, 0])  # koncentracija
        self.axesS = self.fig.add_subplot(self.gs[0, 0], sharex=self.axesC)  # span
        self.axesZ = self.fig.add_subplot(self.gs[1, 0], sharex=self.axesC)  # zero
        self.axesC._CUSTOM_NAME = 'Graf koncentracija'
        self.axesZ._CUSTOM_NAME = 'Graf zero'
        self.axesS._CUSTOM_NAME = 'Graf span'
        # hide x labele za zero i span axes
        self.axesS.xaxis.set_visible(False)
        self.axesZ.xaxis.set_visible(False)
        # prebaci labele srednjeg grafa na desno
        self.axesZ.yaxis.tick_right()
        # podesi spacing izmedju axesa (sljepi grafove)
        self.fig.subplots_adjust(wspace=0.001, hspace=0.001)
        # update geometriju postavi opciju za custom kontekstni meni
        FigureCanvas.updateGeometry(self)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)

        # bitni memberi
        self.koncModel = None  # model sa podacima koncentracije
        self.zeroModel = None  # model sa podacima zero
        self.spanModel = None  # model sa podacima span

        # staus grafa i alata
        self.isDrawn = False
        self.isGridDrawn = True
        self.isLegendDrawn = False
        self.otherToolsInUse = False
        self.isKoncGrafActive = True
        self.isZeroGrafActive = False
        self.isSpanGrafActive = False
        self._polyBin = []  # bin sa nacrtanim spanovima (losi zero i span poligoni)
        # elementi za konc graf
        self.linije = {
            'KONC': {
                'GOOD': None,
                'BAD': None,
                'LDL': None,
                'KOREKCIJA': None,
                'KOREKCIJA_BAD': None,
                'LEFT_LIMIT': None,
                'RIGHT_LIMIT': None},
            'ZERO': {
                'GOOD': None,
                'BAD': None,
                'LINE': None,
                'KOREKCIJA': None,
                'KOREKCIJA_BAD': None,
                'TOP_LIMIT': None,
                'LOW_LIMIT': None},
            'SPAN': {
                'GOOD': None,
                'BAD': None,
                'LINE': None,
                'KOREKCIJA': None,
                'KOREKCIJA_BAD': None,
                'TOP_LIMIT': None,
                'LOW_LIMIT': None}}

        # interakcija sa grafom (kontekstni meni, pick vrijednosti, scroll zoom)
        self.pickCid = self.mpl_connect('button_press_event', self.on_pick)
        self.scrollZoomCid = self.mpl_connect('scroll_event', self.scroll_zoom_along_x)

    def set_axes_focus(self, tip='koncentracija'):
        if tip == 'span':
            self.gs.set_height_ratios([4, 1, 1])
            self.isKoncGrafActive = False
            self.isZeroGrafActive = False
            self.isSpanGrafActive = True
        elif tip == 'zero':
            self.gs.set_height_ratios([1, 4, 1])
            self.isKoncGrafActive = False
            self.isZeroGrafActive = True
            self.isSpanGrafActive = False
        else:
            self.gs.set_height_ratios([1, 1, 4])
            self.isKoncGrafActive = True
            self.isZeroGrafActive = False
            self.isSpanGrafActive = False
        # redraw legendu ako je nacrtana za novi aktivni graf
        self.draw_legend(self.isLegendDrawn)
        self.fig.tight_layout()
        # podesi spacing izmedju axesa (sljepi grafove)
        self.fig.subplots_adjust(wspace=0.001, hspace=0.001)
        self.draw()

    def set_models(self, konc, zero, span):
        """glavna metoda kod promjene kanala, crta, updejta navigation toolbar..."""
        self.koncModel = konc
        self.zeroModel = zero
        self.spanModel = span
        self.crtaj(rend=True)

    def clear_graf(self):
        self.blockSignals(True)
        self.axesC.clear()
        self.axesZ.clear()
        self.axesS.clear()
        self.blockSignals(False)
        self.draw()
        self.isDrawn = False

    def draw_legend(self, toggle):
        self.isLegendDrawn = toggle
        # all legends
        ite = zip([self.axesC, self.axesS, self.axesZ],
                  [self.isKoncGrafActive, self.isSpanGrafActive, self.isZeroGrafActive])
        for i, j in ite:
            i.legend(fontsize=8, loc='center left', bbox_to_anchor=(1, 0.5))
            i.get_legend().draggable(state=True)
            stejt = toggle and j
            i.get_legend().set_visible(stejt)
        # display legend for graph
        self.draw()

    def draw_grid(self, toggle):
        self.isGridDrawn = toggle
        if toggle:
            for i in [self.axesC, self.axesS, self.axesZ]:
                i.grid(which='major', color='black', linestyle='--',
                       linewidth='0.3', alpha=0.7)
                i.grid(which='minor', color='black', linestyle=':',
                       linewidth='0.2', alpha=0.5)
                i.minorticks_on()
        else:
            for i in [self.axesC, self.axesS, self.axesZ]:
                i.grid(False)
                i.minorticks_off()
        self.draw()

    def get_prosirene_x_granice(self, tmin, tmax, t=120):
        """
        Funkcija 'pomice' rubove intervala [tmin, tmax] na [tmin-t, tmax+t].
        -> t je integer, broj minuta
        -> tmin, tmax su pandas timestampovi (pandas.tslib.Timestamp)
        izlazne vrijednosti su 2 'pomaknuta' pandas timestampa
        """
        tmin = tmin - datetime.timedelta(minutes=t)
        tmax = tmax + datetime.timedelta(minutes=t)
        tmin = pd.to_datetime(tmin)
        tmax = pd.to_datetime(tmax)
        return [tmin, tmax]

    def autoscale_y_os(self):
        try:
            if self.isDrawn:
                xmin, xmax = self.axesC.get_xlim()
                baseymin, baseymax = self.axesC.get_ylim()
                t1 = self.matplotlib_time_to_pandas_timestamp(xmin, roundSec=60)
                t2 = self.matplotlib_time_to_pandas_timestamp(xmax, roundSec=60)
                # koncentracija autoscale
                modelymin, modelymax = self.koncModel.get_autoscale_y_range(t1, t2)
                if np.isnan(modelymin):
                    ymin = baseymin
                else:
                    ymin = modelymin
                if np.isnan(modelymax):
                    ymax = baseymax
                else:
                    ymax = modelymax
                spejsing = (ymax - ymin) / 10  # (10% raspona sa svake strane)
                self.axesC.set_ylim((ymin - spejsing, ymax + spejsing))
                # zero autoscale
                modelymin, modelymax = self.zeroModel.get_autoscale_y_range(t1, t2)
                if np.isnan(modelymin):
                    ymin = baseymin
                else:
                    ymin = modelymin
                if np.isnan(modelymax):
                    ymax = baseymax
                else:
                    ymax = modelymax
                spejsing = (ymax - ymin) / 5  # (20% raspona sa svake strane)
                self.axesZ.set_ylim((ymin - spejsing, ymax + spejsing))
                # span autoscale
                modelymin, modelymax = self.spanModel.get_autoscale_y_range(t1, t2)
                if np.isnan(modelymin):
                    ymin = baseymin
                else:
                    ymin = modelymin
                if np.isnan(modelymax):
                    ymax = baseymax
                else:
                    ymax = modelymax
                spejsing = (ymax - ymin) / 5  # (20% raspona sa svake strane)
                self.axesS.set_ylim((ymin - spejsing, ymax + spejsing))
            else:
                pass
        except Exception as ex:
            # do not autoscale y..
            logging.error(str(ex), exc_info=True)
            pass

    def crtaj_zero_span(self, frame, zs, axis):
        linije = self.linije[zs]
        indeks = list(frame.index)
        ok = frame[(frame['vrijednost'] <= frame['maxDozvoljeno']) &
                   (frame['vrijednost'] >= frame['minDozvoljeno'])]
        bad = frame[(frame['vrijednost'] > frame['maxDozvoljeno']) |
                    (frame['vrijednost'] < frame['minDozvoljeno'])]
        korekcijaOk = frame[(frame['korekcija'] <= frame['maxDozvoljeno']) &
                            (frame['korekcija'] >= frame['minDozvoljeno'])]
        korekcijaBad = frame[(frame['korekcija'] > frame['maxDozvoljeno']) |
                             (frame['korekcija'] < frame['minDozvoljeno'])]
        ok = ok.reindex(indeks)
        bad = bad.reindex(indeks)
        korekcijaOk = korekcijaOk.reindex(indeks)
        korekcijaOk = korekcijaOk.reindex(indeks)
        korekcijaBad = korekcijaBad.reindex(indeks)
        ok = list(ok['vrijednost'].astype(float))
        bad = list(bad['vrijednost'].astype(float))
        korekcijaOk = list(korekcijaOk['korekcija'].astype(float))
        korekcijaBad = list(korekcijaBad['korekcija'].astype(float))
#        for pl in ['TOP_LIMIT', 'LOW_LIMIT', 'LINE', 'GOOD', 'BAD', 'KOREKCIJA', 'KOREKCIJA_BAD']:

        self.plotX(axis, indeks, frame['minDozvoljeno'].astype(float), zs, 'LOW_LIMIT')
        self.plotX(axis, indeks, frame['vrijednost'].astype(float), zs, 'LINE')
        self.plotX(axis, indeks, ok, zs, 'GOOD')
        self.plotX(axis, indeks, bad, zs, 'BAD')
        self.plotX(axis, indeks, korekcijaOk, zs, 'KOREKCIJA')
        self.plotX(axis, indeks, korekcijaBad, zs, 'KOREKCIJA_BAD')

    def crtaj_zero(self):
        frame = self.zeroModel.datafrejm
        axis = self.axesZ
        self.axesZ.axhline(0.0,
                           label='0 line',
                           color='black')
        self.crtaj_zero_span(frame, 'ZERO', axis)

    def crtaj_span(self):
        frame = self.spanModel.datafrejm
        axis = self.axesS
        self.crtaj_zero_span(frame, 'SPAN', axis)

    def crtaj_koncentracija(self):
        ##### priprema podataka za crtanje koncentracija #####
        frame = self.koncModel.datafrejm
        linije = self.linije['KONC']
        cfg = self.cfgGraf['KONC']
        axis = self.axesC

        indeks = list(frame.index)

        ok = frame[frame['flag'] > 0]
        bad = frame[frame['flag'] < 0]
        # losa korekcija za los flag takodjer
        korekcijaOk = frame[(frame['korekcija'] >= frame['LDL']) & (frame['flag'] >= 0)]
        korekcijaBad = frame[(frame['korekcija'] < frame['LDL']) | (frame['flag'] < 0)]
        # count korektiranih manjih od 0 i manjih od ldl
        korektirani_manji_od_nule = frame[frame['korekcija'] < 0].count()['korekcija']
        korektirani_manji_od_LDL = korekcijaBad.count()['korekcija']
        broj_dobrih_mjerenja = ok.count()['vrijednost']
        broj_dobrih_korektiranih = korekcijaOk.count()['korekcija']
        # reindex
        ok = ok.reindex(indeks)
        bad = bad.reindex(indeks)
        korekcijaOk = korekcijaOk.reindex(indeks)
        korekcijaBad = korekcijaBad.reindex(indeks)
        # samo stupci od interesa
        ok = list(ok['vrijednost'].astype(float))
        bad = list(bad['vrijednost'].astype(float))
        korekcijaOk = list(korekcijaOk['korekcija'].astype(float))
        korekcijaBad = list(korekcijaBad['korekcija'].astype(float))

        self.xlim_original = self.get_prosirene_x_granice(indeks[0], indeks[-1], t=120)
        self.axesC.set_xlim(self.xlim_original)

        # signlaiziraj update labela za obuhvat...
        mapa = {'ocekivano': len(indeks),
                'broj_mjerenja': broj_dobrih_mjerenja,
                'broj_korektiranih': broj_dobrih_korektiranih,
                'ispod_nula': korektirani_manji_od_nule,
                'ispod_LDL': korektirani_manji_od_LDL}

        self.emit(QtCore.SIGNAL('update_data_point_count(PyQt_PyObject)'), mapa)

        axis.axhline(0.0,
                     label='0 line',
                     color='black')

        self.plotVline(axis, indeks[0], 'KONC',  'LEFT_LIMIT')
        self.plotVline(axis, indeks[-1], 'KONC',  'RIGHT_LIMIT')
        self.plotX(axis, indeks, frame['LDL'].astype(float), 'KONC','LDL')
        self.plotX(axis, indeks, ok, 'KONC', 'GOOD')
        self.plotX(axis, indeks, bad, 'KONC', 'BAD')
        self.plotX(axis, indeks, korekcijaOk, 'KONC','KOREKCIJA')
        self.plotX(axis, indeks, korekcijaBad, 'KONC','KOREKCIJA_BAD')


    def plotVline(self, axis, indeks, section, subsection):
        self.cfgGraf[section][subsection].postavi_opcije(self.linije[section][subsection])
        self.linije[section][subsection] = axis.axvline(
            indeks,
            label=self.cfgGraf[section][subsection].label,
            linestyle=self.cfgGraf[section][subsection].linestyle,
            drawstyle=self.cfgGraf[section][subsection].drawstyle,
            linewidth=self.cfgGraf[section][subsection].linewidth,
            color=self.cfgGraf[section][subsection].color,
            marker=self.cfgGraf[section][subsection].marker,
            markersize=self.cfgGraf[section][subsection].markersize,
            markerfacecolor=self.cfgGraf[section][subsection].markerfacecolor,
            markeredgecolor=self.cfgGraf[section][subsection].markeredgecolor)

    def plotX(self, axis, indeks, c, section, subsection):
        self.cfgGraf[section][subsection].postavi_opcije(self.linije[section][subsection])
        self.linije[section][subsection], = axis.plot(
            indeks,
            c,
            label=self.cfgGraf[section][subsection].label,
            linestyle=self.cfgGraf[section][subsection].linestyle,
            drawstyle=self.cfgGraf[section][subsection].drawstyle,
            linewidth=self.cfgGraf[section][subsection].linewidth,
            color=self.cfgGraf[section][subsection].color,
            marker=self.cfgGraf[section][subsection].marker,
            markersize=self.cfgGraf[section][subsection].markersize,
            markerfacecolor=self.cfgGraf[section][subsection].markerfacecolor,
            markeredgecolor=self.cfgGraf[section][subsection].markeredgecolor)

    def sjencaj_lose_zero_span(self):
        """sjencanje losih zero i span raspona"""
        # spanovi za zero i span koji nisu u redu
        badRasponiZero = self.zeroModel.rasponi
        badRasponiSpan = self.spanModel.rasponi

        # clear all raspone
        for poly in self._polyBin:
            try:
                poly.remove()
            except Exception:
                pass
        self._polyBin = []

        for xmin, xmax in badRasponiZero:
            # returns matplotlib.patches.Polygon, grab instance and remove... by running .remove()
            self._polyBin.append(self.axesZ.axvspan(xmin, xmax, facecolor='red', alpha=0.2))
            self._polyBin.append(self.axesC.axvspan(xmin, xmax, facecolor='red', alpha=0.2))

        for xmin, xmax in badRasponiSpan:
            self._polyBin.append(self.axesS.axvspan(xmin, xmax, facecolor='red', alpha=0.2))
            self._polyBin.append(self.axesC.axvspan(xmin, xmax, facecolor='red', alpha=0.2))

    def get_current_x_zoom(self):
        return self.axesC.get_xlim()

    def set_current_x_zoom(self, x):
        self.axesC.set_xlim(x)
        self.autoscale_y_os()
        self.draw()

    def crtaj(self, rend=True):
        # spremi postavke grafa
        #        self.save_current_display_options()

        # clear grafove
        self.clear_graf()

        # crtaj koncentraciju
        self.crtaj_koncentracija()
        # crtaj zero
        self.crtaj_zero()
        # crtaj span
        self.crtaj_span()

        # rotate date labele x osi
        allXLabels = self.axesC.get_xticklabels()
        for label in allXLabels:
            label.set_rotation(30)
            label.set_fontsize(8)

        # autoskaliranje y osi za sve grafove
        self.autoscale_y_os()

        # shading losih zero/span raspona
        self.sjencaj_lose_zero_span()

        # redraw
        if rend:
            self.fig.tight_layout()
            # podesi spacing izmedju axesa (sljepi grafove)
            self.fig.subplots_adjust(wspace=0.001, hspace=0.001)
            self.draw()
            self.isDrawn = True

    def on_pick(self, event):
        # mora biti nacrtan, unutar osi i drugi alati moraju biti ugaseni
        if self.isDrawn and event.inaxes in [self.axesC, self.axesZ, self.axesS] and not self.otherToolsInUse:
            if event.button == 1:
                # left click
                vrijeme = matplotlib.dates.num2date(event.xdata).replace(tzinfo=None)
                self.emit(QtCore.SIGNAL('klik_na_grafu(PyQt_PyObject)'), vrijeme)
                if event.inaxes == self.axesC:
                    self.emit(QtCore.SIGNAL('table_select_podatak(PyQt_PyObject)'), vrijeme)
            elif event.button == 3 and not self.otherToolsInUse:
                # right click
                xpoint = self.adaptiraj_tocku_od_pick_eventa(event)
                loc = QtGui.QCursor.pos()
                self.show_context_menu(loc, xpoint, xpoint, 'click')

    def span_select(self, xmin, xmax):
        if self.isDrawn:
            # konverzija ulaznih vrijednosti u pandas timestampove
            t1 = self.matplotlib_time_to_pandas_timestamp(xmin, roundSec=60)
            t2 = self.matplotlib_time_to_pandas_timestamp(xmax, roundSec=60)
            # osiguranje da se ne preskoce granice glavnog kanala (izbjegavanje index errora)
            if t1 < self.xlim_original[0]:
                t1 = self.xlim_original[0]
            if t1 > self.xlim_original[1]:
                t1 = self.xlim_original[1]
            if t2 < self.xlim_original[0]:
                t2 = self.xlim_original[0]
            if t2 > self.xlim_original[1]:
                t2 = self.xlim_original[1]
            # tocke ne smiju biti iste (izbjegavamo paljenje dijaloga na ljevi klik)
            if t1 != t2:
                # pronadji lokaciju desnog klika u Qt kooridinatama.
                loc = QtGui.QCursor.pos()
                self.show_context_menu(loc, t1, t2, 'span')  # poziv kontekstnog menija

    def matplotlib_time_to_pandas_timestamp(self, x, roundSec=None):
        t = matplotlib.dates.num2date(x)
        t = datetime.datetime(t.year, t.month, t.day, t.hour, t.minute, t.second)
        if roundSec:
            t = self.zaokruzi_vrijeme(t, roundSec)
        t = pd.to_datetime(t)
        return t

    def span_zoom(self, xmin, xmax):
        if self.isDrawn:
            # konverzija ulaznih vrijednosti u pandas timestampove
            t1 = self.matplotlib_time_to_pandas_timestamp(xmin)
            t2 = self.matplotlib_time_to_pandas_timestamp(xmax)
            # rotate min, max order po potrebi
            if t1 > t2:
                t1, t2 = t2, t1
            # tocke ne smiju biti iste
            if t1 != t2:
                self.axesC.set_xlim((t1, t2))
                self.autoscale_y_os()
                self.draw()
            # push the drawn image to toolbar zoom stack
            self.emit(QtCore.SIGNAL('push_view_to_toolbar_zoom_stack'))

    def scroll_zoom_along_x(self, event):
        try:
            xmin, xmax = self.axesC.get_xlim()
            skala = 1.1
            xdata = event.xdata
            if event.button == 'up':
                faktor = 1 / skala
            elif event.button == 'down':
                faktor = skala
            else:
                faktor = 1
                logging.error('invalid scroll value')
            left = (xdata - xmin) * faktor
            right = (xmax - xdata) * faktor

            x1 = xdata - left
            x2 = xdata + right
            self.axesC.set_xlim((x1, x2))
            self.autoscale_y_os()
            self.draw()
            # push the drawn image to toolbar zoom stack
            self.emit(QtCore.SIGNAL('push_view_to_toolbar_zoom_stack'))
        except Exception as ex:
            logging.error(str(ex))

    def adaptiraj_tocku_od_pick_eventa(self, event):
        xpoint = matplotlib.dates.num2date(event.xdata)  # datetime.datetime
        # problem.. rounding offset aware i offset naive datetimes..workaround
        xpoint = datetime.datetime(xpoint.year,
                                   xpoint.month,
                                   xpoint.day,
                                   xpoint.hour,
                                   xpoint.minute,
                                   xpoint.second)
        # xpoint = self.zaokruzi_vrijeme(xpoint, 60)
        if event.inaxes == self.axesC:
            xpoint = self.zaokruzi_vrijeme(xpoint, self.koncModel.timestep)
        else:
            xpoint = self.zaokruzi_vrijeme(xpoint, 60)
        # konverzija iz datetime.datetime objekta u pandas.tislib.Timestamp
        xpoint = pd.to_datetime(xpoint)
        # pazimo da x vrijednost ne iskace od zadanih granica
        if xpoint >= self.xlim_original[1]:
            xpoint = self.xlim_original[1]
        if xpoint <= self.xlim_original[0]:
            xpoint = self.xlim_original[0]
        return xpoint

    def zaokruzi_vrijeme(self, dt_objekt, nSekundi):
        tmin = datetime.datetime.min
        delta = (dt_objekt - tmin).seconds
        zaokruzeno = ((delta + (nSekundi / 2)) // nSekundi) * nSekundi
        izlaz = dt_objekt + datetime.timedelta(0, zaokruzeno - delta, -dt_objekt.microsecond)
        return izlaz

    def show_context_menu(self, pos, tmin, tmax, tip):
        # zapamti rubna vremena intervala, trebati ce za druge metode
        self.__lastTimeMin = tmin
        self.__lastTimeMax = tmax
        # definiraj menu i
        menu = QtGui.QMenu(self)
        menu.setTitle('Menu')
        # definiranje akcija
        action1 = QtGui.QAction("Flag: dobar", menu)
        action2 = QtGui.QAction("Flag: los", menu)
        # slaganje akcija u menu
        menu.addAction(action1)
        menu.addAction(action2)
        action1.triggered.connect(functools.partial(self.promjena_flaga, flag=1000))
        action2.triggered.connect(functools.partial(self.promjena_flaga, flag=-1000))
        if tip != 'span':
            action3 = QtGui.QAction("show koncentracija", menu)
            action3.setCheckable(True)
            action3.setChecked(self.linije['KONC']['GOOD'].get_visible())
            action4 = QtGui.QAction("show korekcija", menu)
            action4.setCheckable(True)
            action4.setChecked(self.linije['KONC']['KOREKCIJA'].get_visible())
            action5 = QtGui.QAction("show legend", menu)
            action5.setCheckable(True)
            action5.setChecked(self.isLegendDrawn)
            action6 = QtGui.QAction("toggle grid", menu)
            action6.setCheckable(True)
            action6.setChecked(self.isGridDrawn)
            action7 = QtGui.QAction("focus span", menu)
            action7.setCheckable(True)
            action7.setChecked(self.isSpanGrafActive)
            action8 = QtGui.QAction("focus zero", menu)
            action8.setCheckable(True)
            action8.setChecked(self.isZeroGrafActive)
            action9 = QtGui.QAction("focus koncentracija", menu)
            action9.setCheckable(True)
            action9.setChecked(self.isKoncGrafActive)
            menu.addSeparator()
            menu.addAction(action3)
            menu.addAction(action4)
            menu.addAction(action5)
            menu.addAction(action6)
            menu.addSeparator()
            menu.addAction(action7)
            menu.addAction(action8)
            menu.addAction(action9)
            # povezi akcije menua sa metodama
            action3.triggered.connect(functools.partial(self.toggle_visibility_callbacks, label='koncentracija'))
            action4.triggered.connect(functools.partial(self.toggle_visibility_callbacks, label='korekcija'))
            action5.triggered.connect(functools.partial(self.toggle_visibility_callbacks, label='legenda'))
            action6.triggered.connect(functools.partial(self.toggle_visibility_callbacks, label='grid'))
            action7.triggered.connect(functools.partial(self.set_axes_focus, tip='span'))
            action8.triggered.connect(functools.partial(self.set_axes_focus, tip='zero'))
            action9.triggered.connect(functools.partial(self.set_axes_focus, tip='koncentracija'))
        # prikazi menu na definiranoj tocki grafa
        menu.popup(pos)

    def toggle_visibility_callbacks(self, label='banana'):
        if label == 'koncentracija':
            self.linije['KONC']['GOOD'].set_visible(not self.linije['KONC']['GOOD'].get_visible())
            self.linije['KONC']['BAD'].set_visible(not self.linije['KONC']['BAD'].get_visible())
            self.linije['ZERO']['GOOD'].set_visible(not self.linije['ZERO']['GOOD'].get_visible())
            self.linije['ZERO']['BAD'].set_visible(not self.linije['ZERO']['BAD'].get_visible())
            self.linije['SPAN']['GOOD'].set_visible(not self.linije['SPAN']['GOOD'].get_visible())
            self.linije['SPAN']['BAD'].set_visible(not self.linije['SPAN']['BAD'].get_visible())
        elif label == 'korekcija':
            self.linije['KONC']['KOREKCIJA_GOOD'].set_visible(not self.linije['KONC']['KOREKCIJA_GOOD'].get_visible())
            self.linije['KONC']['KOREKCIJA_BAD'].set_visible(not self.linije['KONC']['KOREKCIJA_BAD'].get_visible())
            self.linije['ZERO']['KOREKCIJA_GOOD'].set_visible(not self.linije['ZERO']['KOREKCIJA_GOOD'].get_visible())
            self.linije['ZERO']['KOREKCIJA_BAD'].set_visible(not self.linije['ZERO']['KOREKCIJA_BAD'].get_visible())
            self.linije['SPAN']['KOREKCIJA_GOOD'].set_visible(not self.linije['SPAN']['KOREKCIJA_GOOD'].get_visible())
            self.linije['SPAN']['KOREKCIJA_BAD'].set_visible(not self.linije['SPAN']['KOREKCIJA_BAD'].get_visible())
        elif label == 'legenda':
            self.draw_legend(not self.isLegendDrawn)
        elif label == 'grid':
            if self.isGridDrawn:
                self.draw_grid(False)
            else:
                self.draw_grid(True)
        else:
            pass
        self.draw()

    def promjena_flaga(self, flag=1):
        """Metoda sluzi za promjenu flaga."""
        tmin = self.__lastTimeMin
        tmax = self.__lastTimeMax
        arg = {'od': tmin,
               'do': tmax,
               'noviFlag': flag}
        self.koncModel.promjeni_flag(arg)
        # zapamti current view
        curzumx = self.axesC.get_xlim()
        curzumy = self.axesC.get_ylim()
        # clear koncentracijski axes and redraw
        self.axesC.clear()
        self.isDrawn = False
        self.crtaj_koncentracija()
        self.sjencaj_lose_zero_span()
        # restore view
        self.axesC.set_xlim(curzumx)
        self.axesC.set_ylim(curzumy)
        self.draw()
        self.isDrawn = True

    def set_tools_in_use(self, x):
        """True ako su aktivni alati u navigacijskom baru, False inace"""
        self.otherToolsInUse = x


################################################################################
################################################################################
class GrafDisplayWidget(QtGui.QWidget):
    def __init__(self, iconSpan, iconZoom, graf_opcije, parent=None):
        QtGui.QWidget.__init__(self, parent=parent)
        self.cfgGraf = graf_opcije
        self.pixSpan = QtGui.QPixmap(24, 24)
        self.pixSpan.load(iconSpan)
        self.iconSpan = QtGui.QIcon(self.pixSpan)
        self.pixZoom = QtGui.QPixmap(24, 24)
        self.pixZoom.load(iconZoom)
        self.iconZoom = QtGui.QIcon(self.pixZoom)

        lay = QtGui.QVBoxLayout()

        # create a figure
        self.figure_canvas = Kanvas(self.cfgGraf)
        self.figure_canvas.setFocusPolicy(QtCore.Qt.ClickFocus)
        self.figure_canvas.setFocus()

        # add a navigation toolbar
        self.navigation_toolbar = ExpandedToolbar(self.figure_canvas,
                                                  self,
                                                  self.iconSpan,
                                                  self.figure_canvas.span_select,
                                                  self.iconZoom,
                                                  self.figure_canvas.span_zoom)

        lay.addWidget(self.navigation_toolbar)
        lay.addWidget(self.figure_canvas)

        self.setLayout(lay)

        # connections
        self.connect(self.figure_canvas,
                     QtCore.SIGNAL('push_view_to_toolbar_zoom_stack'),
                     self.navigation_toolbar.push_current)

    def get_xzoom_range(self):
        return self.figure_canvas.get_current_x_zoom()

    def set_xzoom_range(self, x):
        self.figure_canvas.set_current_x_zoom(x)

    def crtaj(self, rend=True):
        xraspon = self.get_xzoom_range()
        self.figure_canvas.crtaj(rend=rend)
        self.navigation_toolbar.clear_and_push_image_to_zoom_stack()
        self.set_xzoom_range(xraspon)

    def set_models(self, konc, zero, span):
        self.figure_canvas.set_models(konc, zero, span)
        self.navigation_toolbar.clear_and_push_image_to_zoom_stack()

################################################################################
################################################################################
