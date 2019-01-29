# -*- coding: utf-8 -*-
"""
Created on Wed Oct 17 12:00:18 2018

@author: user
"""
import sys
import ctypes

import PyGFET.DataStructures as PyData
import PhyREC.NeoInterface as NeoRecord
import PhyREC.PlotWaves as Rplt
#from PyGFET.RecordPlot import PltSlot, PlotRecord

import PyDAQmx as Daq
from ctypes import byref, c_int32
import numpy as np
from scipy import signal
import neo
import quantities as pq
import os

from qtpy.QtWidgets import (QHeaderView, QCheckBox, QSpinBox, QLineEdit,
                            QDoubleSpinBox, QTextEdit, QComboBox,
                            QTableWidget, QAction, QMessageBox, QFileDialog,
                            QInputDialog)

from qtpy import QtWidgets, uic

import matplotlib.pyplot as plt
import deepdish as dd
import matplotlib.cm as cmx
import matplotlib.colors as mpcolors
import pickle


###############################################################################
######
###############################################################################


class ReadAnalog(Daq.Task):

    '''
    Class to read data from Daq card

    TODO - Implement the callback option to read data
    '''

#    Events list
    EveryNEvent = None
    DoneEvent = None

    ContSamps = False
    EverySamps = 1000

    def __init__(self, InChans, Range=5.0):

        Daq.Task.__init__(self)
        self.Channels = InChans

        Dev = self.GetDevName()
        for Ch in self.Channels:
            self.CreateAIVoltageChan(Dev.format(Ch), "",
                                     Daq.DAQmx_Val_RSE,
                                     -Range, Range,
                                     Daq.DAQmx_Val_Volts, None)

        self.AutoRegisterDoneEvent(0)

    def GetDevName(self,):
        # Get Device Name of Daq Card
        n = 1024
        buff = ctypes.create_string_buffer(n)
        Daq.DAQmxGetSysDevNames(buff, n)
        if sys.version_info >= (3,):
            value = buff.value.decode()
        else:
            value = buff.value
        Dev = value + '/{}'

        return Dev

    def ReadData(self, Fs=1000, nSamps=10000, EverySamps=1000):

        self.Fs = Fs
        self.EverySamps = EverySamps

        self.data = np.ndarray([len(self.Channels), ])

        self.CfgSampClkTiming("", Fs, Daq.DAQmx_Val_Rising,
                              Daq.DAQmx_Val_FiniteSamps, nSamps)

        self.AutoRegisterEveryNSamplesEvent(Daq.DAQmx_Val_Acquired_Into_Buffer,
                                            self.EverySamps, 0)
        self.StartTask()

    def ReadContData(self, Fs=1000, EverySamps=1000):
        self.Fs = Fs
        self.EverySamps = np.int32(EverySamps)
        self.ContSamps = True  # TODO check it

        samperr = self.CfgSampClkTiming("", Fs, Daq.DAQmx_Val_Rising,
                                        Daq.DAQmx_Val_ContSamps, self.EverySamps)

        self.CfgInputBuffer(self.EverySamps*10)
        self.AutoRegisterEveryNSamplesEvent(Daq.DAQmx_Val_Acquired_Into_Buffer,
                                            self.EverySamps, 0)

        print (samperr, EverySamps, Fs)
        self.StartTask()
        print ('Errordebug', 'start' )

    def StopContData(self):
        self.StopTask()
        self.ContSamps = False

    def EveryNCallback(self):
        read = c_int32()
        data = np.zeros((self.EverySamps, len(self.Channels)))
        self.ReadAnalogF64(self.EverySamps, 10.0,
                           Daq.DAQmx_Val_GroupByScanNumber,
                           data, data.size, byref(read), None)

        if not self.ContSamps:  # TODO check why stack here
            self.data = np.vstack((self.data, data))

#        print data.size, self.data.shape
        if self.EveryNEvent:
            self.EveryNEvent(data)

    def DoneCallback(self, status):
        self.StopTask()
        self.UnregisterEveryNSamplesEvent()

        if self.DoneEvent:
            self.DoneEvent(self.data)  # TODO check why 1:

        return 0  # The function should return an integer

###############################################################################
#####
###############################################################################


class WriteAnalog(Daq.Task):

    '''
    Class to write data to Daq card
    '''
    def __init__(self, Channels):

        Daq.Task.__init__(self)
        Dev = self.GetDevName()
        for Ch in Channels:
            self.CreateAOVoltageChan(Dev.format(Ch), "",
                                     -5.0, 5.0, Daq.DAQmx_Val_Volts, None)
        self.DisableStartTrig()
        self.StopTask()

    def GetDevName(self,):
        # Get Device Name of Daq Card
        n = 1024
        buff = ctypes.create_string_buffer(n)
        Daq.DAQmxGetSysDevNames(buff, n)
        if sys.version_info >= (3,):
            value = buff.value.decode()
        else:
            value = buff.value
        Dev = value + '/{}'

        return Dev

    def SetVal(self, value):

        self.StartTask()
        self.WriteAnalogScalarF64(1, -1, value, None)
        self.StopTask()


###############################################################################
#####
###############################################################################


class WriteDigital(Daq.Task):

    '''
    Class to write data to Daq card
    '''
    def __init__(self, Channels):
        print 'Init Digital Channels'
        Daq.Task.__init__(self)
        Dev = self.GetDevName()
        for Ch in Channels:
            self.CreateDOChan(Dev.format(Ch), "",
                              Daq.DAQmx_Val_ChanForAllLines)

        self.DisableStartTrig()
        self.StopTask()

    def GetDevName(self):
        n = 1024
        buff = ctypes.create_string_buffer(n)
        Daq.DAQmxGetSysDevNames(buff, n)
        if sys.version_info >= (3,):
            value = buff.value.decode()
        else:
            value = buff.value
        Dev = value + '/{}'

        return Dev

    def SetSignal(self, Signal, nSamps, nLines):
        read = c_int32()
        self.CfgSampClkTiming('ai/SampleClock', 1, Daq.DAQmx_Val_Rising,
                              Daq.DAQmx_Val_ContSamps, Signal.shape[1])
        self.CfgDigEdgeStartTrig('ai/StartTrigger', Daq.DAQmx_Val_Rising)
        self.WriteDigitalLines(Signal.shape[1], False, 1,
                               Daq.DAQmx_Val_GroupByChannel,
                               Signal, byref(read), None)
        self.StartTask()
        print 'End SetSingal', read

###############################################################################
#####
###############################################################################


class ChannelsConfig():

    # Daq card connections mapping 'Chname':(DCout, ACout)
    aiChannels = {'Ch01': ('ai0', 'ai8'),
                  'Ch02': ('ai1', 'ai9'),
                  'Ch03': ('ai2', 'ai10'),
                  'Ch04': ('ai3', 'ai11'),
                  'Ch05': ('ai4', 'ai12'),
                  'Ch06': ('ai5', 'ai13'),
                  'Ch07': ('ai6', 'ai14'),
                  'Ch08': ('ai7', 'ai15'),
                  'Ch09': ('ai16', 'ai24'),
                  'Ch10': ('ai17', 'ai25'),
                  'Ch11': ('ai18', 'ai26'),
                  'Ch12': ('ai19', 'ai27'),
                  'Ch13': ('ai20', 'ai28'),
                  'Ch14': ('ai21', 'ai29'),
                  'Ch15': ('ai22', 'ai30'),
                  'Ch16': ('ai23', 'ai31'),
                  }

    # Daq card digital connections mapping 'Column name':(VsControl, VdControl)
    doColumns = {'Col1': ('line0', 'line1'),
                 'Col2': ('line2', 'line3'),
                 'Col3': ('line4', 'line5'),
                 'Col4': ('line6', 'line7'),
                 'Col5': ('line8', 'line9'),
                 'Col6': ('line10', 'line11'),
                 'Col7': ('line12', 'line13'),
                 'Col8': ('line14', 'line15'),
                 }

# ChannelIndex = {'Ch01': (0-31, 0-15)}-->> {Chname: (input index, sort index)}
    DCChannelIndex = None
    ACChannelIndex = None
    GateChannelIndex = None

    ChNamesList = None
    # ReadAnalog class with all channels
    Inputs = None
    InitConfig = None

    # Events list
    DCDataDoneEvent = None
    DCDataEveryNEvent = None
    ACDataDoneEvent = None
    ACDataEveryNEvent = None
    GateDataDoneEvent = None
    GateDataEveryNEvent = None

    def DelInputs(self):
        self.Inputs.ClearTask()

    def InitInputs(self, Channels,
                   GateChannel=None,
                   Configuration='Both'):

        if self.Inputs is not None:
            self.DelInputs()

        InChans = []

        self.ChNamesList = sorted(Channels)
        self.DCChannelIndex = {}
        self.ACChannelIndex = {}
        index = 0
        sortindex = 0
        for ch in sorted(Channels):
            if Configuration in ('DC', 'Both'):
                InChans.append(self.aiChannels[ch][0])
                self.DCChannelIndex[ch] = (index, sortindex)
                index += 1
            if Configuration in ('AC', 'Both'):
                InChans.append(self.aiChannels[ch][1])
                self.ACChannelIndex[ch] = (index, sortindex)
                index += 1
            sortindex += 1

        if GateChannel:
            print 'Gate'
            self.GateChannelIndex = {GateChannel: (index, 0)}
            InChans.append(self.aiChannels[GateChannel][0])
        else:
            self.GateChannelIndex = None

        print 'Channels configurtation'
        print 'Gate', self.GateChannelIndex
        print 'Channels ', len(self.ChNamesList)
        print 'ai list ->', InChans
        for ch in sorted(Channels):
            if Configuration == 'DC':
                print ch, ' DC -> ', self.aiChannels[ch][0], self.DCChannelIndex[ch]
                self.ACChannelIndex = self.DCChannelIndex
            elif Configuration == 'AC':
                print ch, ' AC -> ', self.aiChannels[ch][1], self.ACChannelIndex[ch]
                self.DCChannelIndex = self.ACChannelIndex
            else:
                print ch, ' DC -> ', self.aiChannels[ch][0], self.DCChannelIndex[ch]
                print ch, ' AC -> ', self.aiChannels[ch][1], self.ACChannelIndex[ch]

#        self.ChOrder = {}
#        for irow, row in enumerate(self.aiChannels):
#            for icol, col in enumerate(self.doColumns):
#                self.ChOrder[row+col] = (irow, icol)
#        print self.ChOrder

        self.Inputs = ReadAnalog(InChans=InChans)
        # events linking
        self.Inputs.EveryNEvent = self.EveryNEventCallBack
        self.Inputs.DoneEvent = self.DoneEventCallBack

    def InitDigitalChannels(self, DigColumns=None):
        DOChannels = []
        self.DigColumns = DigColumns

        for digc in sorted(self.DigColumns):
            DOChannels.append(self.doColumns[digc][0])
            DOChannels.append(self.doColumns[digc][1])

        print DigColumns
        print DOChannels
        self.ColumnsControl = WriteDigital(Channels=DOChannels)

        ChannelNames = []
        for nRow in range(len(self.ChNamesList)):
            for nCol in range(len(DigColumns)):
                ChannelNames.append(self.ChNamesList[nRow]+DigColumns[nCol])
        self.ChannelNames = sorted(ChannelNames)
        print self.ChannelNames

    def __init__(self, Channels,  GateChannel=None,
                 Configuration='Both',
                 ChVg='ao2', ChVs='ao1', ChVds='ao0'):

        self.InitConfig = {}
        self.InitConfig['Channels'] = Channels
        self.InitConfig['GateChannel'] = GateChannel
        self.InitConfig['Configuration'] = Configuration

        self.InitInputs(Channels=Channels,
                        GateChannel=GateChannel,
                        Configuration=Configuration)

        # Output Channels
        self.VsOut = WriteAnalog((ChVs,))
        self.VdsOut = WriteAnalog((ChVds,))
        self.VgOut = WriteAnalog((ChVg,))

    def SetBias(self, Vds, Vgs):
        print 'ChannelsConfig SetBias Vgs ->', Vgs, 'Vds ->', Vds
        self.VdsOut.SetVal(Vds)
        self.VsOut.SetVal(-Vgs)
        self.BiasVd = Vds-Vgs
        self.Vgs = Vgs
        self.Vds = Vds

    def GenerateDigitalSignal(self, nSampsCo):
        DOut = np.array([], dtype=np.bool)

        for nCol in range(len(self.DigColumns)):
            Lout = np.zeros((1, nSampsCo*len(self.DigColumns)), dtype=np.bool)
            Lout[0, nSampsCo * nCol: nSampsCo * (nCol + 1)] = True
            Cout = np.vstack((Lout, ~Lout))
            DOut = np.vstack((DOut, Cout)) if DOut.size else Cout

        SortDInds = []
        for line in DOut[0:-1:2, :]:
            SortDInds.append(np.where(line))

        self.SortDInds = SortDInds

        return DOut.astype(np.uint8)

    def _SortChannels(self, data, SortDict):
        (samps, inch) = data.shape
        sData = np.zeros((samps, len(SortDict)))
        for chn, inds in sorted(SortDict.iteritems()):
            sData[:, inds[1]] = data[:, inds[0]]

        LinesSorted = np.ndarray((len(self.DigColumns)*len(self.ChNamesList),
                                 self.nSampsCo))
        ind = 0
        for chData in sData.transpose()[:, :]:
            for Inds in self.SortDInds:
                LinesSorted[ind, :] = chData[Inds]
                ind += 1

        return LinesSorted

    def EveryNEventCallBack(self, Data):
        _DCDataEveryNEvent = self.DCDataEveryNEvent
        _GateDataEveryNEvent = self.GateDataEveryNEvent
        _ACDataEveryNEvent = self.ACDataEveryNEvent

        if _GateDataEveryNEvent:
            _GateDataEveryNEvent(self._SortChannels(Data,
                                                    self.GateChannelIndex))
        if _DCDataEveryNEvent:
            _DCDataEveryNEvent(self._SortChannels(Data,
                                                  self.DCChannelIndex))
        if _ACDataEveryNEvent:
            _ACDataEveryNEvent(self._SortChannels(Data,
                                                  self.ACChannelIndex))

    def DoneEventCallBack(self, Data):

        _DCDataDoneEvent = self.DCDataDoneEvent
        _GateDataDoneEvent = self.GateDataDoneEvent
        _ACDataDoneEvent = self.ACDataDoneEvent

        if _GateDataDoneEvent:
            _GateDataDoneEvent(self._SortChannels(Data,
                                                  self.GateChannelIndex))
        if _DCDataDoneEvent:
            _DCDataDoneEvent(self._SortChannels(Data,
                                                self.DCChannelIndex))
        if _ACDataDoneEvent:
            _ACDataDoneEvent(self._SortChannels(Data,
                                                self.ACChannelIndex))

    def ReadChannelsData(self, Fs=1000, EverySamps=1000):
        self.Inputs.EveryNEvent = self.EveryNEventCallBack
        self.Inputs.ReadContData(Fs=Fs,
                                 EverySamps=EverySamps)

    def __del__(self):
        print 'Delete class'
        self.VdsOut.ClearTask()
        self.VsOut.ClearTask()
        self.Inputs.ClearTask()


class DataProcess(ChannelsConfig):
    EventDataACReady = None
    EventDataDCReady = None
    IVGainAC = None
    IVGainDC = None
    IVGainGate = None
    DO = None

    debugFileDc = False
    debugFileAc = False

    ChOrder = None

    def InitRecording(self, Vds, Vgs, Fs, RecDC=False, RecAC=False):

        self.ChOrder = {}
        for irow, row in enumerate(self.ChNamesList):
            for icol, col in enumerate(sorted(self.DigColumns)):
                self.ChOrder[row+col] = (irow, icol)

        self.Seg = NeoRecord.NeoSegment()
        if RecDC:
            self.DCDataEveryNEvent = self.CalcDCData
            for ChName in sorted(self.ChannelNames):
                name = ChName + '_DC'
                sig = NeoRecord.NeoSignal(np.array([]),
                                          units=pq.A,
                                          t_start=0*pq.s,
                                          sampling_rate=Fs*pq.Hz,
                                          name=name)
                self.Seg.AddSignal(sig)

        if RecAC:
            self.ACDataEveryNEvent = self.CalcACData
            for ChName in self.ChannelNames:
                name = ChName + '_AC'
                sig = NeoRecord.NeoSignal(np.array([]),
                                          units=pq.A,
                                          t_start=0*pq.s,
                                          sampling_rate=Fs*pq.Hz,
                                          name=name)
                self.Seg.AddSignal(sig)

    def CalcACData(self, Data):
        if self.debugFileAc:
            for si, sn in sorted(enumerate(self.ChannelNames)):
                self.debugDataAC[sn].append(Data[:, si])
            print len(self.debugDataAC['Ch05Col1'])
            if len(self.debugDataAC['Ch05Col1']) >= 10000:
                pickle.dump(self.debugDataAC, open('debugDataAC.pkl', 'wb'))
                self.debugFileAc = False

        # Process Buffer
        Sample = Data.mean(axis=1)[None, :]
        self.BufferAC.RefreshBuffer[self.BufferAC.BufferInd, :] = Sample
        self.BufferAC.BufferInd += 1

        if self.BufferAC.BufferInd == self.BufferAC.ReBufferSize:
            self.BufferAC.RefreshBuffer = (self.BufferAC.RefreshBuffer -
                                           self.BiasVd)/self.IVGainAC

            for si, sn in sorted(enumerate(self.ChannelNames)):
                self.Seg.AppendSignal(sn + '_AC',
                                      self.BufferAC.RefreshBuffer[:, si][:, None])
            self.BufferAC.BufferInd = 0
            self.BufferAC.RefreshBuffer = np.zeros((self.BufferAC.ReBufferSize,
                                                    len(self.DigColumns) *
                                                    len(self.ChNamesList)))

            if self.EventDataACReady is not None:
                self.EventDataACReady()

    def CalcDCData(self, Data):
        if self.debugFileDc:
            for si, sn in sorted(enumerate(self.ChannelNames)):
                self.debugDataDC[sn].append(Data[:, si])
                print len(self.debugDataDC['Ch05Col6'])
            if len(self.debugDataDC['Ch05Col6']) >= 10000:
                print 'DC'
                pickle.dump(self.debugDataDC, open('DebugFileDC.pkl', 'wb'))
                self.debugFileDc = False

        # Process Buffer
        Sample = Data.mean(axis=1)[None, :]
        self.BufferDC.RefreshBuffer[self.BufferDC.BufferInd, :] = Sample
        self.BufferDC.BufferInd += 1

        if self.BufferDC.BufferInd == self.BufferDC.ReBufferSize:
            self.BufferDC.RefreshBuffer = (self.BufferDC.RefreshBuffer -
                                           self.BiasVd)/self.IVGainDC

            for si, sn in sorted(enumerate(self.ChannelNames)):
                self.Seg.AppendSignal(sn + '_DC',
                                      self.BufferDC.RefreshBuffer[:, si][:, None])
            self.BufferDC.BufferInd = 0
            self.BufferDC.RefreshBuffer = np.zeros((self.BufferDC.ReBufferSize,
                                                    len(self.DigColumns) *
                                                    len(self.ChNamesList)))

            if self.EventDataDCReady is not None:
                self.EventDataDCReady()

    def ClearEventsCallBacks(self):
        self.DCDataDoneEvent = None
        self.DCDataEveryNEvent = None
        self.ACDataDoneEvent = None
        self.ACDataEveryNEvent = None
        self.GateDataDoneEvent = None
        self.GateDataEveryNEvent = None

    def StartAcquisition(self, Vds, Vgs, Fs, nSampsCo, RecDC, RecAC,
                         ReBufferSize):

        self.ClearEventsCallBacks()
        
        # Init Buffers
        if RecDC:
            self.BufferDC = Buffer(ReBufferSize=ReBufferSize,
                                   DigColumns=self.DigColumns,
                                   ChNamesList=self.ChNamesList)
            self.debugDataDC = self.InitDebugFile()
        if RecAC:
            self.BufferAC = Buffer(ReBufferSize=ReBufferSize,
                                   DigColumns=self.DigColumns,
                                   ChNamesList=self.ChNamesList)
            self.debugDataAC = self.InitDebugFile()

        SwitchFreq = Fs/(len(self.DigColumns)*nSampsCo)
        print 'Switching Freq -->', SwitchFreq
        self.InitRecording(Vds=Vds,
                           Vgs=Vgs,
                           Fs=SwitchFreq,
                           RecAC=RecAC,
                           RecDC=RecDC)

        self.SetBias(Vds=Vds, Vgs=Vgs)
        self.Fs = Fs
        self.nSampsCo = nSampsCo

        if not self.ColumnsControl:
            self.InitDigitalChannels(DigColumns=self.DigColumns)
        self.DO = self.GenerateDigitalSignal(nSampsCo=nSampsCo)
        print 'nLines', len(self.DigColumns * 2)

        self.ColumnsControl.SetSignal(Signal=self.DO,
                                      nSamps=nSampsCo,
                                      nLines=len(self.DigColumns) * 2)

#    def RecalculateFs(self):
#        while self.Fs % (len(self.DigColumns)*self.nSampsCo) != 0:
#            self.Fs = self.Fs - 1

    def InitDebugFile(self):
        DebugData = {}
        for si, sn in sorted(enumerate(self.ChannelNames)):
            DebugData[sn] = []
        
        return DebugData

    def LauchAq(self):
        EveryN = len(self.DigColumns)*self.nSampsCo
        print self.DO.shape
        print self.DO

#        while self.Fs % EveryN != 0:
#            EveryN = EveryN + 1

        self.ReadChannelsData(Fs=self.Fs,
                              EverySamps=EveryN)

    def StopAcq(self):
        if self.ColumnsControl is not None:
            self.ColumnsControl.ClearTask()
            self.ColumnsControl = None

###############################################################################
#####
###############################################################################


class Buffer():

    BufferInd = 0

    def __init__(self, ReBufferSize, DigColumns, ChNamesList):

        self.ReBufferSize = ReBufferSize
        self.RefreshBuffer = np.zeros((self.ReBufferSize,
                                       len(DigColumns)*len(ChNamesList)))

###############################################################################
#####
###############################################################################


class TimeMuxAPP(QtWidgets.QMainWindow):

    OutFigFormats = ('svg', 'png')
    TimeMux = None
    IsRunning = False
    PltSlAC = None
    PltSlDC = None
    PlotTimeIds = None
    EventContGateDone = None
    refreshiters = 0

    def __init__(self, parent=None):

        QtWidgets.QMainWindow.__init__(self)
        uipath = os.path.join(os.path.dirname(__file__),
                              'TimeMuxGui.ui')
        print uipath
        uic.loadUi(uipath, self)
        self.setWindowTitle('Time Multiplexing')

        # Buttons
        self.ButInitChannels.clicked.connect(self.ButInitChannelsClick)
        self.ButUnselAll.clicked.connect(self.ButUnselAllClick)
        self.ButStart.clicked.connect(self.StartBut)

        # Spin Box
        self.SpnSVgs.valueChanged.connect(self.VgsChanged)
        self.SpnSVds.valueChanged.connect(self.VdsChanged)

        self.EnableObjects = [self.SpnFs,
                              self.SpnSamps,
                              self.SpnBuffSize,
                              ]

    def ButUnselAllClick(self):
        print 'But UnselAll'
        for ck in self.GrChannels.findChildren(QtWidgets.QCheckBox):
            ck.setChecked(False)
        for cj in self.GrColumns.findChildren(QtWidgets.QCheckBox):
            cj.setChecked(False)


    def ButInitChannelsClick(self):
        print 'But InitChannels'
        # Event InitChannels button
        Channels = self.GetSelectedChannels(self.GrChannels)
        DigColumns = self.GetSelectedDigitals(self.GrColumns)
        GateChannel = None

        if len(Channels) is 0:
            return
        if len(DigColumns) is 0:
            return

        Config = self.GetConfig(self.GrConfig)

        if self.TimeMux is not None:
            self.TimeMux.__del__()

        self.TimeMux = DataProcess(Channels=Channels,
                                   GateChannel=GateChannel,
                                   Configuration=Config)

        self.TimeMux.InitDigitalChannels(DigColumns=DigColumns)

        self.TimeMux.EventDataDCReady = self.CharDCContDataCallback
        self.TimeMux.EventDataACReady = self.CharACContDataCallback
#        if Gate:
#            self.TimeMux.GateDataEveryNEvent = self.GatedataCallBack

        self.TimeMux.IVGainAC = float(self.QGainAC.text())
        self.TimeMux.IVGainDC = float(self.QGainDC.text())
        self.TimeMux.IVGainGate = float(self.QGainGate.text())

    def CharACContDataCallback(self):
        self.PlotACTime()

    def CharDCContDataCallback(self):
        self.PlotDCTime()

    def GetSelectedChannels(self, ChGroup):
        Chs = []
        for ck in ChGroup.findChildren(QtWidgets.QCheckBox):
            if ck.isChecked():
                Chs.append(str(ck.text()))
        return Chs  # Dictat amb els canals ['Ch08', 'Ch16', ...

    def GetSelectedDigitals(self, DigGroup):
        Dig = []
        for dc in DigGroup.findChildren(QtWidgets.QCheckBox):
            if dc.isChecked():
                Dig.append(str(dc.text()))
        return Dig

    def GetConfig(self, ConfGroup):
        Config = []
        for n in ConfGroup.findChildren(QtWidgets.QCheckBox):
            if n.isChecked():
                Config.append(str(n.text()))
        self.ConfSize = len(Config)
        if self.ConfSize > 1:
            Config = ['Both']

        return Config[0]

# Main Program
###############################################################################

    def StartBut(self):
        if self.TimeMux is None:
            print 'Init Channels first'
            return

        if self.IsRunning:
            print 'Stop'
            self.Stop()
            self.ButStart.setText('Start')
            self.SetEnableObjects(val=True, Objects=self.EnableObjects)
            self.SaveData()
            self.IsRunning = False

        else:
            self.IsRunning = True

            self.SetEnableObjects(val=False, Objects=self.EnableObjects)
            self.ButStart.setText('Stop')

            self.TimeMux.StartAcquisition(Vds=self.SpnSVds.value(),
                                          Vgs=self.SpnSVgs.value(),
                                          Fs=self.SpnFs.value(),
                                          nSampsCo=self.SpnSamps.value(),
                                          RecDC=self.ChckDCSetup.isChecked(),
                                          RecAC=self.ChckACSetup.isChecked(),
                                          ReBufferSize=self.SpnBuffSize.value())

            if self.ChckDCSetup.isChecked():
                self.InitDCFigure(Axs=self.ChckDCAxs.isChecked())
            if self.ChckACSetup.isChecked():
                self.InitACFigure(Axs=self.ChckDCAxs.isChecked())

            self.TimeMux.LauchAq()

    def InitDCFigure(self, Axs=None):
        if Axs is True:
            Axs = 'All'
        else:
            Axs = None
        figdc, axdc = plt.subplots(len(self.TimeMux.DigColumns),
                                   len(self.TimeMux.ChNamesList), sharex=True)
#        axdc = axdc.flatten()
        Slots = []
#        iSlot = 0

        for sig in self.TimeMux.Seg.Signals():
            if not sig.name.endswith('DC'):
                continue
            chname = sig.name.split('_')[0]
            print chname
            print self.TimeMux.ChOrder[chname]
#            sig.ProcessChain = SigCond
            Slots.append(Rplt.WaveSlot(sig,
#                                       Units='A',
                                       Ax=axdc[self.TimeMux.ChOrder[chname]],
                                       Fig=figdc,
#                                       clip_on=True
                                        ))
            print 'x'
#        for isl, sn in sorted(enumerate(self.TimeMux.Seg.signames)):
#            if sn.endswith('DC'):
#                sig = self.TimeMux.Seg.GetSignal(sn)
#                Slots.append(Rplt.WaveSlot(sig,
#                                           Ax=axdc[iSlot],
#                                           Fig=figdc))
#                iSlot += 1

        self.PltSlDC = Rplt.PlotSlots(Slots,
                                      Fig=figdc,
                                      ShowAxis=Axs,
                                      )

    def InitACFigure(self, Axs=None):
        if Axs is True:
            Axs = 'All'
        else:
            Axs = None

        figac, axac = plt.subplots(len(self.TimeMux.DigColumns),
                                   len(self.TimeMux.ChNamesList), sharex=True)
        axac = axac.flatten()
        Slots = []
        iSlot = 0

        for isl, sn in sorted(enumerate(self.TimeMux.Seg.signames)):
            if sn.endswith('AC'):
                sig = self.TimeMux.Seg.GetSignal(sn)
                Slots.append(Rplt.WaveSlot(sig,
                                           Ax=axac[iSlot],
                                           Fig=figac))
                iSlot += 1

        self.PltSlAC = Rplt.PlotSlots(Slots,
                                      Fig=figac,
                                      ShowAxis=Axs,
                                      )

    def PlotACTime(self):
        for sn in self.TimeMux.Seg.signames:
            if sn.endswith('AC'):
                for sl in self.PltSlAC.Slots:
                    if sl.name == sn:
                        sl.Signal = self.TimeMux.Seg.GetSignal(sn)

        tstop = sl.Signal.t_stop
        time = (tstop - 10*pq.s, tstop)

        self.PltSlAC.PlotChannels(Time=time)
        self.PltSlAC.Fig.canvas.draw()

        if not self.IsRunning:
            self.Stop()

    def PlotDCTime(self):
        for sn in self.TimeMux.Seg.signames:
            if sn.endswith('DC'):
                for sl in self.PltSlDC.Slots:
                    if sl.name == sn:
                        sl.Signal = self.TimeMux.Seg.GetSignal(sn)

        tstop = sl.Signal.t_stop
        time = (tstop - 10*pq.s, tstop)

        self.PltSlDC.PlotChannels(Time=time)
        self.PltSlDC.Fig.canvas.draw()

        if not self.IsRunning:
            self.Stop()

    def VgsChanged(self):
        if self.IsRunning:
            self.TimeMux.SetBias(Vds=self.SpnSVds.value(),
                                 Vgs=self.SpnSVgs.value())

    def VdsChanged(self):
        if self.IsRunning:
            self.TimeMux.SetBias(Vds=self.SpnSVds.value(),
                                 Vgs=self.SpnSVgs.value())

    def SetEnableObjects(self, val, Objects):
        print 'SetEnableObjects'
        for obj in Objects:
            obj.setEnabled(val)

    def SaveData(self):
        name, _ = QFileDialog.getSaveFileName(self, 'Save File')
        if not name:
            return
        else:
            self.TimeMux.Seg.SaveRecord(name + '.h5')

    def Stop(self):
        print 'Stop'
        self.TimeMux.SetBias(Vds=0, Vgs=0)
        self.TimeMux.Inputs.StopContData()
        self.TimeMux.StopAcq()


def main():
    import argparse
    import pkg_resources

    # Add version option
    __version__ = pkg_resources.require("PyGFET")[0].version
    parser = argparse.ArgumentParser()
    parser.add_argument('--version', action='version',
                        version='%(prog)s {version}'.format(
                            version=__version__))
    parser.parse_args()

    app = QtWidgets.QApplication(sys.argv)
    w = TimeMuxAPP()
    w.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()




















