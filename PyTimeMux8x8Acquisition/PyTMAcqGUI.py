#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Mar  6 12:29:47 2019

@author: aguimera
"""


from __future__ import print_function
from PyQt5 import Qt
from qtpy.QtWidgets import (QHeaderView, QCheckBox, QSpinBox, QLineEdit,
                            QDoubleSpinBox, QTextEdit, QComboBox,
                            QTableWidget, QAction, QMessageBox, QFileDialog,
                            QInputDialog)

from qtpy import QtWidgets, uic
import numpy as np
import time
import os
import sys
from pyqtgraph.parametertree import Parameter, ParameterTree

# import PyCont.FileModule as FileMod
# import PyCont.PlotModule as PltMod
import PyqtTools.FileModule as FileMod
import PyqtTools.PlotModule as PltMod

#import PyTMCore.FileModule as FileMod
#import PyTMCore.PlotModule as PltMod
import PyTMCore.TMacqThread as AcqMod


class MainWindow(Qt.QWidget):
    ''' Main Window '''

    def __init__(self):
        super(MainWindow, self).__init__()

        layout = Qt.QVBoxLayout(self)

        self.btnAcq = Qt.QPushButton("Start Acq!")
        layout.addWidget(self.btnAcq)

        self.SamplingPar = AcqMod.SampSetParam(name='SampSettingConf')
        self.Parameters = Parameter.create(name='App Parameters',
                                           type='group',
                                           children=(self.SamplingPar,))

        self.SamplingPar.NewConf.connect(self.on_NewConf)

        self.PlotParams = PltMod.PlotterParameters(name='Plot options')
        self.PlotParams.SetChannels(self.SamplingPar.GetChannelsNames())
        self.PlotParams.param('Fs').setValue(self.SamplingPar.FsxCh.value())

        self.Parameters.addChild(self.PlotParams)

        self.RawPlotParams = PltMod.PlotterParameters(name='Raw Plot')
        self.RawPlotParams.SetChannels(self.SamplingPar.GetRowNames())
        self.RawPlotParams.param('Fs').setValue(self.SamplingPar.Fs.value())

        self.Parameters.addChild(self.RawPlotParams)

        self.PSDParams = PltMod.PSDParameters(name='PSD Options')
        self.PSDParams.param('Fs').setValue(self.SamplingPar.FsxCh.value())
        self.Parameters.addChild(self.PSDParams)
        self.Parameters.sigTreeStateChanged.connect(self.on_pars_changed)

        self.treepar = ParameterTree()
        self.treepar.setParameters(self.Parameters, showTop=False)
        self.treepar.setWindowTitle('pyqtgraph example: Parameter Tree')

        layout.addWidget(self.treepar)

        self.setGeometry(650, 20, 400, 800)
        self.setWindowTitle('MainWindow')

        self.btnAcq.clicked.connect(self.on_btnStart)
        self.threadAcq = None
        self.threadSave = None
        self.threadPlotter = None

        self.FileParameters = FileMod.SaveFileParameters(QTparent=self,
                                                         name='Record File')
        self.Parameters.addChild(self.FileParameters)

        self.ConfigParameters = FileMod.SaveSateParameters(QTparent=self,
                                                           name='Configuration File')
        self.Parameters.addChild(self.ConfigParameters)

#        self.FileParams = Parameter.create(name='File Params',
#                                           type='group',
#                                           children=self.FileParameters)
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

        if childName == 'SampSettingConf.Sampling Settings.FsxCh':
            self.PlotParams.param('Fs').setValue(data)
            self.PSDParams.param('Fs').setValue(data)

        if childName == 'SampSettingConf.Sampling Settings.Fs':
            self.RawPlotParams.param('Fs').setValue(data)

        if childName == 'SampSettingConf.Sampling Settings.Vgs':
            if self.threadAcq:
                Vds = self.threadAcq.DaqInterface.Vds
                self.threadAcq.DaqInterface.SetBias(Vgs=data, Vds=Vds)

        if childName == 'SampSettingConf.Sampling Settings.Vds':
            if self.threadAcq:
                Vgs = self.threadAcq.DaqInterface.Vgs
                self.threadAcq.DaqInterface.SetBias(Vgs=Vgs, Vds=data)

        if childName == 'Plot options.RefreshTime':
            if self.threadPlotter is not None:
                self.threadPlotter.SetRefreshTime(data)

        if childName == 'Plot options.ViewTime':
            if self.threadPlotter is not None:
                self.threadPlotter.SetViewTime(data)

        if childName == 'Raw Plot.ViewTime':
            if self.threadPlotterRaw is not None:
                self.threadPlotterRaw.SetViewTime(data)

        if childName == 'Raw Plot.RefreshTime':
            if self.threadPlotterRaw is not None:
                self.threadPlotterRaw.SetRefreshTime(data)

    def on_NewConf(self):
        self.Parameters.sigTreeStateChanged.disconnect()
        self.PlotParams.SetChannels(self.SamplingPar.GetChannelsNames())
#        ch = {}
#        for i, r in enumerate(sorted(self.SamplingPar.Rows)):
#            ch[r] = i
        self.RawPlotParams.SetChannels(self.SamplingPar.GetRowNames())
        self.Parameters.sigTreeStateChanged.connect(self.on_pars_changed)

    def on_btnStart(self):
        if self.threadAcq is None:
            GenKwargs = self.SamplingPar.GetSampKwargs()
            GenChanKwargs = self.SamplingPar.GetChannelsConfigKwargs()
            AvgIndex = self.SamplingPar.SampSet.param('nAvg').value()
            print(GenChanKwargs)
            AnalogOutputsKwargs = self.SamplingPar.GetAnalogOutputs()
            if AnalogOutputsKwargs['Ao2_en'] is True:
                GenChanKwargs['ChVg'] = 'ao2'
                GenKwargs['Vg'] = AnalogOutputsKwargs['ao2']
            else:
                GenKwargs['Vg'] = None

            if AnalogOutputsKwargs['Ao3_en'] is True:
                GenChanKwargs['ChVsig'] = 'ao3'
                GenKwargs['Vsig'] = AnalogOutputsKwargs['ao3']
            else:
                GenKwargs['Vsig'] = None

            self.threadAcq = AcqMod.DataAcquisitionThread(ChannelsConfigKW=GenChanKwargs,
                                                          SampKw=GenKwargs,
                                                          AvgIndex=AvgIndex)

            self.threadAcq.NewMuxData.connect(self.on_NewSample)
            self.threadAcq.start()

            PlotterKwargs = self.PlotParams.GetParams()

#            FileName = self.Parameters.param('File Path').value()
            FileName = self.FileParameters.FilePath()
            print('Filename', FileName)
            if FileName == '':
                print('No file')
            else:
                if os.path.isfile(FileName):
                    print('Remove File')
                    os.remove(FileName)
                MaxSize = self.FileParameters.param('MaxSize').value()
#                MaxSize = self.Parameters.param('MaxSize').value()
                self.threadSave = FileMod.DataSavingThread(FileName=FileName,
                                                           nChannels=PlotterKwargs['nChannels'],
                                                           MaxSize=MaxSize)
                self.threadSave.start()
            self.threadPlotter = PltMod.Plotter(**PlotterKwargs)
            self.threadPlotter.start()

            RawPlotterKwargs = self.RawPlotParams.GetParams()
#            print(PlotterKwargs)
            self.threadPlotterRaw = PltMod.Plotter(ShowTime=False,
                                                   **RawPlotterKwargs)
            self.threadPlotterRaw.start()

            self.threadPSDPlotter = PltMod.PSDPlotter(ChannelConf=PlotterKwargs['ChannelConf'],
                                                      nChannels=PlotterKwargs['nChannels'],
                                                      **self.PSDParams.GetParams())
            self.threadPSDPlotter.start()

            self.btnAcq.setText("Stop Gen")
            self.OldTime = time.time()
            self.Tss = []
        else:
            self.threadAcq.DaqInterface.Stop()
            self.threadAcq = None

            if self.threadSave is not None:
                self.threadSave.terminate()
                self.threadSave = None

            self.threadPlotter.terminate()
            self.threadPlotter = None

            self.btnAcq.setText("Start Gen")

    def on_NewSample(self):
        ''' Visualization of streaming data-WorkThread. '''
        Ts = time.time() - self.OldTime
        self.Tss.append(Ts)
        self.OldTime = time.time()
        print(self.threadAcq.aiData.shape)
        if self.threadSave is not None:
            self.threadSave.AddData(self.threadAcq.OutData.transpose())
        self.threadPlotter.AddData(self.threadAcq.OutData.transpose())
        self.threadPlotterRaw.AddData(self.threadAcq.aiData.transpose())
        self.threadPSDPlotter.AddData(self.threadAcq.OutData.transpose())
        print('Sample time', Ts, np.mean(self.Tss))


def main():
    import argparse
    import pkg_resources

    # Add version option
    __version__ = pkg_resources.require("PyCont")[0].version
    parser = argparse.ArgumentParser()
    parser.add_argument('--version', action='version',
                        version='%(prog)s {version}'.format(
                            version=__version__))
    parser.parse_args()

    app = QtWidgets.QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
