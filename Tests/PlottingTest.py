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
import PyTimeMux8x8Acquisition.PyTMCore.SampleGenerator as SampGen
import PyTimeMux8x8Acquisition.PyTMCore.PlotModule as PltMod


class MainWindow(Qt.QWidget):
    ''' Main Window '''

    def __init__(self):
        super(MainWindow, self).__init__()

        layout = Qt.QVBoxLayout(self) 

        self.btnGen = Qt.QPushButton("Start Gen!")
        layout.addWidget(self.btnGen)

        self.DataGenParams = SampGen.DataGeneratorParameters(name='Data Generator')
        self.Parameters = Parameter.create(name='params',
                                           type='group',
                                           children=(self.DataGenParams,))

        self.FileParameters = FileMod.SaveFileParameters(QTparent=self,
                                                         name='Record File')
        self.Parameters.addChild(self.FileParameters)
        
        self.PlotParams = PltMod.PlotterParameters(name='Plot options')
        self.PlotParams.SetChannels(self.DataGenParams.GetChannels())
        self.Parameters.addChild(self.PlotParams)
        
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

        if childName == 'Data Generator.nChannels':
            self.PlotParams.SetChannels(self.DataGenParams.GetChannels())

    def on_btnGen(self):
        if self.threadGen is None:
            GenKwargs = self.DataGenParams.GetParams()
            self.threadGen = SampGen.DataSamplingThread(**GenKwargs)
            self.threadGen.NewSample.connect(self.on_NewSample)
            self.threadGen.start()
            
            self.btnGen.setText("Stop Gen")
            self.OldTime = time.time()
        else:
            self.threadGen.NewSample.disconnect()
            self.threadGen.terminate()
            self.threadGen = None
            self.btnGen.setText("Start Gen")
            
    def on_NewSample(self):
        ''' Visualization of streaming data-WorkThread. '''
        Ts = time.time() - self.OldTime
        self.OldTime = time.time()
        print('Sample time', Ts)


if __name__ == '__main__':
    app = Qt.QApplication([])
    mw  = MainWindow()
    mw.show()
    app.exec_()        
        