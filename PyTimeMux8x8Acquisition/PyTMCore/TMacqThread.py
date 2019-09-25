#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Mar  6 12:25:45 2019

@author: aguimera
"""

from PyQt5 import Qt
import pyqtgraph.parametertree.parameterTypes as pTypes
import numpy as np
import PyTMCore.TMacqCore as CoreMod
import PyCont.FileModule as FileMod


SampSettingConf = ({'title': 'Channels Config',
                    'name': 'ChsConfig',
                    'type': 'group',
                    'children': ({'title': 'Acquire DC',
                                  'name': 'AcqDC',
                                  'type': 'bool',
                                  'value': False},
                                 {'title': 'Acquire AC',
                                  'name': 'AcqAC',
                                  'type': 'bool',
                                  'value': True},
                                 {'title': 'Gain DC',
                                  'name': 'DCGain',
                                  'type': 'float',
                                  'value': 10e3,
                                  'siPrefix': True, },
                                 {'title': 'Gain AC',
                                  'name': 'ACGain',
                                  'type': 'float',
                                  'value': 1e5,
                                  'siPrefix': True, },
                                 {'tittle': 'Row Channels',
                                  'name': 'Channels',
                                  'type': 'group',
                                  'children': ({'name': 'Ch05',
                                                'tip': 'Ch05',
                                                'type': 'bool',
                                                'value': False},
                                               {'name': 'Ch06',
                                                'tip': 'Ch06',
                                                'type': 'bool',
                                                'value': False},
                                               {'name': 'Ch07',
                                                'tip': 'Ch07',
                                                'type': 'bool',
                                                'value': False},
                                               {'name': 'Ch08',
                                                'tip': 'Ch08',
                                                'type': 'bool',
                                                'value': False},
                                               {'name': 'Ch13',
                                                'tip': 'Ch13',
                                                'type': 'bool',
                                                'value': False},
                                               {'name': 'Ch14',
                                                'tip': 'Ch14',
                                                'type': 'bool',
                                                'value': True},
                                               {'name': 'Ch15',
                                                'tip': 'Ch15',
                                                'type': 'bool',
                                                'value': True},
                                               {'name': 'Ch16',
                                                'tip': 'Ch16',
                                                'type': 'bool',
                                                'value': True}, ), },

                                 {'tittle': 'Columns Channels',
                                  'name': 'DigColumns',
                                  'type': 'group',
                                  'children': ({'name': 'Col1',
                                                'tip': 'Col1',
                                                'type': 'bool',
                                                'value': False},
                                               {'name': 'Col2',
                                                'tip': 'Col2',
                                                'type': 'bool',
                                                'value': False},
                                               {'name': 'Col3',
                                                'tip': 'Col3',
                                                'type': 'bool',
                                                'value': False},
                                               {'name': 'Col4',
                                                'tip': 'Col4',
                                                'type': 'bool',
                                                'value': False},
                                               {'name': 'Col5',
                                                'tip': 'Col5',
                                                'type': 'bool',
                                                'value': False},
                                               {'name': 'Col6',
                                                'tip': 'Col6',
                                                'type': 'bool',
                                                'value': True},
                                               {'name': 'Col7',
                                                'tip': 'Col7',
                                                'type': 'bool',
                                                'value': True},
                                               {'name': 'Col8',
                                                'tip': 'Col8',
                                                'type': 'bool',
                                                'value': True}, ), },
                                 ), },

                   {'name': 'Sampling Settings',
                    'type': 'group',
                    'children': ({'title': 'Sampling Frequency',
                                  'name': 'Fs',
                                  'type': 'float',
                                  'value': 100e3,
                                  'step': 100,
                                  'siPrefix': True,
                                  'suffix': 'Hz'},
                                 {'title': 'Column Samples',
                                  'name': 'nSampsCo',
                                  'type': 'int',
                                  'value': 10,
                                  'step': 1,
                                  'limits': (1, 100)},
                                 {'title': 'Acquired Blocks',
                                  'name': 'nBlocks',
                                  'type': 'int',
                                  'value': 3000,
                                  'step': 10,
                                  'limits': (10, 10000)},
                                 {'title': 'Averaging',
                                  'name': 'nAvg',
                                  'type': 'int',
                                  'value': 5,
                                  'step': 1,
                                  'limits': (1, 10)},
                                 {'title': 'Interrup Time',
                                  'name': 'Inttime',
                                  'type': 'float',
                                  'value': 0.10,
                                  'step': 0.01,
                                  'limits': (0.10, 50),
                                  'siPrefix': True,
                                  'suffix': 's',
                                  'readonly': True},
                                 {'title': 'Fs by Channel',
                                  'name': 'FsxCh',
                                  'type': 'float',
                                  'value': 1e4,
                                  'step': 100,
                                  'siPrefix': True,
                                  'suffix': 'Hz',
                                  'readonly': True},
                                 {'title': '_Vds',
                                  'name': 'Vds',
                                  'type': 'float',
                                  'value': 0.05,
                                  'step': 0.01,
                                  'limits': (-0.1, 0.1)},
                                 {'title': '_Vgs',
                                  'name': 'Vgs',
                                  'type': 'float',
                                  'value': 0.1,
                                  'step': 0.1,
                                  'limits': (-0.1, 0.5)}, ), }
                   )


###############################################################################


class SampSetParam(pTypes.GroupParameter):
    NewConf = Qt.pyqtSignal()

    Columns = []
    Rows = []
    Acq = {}

    def __init__(self, **kwargs):
        super(SampSetParam, self).__init__(**kwargs)
        self.addChildren(SampSettingConf)

        self.SampSet = self.param('Sampling Settings')
        self.Fs = self.SampSet.param('Fs')
        self.FsxCh = self.SampSet.param('FsxCh')
        self.SampsCo = self.SampSet.param('nSampsCo')
        self.nBlocks = self.SampSet.param('nBlocks')
        self.Vds = self.SampSet.param('Vds')

        self.ChsConfig = self.param('ChsConfig')
        self.RowChannels = self.ChsConfig.param('Channels')
        self.ColChannels = self.ChsConfig.param('DigColumns')

        # Init Settings
        self.on_Acq_Changed()
        self.on_Row_Changed()
        self.on_Col_Changed()
        self.on_Fs_Changed()

        print(self.children())
        # Signals
        self.RowChannels.sigTreeStateChanged.connect(self.on_Row_Changed)
        self.ColChannels.sigTreeStateChanged.connect(self.on_Col_Changed)
        self.ChsConfig.param('AcqAC').sigValueChanged.connect(self.on_Acq_Changed)
        self.ChsConfig.param('AcqDC').sigValueChanged.connect(self.on_Acq_Changed)
        self.Fs.sigValueChanged.connect(self.on_Fs_Changed)
        self.SampsCo.sigValueChanged.connect(self.on_Fs_Changed)
        self.nBlocks.sigValueChanged.connect(self.on_Fs_Changed)
        self.Vds.sigValueChanged.connect(self.on_Col_Changed)

#        self.ChsConfig.sigTreeStateChanged.connect(self.GetConfig)

    def on_Acq_Changed(self):
        for p in self.ChsConfig.children():
            if p.name() is 'AcqAC':
                self.Acq[p.name()] = p.value()
            if p.name() is 'AcqDC':
                self.Acq[p.name()] = p.value()
        self.NewConf.emit()

    def on_Fs_Changed(self):
        Ts = 1/self.Fs.value()
        FsxCh = 1/(Ts*self.SampsCo.value()*len(self.Columns))
        IntTime = (1/(FsxCh)*self.nBlocks.value())
        self.SampSet.param('FsxCh').setValue(FsxCh)
        self.SampSet.param('Inttime').setValue(IntTime)

    def on_Row_Changed(self):
        self.Rows = []
        for p in self.RowChannels.children():
            if p.value() is True:
                self.Rows.append(p.name())
        self.NewConf.emit()

    def on_Col_Changed(self):
        self.Columns = []
        for p in self.ColChannels.children():
            if p.value() is True:
                self.Columns.append(p.name())
        self.on_Fs_Changed()
        self.NewConf.emit()

    def GetRowNames(self):
        Ind = 0
        RowNames = {}

        if self.ChsConfig.param('AcqDC').value():
            for Row in self.Rows:
                RowNames[Row + 'DC'] = Ind
                Ind += 1

        if self.ChsConfig.param('AcqAC').value():
            for Row in self.Rows:
                RowNames[Row + 'AC'] = Ind
                Ind += 1

        return RowNames

    def GetChannelsNames(self):
        Ind = 0
        ChannelNames = {}

        if self.ChsConfig.param('AcqDC').value():
            for Row in self.Rows:
                for Col in self.Columns:
                    ChannelNames[Row + Col + 'DC'] = Ind
                    Ind += 1

        if self.ChsConfig.param('AcqAC').value():
            for Row in self.Rows:
                for Col in self.Columns:
                    ChannelNames[Row + Col + 'AC'] = Ind
                    Ind += 1

        return ChannelNames

    def GetSampKwargs(self):
        GenKwargs = {}
        for p in self.SampSet.children():
            GenKwargs[p.name()] = p.value()
        return GenKwargs

    def GetChannelsConfigKwargs(self):
        ChanKwargs = {}
        for p in self.ChsConfig.children():
            if p.name() is 'Channels':
                ChanKwargs[p.name()] = self.Rows
            elif p.name() is 'DigColumns':
                ChanKwargs[p.name()] = self.Columns
            else:
                ChanKwargs[p.name()] = p.value()

        return ChanKwargs

###############################################################################


class DataAcquisitionThread(Qt.QThread):
    NewMuxData = Qt.pyqtSignal()

    def __init__(self, ChannelsConfigKW, SampKw, AvgIndex=5):
        super(DataAcquisitionThread, self).__init__()
        self.DaqInterface = CoreMod.ChannelsConfig(**ChannelsConfigKW)
        self.DaqInterface.DataEveryNEvent = self.NewData
        self.SampKw = SampKw
        self.AvgIndex = AvgIndex

    def run(self, *args, **kwargs):
        self.DaqInterface.StartAcquisition(**self.SampKw)
        loop = Qt.QEventLoop()
        loop.exec_()

    def CalcAverage(self, MuxData):
        return np.mean(MuxData[:, self.AvgIndex:, :], axis=1)

    def NewData(self, aiData, MuxData):
        self.OutData = self.CalcAverage(MuxData)
        self.aiData = aiData
        self.NewMuxData.emit()
