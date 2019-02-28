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




#ChannelsConfigKW = {'Channels': ('Ch01',
#                                 'Ch02',
#                                 'Ch03',
#                                 'Ch04'),
#                    'DigColumns': ('Col1',
#                                   'Col2',
#                                   'Col3',
#                                   'Col4',
#                                   'Col5',
#                                   'Col6',
#                                   'Col7',
#                                   'Col8'),
#                    'AcqDC': True,
#                    'AcqAC': True,
#                    }
#
#SampKw = {'Fs': 100e3,
#          'nSampsCo': 6,
#          'nBlocks': 1000,
#          'Vgs': 0.1,
#          'Vds': 0.05}

SampSettingConf = ({'name': 'Channels Config',
                    'type': 'group',
                    'children': ({'name': 'Acquire DC',
                                  'tip': 'AcqDC',
                                  'type': 'bool'},
                                 {'name': 'Acquire AC',
                                  'tip': 'AcqAC',
                                  'type': 'bool'},
                                {'name': 'Row Channels',
                                 'type': 'group',
                                 'children':({'name': 'Ch01',
                                              'tip': 'Ch01',
                                              'type': 'bool'},),},
                                     ),},
                        
                    {'name': 'Sampling Settings',
                    'type': 'group',
                    'children': ({'title': 'Sampling Frequency',
                                  'name': 'Fs',
                                  'type': 'float',
                                  'value': 1e4,
                                  'step': 100,
                                  'siPrefix': True,
                                  'suffix': 'Hz'},
                                 {'name': 'Column Samples',
                                  'tip': 'FsKw.nSampsCo',
                                  'type': 'int',
                                  'value': 10,
                                  'step': 1,
                                  'limits': (1, 100)},
                                 {'name': 'Acquired Blocks',
                                  'tip': 'FsKw.nBlocks',
                                  'type': 'int',
                                  'value': 1000,
                                  'step': 10,
                                  'limits': (10, 10000)},
                                 {'name': 'Inttime',
                                  'title': 'Interrup Time',
                                  'type': 'float',
                                  'value': 0.10,
                                  'step': 0.01,
                                  'limits': (0.10, 50),                   
                                  'siPrefix': True,
                                  'suffix': 's'},),}
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

class SamplingSettingsParameters(pTypes.GroupParameter):
        def __init__(self, **kwargs):
            super(SamplingSettingsParameters,self).__init__(**kwargs)
            self.addChildren(SampSettingConf)
            
            self.SampSet = self.param('Sampling Settings')
            self.Fs = self.SampSet.param('Fs')
            
            self.Fs.sigValueChanged.connect(self.on_Fs_Changed)

        def on_Fs_Changed(self):
            print(self.Fs.value())
            self.GenSampKwargs()
            
        def GenSampKwargs(self):
            GenKwargs = {}
            for p in self.SampSet.children():
                GenKwargs[p.name()] = p.value()
            print(GenKwargs)    

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
        self.SamplingSettingPar = SamplingSettingsParameters(name='Sampling Settings')
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



#        self.setGeometry(550, 10, 300, 700)
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
        print('  parameter: %s'% childName)
        print('  change:    %s'% change)
        print('  data:      %s'% str(data))
        print('  ----------')
       



if __name__ == '__main__':
    app = Qt.QApplication([])
    mw  = MainWindow()
    mw.show()
    app.exec_() 