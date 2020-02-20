#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Mar  5 14:13:45 2019

@author: aguimera
"""
# import PyCont.DaqInterface as DaqInt
import PyqtTools.DaqInterface as DaqInt
#import PyTMCore.DaqInterface as DaqInt
import numpy as np



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

    # DCChannelIndex[ch] = (index, sortindex)
    DCChannelIndex = None
    ACChannelIndex = None
    ChNamesList = None
    AnalogInputs = None
    DigitalOutputs = None

    # Events list
    DataEveryNEvent = None
    DataDoneEvent = None
    VgOut = None
    VsigOut = None

    ClearSig = np.zeros((1, len(doColumns)), dtype=np.bool).astype(np.uint8)
    ClearSig = np.hstack((ClearSig, ClearSig))

    def _InitAnalogInputs(self):
        print('InitAnalogInputs')
        self.DCChannelIndex = {}
        self.ACChannelIndex = {}
        InChans = []
        index = 0
        sortindex = 0
        for ch in self.ChNamesList:
            if self.AcqDC:
                InChans.append(aiChannels[ch][0])
                self.DCChannelIndex[ch] = (index, sortindex)
                index += 1
                print(ch, ' DC -->', aiChannels[ch][0])
                print('SortIndex ->', self.DCChannelIndex[ch])
            if self.AcqAC:
                InChans.append(aiChannels[ch][1])
                self.ACChannelIndex[ch] = (index, sortindex)
                index += 1
                print(ch, ' AC -->', aiChannels[ch][1])
                print('SortIndex ->', self.ACChannelIndex[ch])
            sortindex += 1
        print('Input ai', InChans)

        self.AnalogInputs = DaqInt.ReadAnalog(InChans=InChans)
        # events linking
        self.AnalogInputs.EveryNEvent = self.EveryNEventCallBack
        self.AnalogInputs.DoneEvent = self.DoneEventCallBack

    def _InitDigitalOutputs(self):
        print('InitDigitalOutputs')
        print(self.DigColumns)
        DOChannels = []

        for digc in sorted(doColumns):
            print(digc)
            DOChannels.append(doColumns[digc][0])
            DOChannels.append(doColumns[digc][1])
        print(DOChannels)

#        DOChannels = []
#
#        for digc in self.DigColumns:
#            DOChannels.append(doColumns[digc][0])
#            DOChannels.append(doColumns[digc][1])

        self.DigitalOutputs = DaqInt.WriteDigital(Channels=DOChannels)

    def _InitAnalogOutputs(self, ChVds, ChVs, ChVg, ChVsig):
        print('ChVds ->', ChVds)
        print('ChVs ->', ChVs)
        print('ChVg ->', ChVg)
        print('ChVsig ->', ChVsig)

        self.VsOut = DaqInt.WriteAnalog((ChVs,))
        self.VdsOut = DaqInt.WriteAnalog((ChVds,))
        if ChVg:
            self.VgOut = DaqInt.WriteAnalog((ChVg,))
        if ChVsig:
            self.VsigOut = DaqInt.WriteAnalog((ChVsig,))

    def __init__(self, Channels, DigColumns,
                 AcqDC=True, AcqAC=True,
                 ChVds='ao0', ChVs='ao1',
                 ChVg=None, ChVsig=None,
                 ACGain=1.1e5, DCGain=10e3):
        print('InitChannels')
        self._InitAnalogOutputs(ChVds=ChVds, ChVs=ChVs, 
                                ChVg=ChVg, ChVsig=ChVsig)

        self.ChNamesList = sorted(Channels)
        print(self.ChNamesList)
        self.AcqAC = AcqAC
        self.AcqDC = AcqDC
        self.ACGain = ACGain
        self.DCGain = DCGain
        self._InitAnalogInputs()

        self.DigColumns = sorted(DigColumns)
        self._InitDigitalOutputs()

        MuxChannelNames = []
        for Row in self.ChNamesList:
            for Col in self.DigColumns:
                MuxChannelNames.append(Row + Col)
        self.MuxChannelNames = MuxChannelNames
        print(self.MuxChannelNames)

        if self.AcqAC and self.AcqDC:
            self.nChannels = len(self.MuxChannelNames)*2
        else:
            self.nChannels = len(self.MuxChannelNames)

    def StartAcquisition(self, Fs, nSampsCo, nBlocks, 
                         Vgs, Vds, Vg, Vsig, **kwargs):
        print('StartAcquisition')
        self.SetBias(Vgs=Vgs, Vds=Vds)
        self.SetBiasSignal(Vg=Vg, Vsig=Vsig)
        self.SetDigitalOutputs(nSampsCo=nSampsCo)
        print('DSig set')
        self.nBlocks = nBlocks
        self.nSampsCo = nSampsCo
#        self.OutputShape = (nColumns * nRows, nSampsCh, nblocs)
        self.OutputShape = (len(self.MuxChannelNames), nSampsCo, nBlocks)
        EveryN = len(self.DigColumns)*nSampsCo*nBlocks
        self.AnalogInputs.ReadContData(Fs=Fs,
                                       EverySamps=EveryN)

    def SetBias(self, Vgs, Vds):
        print('ChannelsConfig SetBias Vgs ->', Vgs, 'Vds ->', Vds)
        self.VdsOut.SetVal(Vds)
        self.VsOut.SetVal(-Vgs)
        self.BiasVd = Vds-Vgs
        self.Vgs = Vgs
        self.Vds = Vds

    def SetBiasSignal(self, Vg, Vsig):
        if self.VgOut:
            self.VgOut.SetVal(Vg)
        if self.VsigOut:
            self.VsigOut.SetVal(Vsig)

    def SetDigitalOutputs(self, nSampsCo):
        print('SetDigitalOutputs')
        DOut = np.array([], dtype=np.bool)

        for nCol, iCol in zip(range(len(doColumns)), sorted(list(doColumns.keys()))):
            Lout = np.zeros((1, nSampsCo*len(self.DigColumns)), dtype=np.bool)
            for i, n in enumerate(self.DigColumns):
                if n == iCol:
                    Lout[0, nSampsCo * i: nSampsCo * (i + 1)] = True
                Cout = np.vstack((Lout, ~Lout))
            DOut = np.vstack((DOut, Cout)) if DOut.size else Cout

        SortDInds = []
        for line in DOut[0:-1:2, :]:
            if True in line:
                SortDInds.append(np.where(line))

        self.SortDInds = SortDInds
        self.DigitalOutputs.SetContSignal(Signal=DOut.astype(np.uint8))

    def _SortChannels(self, data, SortDict):
        print('SortChannels')
        print(data.shape)
        # Sort by aianalog input
        (samps, inch) = data.shape
        aiData = np.zeros((samps, len(SortDict)))
        for chn, inds in sorted(SortDict.items()):
            aiData[:, inds[1]] = data[:, inds[0]]

        # Sort by digital columns
        aiData = aiData.transpose()
        MuxData = np.ndarray(self.OutputShape)

        print('columns')
        nColumns = len(self.DigColumns)
        for indB in range(self.nBlocks):
            startind = indB * self.nSampsCo * nColumns
            stopind = self.nSampsCo * nColumns * (indB + 1)
            Vblock = aiData[:, startind: stopind]
            ind = 0
            for chData in Vblock[:, :]:
                for Inds in self.SortDInds:
                    MuxData[ind, :, indB] = chData[Inds]
                    ind += 1

        return aiData, MuxData

    def EveryNEventCallBack(self, Data):
        print('EveryNEventCallBack')
        _DataEveryNEvent = self.DataEveryNEvent

        if _DataEveryNEvent is not None:
            if self.AcqDC:
                aiDataDC, MuxDataDC = self._SortChannels(Data,
                                                         self.DCChannelIndex)
                aiDataDC = (aiDataDC-self.BiasVd) / self.DCGain
                MuxDataDC = (MuxDataDC-self.BiasVd) / self.DCGain
            if self.AcqAC:
                aiDataAC, MuxDataAC = self._SortChannels(Data,
                                                         self.ACChannelIndex)
                aiDataAC = aiDataAC / self.ACGain
                MuxDataAC = MuxDataAC / self.ACGain

            if self.AcqAC and self.AcqDC:
                aiData = np.vstack((aiDataDC, aiDataAC))
                MuxData = np.vstack((MuxDataDC, MuxDataAC))
                _DataEveryNEvent(aiData, MuxData)
            elif self.AcqAC:
                _DataEveryNEvent(aiDataAC, MuxDataAC)
            elif self.AcqDC:
                _DataEveryNEvent(aiDataDC, MuxDataDC)

    def DoneEventCallBack(self, Data):
        print('Done callback')

    def Stop(self):
        print('Stopppp')
        self.SetBias(Vgs=0, Vds=0)
        self.SetBiasSignal(Vg=0, Vsig=0)   
        self.AnalogInputs.StopContData()
        if self.DigitalOutputs is not None:
            print('Clear Digital')
#            self.DigitalOutputs.SetContSignal(Signal=self.ClearSig)
            self.DigitalOutputs.ClearTask()
            self.DigitalOutputs = None


#    def __del__(self):
#        print('Delete class')
#        self.Inputs.ClearTask()
#
