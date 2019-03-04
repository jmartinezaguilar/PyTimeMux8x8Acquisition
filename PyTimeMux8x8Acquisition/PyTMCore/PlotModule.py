#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Mar  1 18:44:39 2019

@author: aguimera
"""

import pyqtgraph.parametertree.parameterTypes as pTypes
import pyqtgraph as pg
import copy

ChannelPars = {'name': 'Ch01',
               'type': 'group',
               'children': [{'name': 'Name',
                             'type': 'str',
                             'value': 'Ch10'},
                            {'name': 'color',
                             'type': 'color',
                             'value': "FFF"},
                            {'name': 'width',
                             'type': 'float',
                             'value': 0.5},
                            {'name': 'Plot Window',
                             'type': 'int',
                             'value': 1,},
                            {'name': 'Input index',
                             'type': 'int',
                             'readonly': True,
                             'value': 1,}]
               }

PlotterPars = ({'name': 'Plot Windows',
                'type': 'int',
                'value': 1},
               {'name': 'Channels',
                'type': 'group',
                'children': []},)


class PlotterParameters(pTypes.GroupParameter):
    def __init__(self, **kwargs):
        pTypes.GroupParameter.__init__(self, **kwargs)

#        self.QTparent = QTparent
        self.addChildren(PlotterPars)
        self.param('Plot Windows').sigValueChanged.connect(self.on_WindChange)

    def on_WindChange(self):
        print('tyest')
        chs = self.param('Channels').children()
        chPWind = int(len(chs)/self.param('Plot Windows').value())
        for ch in chs:
            ind = ch.child('Input index').value()
            ch.child('Plot Window').setValue(int(ind/chPWind))

    def SetChannels(self, Channels):
        self.param('Channels').clearChildren()
        nChannels = len(Channels)
        chPWind = int(nChannels/self.param('Plot Windows').value())
        Chs = []
        for chn, ind in Channels.items():
            Ch = copy.deepcopy(ChannelPars)
            pen = pg.mkPen((ind, 1.3*nChannels))
            Ch['name'] = chn
            Ch['children'][0]['value'] = chn
            Ch['children'][1]['value'] = pen.color()
            Ch['children'][3]['value'] = int(ind/chPWind)
            Ch['children'][4]['value'] = ind
            Chs.append(Ch)

        self.param('Channels').addChildren(Chs)

    def GetParams(self):
        channelspars = {}
        for i in range(self.param('Plot Windows').value()):
            channelspars[i] = []

        for p in self.param('Channels').children():
            chp = {}
            for pp in p.children():
                chp[pp.name()] = pp.value()
            channelspars[chp['Plot Window']].append(chp.copy())
        return channelspars

