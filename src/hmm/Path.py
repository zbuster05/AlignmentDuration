# Copyright (C) 2014-2017  Music Technology Group - Universitat Pompeu Fabra
#
# This file is part of AlignmentDuration:  tool for Lyrics-to-audio alignment with syllable duration modeling

#
# AlignmentDuration is free software: you can redistribute it and/or modify it under
# the terms of the GNU Affero General Public License as published by the Free
# Software Foundation (FSF), either version 3 of the License, or (at your
# option) any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the Affero GNU General Public License
# version 3 along with this program. If not, see http://www.gnu.org/licenses/


'''
Created on Nov 4, 2014

@author: joro
'''
import numpy
import sys
import logging
from src.align.Decoder import BACKTRACK_MARGIN_PERCENT
from src.align.ParametersAlgo import ParametersAlgo
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)




class Path(object):
    '''
    Result path postprocessing
    '''

    def __init__(self,  chiBackPointers, psiBackPointer, phi, hmm):
        '''
        Constructor
        '''
        # detected durations
        self.durations = []
        # ending time for each state
        self.endingTimes = []
        
        if  psiBackPointer != None:
            
            # infer from pointer matrix 
            totalTime, numStates = numpy.shape(psiBackPointer)
            finalTime = totalTime
            self.pathRaw = [1]
            totalAllowedDevTime = (totalTime - BACKTRACK_MARGIN_PERCENT * totalTime)
            
            while self.pathRaw[0] != 0 and finalTime >= totalAllowedDevTime: # not reached first state
                '''
                decrease final time until reached first state
                '''
                finalTime = finalTime - 1
                logger.debug('backtracking from final time {}'.format(finalTime))
                if ParametersAlgo.WITH_DURATIONS:
                    self.pathRaw = self._backtrackForcedDur(chiBackPointers, psiBackPointer, finalTime)
                else:
                    self.pathRaw = self._backtrack(hmm, finalTime)
                    
                try:
                    self.path2stateIndices()
                    numdecodedStates = len(self.indicesStateStarts)
                    currLikelihood = self.getPhiLikelihood(phi, finalTime) / float(numdecodedStates)
                except FloatingPointError:
                    logger.warning('currLikelihood is underflow')
                    currLikelihood = 0
            
            # final sanity check 
            if self.pathRaw[0] != 0:
                logger.debug(' backtracking NOT completed! stopped because reached totalAllowedDevTime  {}'.format(totalAllowedDevTime))
            
            self.phiPathLikelihood = currLikelihood
            
            
 
    def getPhiLikelihood(self,   phi, finalTime):
        '''
        phi from last state for given final time
        '''
        length, numStates = numpy.shape(phi)
        phi_= phi[finalTime, numStates -1] 
        return phi_
        
    def setPathRaw(self, pathRaw):
        self.pathRaw = pathRaw
    
    def _backtrack(self, hmm,  finalTime):
        '''
        backtrack Viterbi starting from last state. no durations, standard viterbi
        '''
        
        totalTIme, numStates = numpy.shape(hmm.psi)
        rawPath = numpy.zeros( (finalTime + 1), dtype=int )
        
        t = finalTime
        # start from last state
        currState = numStates - 1
        # start from state with biggest prob
#         currState = numpy.argmax(hmm.phi[finalTime,:])
        rawPath[finalTime] = currState
        
        while(t>0):
            # backpointer
            pointer = hmm.psi[t, currState]
            if pointer == -1:
                sys.exit("at time {} the backpointer for state {} is not defined".format(t,currState))
            currState = pointer
            rawPath[t-1] = currState
            ### update 
            t = t-1
    
        self.pathRaw = rawPath
        return rawPath
        
    
    def _backtrackForcedDur(self, chiBackPointers, psiBackPointer, finalTime):
        '''
        starts at last state. 
        finds path following back pointers
        '''
        
        if chiBackPointers == None:
            sys.exit(chiBackPointers == 0)
        
        totalTIme, numStates = numpy.shape(psiBackPointer)
        rawPath = numpy.empty( (totalTIme), dtype=int )
        
        # put last state till end of path
        if finalTime < totalTIme - 1:
            rawPath[finalTime+1:totalTIme] = numStates - 1

        
        # termination: start at end state
        t = finalTime
        currState = numStates - 1
        duration = chiBackPointers[t,currState]

        
        # path backtrakcing. allows to 0 to be starting state, but not to go below 0 state
        while (t>duration and currState > 0):
            if duration <= 0:
                print "Backtracking error: duration for state {} is {}. Should be > 0".format(currState, duration)
                sys.exit()
            
            rawPath[t-duration+1:t+1] = currState
            
            # for DEBUG: track durations: 
            self.durations.append(duration)
            self.endingTimes.append(t)

            
            ###### increment
            # pointer of coming state
            currState = psiBackPointer[t, currState]
            
            t = t - duration
            # sanity check. 
            if currState < 0:
                sys.exit("state {} at time {} < 0".format(currState,t))
            
            duration = chiBackPointers[t,currState]
        # fill in with beginning state
        rawPath[0:t+1] = currState
        
        # DEBUG: add last t
        self.durations.append(t)
        self.endingTimes.append(t)
        
        self.durations.reverse() 
        self.endingTimes.reverse()    
   
        return rawPath
    
    def path2stateIndices(self):
        '''
         indices in pathRaw where a new state starts. 
         the array index is the consequtive state count from sequence  
        '''
        self.indicesStateStarts = []
        currState = -1
        for i, p in enumerate(self.pathRaw):
            if p != currState:
              self.indicesStateStarts.append(i)
              currState = p
              
              
    def printDurations(self):
        '''
        DEBUG: print durations
        ''' 
        print self.durations
    
    

        
                 
        