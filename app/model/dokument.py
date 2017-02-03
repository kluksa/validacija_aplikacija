# -*- coding: utf-8 -*-
import copy
from app.model import qtmodels
import pickle

class Dokument(object):
    def __init__(self):
        #nested dict mjerenja
        self._mjerenja = {}
        #empty tree model programa mjerenja
        drvo = qtmodels.TreeItem(['stanice', None, None, None], parent=None)
        self._treeModelProgramaMjerenja = qtmodels.ModelDrva(drvo)

        #modeli za prikaz podataka
        self._koncModel = qtmodels.KoncFrameModel()
        self._zeroModel = qtmodels.ZeroSpanFrameModel('zero')
        self._spanModel = qtmodels.ZeroSpanFrameModel('span')
        self._korekcijaModel = qtmodels.KorekcijaFrameModel()

    @property
    def mjerenja(self):
        """nested dict podataka o pojedinom kanalu"""
        return copy.deepcopy(self._mjerenja)

    @mjerenja.setter
    def mjerenja(self, x):
        if isinstance(x, dict):
            self._mjerenja = x
            self._konstruiraj_tree_model()
        else:
            raise TypeError('Ulazni argument mora biti dict, arg = {0}'.format(str(type(x))))

    @property
    def treeModelProgramaMjerenja(self):
        """Qt tree model za izbor kanala"""
        return self._treeModelProgramaMjerenja

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

    def get_pickleBinary(self, fname, kanal, od, do):
        mapa = {'kanal':kanal,
                'od':od,
                'do':do,
                'koncFrejm':self.koncModel.datafrejm,
                'zeroFrejm':self.zeroModel.datafrejm,
                'spanFrejm':self.spanModel.datafrejm,
                'korekcijaFrejm':self.korekcijaModel.datafrejm}
        return pickle.dumps(mapa)

    def set_pickleBinary(self, binstr):
        mapa = pickle.loads(binstr)
        self.koncModel.datafrejm = mapa['koncFrejm']
        self.zeroModel.datafrejm = mapa['zeroFrejm']
        self.spanModel.datafrejm = mapa['spanFrejm']
        self.korekcijaModel.datafrejm = mapa['korekcijaFrejm']
        od = mapa['od']
        do = mapa['do']
        kanal = mapa['kanal']
        #TODO! emit request za redraw



    def primjeni_korekciju(self):
        """pokupi frejmove, primjeni korekciju i spremi promjenu"""
        self.koncModel.datafrejm = self.korekcijaModel.primjeni_korekciju_na_frejm(self.koncModel.datafrejm)
        self.zeroModel.datafrejm = self.korekcijaModel.primjeni_korekciju_na_frejm(self.zeroModel.datafrejm)
        self.spanModel.datafrejm = self.korekcijaModel.primjeni_korekciju_na_frejm(self.spanModel.datafrejm)

    def set_kanal_info_string(self, kanal, od, do):
        """setter metapodataka o kanalu u model koncentracije"""
        kid = str(kanal)
        postaja = self._mjerenja[kanal]['postajaNaziv']
        #naziv = mapa[kanal]['komponentaNaziv']
        formula = self._mjerenja[kanal]['komponentaFormula']
        mjernaJedinica = self._mjerenja[kanal]['komponentaMjernaJedinica']
        out = "{0}: {1} | {2} ({3}) | OD: {4} | DO: {5}".format(
            kid,
            postaja,
            formula,
            mjernaJedinica,
            od,
            do)
        #set podatke u konc model
        self.koncModel.opis = out
        self.koncModel.kanalMeta = self.mjerenja[kanal]


    def _konstruiraj_tree_model(self):
        #sredjivanje povezanih kanala (NOx grupa i PM grupa)
        for kanal in self._mjerenja:
            pomocni = self._get_povezane_kanale(kanal)
            for i in pomocni:
                self._mjerenja[kanal]['povezaniKanali'].append(i)
            #sortiraj povezane kanale, predak je bitan zbog radio buttona
            lista = sorted(self._mjerenja[kanal]['povezaniKanali'])
            self._mjerenja[kanal]['povezaniKanali'] = lista

        drvo = qtmodels.TreeItem(['stanice', None, None, None], parent=None)
        #za svaku individualnu stanicu napravi TreeItem objekt, reference objekta spremi u dict
        stanice = []
        for pmid in sorted(list(self._mjerenja.keys())):
            stanica = self._mjerenja[pmid]['postajaNaziv']
            if stanica not in stanice:
                stanice.append(stanica)
        stanice = sorted(stanice)
        postaje = [qtmodels.TreeItem([name, None, None, None], parent=drvo) for name in stanice]
        strPostaje = [str(i) for i in postaje]
        for pmid in self._mjerenja:
            stanica = self._mjerenja[pmid]['postajaNaziv']  #parent = stanice[stanica]
            komponenta = self._mjerenja[pmid]['komponentaNaziv']
            formula = self._mjerenja[pmid]['komponentaFormula']
            mjernaJedinica = self._mjerenja[pmid]['komponentaMjernaJedinica']
            opis = " ".join([formula, '[', mjernaJedinica, ']'])
            usporedno = self._mjerenja[pmid]['usporednoMjerenje']
            data = [komponenta, usporedno, pmid, opis]
            redniBrojPostaje = strPostaje.index(stanica)
            #kreacija TreeItem objekta
            qtmodels.TreeItem(data, parent=postaje[redniBrojPostaje])
        self._treeModelProgramaMjerenja = qtmodels.ModelDrva(drvo)

    def _get_povezane_kanale(self, kanal):
        """
        Za zadani kanal, ako je formula kanala unutar nekog od setova,
        vrati sve druge kanale na istoj postaji koji takodjer pripadaju istom
        setu (NOx i PM).

        npr. ako je izabrani kanal Desinic NO, funkcija vraca id mjerenja za
        NO2 i NOx sa Desinica (ako postoje)
        """
        setovi = [('NOx', 'NO', 'NO2'), ('PM10', 'PM1', 'PM2.5')]
        output = set()
        postaja = self._mjerenja[kanal]['postajaId']
        formula = self._mjerenja[kanal]['komponentaFormula']
        usporednoMjerenje = self._mjerenja[kanal]['usporednoMjerenje']
        ciljaniSet = None
        for kombinacija in setovi:
            if formula in kombinacija:
                ciljaniSet = kombinacija
                break
        #ako kanal ne pripada setu povezanih...
        if ciljaniSet == None:
            return output
        for pmid in self._mjerenja:
            if self._mjerenja[pmid]['postajaId'] == postaja and pmid != kanal:
                if self._mjerenja[pmid]['komponentaFormula'] in ciljaniSet:
                    #usporedno mjerenje se mora poklapati...
                    if self._mjerenja[pmid]['usporednoMjerenje'] == usporednoMjerenje:
                        output.add(pmid)
        return output
