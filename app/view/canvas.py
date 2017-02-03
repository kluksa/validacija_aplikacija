# -*- coding: utf-8 -*-
import os
import logging
import datetime
import functools
import numpy as np
import pandas as pd
from PyQt4 import QtCore, QtGui
import matplotlib
from matplotlib import gridspec
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt4agg import NavigationToolbar2QT as NavigationToolbar2
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
            #release span selector lock
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
            #release span selector lock
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
            self.canvas.widgetlock.release(self) #release other locks
            self.canvas.widgetlock.available(self.spanSelector) #lock selector
        else:
            self.canvas.widgetlock.release(self.spanSelector)
        for a in self.canvas.figure.get_axes():
            a.set_navigate_mode(self._active)
        self.set_message(self.mode)
        self._update_buttons_checked()

    def toggle_hzoom(self):
        #push original view to stack if stack is empty
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
            self.canvas.widgetlock.release(self) #release other locks
            #release span Selector lock
            if self.canvas.widgetlock.isowner(self.spanSelector):
                self.canvas.widgetlock.release(self.spanSelector)
        else:
            self.canvas.widgetlock.release(self)
        for a in self.canvas.figure.get_axes():
            a.set_navigate_mode(self._active)
        self.set_message(self.mode)
        self._update_buttons_checked()


    def _update_buttons_checked(self):
        #sync button checkstates to match active mode
        self._actions['pan'].setChecked(self._active == 'PAN')
        self._actions['zoom'].setChecked(self._active == 'ZOOM')
        self._actions['toggle_span'].setChecked(self._active == 'SPAN')
        self._actions['toggle_hzoom'].setChecked(self._active == 'HZOOM')
        if self._active:
            self.canvas.set_tools_in_use(True)
        else:
            self.canvas.set_tools_in_use(False)

    def _init_toolbar(self):
        self.basedir = os.path.join(matplotlib.rcParams[ 'datapath' ],'images')
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
            self.locLabel = QtGui.QLabel( "", self )
            self.locLabel.setAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignTop )
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
                    titles.append(fmt % dict(title = title,
                                         ylabel = ylabel,
                                         axes_repr = repr(axes),
                                         CUSTOM_NAME = axes._CUSTOM_NAME))
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
        #gridspec layout subplotova
        self.gs = gridspec.GridSpec(3, 1, height_ratios=[1,1,4])
        #defiincija pojedinih subplotova
        self.axesC = self.fig.add_subplot(self.gs[2, 0]) #koncentracija
        self.axesS = self.fig.add_subplot(self.gs[0, 0], sharex=self.axesC) #span
        self.axesZ = self.fig.add_subplot(self.gs[1, 0], sharex=self.axesC) #zero
        self.axesC._CUSTOM_NAME = 'Graf koncentracija'
        self.axesZ._CUSTOM_NAME = 'Graf zero'
        self.axesS._CUSTOM_NAME = 'Graf span'
        #hide x labele za zero i span axes
        self.axesS.xaxis.set_visible(False)
        self.axesZ.xaxis.set_visible(False)
        #prebaci labele srednjeg grafa na desno
        self.axesZ.yaxis.tick_right()
        #podesi spacing izmedju axesa (sljepi grafove)
        self.fig.subplots_adjust(wspace=0.001, hspace=0.001)
        #update geometriju postavi opciju za custom kontekstni meni
        FigureCanvas.updateGeometry(self)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)

        #bitni memberi
        self.koncModel = None #model sa podacima koncentracije
        self.zeroModel = None #model sa podacima zero
        self.spanModel = None #model sa podacima span

        #staus grafa i alata
        self.isDrawn = False
        self.isGridDrawn = True
        self.isLegendDrawn = False
        self.otherToolsInUse = False
        self.isKoncGrafActive = True
        self.isZeroGrafActive = False
        self.isSpanGrafActive = False
        #elementi za konc graf
        self.koncLDL = None
        self.koncGood = None
        self.koncBad = None
        self.koncKorekcija = None
        self.leftLimit = None
        self.rightLimit = None
        #elementi za zero graf
        self.zeroGood = None
        self.zeroBad = None
        self.zeroLine = None
        self.zeroKorekcija = None
        self.zeroTopLimit = None
        self.zeroLowLimit = None
        #elementi za span graf
        self.spanGood = None
        self.spanBad = None
        self.spanLine = None
        self.spanKorekcija = None
        self.spanTopLimit = None
        self.spanLowLimit = None

        #interakcija sa grafom (kontekstni meni, pick vrijednosti, scroll zoom)
        self.pickCid = self.mpl_connect('button_press_event', self.on_pick)
        self.scrollZoomCid = self.mpl_connect('scroll_event', self.scroll_zoom_along_x)

        #re-emit some signals
        self.connect(self,
                     QtCore.SIGNAL('update_data_point_count(PyQt_PyObject)'),
                     self.emit_graf_modified)
        self.connect(self,
                     QtCore.SIGNAL('point_selected(PyQt_PyObject)'),
                     self.emit_point_selected)

    def emit_graf_modified(self, mapa):
        self.emit(QtCore.SIGNAL('graf_is_modified(PyQt_PyObject)'), mapa)

    def emit_point_selected(self, red):
        self.emit(QtCore.SIGNAL('table_select_podatak(PyQt_PyObject)'), red)

    def set_axes_focus(self, tip='koncentracija'):
        if tip == 'span':
            self.gs.set_height_ratios([4,1,1])
            self.isKoncGrafActive = False
            self.isZeroGrafActive = False
            self.isSpanGrafActive = True
        elif tip == 'zero':
            self.gs.set_height_ratios([1,4,1])
            self.isKoncGrafActive = False
            self.isZeroGrafActive = True
            self.isSpanGrafActive = False
        else:
            self.gs.set_height_ratios([1,1,4])
            self.isKoncGrafActive = True
            self.isZeroGrafActive = False
            self.isSpanGrafActive = False
        #redraw legendu ako je nacrtana za novi aktivni graf
        self.draw_legend(self.isLegendDrawn)
        self.fig.tight_layout()
        #podesi spacing izmedju axesa (sljepi grafove)
        self.fig.subplots_adjust(wspace=0.001, hspace=0.001)
        self.draw()

    def save_current_display_options(self):
        """save graph information..."""
        func_getters = {'label':'get_label',
                        'linestyle':'get_linestyle',
                        'drawstyle':'get_drawstyle',
                        'linewidth':'get_linewidth',
                        'linecolor':'get_color',
                        'markerstyle':'get_marker',
                        'markersize':'get_markersize',
                        'markerfacecolor':'get_markerfacecolor',
                        'markeredgecolor':'get_markeredgecolor'}

        curves = {'KONC_GOOD':self.koncGood,
                  'KONC_BAD':self.koncBad,
                  'KONC_KOREKCIJA':self.koncKorekcija,
                  'KONC_LEFT_LIMIT':self.leftLimit,
                  'KONC_RIGHT_LIMIT':self.rightLimit,
                  'ZERO_GOOD':self.zeroGood,
                  'ZERO_BAD':self.zeroBad,
                  'ZERO_LINE':self.zeroLine,
                  'ZERO_KOREKCIJA':self.zeroKorekcija,
                  'ZERO_TOP_LIMIT':self.zeroTopLimit,
                  'ZERO_LOW_LIMIT':self.zeroLowLimit,
                  'SPAN_GOOD':self.spanGood,
                  'SPAN_BAD':self.spanBad,
                  'SPAN_LINE':self.spanLine,
                  'SPAN_KOREKCIJA':self.spanKorekcija,
                  'SPAN_TOP_LIMIT':self.spanTopLimit,
                  'SPAN_LOW_LIMIT':self.spanLowLimit}

        for section, lajnObjekt in curves.items():
            if lajnObjekt != None:
                for option, geter in func_getters.items():
                    #dohvati odgovarajuci setter
                    tmpfunc = getattr(lajnObjekt, geter)
                    self.cfgGraf.set_konfig_option(section, option, tmpfunc())

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
        #all legends
        ite = zip([self.axesC, self.axesS, self.axesZ],
                  [self.isKoncGrafActive, self.isSpanGrafActive, self.isZeroGrafActive])
        for i, j in ite:
            i.legend(fontsize=8, loc='center left', bbox_to_anchor=(1, 0.5))
            i.get_legend().draggable(state=True)
            stejt = toggle and j
            i.get_legend().set_visible(stejt)
        #display legend for graph
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
                #koncentracija autoscale
                modelymin, modelymax = self.koncModel.get_autoscale_y_range(t1, t2)
                if np.isnan(modelymin):
                    ymin = baseymin
                else:
                    ymin = modelymin
                if np.isnan(modelymax):
                    ymax = baseymax
                else:
                    ymax = modelymax
                spejsing = (ymax-ymin)/10 #(10% raspona sa svake strane)
                self.axesC.set_ylim((ymin-spejsing, ymax+spejsing))
                #zero autoscale
                modelymin, modelymax = self.zeroModel.get_autoscale_y_range(t1, t2)
                if np.isnan(modelymin):
                    ymin = baseymin
                else:
                    ymin = modelymin
                if np.isnan(modelymax):
                    ymax = baseymax
                else:
                    ymax = modelymax
                spejsing = (ymax-ymin)/5 #(20% raspona sa svake strane)
                self.axesZ.set_ylim((ymin-spejsing, ymax+spejsing))
                #span autoscale
                modelymin, modelymax = self.spanModel.get_autoscale_y_range(t1, t2)
                if np.isnan(modelymin):
                    ymin = baseymin
                else:
                    ymin = modelymin
                if np.isnan(modelymax):
                    ymax = baseymax
                else:
                    ymax = modelymax
                spejsing = (ymax-ymin)/5 #(20% raspona sa svake strane)
                self.axesS.set_ylim((ymin-spejsing, ymax+spejsing))
            else:
                pass
        except Exception as err:
            #do not autoscale y..
            logging.error(str(err), exc_info=True)
            pass

    def crtaj_zero(self):
        frejmZero = self.zeroModel.datafrejm
        indeks = list(frejmZero.index)
        #granice
        topLim = list(frejmZero['maxDozvoljeno'].astype(float))
        lowLim = list(frejmZero['minDozvoljeno'].astype(float))
        preko = [i > j for i, j in zip(list(frejmZero['zero']), topLim)]
        ispod = [i < j for i, j in zip(list(frejmZero['zero']), lowLim)]
        badflags = [i or j for i, j in zip(preko, ispod)]
        goodflags = [not i for i in badflags]
        dobri = frejmZero.loc[goodflags, 'zero'].astype(float)
        dobri = dobri.reindex(indeks)
        losi = frejmZero.loc[badflags, 'zero'].astype(float)
        losi = losi.reindex(indeks)

        self.zeroTopLimit, = self.axesZ.plot(
            indeks,
            topLim,
            label=self.cfgGraf.get_konfig_option('ZERO_TOP_LIMIT', 'label', 'Max dozvoljeni'),
            linestyle=self.cfgGraf.get_konfig_option('ZERO_TOP_LIMIT', 'linestyle', '--'),
            drawstyle=self.cfgGraf.get_konfig_option('ZERO_TOP_LIMIT', 'drawstyle', 'default'),
            linewidth=self.cfgGraf.get_konfig_option('ZERO_TOP_LIMIT', 'linewidth', 1.2),
            color=self.cfgGraf.get_konfig_option('ZERO_TOP_LIMIT', 'linecolor', 'red'),
            marker=self.cfgGraf.get_konfig_option('ZERO_TOP_LIMIT', 'markerstyle', 'None'),
            markersize=self.cfgGraf.get_konfig_option('ZERO_TOP_LIMIT', 'markersize', 6),
            markerfacecolor=self.cfgGraf.get_konfig_option('ZERO_TOP_LIMIT', 'markerfacecolor', 'red'),
            markeredgecolor=self.cfgGraf.get_konfig_option('ZERO_TOP_LIMIT', 'markeredgecolor', 'red'))

        self.zeroLowLimit, = self.axesZ.plot(
            indeks,
            lowLim,
            label=self.cfgGraf.get_konfig_option('ZERO_LOW_LIMIT', 'label', 'Min dozvoljeni'),
            linestyle=self.cfgGraf.get_konfig_option('ZERO_LOW_LIMIT', 'linestyle', '--'),
            drawstyle=self.cfgGraf.get_konfig_option('ZERO_LOW_LIMIT', 'drawstyle', 'default'),
            linewidth=self.cfgGraf.get_konfig_option('ZERO_LOW_LIMIT', 'linewidth', 1.2),
            color=self.cfgGraf.get_konfig_option('ZERO_LOW_LIMIT', 'linecolor', 'red'),
            marker=self.cfgGraf.get_konfig_option('ZERO_LOW_LIMIT', 'markerstyle', 'None'),
            markersize=self.cfgGraf.get_konfig_option('ZERO_LOW_LIMIT', 'markersize', 6),
            markerfacecolor=self.cfgGraf.get_konfig_option('ZERO_LOW_LIMIT', 'markerfacecolor', 'red'),
            markeredgecolor=self.cfgGraf.get_konfig_option('ZERO_LOW_LIMIT', 'markeredgecolor', 'red'))

        self.zeroLine, = self.axesZ.plot(
            indeks,
            frejmZero['zero'].astype(float),
            label=self.cfgGraf.get_konfig_option('ZERO_LINE', 'label', 'Zero'),
            linestyle=self.cfgGraf.get_konfig_option('ZERO_LINE', 'linestyle', ':'),
            drawstyle=self.cfgGraf.get_konfig_option('ZERO_LINE', 'drawstyle', 'default'),
            linewidth=self.cfgGraf.get_konfig_option('ZERO_LINE', 'linewidth', 1.0),
            color=self.cfgGraf.get_konfig_option('ZERO_LINE', 'linecolor', 'blue'),
            marker=self.cfgGraf.get_konfig_option('ZERO_LINE', 'markerstyle', 'None'),
            markersize=self.cfgGraf.get_konfig_option('ZERO_LINE', 'markersize', 6),
            markerfacecolor=self.cfgGraf.get_konfig_option('ZERO_LINE', 'markerfacecolor', 'blue'),
            markeredgecolor=self.cfgGraf.get_konfig_option('ZERO_LINE', 'markeredgecolor', 'blue'))

        self.zeroGood, = self.axesZ.plot(
            indeks,
            dobri,
            label=self.cfgGraf.get_konfig_option('ZERO_GOOD', 'label', 'Zero ok'),
            linestyle=self.cfgGraf.get_konfig_option('ZERO_GOOD', 'linestyle', 'None'),
            drawstyle=self.cfgGraf.get_konfig_option('ZERO_GOOD', 'drawstyle', 'default'),
            linewidth=self.cfgGraf.get_konfig_option('ZERO_GOOD', 'linewidth', 0.8),
            color=self.cfgGraf.get_konfig_option('ZERO_GOOD', 'linecolor', 'green'),
            marker=self.cfgGraf.get_konfig_option('ZERO_GOOD', 'markerstyle', 'd'),
            markersize=self.cfgGraf.get_konfig_option('ZERO_GOOD', 'markersize', 6),
            markerfacecolor=self.cfgGraf.get_konfig_option('ZERO_GOOD', 'markerfacecolor', 'green'),
            markeredgecolor=self.cfgGraf.get_konfig_option('ZERO_GOOD', 'markeredgecolor', 'green'))

        self.zeroBad, = self.axesZ.plot(
            indeks,
            losi,
            label=self.cfgGraf.get_konfig_option('ZERO_BAD', 'label', 'Zero bad'),
            linestyle=self.cfgGraf.get_konfig_option('ZERO_BAD', 'linestyle', 'None'),
            drawstyle=self.cfgGraf.get_konfig_option('ZERO_BAD', 'drawstyle', 'default'),
            linewidth=self.cfgGraf.get_konfig_option('ZERO_BAD', 'linewidth', 0.8),
            color=self.cfgGraf.get_konfig_option('ZERO_BAD', 'linecolor', 'red'),
            marker=self.cfgGraf.get_konfig_option('ZERO_BAD', 'markerstyle', 'd'),
            markersize=self.cfgGraf.get_konfig_option('ZERO_BAD', 'markersize', 6),
            markerfacecolor=self.cfgGraf.get_konfig_option('ZERO_BAD', 'markerfacecolor', 'red'),
            markeredgecolor=self.cfgGraf.get_konfig_option('ZERO_BAD', 'markeredgecolor', 'red'))

        self.zeroKorekcija, = self.axesZ.plot(
            indeks,
            frejmZero['korekcija'].astype(float),
            label=self.cfgGraf.get_konfig_option('ZERO_KOREKCIJA', 'label', 'Korekcija'),
            linestyle=self.cfgGraf.get_konfig_option('ZERO_KOREKCIJA', 'linestyle', '-'),
            drawstyle=self.cfgGraf.get_konfig_option('ZERO_KOREKCIJA', 'drawstyle', 'default'),
            linewidth=self.cfgGraf.get_konfig_option('ZERO_KOREKCIJA', 'linewidth', 1.2),
            color=self.cfgGraf.get_konfig_option('ZERO_KOREKCIJA', 'linecolor', 'black'),
            marker=self.cfgGraf.get_konfig_option('ZERO_KOREKCIJA', 'markerstyle', 'None'),
            markersize=self.cfgGraf.get_konfig_option('ZERO_KOREKCIJA', 'markersize', 6),
            markerfacecolor=self.cfgGraf.get_konfig_option('ZERO_KOREKCIJA', 'markerfacecolor', 'black'),
            markeredgecolor=self.cfgGraf.get_konfig_option('ZERO_KOREKCIJA', 'markeredgecolor', 'black'))

    def crtaj_span(self):
        frejmSpan = self.spanModel.datafrejm
        indeks = list(frejmSpan.index)
        #granice
        topLim = list(frejmSpan['maxDozvoljeno'].astype(float))
        lowLim = list(frejmSpan['minDozvoljeno'].astype(float))
        preko = [i > j for i, j in zip(list(frejmSpan['span']), topLim)]
        ispod = [i < j for i, j in zip(list(frejmSpan['span']), lowLim)]
        badflags = [i or j for i, j in zip(preko, ispod)]
        goodflags = [not i for i in badflags]
        dobri = frejmSpan.loc[goodflags, 'span'].astype(float)
        dobri = dobri.reindex(indeks)
        losi = frejmSpan.loc[badflags, 'span'].astype(float)
        losi = losi.reindex(indeks)

        self.spanTopLimit, = self.axesS.plot(
            indeks,
            topLim,
            label=self.cfgGraf.get_konfig_option('SPAN_TOP_LIMIT', 'label', 'Max dozvoljeni'),
            linestyle=self.cfgGraf.get_konfig_option('SPAN_TOP_LIMIT', 'linestyle', '--'),
            drawstyle=self.cfgGraf.get_konfig_option('SPAN_TOP_LIMIT', 'drawstyle', 'default'),
            linewidth=self.cfgGraf.get_konfig_option('SPAN_TOP_LIMIT', 'linewidth', 1.2),
            color=self.cfgGraf.get_konfig_option('SPAN_TOP_LIMIT', 'linecolor', 'red'),
            marker=self.cfgGraf.get_konfig_option('SPAN_TOP_LIMIT', 'markerstyle', 'None'),
            markersize=self.cfgGraf.get_konfig_option('SPAN_TOP_LIMIT', 'markersize', 6),
            markerfacecolor=self.cfgGraf.get_konfig_option('SPAN_TOP_LIMIT', 'markerfacecolor', 'red'),
            markeredgecolor=self.cfgGraf.get_konfig_option('SPAN_TOP_LIMIT', 'markeredgecolor', 'red'))

        self.spanLowLimit, = self.axesS.plot(
            indeks,
            lowLim,
            label=self.cfgGraf.get_konfig_option('SPAN_LOW_LIMIT', 'label', 'Min dozvoljeni'),
            linestyle=self.cfgGraf.get_konfig_option('SPAN_LOW_LIMIT', 'linestyle', '--'),
            drawstyle=self.cfgGraf.get_konfig_option('SPAN_LOW_LIMIT', 'drawstyle', 'default'),
            linewidth=self.cfgGraf.get_konfig_option('SPAN_LOW_LIMIT', 'linewidth', 1.2),
            color=self.cfgGraf.get_konfig_option('SPAN_LOW_LIMIT', 'linecolor', 'red'),
            marker=self.cfgGraf.get_konfig_option('SPAN_LOW_LIMIT', 'markerstyle', 'None'),
            markersize=self.cfgGraf.get_konfig_option('SPAN_LOW_LIMIT', 'markersize', 6),
            markerfacecolor=self.cfgGraf.get_konfig_option('SPAN_LOW_LIMIT', 'markerfacecolor', 'red'),
            markeredgecolor=self.cfgGraf.get_konfig_option('SPAN_LOW_LIMIT', 'markeredgecolor', 'red'))

        self.spanLine, = self.axesS.plot(
            indeks,
            frejmSpan['span'].astype(float),
            label=self.cfgGraf.get_konfig_option('SPAN_LINE', 'label', 'Span'),
            linestyle=self.cfgGraf.get_konfig_option('SPAN_LINE', 'linestyle', ':'),
            drawstyle=self.cfgGraf.get_konfig_option('SPAN_LINE', 'drawstyle', 'default'),
            linewidth=self.cfgGraf.get_konfig_option('SPAN_LINE', 'linewidth', 1.0),
            color=self.cfgGraf.get_konfig_option('SPAN_LINE', 'linecolor', 'blue'),
            marker=self.cfgGraf.get_konfig_option('SPAN_LINE', 'markerstyle', 'None'),
            markersize=self.cfgGraf.get_konfig_option('SPAN_LINE', 'markersize', 6),
            markerfacecolor=self.cfgGraf.get_konfig_option('SPAN_LINE', 'markerfacecolor', 'blue'),
            markeredgecolor=self.cfgGraf.get_konfig_option('SPAN_LINE', 'markeredgecolor', 'blue'))

        self.spanGood, = self.axesS.plot(
            indeks,
            dobri,
            label=self.cfgGraf.get_konfig_option('SPAN_GOOD', 'label', 'Span ok'),
            linestyle=self.cfgGraf.get_konfig_option('SPAN_GOOD', 'linestyle', 'None'),
            drawstyle=self.cfgGraf.get_konfig_option('SPAN_GOOD', 'drawstyle', 'default'),
            linewidth=self.cfgGraf.get_konfig_option('SPAN_GOOD', 'linewidth', 0.8),
            color=self.cfgGraf.get_konfig_option('SPAN_GOOD', 'linecolor', 'green'),
            marker=self.cfgGraf.get_konfig_option('SPAN_GOOD', 'markerstyle', 'd'),
            markersize=self.cfgGraf.get_konfig_option('SPAN_GOOD', 'markersize', 6),
            markerfacecolor=self.cfgGraf.get_konfig_option('SPAN_GOOD', 'markerfacecolor', 'green'),
            markeredgecolor=self.cfgGraf.get_konfig_option('SPAN_GOOD', 'markeredgecolor', 'green'))

        self.spanBad, = self.axesS.plot(
            indeks,
            losi,
            label=self.cfgGraf.get_konfig_option('SPAN_BAD', 'label', 'Span bad'),
            linestyle=self.cfgGraf.get_konfig_option('SPAN_BAD', 'linestyle', 'None'),
            drawstyle=self.cfgGraf.get_konfig_option('SPAN_BAD', 'drawstyle', 'default'),
            linewidth=self.cfgGraf.get_konfig_option('SPAN_BAD', 'linewidth', 0.8),
            color=self.cfgGraf.get_konfig_option('SPAN_BAD', 'linecolor', 'red'),
            marker=self.cfgGraf.get_konfig_option('SPAN_BAD', 'markerstyle', 'd'),
            markersize=self.cfgGraf.get_konfig_option('SPAN_BAD', 'markersize', 6),
            markerfacecolor=self.cfgGraf.get_konfig_option('SPAN_BAD', 'markerfacecolor', 'red'),
            markeredgecolor=self.cfgGraf.get_konfig_option('SPAN_BAD', 'markeredgecolor', 'red'))

        self.spanKorekcija, = self.axesS.plot(
            indeks,
            frejmSpan['korekcija'].astype(float),
            label=self.cfgGraf.get_konfig_option('SPAN_KOREKCIJA', 'label', 'Korekcija'),
            linestyle=self.cfgGraf.get_konfig_option('SPAN_KOREKCIJA', 'linestyle', '-'),
            drawstyle=self.cfgGraf.get_konfig_option('SPAN_KOREKCIJA', 'drawstyle', 'default'),
            linewidth=self.cfgGraf.get_konfig_option('SPAN_KOREKCIJA', 'linewidth', 1.2),
            color=self.cfgGraf.get_konfig_option('SPAN_KOREKCIJA', 'linecolor', 'black'),
            marker=self.cfgGraf.get_konfig_option('SPAN_KOREKCIJA', 'markerstyle', 'None'),
            markersize=self.cfgGraf.get_konfig_option('SPAN_KOREKCIJA', 'markersize', 6),
            markerfacecolor=self.cfgGraf.get_konfig_option('SPAN_KOREKCIJA', 'markerfacecolor', 'black'),
            markeredgecolor=self.cfgGraf.get_konfig_option('SPAN_KOREKCIJA', 'markeredgecolor', 'black'))

    def crtaj_koncentracija(self):
        ##### priprema podataka za crtanje koncentracija #####
        frejmKonc = self.koncModel.datafrejm
        indeks = list(frejmKonc.index)
        #dobro flagirani
        goodData = frejmKonc[frejmKonc['flag'] >= 0]
        goodData = goodData.reindex(indeks)
        #lose flagirani
        badData = frejmKonc[frejmKonc['flag'] < 0]
        badData = badData.reindex(indeks)

        self.xlim_original = self.get_prosirene_x_granice(indeks[0], indeks[-1], t=120)
        self.axesC.set_xlim(self.xlim_original)
        #self.axesC.xaxis_date() #force date...

        #korektirani = goodData['korekcija'].astype(float)
        korektirani_manji_od_nule = goodData[goodData['korekcija'] < 0].count()['korekcija']
        if 'LDL' in goodData:
            c = [i<j for i, j in zip(goodData['korekcija'], goodData['LDL'])]
            korektirani_manji_od_LDL = sum(c)
        else:
            korektirani_manji_od_LDL = 0

        #signlaiziraj update labela za obuhvat
        #TODO!
        mapa = {'ocekivano':len(indeks),
                'broj_mjerenja':goodData.count()['koncentracija'],
                'broj_korektiranih':goodData.count()['korekcija'],
                'ispod_nula':korektirani_manji_od_nule,
                'ispod_LDL':korektirani_manji_od_LDL}
        self.emit(QtCore.SIGNAL('update_data_point_count(PyQt_PyObject)'), mapa)

        if 'LDL' in frejmKonc.columns:
            self.koncLDL = self.axesC.plot(
                indeks,
                frejmKonc['LDL'],
                label=self.cfgGraf.get_konfig_option('KONC_LDL', 'label', 'LDL'),
                linestyle=self.cfgGraf.get_konfig_option('KONC_LDL', 'linestyle', '-'),
                drawstyle=self.cfgGraf.get_konfig_option('KONC_LDL', 'drawstyle', 'default'),
                linewidth=self.cfgGraf.get_konfig_option('KONC_LDL', 'linewidth', 1.4),
                color=self.cfgGraf.get_konfig_option('KONC_LDL', 'linecolor', 'red'),
                marker=self.cfgGraf.get_konfig_option('KONC_LDL', 'markerstyle', 'None'),
                markersize=self.cfgGraf.get_konfig_option('KONC_LDL', 'markersize', 6),
                markerfacecolor=self.cfgGraf.get_konfig_option('KONC_LDL', 'markerfacecolor', 'red'),
                markeredgecolor=self.cfgGraf.get_konfig_option('KONC_LDL', 'markeredgecolor', 'red'))

        self.leftLimit = self.axesC.axvline(
            indeks[0],
            label=self.cfgGraf.get_konfig_option('KONC_LEFT_LIMIT', 'label', 'Min vrijeme'),
            linestyle=self.cfgGraf.get_konfig_option('KONC_LEFT_LIMIT', 'linestyle', '-.'),
            drawstyle=self.cfgGraf.get_konfig_option('KONC_LEFT_LIMIT', 'drawstyle', 'default'),
            linewidth=self.cfgGraf.get_konfig_option('KONC_LEFT_LIMIT', 'linewidth', 1.2),
            color=self.cfgGraf.get_konfig_option('KONC_LEFT_LIMIT', 'linecolor', 'blue'),
            marker=self.cfgGraf.get_konfig_option('KONC_LEFT_LIMIT', 'markerstyle', 'None'),
            markersize=self.cfgGraf.get_konfig_option('KONC_LEFT_LIMIT', 'markersize', 6),
            markerfacecolor=self.cfgGraf.get_konfig_option('KONC_LEFT_LIMIT', 'markerfacecolor', 'blue'),
            markeredgecolor=self.cfgGraf.get_konfig_option('KONC_LEFT_LIMIT', 'markeredgecolor', 'blue'))

        self.rightLimit = self.axesC.axvline(
            indeks[-1],
            label=self.cfgGraf.get_konfig_option('KONC_RIGHT_LIMIT', 'label', 'Max vrijeme'),
            linestyle=self.cfgGraf.get_konfig_option('KONC_RIGHT_LIMIT', 'linestyle', '-.'),
            drawstyle=self.cfgGraf.get_konfig_option('KONC_RIGHT_LIMIT', 'drawstyle', 'default'),
            linewidth=self.cfgGraf.get_konfig_option('KONC_RIGHT_LIMIT', 'linewidth', 1.2),
            color=self.cfgGraf.get_konfig_option('KONC_RIGHT_LIMIT', 'linecolor', 'blue'),
            marker=self.cfgGraf.get_konfig_option('KONC_RIGHT_LIMIT', 'markerstyle', 'None'),
            markersize=self.cfgGraf.get_konfig_option('KONC_RIGHT_LIMIT', 'markersize', 6),
            markerfacecolor=self.cfgGraf.get_konfig_option('KONC_RIGHT_LIMIT', 'markerfacecolor', 'blue'),
            markeredgecolor=self.cfgGraf.get_konfig_option('KONC_RIGHT_LIMIT', 'markeredgecolor', 'blue'))

        self.koncGood, = self.axesC.plot(
            indeks,
            goodData['koncentracija'].astype(float),
            label=self.cfgGraf.get_konfig_option('KONC_GOOD', 'label', 'Dobar flag'),
            linestyle=self.cfgGraf.get_konfig_option('KONC_GOOD', 'linestyle', '-'),
            drawstyle=self.cfgGraf.get_konfig_option('KONC_GOOD', 'drawstyle', 'default'),
            linewidth=self.cfgGraf.get_konfig_option('KONC_GOOD', 'linewidth', 0.8),
            color=self.cfgGraf.get_konfig_option('KONC_GOOD', 'linecolor', 'green'),
            marker=self.cfgGraf.get_konfig_option('KONC_GOOD', 'markerstyle', 'None'),
            markersize=self.cfgGraf.get_konfig_option('KONC_GOOD', 'markersize', 6),
            markerfacecolor=self.cfgGraf.get_konfig_option('KONC_GOOD', 'markerfacecolor', 'green'),
            markeredgecolor=self.cfgGraf.get_konfig_option('KONC_GOOD', 'markeredgecolor', 'green'))

        self.koncBad, = self.axesC.plot(
            indeks,
            badData['koncentracija'].astype(float),
            label=self.cfgGraf.get_konfig_option('KONC_BAD', 'label', 'Los flag'),
            linestyle=self.cfgGraf.get_konfig_option('KONC_BAD', 'linestyle', '-'),
            drawstyle=self.cfgGraf.get_konfig_option('KONC_BAD', 'drawstyle', 'default'),
            linewidth=self.cfgGraf.get_konfig_option('KONC_BAD', 'linewidth', 0.8),
            color=self.cfgGraf.get_konfig_option('KONC_BAD', 'linecolor', 'red'),
            marker=self.cfgGraf.get_konfig_option('KONC_BAD', 'markerstyle', 'None'),
            markersize=self.cfgGraf.get_konfig_option('KONC_BAD', 'markersize', 6),
            markerfacecolor=self.cfgGraf.get_konfig_option('KONC_BAD', 'markerfacecolor', 'red'),
            markeredgecolor=self.cfgGraf.get_konfig_option('KONC_BAD', 'markeredgecolor', 'red'))

        self.koncKorekcija, = self.axesC.plot(
            indeks,
            goodData['korekcija'].astype(float),
            label=self.cfgGraf.get_konfig_option('KONC_KOREKCIJA', 'label', 'Korekcija'),
            linestyle=self.cfgGraf.get_konfig_option('KONC_KOREKCIJA', 'linestyle', '-'),
            drawstyle=self.cfgGraf.get_konfig_option('KONC_KOREKCIJA', 'drawstyle', 'default'),
            linewidth=self.cfgGraf.get_konfig_option('KONC_KOREKCIJA', 'linewidth', 1.2),
            color=self.cfgGraf.get_konfig_option('KONC_KOREKCIJA', 'linecolor', 'black'),
            marker=self.cfgGraf.get_konfig_option('KONC_KOREKCIJA', 'markerstyle', 'None'),
            markersize=self.cfgGraf.get_konfig_option('KONC_KOREKCIJA', 'markersize', 6),
            markerfacecolor=self.cfgGraf.get_konfig_option('KONC_KOREKCIJA', 'markerfacecolor', 'black'),
            markeredgecolor=self.cfgGraf.get_konfig_option('KONC_KOREKCIJA', 'markeredgecolor', 'black'))

    def sjencaj_lose_zero_span(self):
        """sjencanje losih zero i span raspona"""
        #spanovi za zero i span koji nisu u redu
        badRasponiZero = self.zeroModel.rasponi
        badRasponiSpan = self.spanModel.rasponi

        for xmin, xmax in badRasponiZero:
            self.axesZ.axvspan(xmin, xmax, facecolor='red', alpha=0.2)
            self.axesC.axvspan(xmin, xmax, facecolor='red', alpha=0.2)

        for xmin, xmax in badRasponiSpan:
            self.axesS.axvspan(xmin, xmax, facecolor='red', alpha=0.2)
            self.axesC.axvspan(xmin, xmax, facecolor='red', alpha=0.2)


    def crtaj(self, rend=True):
        #spremi postavke grafa
        self.save_current_display_options()

        #clear grafove
        self.clear_graf()

        #crtaj koncentraciju
        self.crtaj_koncentracija()
        #crtaj zero
        self.crtaj_zero()
        #crtaj span
        self.crtaj_span()

        #rotate date labele x osi
        allXLabels = self.axesC.get_xticklabels()
        for label in allXLabels:
            label.set_rotation(30)
            label.set_fontsize(8)

        #autoskaliranje y osi za sve grafove
        self.autoscale_y_os()

        #shading losih zero/span raspona
        self.sjencaj_lose_zero_span()

        #redraw
        if rend:
            self.fig.tight_layout()
            #podesi spacing izmedju axesa (sljepi grafove)
            self.fig.subplots_adjust(wspace=0.001, hspace=0.001)
            self.draw()
            self.isDrawn = True

    def _mpltime_to_pdtime(self, x):
        xpoint = matplotlib.dates.num2date(x) #datetime.datetime
        #problem.. rounding offset aware i offset naive datetimes..workaround
        xpoint = datetime.datetime(xpoint.year,
                                   xpoint.month,
                                   xpoint.day,
                                   xpoint.hour,
                                   xpoint.minute,
                                   xpoint.second)
        #konverzija iz datetime.datetime objekta u pandas.tislib.Timestamp
        xpoint = pd.to_datetime(xpoint)
        return xpoint

    def on_pick(self, event):
        #mora biti nacrtan, unutar osi i drugi alati moraju biti ugaseni
        if self.isDrawn and event.inaxes in [self.axesC, self.axesZ, self.axesS]:
            if event.button == 1:
                #left click
                xpoint = self.adaptiraj_tocku_od_pick_eventa(event)
                #TODO! konc label update
                t, val = xpoint, self.koncModel.datafrejm.loc[xpoint, 'koncentracija']
                self.emit(QtCore.SIGNAL('update_konc_label(PyQt_PyObject)'),(t, val))
                #TODO! nadji najblizi span
                tajm = self._mpltime_to_pdtime(event.xdata)
                t, val = self.spanModel.get_najblizu_vrijednost(tajm)
                self.emit(QtCore.SIGNAL('update_span_label(PyQt_PyObject)'), (t, val))
                #TODO! nadji najblizi zero
                tajm = self._mpltime_to_pdtime(event.xdata)
                t, val = self.zeroModel.get_najblizu_vrijednost(tajm)
                self.emit(QtCore.SIGNAL('update_zero_label(PyQt_PyObject)'), (t, val))
                if event.inaxes == self.axesC:
                    #koncentraija canvas
                    red = self.koncModel.get_index_position(xpoint)
                    #emit za select table podataka
                    self.emit(QtCore.SIGNAL('point_selected(PyQt_PyObject)'), red)
                    #emit za select relevantnog korekcijskog faktora
                    self.emit(QtCore.SIGNAL('zoom_to_korekcija_table(PyQt_PyObject)'), xpoint)
            elif event.button == 3 and not self.otherToolsInUse:
                #right click
                xpoint = self.adaptiraj_tocku_od_pick_eventa(event)
                loc = QtGui.QCursor.pos()
                self.show_context_menu(loc, xpoint, xpoint, 'click')

    def span_select(self, xmin, xmax):
        if self.isDrawn:
            #konverzija ulaznih vrijednosti u pandas timestampove
            t1 = self.matplotlib_time_to_pandas_timestamp(xmin, roundSec=60)
            t2 = self.matplotlib_time_to_pandas_timestamp(xmax, roundSec=60)
            #osiguranje da se ne preskoce granice glavnog kanala (izbjegavanje index errora)
            if t1 < self.xlim_original[0]:
                t1 = self.xlim_original[0]
            if t1 > self.xlim_original[1]:
                t1 = self.xlim_original[1]
            if t2 < self.xlim_original[0]:
                t2 = self.xlim_original[0]
            if t2 > self.xlim_original[1]:
                t2 = self.xlim_original[1]
            #tocke ne smiju biti iste (izbjegavamo paljenje dijaloga na ljevi klik)
            if t1 != t2:
                #pronadji lokaciju desnog klika u Qt kooridinatama.
                loc = QtGui.QCursor.pos()
                self.show_context_menu(loc, t1, t2, 'span') #poziv kontekstnog menija


    def matplotlib_time_to_pandas_timestamp(self, x, roundSec=None):
        t = matplotlib.dates.num2date(x)
        t = datetime.datetime(t.year, t.month, t.day, t.hour, t.minute, t.second)
        if roundSec:
            t = self.zaokruzi_vrijeme(t, roundSec)
        t = pd.to_datetime(t)
        return t

    def span_zoom(self, xmin, xmax):
        if self.isDrawn:
            #konverzija ulaznih vrijednosti u pandas timestampove
            t1 = self.matplotlib_time_to_pandas_timestamp(xmin)
            t2 = self.matplotlib_time_to_pandas_timestamp(xmax)
            #rotate min, max order po potrebi
            if t1 > t2:
                t1, t2 = t2, t1
            #tocke ne smiju biti iste
            if t1 != t2:
                self.axesC.set_xlim((t1, t2))
                self.autoscale_y_os()
                self.draw()
            #push the drawn image to toolbar zoom stack
            self.emit(QtCore.SIGNAL('push_view_to_toolbar_zoom_stack'))

    def scroll_zoom_along_x(self, event):
        try:
            xmin, xmax = self.axesC.get_xlim()
            skala = 1.1
            xdata = event.xdata
            if event.button == 'up':
                faktor = 1/skala
            elif event.button == 'down':
                faktor = skala
            else:
                faktor = 1
                logging.error('invalid scroll value')
            left = (xdata - xmin) * faktor
            right = (xmax - xdata) * faktor

            x1 = xdata - left
            x2 = xdata + right
            self.axesC.set_xlim((x1,x2))
            self.autoscale_y_os()
            self.draw()
            #push the drawn image to toolbar zoom stack
            self.emit(QtCore.SIGNAL('push_view_to_toolbar_zoom_stack'))
        except Exception as err:
            logging.error(str(err))

    def adaptiraj_tocku_od_pick_eventa(self, event):
        xpoint = matplotlib.dates.num2date(event.xdata) #datetime.datetime
        #problem.. rounding offset aware i offset naive datetimes..workaround
        xpoint = datetime.datetime(xpoint.year,
                                   xpoint.month,
                                   xpoint.day,
                                   xpoint.hour,
                                   xpoint.minute,
                                   xpoint.second)
        #xpoint = self.zaokruzi_vrijeme(xpoint, 60)
        if event.inaxes == self.axesC:
            xpoint = self.zaokruzi_vrijeme(xpoint, self.koncModel.timestep)
        else:
            xpoint = self.zaokruzi_vrijeme(xpoint, 60)
        #konverzija iz datetime.datetime objekta u pandas.tislib.Timestamp
        xpoint = pd.to_datetime(xpoint)
        #pazimo da x vrijednost ne iskace od zadanih granica
        if xpoint >= self.xlim_original[1]:
            xpoint = self.xlim_original[1]
        if xpoint <= self.xlim_original[0]:
            xpoint = self.xlim_original[0]
        return xpoint

    def zaokruzi_vrijeme(self, dt_objekt, nSekundi):
        tmin = datetime.datetime.min
        delta = (dt_objekt - tmin).seconds
        zaokruzeno = ((delta + (nSekundi / 2)) // nSekundi) * nSekundi
        izlaz = dt_objekt + datetime.timedelta(0, zaokruzeno-delta, -dt_objekt.microsecond)
        return izlaz

    def show_context_menu(self, pos, tmin, tmax, tip):
        #zapamti rubna vremena intervala, trebati ce za druge metode
        self.__lastTimeMin = tmin
        self.__lastTimeMax = tmax
        #definiraj menu i
        menu = QtGui.QMenu(self)
        menu.setTitle('Menu')
        #definiranje akcija
        action1 = QtGui.QAction("Flag: dobar", menu)
        action2 = QtGui.QAction("Flag: los", menu)
        if tip != 'span':
            action3 = QtGui.QAction("show koncentracija", menu)
            action3.setCheckable(True)
            action3.setChecked(self.koncGood.get_visible())
            action4 = QtGui.QAction("show korekcija", menu)
            action4.setCheckable(True)
            action4.setChecked(self.koncKorekcija.get_visible())
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
        #slaganje akcija u menu
        menu.addAction(action1)
        menu.addAction(action2)
        if tip != 'span':
            menu.addSeparator()
            menu.addAction(action3)
            menu.addAction(action4)
            menu.addAction(action5)
            menu.addAction(action6)
            menu.addSeparator()
            menu.addAction(action7)
            menu.addAction(action8)
            menu.addAction(action9)
        #povezi akcije menua sa metodama
        action1.triggered.connect(functools.partial(self.promjena_flaga, flag=1000))
        action2.triggered.connect(functools.partial(self.promjena_flaga, flag=-1000))
        if tip != 'span':
            action3.triggered.connect(functools.partial(self.toggle_visibility_callbacks, label='koncentracija'))
            action4.triggered.connect(functools.partial(self.toggle_visibility_callbacks, label='korekcija'))
            action5.triggered.connect(functools.partial(self.toggle_visibility_callbacks, label='legenda'))
            action6.triggered.connect(functools.partial(self.toggle_visibility_callbacks, label='grid'))
            action7.triggered.connect(functools.partial(self.set_axes_focus, tip='span'))
            action8.triggered.connect(functools.partial(self.set_axes_focus, tip='zero'))
            action9.triggered.connect(functools.partial(self.set_axes_focus, tip='koncentracija'))
        #prikazi menu na definiranoj tocki grafa
        menu.popup(pos)

    def toggle_visibility_callbacks(self, label='banana'):
        if label == 'koncentracija':
            self.koncGood.set_visible(not self.koncGood.get_visible())
            self.koncBad.set_visible(not self.koncBad.get_visible())
            self.zeroGood.set_visible(not self.zeroGood.get_visible())
            self.zeroBad.set_visible(not self.zeroBad.get_visible())
            self.spanGood.set_visible(not self.spanGood.get_visible())
            self.spanBad.set_visible(not self.spanBad.get_visible())
        elif label == 'korekcija':
            self.koncKorGood.set_visible(not self.koncKorekcija.get_visible())
            self.zeroKorGood.set_visible(not self.zeroKorekcija.get_visible())
            self.spanKorGood.set_visible(not self.spanKorekcija.get_visible())
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
        arg = {'od':tmin,
               'do':tmax,
               'noviFlag':flag}
        self.koncModel.promjeni_flag(arg)
        #zapamti current view
        curzumx = self.axesC.get_xlim()
        curzumy = self.axesC.get_ylim()
        #clear koncentracijski axes and redraw
        self.axesC.clear()
        self.isDrawn = False
        self.crtaj_koncentracija()
        #restore view
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
        self.pixSpan = QtGui.QPixmap(24,24)
        self.pixSpan.load(iconSpan)
        self.iconSpan = QtGui.QIcon(self.pixSpan)
        self.pixZoom = QtGui.QPixmap(24,24)
        self.pixZoom.load(iconZoom)
        self.iconZoom = QtGui.QIcon(self.pixZoom)

        lay = QtGui.QVBoxLayout()

        #create a figure
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

        #connections
        self.connect(self.figure_canvas,
                     QtCore.SIGNAL('push_view_to_toolbar_zoom_stack'),
                     self.navigation_toolbar.push_current)

        self.connect(self.figure_canvas,
                     QtCore.SIGNAL('zoom_to_korekcija_table(PyQt_PyObject)'),
                     self.emit_korekcija_selected)

    def emit_korekcija_selected(self, xpoint):
        self.emit(QtCore.SIGNAL('korekcija_table_select_podatak(PyQt_PyObject)'), xpoint)

    def crtaj(self, rend=True):
        self.figure_canvas.crtaj(rend=rend)
        self.navigation_toolbar.clear_and_push_image_to_zoom_stack()

    def set_models(self, konc, zero, span):
        self.figure_canvas.set_models(konc, zero, span)
        self.navigation_toolbar.clear_and_push_image_to_zoom_stack()
################################################################################
################################################################################
