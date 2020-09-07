# -*- coding: utf-8 -*-
"""
Created on Wed Nov 21 12:19:57 2018

@author: user
"""

import matplotlib.pylab as plt
import numpy as np
import time
from PhyREC.NeoInterface import NeoSegment, NeoSignal
import PhyREC.PlotWaves as Rplt
import quantities as pq


def GenDigitalLines(nColumns):
    DOut = np.array([], dtype=np.bool)

    for nCol in range(nColumns):
        Lout = np.zeros((1, nSampsCh*nColumns), dtype=np.bool)
        Lout[0, nSampsCh * nCol: nSampsCh*(nCol + 1)] = True
        Cout = np.vstack((Lout, ~Lout))
        DOut = np.vstack((DOut, Cout)) if DOut.size else Cout

    SortDInds = []
    for line in DOut[0:-1:2, :]:
            SortDInds.append(np.where(line))

    return DOut.astype(np.uint8), SortDInds

def GenTruthTable(n):
    if n < 1:
        return[[]]
    subtable = GenTruthTable(n-1)
    return [row+[v] for row in subtable for v in [0,1]]



def GenDummySamples(nColumns, nRows, nSampsCh):
    DummySamps = np.array([])
    for V in np.arange(nColumns):
        samp = np.ones((nSampsCh, nRows))*V
        for nr in range(nRows):
            samp[:, nr] = samp[:, nr]+nr*10
        DummySamps = np.vstack((DummySamps, samp)) if DummySamps.size else samp

    return DummySamps.transpose()


def SortingData_np(DigLines, Samps):
    # Sorting
    LinesSorted = np.array([])
    for chData in Samps[:, :]:
        for line in DigLines[0:-1:2, :]:
            LineSamps = chData[np.where(line)]
            LinesSorted = np.vstack((LinesSorted, LineSamps)) if LinesSorted.size else LineSamps

    return LinesSorted


def SortingData_list(DigLines, Samps):
    # Sorting
    LinesSorted = []
    for chData in Samps[:, :]:
        for line in DigLines[0:-1:2, :]:
            LinesSorted.append(chData[np.where(line)])

    return np.array(LinesSorted)


def SortingData_list2(SortDInds, Samps):
    # Sorting
    LinesSorted = []
    for chData in Samps[:, :]:
        for Inds in SortDInds:
            LinesSorted.append(chData[Inds])

    return np.array(LinesSorted)


def SortingData_list3(SortDInds, Samps, nCols, nRows, nSampsCh):
    # Sorting
    LinesSorted = np.ndarray((nCols*nRows, nSampsCh))
    ind = 0
    for chData in Samps[:, :]:
        for Inds in SortDInds:
            LinesSorted[ind, :] = chData[Inds]
            ind += 1

    return LinesSorted


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

AxesProp = {
            'ylim': (-1, 1),
            'facecolor': '#FFFFFF00',
            'autoscaley_on': True,
            'xaxis': {'visible': False,
                      },
            'yaxis': {'visible': False,
                      },
            'ylabel': '',
            'title': None,
            }

FigProp = {'tight_layout': True,
           'size_inches': (10,5),
#               'facecolor': '#FFFFFF00',
           }

if __name__ == '__main__':
    plt.close('all')
    
    ####### TimeMux-Test
    # Variable inputs
    Fs = float(1e5)
    Ts = 1/Fs
    nSampsCh = 25
    nColumns = 8
    nRows = 8
    FsCh = 1/(Ts*nSampsCh*nColumns)
    ReBufferSize = 3000
    nIters = ReBufferSize * 20

    # Create channel names
    ChannelNames = []
    Columns = sorted(doColumns.keys())
    for RowName in sorted(aiChannels.keys())[0:nRows]:
        for ColName in sorted(doColumns.keys())[0: nColumns]:
            ChannelNames.append(RowName+ColName)

    # Init Recording to store the data
    RecOut = NeoSegment()
    for ChName in ChannelNames:
        sig = NeoSignal(np.array([]),
                        units=pq.V,
                        t_start=0*pq.s,
                        sampling_rate=FsCh*pq.Hz,
                        name=ChName)
        RecOut.AddSignal(sig)

    # Init figure
    fig, ax = plt.subplots(nColumns, nRows, sharex=True)
    ax = ax.flatten()
    Slots = []
    for isl, sig in enumerate(RecOut.Signals()):
        Slots.append(Rplt.WaveSlot(sig,
                                   Ax=ax[isl],
                                   ))
    PltSl = Rplt.PlotSlots(Slots,
                           Fig=fig,
                           AxKwargs=AxesProp,
                           FigKwargs=FigProp,
                           TimeAxis=None)
    PltSl.PlotChannels(None)

    # Generate digital lines, sorting indexes and dummy samples
    DigLines, SortDInds = GenDigitalLines(nColumns=nColumns)
    DummySamps = GenDummySamples(nColumns=nColumns,
                                 nRows=nRows,
                                 nSampsCh=nSampsCh)

    # Define process buffer
    RefreshBuffer = np.zeros((ReBufferSize, nColumns*nRows))
    BufferInd = 0

    # Start timer
    Tstart = time.time()

    ##
#    f = open('TstRealTimeEval.dat', 'wb')
#    np.savetxt(f, [])
    ##
    for i in range(nIters):
#        DummyChSamps = SortingData_list(DigLines=DigLines,
#                                        Samps=DummySamps)
        # Sorting input data
#        DummyChSamps = SortingData_list2(SortDInds=SortDInds,
#                                         Samps=DummySamps)
        DummyChSamps = SortingData_list3(SortDInds=SortDInds,
                                         Samps=DummySamps,
                                         nCols=nColumns,
                                         nRows=nRows,
                                         nSampsCh=nSampsCh)
        
        # Store data in plealocated buffer
        Sample = DummyChSamps.mean(axis=1)[None, :]
        RefreshBuffer[BufferInd, :] = Sample
        BufferInd += 1

        # Update recording and plot data
        if BufferInd == ReBufferSize:
            for si, sn in enumerate(ChannelNames):
                RecOut.AppendSignal(sn,
                                    RefreshBuffer[:, si][:, None])
                sig = RecOut.GetSignal(sn)
            ##
#            np.savetxt(f, RefreshBuffer)
#            f.flush()
            ##
            BufferInd = 0
            RefreshBuffer = np.zeros((ReBufferSize, nColumns*nRows))
            for sl in PltSl.Slots:
                sl.Signal = RecOut.GetSignal(sl.name)
            PltSl.PlotChannels(None)

    PltSl.AddLegend()
    Tend = time.time()

#    f.close()

    AcqTime = Ts*nSampsCh*nColumns
    ProcTime = (Tend-Tstart)/nIters
    FsMax = 1/(ProcTime/(nSampsCh*nColumns))
    SwFreqMax = 1/((1/FsMax) * nSampsCh * nColumns)
    print('Process time -> ', ProcTime)
    print('Max Sampling -> ', FsMax)
    print('Max SwitchFreq -> ', SwFreqMax)
    print('Max RefreshFreq -> ', 1/((1/SwFreqMax)*ReBufferSize))
    print('Acquisition time -> ', AcqTime)
    print('TimeRefresh ->', (1/FsCh)*ReBufferSize)
    if AcqTime < ProcTime:
        print('BAD!!!!!!!!!!!')
    else:
        print('Good')
