#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Mar  1 17:37:09 2019

@author: aguimera
"""

from __future__ import print_function
import os
from PyQt5 import Qt
from PyQt5.QtWidgets import QFileDialog

import numpy as np
import time

import pyqtgraph as pg

import pyqtgraph.parametertree.parameterTypes as pTypes
from pyqtgraph.parametertree import Parameter, ParameterTree, ParameterItem, registerParameterType
from itertools import  cycle
import copy
from scipy.signal import welch

import PyTimeMux8x8Acquisition.PyTMCore.FileModule as FileMod


GenFsPar = {'name': 'Fs',
            'tip': 'FsKw.Fs',
            'type': 'float',
            'value': 1e4,
            'step': 100,
            'siPrefix': True,
            'suffix': 'Hz'}

GenIntTimePar = {'name': 'IntervalTime',
                 'tip': 'FsKw.Fs',
                 'type': 'float',
                 'value': 1,
                 'step': 0.1,
                 'siPrefix': True,
                 'suffix': 's'}

GenIntSamplesPar = {'name':'nSamples',
                    'tip': 'Interval samples',
                    'type': 'int',
                    'value': 1e4,
                    }

GenNChannelsPar = {'name': 'nChannels',
                   'tip': 'Channels Number',
                   'type': 'int',
                   'value': 16,
                   'limits': (1, 128),
                   'step': 1}


class DataGeneratorParameters(pTypes.GroupParameter):
    def __init__(self, **kwargs):
#        kwargs['type'] = 'bool'
#        kwargs['value'] = True
        pTypes.GroupParameter.__init__(self, **kwargs)

        self.addChild(GenFsPar)
        self.addChild(GenIntTimePar)
        self.addChild(GenIntSamplesPar)
        self.addChild(GenNChannelsPar)
        self.Fs = self.param(GenFsPar['name'])
        self.IntTime = self.param(GenIntTimePar['name'])
        self.IntSamples = self.param(GenIntSamplesPar['name'])
        self.NChannels = self.param(GenNChannelsPar['name'])

        self.Fs.sigValueChanged.connect(self.on_Fs_Changed)
        self.IntTime.sigValueChanged.connect(self.on_Time_Changed)
        self.IntSamples.sigValueChanged.connect(self.on_Samples_Changed)

    def on_Fs_Changed(self):
        Fs = self.Fs.value()
        Ts = 1/Fs
        nSamps = self.IntSamples.value()

        nTime = nSamps * Ts
        self.IntTime.setValue(nTime, blockSignal=self.on_Time_Changed)

    def on_Time_Changed(self):
        Fs = self.Fs.value()
        Ts = 1/Fs
        nTime = self.IntTime.value()

        nSamps = int(nTime/Ts)
        self.IntSamples.setValue(nSamps, blockSignal=self.on_Samples_Changed)

    def on_Samples_Changed(self):
        Fs = self.Fs.value()
        Ts = 1/Fs
        nSamps = self.IntSamples.value()

        nTime = nSamps * Ts
        self.IntTime.setValue(nTime, blockSignal=self.on_Time_Changed)
        

class DataSamplingThread(Qt.QThread):
    ''' Data generator '''
    NewSample = Qt.pyqtSignal()

    def __init__(self, Fs, nChannels, nSamples, IntervalTime):
        super(DataSamplingThread, self).__init__()
        
        self.Timer = Qt.QTimer()
        self.Timer.moveToThread(self)
        self.Timer.timeout.connect(self.GenData)

        self.Fs = float(Fs)
        self.nChannels = int(nChannels)
        self.nSamples = int(nSamples)
        self.OutData = np.ndarray((self.nSamples, self.nChannels))
        self.IntervalTime = IntervalTime*1000
        self.Timer.setInterval(self.IntervalTime)
        
        Pcycle = np.round(self.Fs/1)
        Fsig = Fs/Pcycle

        Ts =  1/self.Fs
        tstop = Ts*(Pcycle)
        t = np.arange(0, tstop, Ts)

        samples = np.sin(2*np.pi*Fsig*t)
        self.InSamples = cycle(samples)
        self.chFacts = np.linspace(0, nChannels/10, nChannels)
        
        for isamp in range(self.nSamples):
            samps = self.chFacts * next(self.InSamples)
            self.OutData[isamp, :] = samps

    def run(self, *args, **kwargs):        
        self.Timer.start()
        loop = Qt.QEventLoop()
        loop.exec_()
        
#        while True:
#            Qt.QThread.msleep(self.IntervalTime)
#            self.OutData = np.random.sample(self.OutData.shape)
#            self.NewSample.emit()
#    
    def GenData(self):
#        for isamp in range(self.nSamples):
#            samps = self.chFacts * next(self.InSamples)
#            self.OutData[isamp, :] = samps
#        self.OutData = self.OutData + np.random.sample(self.OutData.shape)            
#        self.OutData = np.random.sample(self.OutData.shape)
        self.NewSample.emit()


class MainWindow(Qt.QWidget):
    ''' Main Window '''

    def __init__(self):
        super(MainWindow, self).__init__()

        layout = Qt.QVBoxLayout(self) 

        self.btnGen = Qt.QPushButton("Start Gen!")
        layout.addWidget(self.btnGen)

        self.DataGenParams = DataGeneratorParameters(name='Data Generator')
        self.Parameters = Parameter.create(name='params',
                                           type='group',
                                           children=(self.DataGenParams,))

        self.FileParameters = FileMod.SaveFileParameters(QTparent=self,
                                                         name='Record File')
        self.Parameters.addChild(self.FileParameters)
        
        
        self.Parameters.sigTreeStateChanged.connect(self.on_pars_changed)
        self.treepar = ParameterTree()
        self.treepar.setParameters(self.Parameters, showTop=False)
        self.treepar.setWindowTitle('pyqtgraph example: Parameter Tree')

        layout.addWidget(self.treepar)

#        self.setGeometry(550, 10, 300, 700)
        self.setWindowTitle('MainWindow')

        self.btnGen.clicked.connect(self.on_btnGen)
        self.threadGen = None

#        self.FileParams = Parameter.create(name='File Params',
#                                           type='group',
#                                           children=SaveFilePars)
#        self.pars.addChild(self.FileParams)
#        self.FileParams.param('Save File').sigActivated.connect(self.FileDialog)
#
#        self.GenChannelsViewParams(nChannels=self.DataGenConf.NChannels.value(),
#                                   nWindows=1)
 
    def on_pars_changed(self, param, changes):
        print("tree changes:")
        for param, change, data in changes:
            path = self.Parameters.childPath(param)
            if path is not None:
                childName = '.'.join(path)
            else:
                childName = param.name()
        print('  parameter: %s'% childName)
        print('  change:    %s'% change)
        print('  data:      %s'% str(data))
        print('  ----------')

    def on_btnGen(self):
        print('button')

        
if __name__ == '__main__':
    app = Qt.QApplication([])
    mw  = MainWindow()
    mw.show()
    app.exec_()        
        