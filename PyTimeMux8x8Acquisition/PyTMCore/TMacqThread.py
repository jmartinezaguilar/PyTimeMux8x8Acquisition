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
import PyTMCore.FileModule as FileMod


SampSettingConf = ({'name': 'Channels Config',
                    'type': 'group',
                    'children': ({'title': 'Acquire DC',
                                  'name': 'AcqDC',
                                  'type': 'bool',
                                  'value': True},
                                 {'title': 'Acquire AC',
                                  'name': 'AcqAC',
                                  'type': 'bool',
                                  'value': True},
                                 {'tittle': 'Row Channels',
                                  'name': 'Channels',
                                  'type': 'group',
                                  'children': ({'name': 'Ch05',
                                                'tip': 'Ch05',
                                                'type': 'bool',
                                                'value': True},
                                               {'name': 'Ch06',
                                                'tip': 'Ch06',
                                                'type': 'bool',
                                                'value': True},
                                               {'name': 'Ch07',
                                                'tip': 'Ch07',
                                                'type': 'bool',
                                                'value': True},
                                               {'name': 'Ch08',
                                                'tip': 'Ch08',
                                                'type': 'bool',
                                                'value': True},
                                               {'name': 'Ch13',
                                                'tip': 'Ch13',
                                                'type': 'bool',
                                                'value': True},
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
                                                'value': True},
                                               {'name': 'Col2',
                                                'tip': 'Col2',
                                                'type': 'bool',
                                                'value': True},
                                               {'name': 'Col3',
                                                'tip': 'Col3',
                                                'type': 'bool',
                                                'value': True},
                                               {'name': 'Col4',
                                                'tip': 'Col4',
                                                'type': 'bool',
                                                'value': True},
                                               {'name': 'Col5',
                                                'tip': 'Col5',
                                                'type': 'bool',
                                                'value': True},
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
                                  'value': 1e4,
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
                                  'value': 1000,
                                  'step': 10,
                                  'limits': (10, 10000)},
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
                                 {'name': 'Vds',
                                  'type': 'float',
                                  'value': 0.05,
                                  'step': 0.01,
                                  'limits': (0, 0.1)},
                                 {'name': 'Vgs',
                                  'type': 'float',
                                  'value': 0.1,
                                  'step': 0.1,
                                  'limits': (-0.1, 0.5)}, ), }
                   )


###############################################################################


class SampSetParam(pTypes.GroupParameter):

    Columns = None
    Rows = None

    def __init__(self, **kwargs):
        super(SampSetParam, self).__init__(**kwargs)
        self.addChildren(SampSettingConf)

        self.SampSet = self.param('Sampling Settings')
        self.Fs = self.SampSet.param('Fs')
        self.SampsCo = self.SampSet.param('nSampsCo')
        self.nBlocks = self.SampSet.param('nBlocks')

        self.ChsConfig = self.param('Channels Config')
        self.RowChannels = self.ChsConfig.param('Channels')
        self.ColChannels = self.ChsConfig.param('DigColumns')

        # Init Settings
        self.on_Row_Changed()
        self.on_Col_Changed()
        self.GetConfig()
        self.GenSampKwargs()

        # Signals
        self.RowChannels.sigTreeStateChanged.connect(self.on_Row_Changed)
        self.ColChannels.sigTreeStateChanged.connect(self.on_Col_Changed)
        self.ChsConfig.sigTreeStateChanged.connect(self.GetConfig)
        self.Fs.sigValueChanged.connect(self.on_Fs_Changed)
        self.SampsCo.sigValueChanged.connect(self.on_Fs_Changed)
        self.nBlocks.sigValueChanged.connect(self.on_Fs_Changed)

    def on_Fs_Changed(self):
        Ts = 1/self.Fs.value()
        FsxCh = 1/(Ts*self.SampsCo.value()*len(self.Columns))
        if self.Config['AcqDC'] and self.Config['AcqAC'] is True:
            FsxCh = FsxCh * 0.5
        IntTime = (1/(FsxCh)*self.nBlocks.value())
        self.SampSet.param('FsxCh').setValue(FsxCh)
        self.SampSet.param('Inttime').setValue(IntTime)
        self.GenSampKwargs()

    def on_Row_Changed(self):
        Rows = []
        for p in self.RowChannels.children():
            if p.value() is True:
                Rows.append(p.name())
        self.Rows = Rows
        self.GenChannelsConfigKwargs()

    def on_Col_Changed(self):
        Columns = []
        for p in self.ColChannels.children():
            if p.value() is True:
                Columns.append(p.name())
        self.Columns = Columns
        self.GenChannelsConfigKwargs()
        self.on_Fs_Changed()

    def GenerateChannelsNames(self):
        if self.Columns:
            Ind = 0
            ChannelNames = {}
            for ty in self.Config:
                for Row in self.Rows:
                    for Col in self.Columns:
                        if self.Config[ty] is True:
                            ChannelNames[Row + Col + ty.split('Acq')[1]] = Ind
                            Ind += 1
            self.ChannelNames = ChannelNames
        return self.ChannelNames

    def GetConfig(self):
        self.GenChannelsConfigKwargs()
        self.on_Fs_Changed()

    def GenSampKwargs(self):
        GenKwargs = {}
        for p in self.SampSet.children():
            GenKwargs[p.name()] = p.value()
        print(GenKwargs)
        return GenKwargs

    def GenChannelsConfigKwargs(self):
        ChanKwargs = {}
        Config = {}
        for p in self.ChsConfig.children():
            if p.name() is 'Channels':
                ChanKwargs[p.name()] = self.Rows
            elif p.name() is 'DigColumns':
                ChanKwargs[p.name()] = self.Columns
            else:
                ChanKwargs[p.name()] = p.value()
                Config[p.name()] = p.value()

        self.Config = Config
        self.GenerateChannelsNames()
        print(ChanKwargs)

###############################################################################


class DataAcquisitionThread(Qt.QThread):
    NewMuxData = Qt.pyqtSignal()

    def __init__(self, ChannelsConfigKW, SampKw, BufferSize, AvgIndex=5):

        super(DataAcquisitionThread, self).__init__()

        self.DaqInterface = CoreMod.ChannelsConfig(**ChannelsConfigKW)
        self.DaqInterface.DataEveryNEvent = self.NewData
        self.SampKw = SampKw
        self.AvgIndex = AvgIndex

#        self.MuxBuffer = Buffer(BufferSize=BufferSize,
#                                nChannels=self.DaqInterface.nChannels)
#        self.MuxBuffer = FileMod.FileBuffer()

    def run(self, *args, **kwargs):
        self.DaqInterface.StartAcquisition(**self.SampKw)
        print('Run')
        loop = Qt.QEventLoop()
        loop.exec_()

    def CalcAverage(self, MuxData):
        print('CalcAverage')

#        Avg = np.mean(LinesSorted[:,-2:,:], axis=1)
        return np.mean(MuxData[:, self.AvgIndex:, :], axis=1)

    def NewData(self, aiData, MuxData):
        self.OutData = self.CalcAverage(MuxData)
        self.NewMuxData.emit()
