#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Feb 28 11:02:02 2019

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
                                  'suffix': 's'},
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

SaveFilePars = [{'name': 'Save File',
                 'type': 'action'},
                {'name': 'File Path',
                 'type': 'str',
                 'value': ''},
                {'name': 'MaxSize',
                 'type': 'int',
                 'siPrefix': True,
                 'suffix': 'B',
                 'limits': (1e6, 1e9),
                 'step': 1e6,
                 'value': 50e6}
                ]


###############################################################################


class SamplingSettingsParameters(pTypes.GroupParameter):

    DigColumns = None
    Channels = None

    def __init__(self, **kwargs):
        super(SamplingSettingsParameters, self).__init__(**kwargs)
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

    def on_Fs_Changed(self):
        print(self.Fs.value())
#            retime = len(self.DigColumns)*self.SampsCo*self.nBlocks*1/self.Fs.value()
#            print(retime)
#            self.SampSet.param('Inttime').value(retime)
        self.GenSampKwargs()

    def on_Row_Changed(self):
        Channels = []
        for p in self.RowChannels.children():
            if p.value() is True:
                Channels.append(p.name())
        self.Channels = Channels
        self.GenChannelsConfigKwargs()

    def on_Col_Changed(self):
        DigColumns = []
        for p in self.ColChannels.children():
            if p.value() is True:
                DigColumns.append(p.name())
        self.DigColumns = DigColumns
        self.GenChannelsConfigKwargs()

    def GetConfig(self):
        self.GenChannelsConfigKwargs()

    def GenSampKwargs(self):
        GenKwargs = {}
        for p in self.SampSet.children():
            GenKwargs[p.name()] = p.value()
        print(GenKwargs)

    def GenChannelsConfigKwargs(self):
        ChanKwargs = {}
        for p in self.ChsConfig.children():
            if p.name() is 'Channels':
                ChanKwargs[p.name()] = self.Channels
            elif p.name() is 'DigColumns':
                ChanKwargs[p.name()] = self.DigColumns
            else:
                ChanKwargs[p.name()] = p.value()
        print(self.Channels)
        print(ChanKwargs)


###############################################################################


class MainWindow(Qt.QWidget):
    ''' Main Window '''

    def __init__(self):
        super(MainWindow, self).__init__()

        # Get vertical layout
        layout = Qt.QVBoxLayout(self)
        # Insert Button
        self.btnGen = Qt.QPushButton("Start Gen!")
        layout.addWidget(self.btnGen)

        # Conf parameter tree
        # Sampling settings
        self.SamplingSettingPar = SamplingSettingsParameters(name='Acquisition Settings')
        self.Parameters = Parameter.create(name='App Parameters',
                                           type='group',
                                           children=(self.SamplingSettingPar,))

        self.FilePars = Parameter.create(name='File Params',
                                         type='group',
                                         children=SaveFilePars)
        self.Parameters.addChild(self.FilePars)

        # Add parameter tree to layout
        self.treepar = ParameterTree()
        self.treepar.setParameters(self.Parameters, showTop=False)
        self.treepar.setWindowTitle('pyqtgraph example: Parameter Tree')
        layout.addWidget(self.treepar)

        self.Parameters.sigTreeStateChanged.connect(self.on_pars_changed)
        self.FilePars.param('Save File').sigActivated.connect(self.FileDialog)

        self.setGeometry(600, 30, 400, 700)
        self.setWindowTitle('MainWindow')

        self.btnGen.clicked.connect(self.on_btnGen)

    def FileDialog(self):
        RecordFile, _ = QFileDialog.getSaveFileName(self,
                                                    "Recording File",
                                                    "",
                                                    )
        if RecordFile:
            if not RecordFile.endswith('.h5'):
                RecordFile = RecordFile + '.h5'
            self.pars.param('File Path').setValue(RecordFile)

    def on_btnGen(self):
        print('button')

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


if __name__ == '__main__':
    app = Qt.QApplication([])
    mw = MainWindow()
    mw.show()
    app.exec_()
