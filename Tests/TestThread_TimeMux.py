# -*- coding: utf-8 -*-
"""
Created on Tue Feb 19 15:38:55 2019

@author: Javier
"""

from __future__ import print_function

import sys
import ctypes
from ctypes import byref, c_int32

import h5py
import pyqtgraph as pg
from PyQt5 import Qt
import numpy as np
import time
import PyDAQmx as Daq


##############################################################################


def GetDevName():
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


##############################################################################


class ReadAnalog(Daq.Task):

    EveryNEvent = None
    DoneEvent = None

    def __init__(self, InChans, Range=5.0):
        Daq.Task.__init__(self)
        self.Channels = InChans

        Dev = GetDevName()
        for Ch in self.Channels:
            self.CreateAIVoltageChan(Dev.format(Ch), "",
                                     Daq.DAQmx_Val_RSE,
                                     -Range, Range,
                                     Daq.DAQmx_Val_Volts, None)

        self.AutoRegisterDoneEvent(0)

    def ReadContData(self, Fs, EverySamps):
        self.Fs = Fs
        self.EverySamps = np.int32(EverySamps)
        self.ContSamps = True

        self.CfgSampClkTiming("", Fs, Daq.DAQmx_Val_Rising,
                              Daq.DAQmx_Val_ContSamps,
                              self.EverySamps)

        self.CfgInputBuffer(self.EverySamps*10)
        self.AutoRegisterEveryNSamplesEvent(Daq.DAQmx_Val_Acquired_Into_Buffer,
                                            self.EverySamps, 0)

        self.StartTask()

    def StopContData(self):
        self.StopTask()
        self.ContSamps = False

    def EveryNCallback(self):
        read = c_int32()
        data = np.zeros((self.EverySamps, len(self.Channels)))
        self.ReadAnalogF64(self.EverySamps, 10.0,
                           Daq.DAQmx_Val_GroupByScanNumber,
                           data, data.size, byref(read), None)

        if not self.ContSamps:
            self.data = np.vstack((self.data, data))

        if self.EveryNEvent:
            self.EveryNEvent(data)

    def DoneCallback(self, status):
        self.StopTask()
        self.UnregisterEveryNSamplesEvent()

        if self.DoneEvent:
            self.DoneEvent(self.data)

        return 0  # The function should return an integer


##############################################################################


class WriteAnalog(Daq.Task):

    '''
    Class to write data to Daq card
    '''
    def __init__(self, Channels):

        Daq.Task.__init__(self)
        Dev = GetDevName()
        for Ch in Channels:
            self.CreateAOVoltageChan(Dev.format(Ch), "",
                                     -5.0, 5.0, Daq.DAQmx_Val_Volts, None)
        self.DisableStartTrig()
        self.StopTask()

    def SetVal(self, value):
        self.StartTask()
        self.WriteAnalogScalarF64(1, -1, value, None)
        self.StopTask()

    def SetSignal(self, Signal, nSamps):
        read = c_int32()

        self.CfgSampClkTiming('ai/SampleClock', 1, Daq.DAQmx_Val_Rising,
                              Daq.DAQmx_Val_FiniteSamps, nSamps)

        self.CfgDigEdgeStartTrig('ai/StartTrigger', Daq.DAQmx_Val_Rising)
        self.WriteAnalogF64(nSamps, False, -1, Daq.DAQmx_Val_GroupByChannel,
                            Signal, byref(read), None)
        self.StartTask()

    def SetContSignal(self, Signal, nSamps):
        read = c_int32()

        self.CfgSampClkTiming('ai/SampleClock', 1, Daq.DAQmx_Val_Rising,
                              Daq.DAQmx_Val_ContSamps, nSamps)

        self.CfgDigEdgeStartTrig('ai/StartTrigger', Daq.DAQmx_Val_Rising)
        self.WriteAnalogF64(nSamps, False, -1, Daq.DAQmx_Val_GroupByChannel,
                            Signal, byref(read), None)
        self.StartTask()


##############################################################################


class WriteDigital(Daq.Task):

    '''
    Class to write data to Daq card
    '''
    def __init__(self, Channels):
        Daq.Task.__init__(self)
        Dev = GetDevName()
        for Ch in Channels:
            self.CreateDOChan(Dev.format(Ch), "",
                              Daq.DAQmx_Val_ChanForAllLines)

        self.DisableStartTrig()
        self.StopTask()

    def SetDigitalSignal(self, Signal, nSamps, nLines):
        read = c_int32()
        self.CfgSampClkTiming('ai/SampleClock', 1, Daq.DAQmx_Val_Rising,
                              Daq.DAQmx_Val_ContSamps, Signal.shape[1])
        self.CfgDigEdgeStartTrig('ai/StartTrigger', Daq.DAQmx_Val_Rising)
        self.WriteDigitalLines(Signal.shape[1], False, 1,
                               Daq.DAQmx_Val_GroupByChannel,
                               Signal, byref(read), None)
        self.StartTask()


##############################################################################


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


##############################################################################


class ChannelsConfig():

    DCChannelIndex = None
    ACChannelIndex = None
    ChNamesList = None
    Inputs = None
    InitConfig = None

    # Events list
    DCDataDoneEvent = None
    DCDataEveryNEvent = None
    ACDataDoneEvent = None
    ACDataEveryNEvent = None

    def __init__(self, Channels, Config_DC=True, Config_AC=True,
                 SampKwargs=None, ChVg='ao2', ChVs='ao1', ChVds='ao0'):

        if self.Inputs is not None:
            self.Inputs.ClearTask()

        InChans = []

        self.ChNamesList = sorted(Channels)
        self.DCChannelIndex = {}
        self.ACChannelIndex = {}
        index = 0
        sortindex = 0
        for ch in sorted(Channels):
            if Config_DC:
                InChans.append(aiChannels[ch][0])
                self.DCChannelIndex[ch] = (index, sortindex)
                index += 1
            if Config_AC:
                InChans.append(aiChannels[ch][1])
                self.ACChannelIndex[ch] = (index, sortindex)
                index += 1
            sortindex += 1

        for ch in sorted(Channels):
            if Configuration == 'DC':
                print(ch, ' DC -> ',
                      aiChannels[ch][0], self.DCChannelIndex[ch])
                self.ACChannelIndex = self.DCChannelIndex
            elif Configuration == 'AC':
                print(ch, ' AC -> ',
                      aiChannels[ch][1], self.ACChannelIndex[ch])
                self.DCChannelIndex = self.ACChannelIndex
            else:
                print(ch, ' DC -> ',
                      aiChannels[ch][0], self.DCChannelIndex[ch])
                print(ch, ' AC -> ',
                      aiChannels[ch][1], self.ACChannelIndex[ch])

        self.Inputs = ReadAnalog(InChans=InChans)
        # events linking
        self.Inputs.EveryNEvent = self.EveryNEventCallBack
        self.Inputs.DoneEvent = self.DoneEventCallBack

    def InitDigitalChannels(self, DigColumns=None, **Kwargs):
            DOChannels = []
            self.DigColumns = DigColumns

            for digc in sorted(self.DigColumns):
                DOChannels.append(doColumns[digc][0])
                DOChannels.append(doColumns[digc][1])

            self.ColumnsControl = WriteDigital(Channels=DOChannels)

            ChannelNames = []
            for nRow in range(len(self.ChNamesList)):
                for nCol in range(len(DigColumns)):
                    ChannelNames.append(self.ChNamesList[nRow]+DigColumns[nCol])
            self.ChannelNames = sorted(ChannelNames)

    def SetBias(self, Vds, Vgs):
        print('ChannelsConfig SetBias Vgs ->', Vgs, 'Vds ->', Vds)
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

        print(_DCDataEveryNEvent)
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

    def ReadChannelsData(self, **Kwrargs):
        self.Inputs.EveryNEvent = self.EveryNEventCallBack
        self.SampKwargs.update(Kwrargs)
        self.Inputs.ReadContData(**self.SampKwargs)

    def __del__(self):
        print('Delete class')
        self.Inputs.ClearTask()


##############################################################################


class DataAcquisitionThread(Qt.QThread):
    NewSample = Qt.pyqtSignal()

    def __init__(self, Fs, ChannelsConfigKW, SampKw,  nSamples, BufferSize,
                 RowChannels, ColChannels, Config_DC, Config_AC):

        super(DataAcquisitionThread, self).__init__()

        self.Fs = float(Fs)
        self.Ts = 1/self.Fs

        self.Process = ChannelsConfig(**ChannelsConfigKW)

        self.Process.DCDataEveryNEvent = self.GetData

        self.nChannels = len(Channels)
        self.nSamples = nSamples

        self.Process.ReadChannelsData(**SampKw)

    def run(self, *args, **kwargs):
        loop = Qt.QEventLoop()
        loop.exec_()

    def GetData(self, Data):
        print('GetData')
        self.OutData = Data
        self.NewSample.emit()


##############################################################################


class PlottingThread(Qt.QThread):
    def __init__(self, nChannels):
        super(PlottingThread, self).__init__()
        self.NewData = None
        self.win = pg.GraphicsWindow(title="Real Time Plot")
        self.nChannels = nChannels
        self.Plots = []
        self.Curves = []
        for i in range(nChannels):
            self.win.nextRow()
            p = self.win.addPlot()
            p.hideAxis('bottom')
            self.Plots.append(p)
            self.Curves.append(p.plot())

        self.Plots[-1].showAxis('bottom')
        for p in self.Plots[0:-1]:
            p.setXLink(self.Plots[-1])

#        self.Fig, self.Ax = plt.subplots()

    def run(self, *args, **kwargs):
        while True:
            if self.NewData is not None:
                for i in range(self.nChannels):
                    self.Curves[i].setData(self.NewData[:, i])
#                self.Ax.clear()
#                self.Ax.plot(self.NewData)
#                self.Fig.canvas.draw()
                self.NewData = None
#                print('Plot')
            else:
                Qt.QThread.msleep(10)

    def AddData(self, NewData):
        if self.NewData is not None:
            print('Error plotting!!!!')
        self.NewData = NewData


##############################################################################


class MainWindow(Qt.QWidget):
    ''' Main Window '''

    def __init__(self):
        super(MainWindow, self).__init__()

        # Qt Objects
        layout = Qt.QVBoxLayout(self)
        self.btnAcq = Qt.QPushButton("Start Acq!")
        layout.addWidget(self.btnAcq)

        self.setGeometry(550, 65, 300, 200)
        self.setWindowTitle('MainWindow')

        self.btnAcq.clicked.connect(self.on_btnAcq)

        self.threadAcq = None

    def on_btnAcq(self):
        ''' Starting or Stopping an Additional Stream-WorkThread from the main window '''

        AcqKwargs = {'Inputs': {'RowChannels': ('Ch01', 'Ch02', 'Ch03', ),
                                'ColChannels': ('Col1', 'Col2', ),
                                'Config_DC': True,
                                'Config_AC': False,
                                },
                     'Sampling': {'Fs': 300e3,
                                  'nSamples': 100000,
                                  'BufferSize': 10000,
                                  },
                     'Outputs': {'Vds': 0.05,
                                 'Vgs': 0.1,
                                 'TestSignal': None,
                                 }
                     }

        if self.threadAcq is None:
            self.threadAcq = DataAcquisitionThread(Fs=4, **AcqKwargs['Sampling'])

            self.threadAcq.NewSample.connect(self.on_NewSample)
            self.threadAcq.start()
            print('test')

            self.btnAcq.setText("Stop Acq")
            self.OldTime = time.time()

            self.threadPlot = PlottingThread(**AcqKwargs['Inputs'])
            self.threadPlot.start()

        else:
            self.threadAcq.terminate()
            self.threadAcq = None
            self.btnAcq.setText("Start Acq")

    def on_NewSample(self):
        ''' Visualization of streaming data-WorkThread. '''
        Ts = time.time() - self.OldTime
        print('Sample time', Ts, 1/Ts)
        print(self.threadAcq.OutData.shape)
        self.OldTime = time.time()
        self.threadPlot.AddData(self.threadAcq.OutData)


if __name__ == '__main__':
    app = Qt.QApplication([])
    mw = MainWindow()
    mw.show()
    app.exec_()
