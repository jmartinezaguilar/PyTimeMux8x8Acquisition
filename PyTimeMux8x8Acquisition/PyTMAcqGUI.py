#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Mar  6 12:29:47 2019

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

import PyTMCore.FileModule as FileMod
#import PyTimeMux8x8Acquisition.PyTMCore.SampleGenerator as SampGen
import PyTMCore.PlotModule as PltMod
import PyTMCore.TMacqThread as AcqMod


class MainWindow(Qt.QWidget):
    ''' Main Window '''

    def __init__(self):
        super(MainWindow, self).__init__()

        layout = Qt.QVBoxLayout(self)

        self.btnGen = Qt.QPushButton("Start Gen!")
        layout.addWidget(self.btnGen)

#        self.DataGenParams = SampGen.DataGeneratorParameters(name='Data Generator')
#        self.Parameters = Parameter.create(name='params',
#                                           type='group',
#                                           children=(self.DataGenParams,))
#
        self.SamplingPar = AcqMod.SampSetParam(name='Acquisition Settings')
        self.Parameters = Parameter.create(name='App Parameters',
                                           type='group',
                                           children=(self.SamplingPar,))

        self.FileParameters = FileMod.SaveFileParameters(QTparent=self,
                                                         name='Record File')
        self.Parameters.addChild(self.FileParameters)

        self.PlotParams = PltMod.PlotterParameters(name='Plot options')
        self.PlotParams.SetChannels(self.SamplingPar.GenerateChannelsNames())
        self.PlotParams.param('Fs').setValue(self.SamplingPar.param('Fs').value())
#        self.PlotParams.param('Fs').setValue(self.DataGenParams.param('Fs').value())

        self.Parameters.addChild(self.PlotParams)

        self.Parameters.sigTreeStateChanged.connect(self.on_pars_changed)
        self.treepar = ParameterTree()
        self.treepar.setParameters(self.Parameters, showTop=False)
        self.treepar.setWindowTitle('pyqtgraph example: Parameter Tree')

        layout.addWidget(self.treepar)

#        self.setGeometry(550, 10, 300, 700)
        self.setWindowTitle('MainWindow')

        self.btnGen.clicked.connect(self.on_btnGen)
        self.threadAcq = None
        self.threadSave = None
        self.threadPlotter = None

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
        print('  parameter: %s' % childName)
        print('  change:    %s' % change)
        print('  data:      %s' % str(data))
        print('  ----------')

        if childName == 'Data Generator.nChannels':
            self.PlotParams.SetChannels(self.SamplingPar.GenerateChannelsNames())

        if childName == 'Data Generator.Fs':
            self.PlotParams.param('Fs').setValue(data)

        if childName == 'Plot options.RefreshTime':
            if self.threadPlotter is not None:
                self.threadPlotter.SetRefreshTime(data)

        if childName == 'Plot options.ViewTime':
            if self.threadPlotter is not None:
                self.threadPlotter.SetViewTime(data)

    def on_btnGen(self):
        if self.threadAcq is None:
            GenKwargs = self.SamplingPar.GenSampKwargs()
            self.threadAcq = AcqMod.DataAcquisitionThread(**GenKwargs)
            self.threadAcq.NewSample.connect(self.on_NewSample)
            self.threadAcq.start()

            FileName = self.FileParameters.param('File Path').value()
            if FileName == '':
                print('No file')
            else:
                if os.path.isfile(FileName):
                    print('Remove File')
                    os.remove(FileName)
                MaxSize = self.FileParameters.param('MaxSize').value()
                self.threadSave = FileMod.DataSavingThread(FileName=FileName,
                                                           nChannels=GenKwargs['nChannels'],
                                                           MaxSize=MaxSize)
                self.threadSave.start()

            PlotterKwargs = self.PlotParams.GetParams()
            print(PlotterKwargs)
            self.threadPlotter = PltMod.Plotter(**PlotterKwargs)
            self.threadPlotter.start()

#            self.threadPSDPlotter = PltMod.PSDPlotter(nChannels=GenKwargs['nChannels'],
#                                                      ChannelConf=PlotterKwargs['ChannelConf'])
#            self.threadPSDPlotter.start()            
#
            self.btnGen.setText("Stop Gen")
            self.OldTime = time.time()
            self.Tss = []
        else:
            self.threadAcq.NewSample.disconnect()
            self.threadAcq.terminate()
            self.threadAcq = None

            if self.threadSave is not None:
                self.threadSave.terminate()
                self.threadSave = None

            self.threadPlotter.terminate()
            self.threadPlotter = None

            self.btnGen.setText("Start Gen")

    def on_NewSample(self):
        ''' Visualization of streaming data-WorkThread. '''
        Ts = time.time() - self.OldTime
        self.Tss.append(Ts)
        self.OldTime = time.time()
        if self.threadSave is not None:
            self.threadSave.AddData(self.threadGen.OutData)
        self.threadPlotter.AddData(self.threadGen.OutData)
#        self.threadPSDPlotter.AddData(self.threadGen.OutData)
        print('Sample time', Ts, np.mean(self.Tss))


if __name__ == '__main__':
    app = Qt.QApplication([])
    mw = MainWindow()
    mw.show()
    app.exec_()
