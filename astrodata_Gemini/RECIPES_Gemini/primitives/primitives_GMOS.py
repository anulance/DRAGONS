#from Reductionobjects import Reductionobject
from primitives_GEMINI import GEMINIPrimitives
# All GEMINI IRAF task wrappers.
import time
from astrodata.adutils import filesystem
from astrodata.adutils import gemLog
from astrodata import IDFactory
from astrodata import Descriptors
from astrodata.data import AstroData

from pyraf.iraf import tables, stsdas, images
from pyraf.iraf import gemini
import pyraf
import iqtool
from iqtool.iq import getiq
from gempy.instruments.gemini import *
from gempy.instruments.gmos import *

import pyfits
import numdisplay
import string
log=gemLog.getGeminiLog()
yes = pyraf.iraf.yes
no = pyraf.iraf.no
import shutil

# NOTE, the sys.stdout stuff is to shut up gemini and gmos startup... some primitives
# don't execute pyraf code and so do not need to print this interactive 
# package init display (it shows something akin to the dir(gmos)
import sys, StringIO, os
SAVEOUT = sys.stdout
capture = StringIO.StringIO()#from Reductionobjects import Reductionobject

log=gemLog.getGeminiLog()
yes = pyraf.iraf.yes
no = pyraf.iraf.no


# NOTE, the sys.stdout stuff is to shut up gemini and gmos startup... some primitives
# don't execute pyraf code and so do not need to print this interactive 
# package init display (it shows something akin to the dir(gmos)
import sys, StringIO, os
SAVEOUT = sys.stdout
capture = StringIO.StringIO()
sys.stdout = capture
gemini()
gemini.gmos()
sys.stdout = SAVEOUT

class GMOSException:
    """ This is the general exception the classes and functions in the
    Structures.py module raise.
    """
    def __init__(self, msg="Exception Raised in Recipe System"):
        """This constructor takes a message to print to the user."""
        self.message = msg
    def __str__(self):
        """This str conversion member returns the message given by the user (or the default message)
        when the exception is not caught."""
        return self.message


class GMOSPrimitives(GEMINIPrimitives):
    astrotype = "GMOS"
    
    def init(self, rc):
        
        if "iraf" in rc and "adata" in rc["iraf"]:
            pyraf.iraf.set (adata=rc["iraf"]['adata'])  
        else:
            # @@REFERENCEIMAGE: used to set adata path for primitives
            if len(rc.inputs) > 0:
                (root, name) = os.path.split(rc.inputs[0].filename)
                pyraf.iraf.set (adata=root)
                if "iraf" not in rc:
                    rc.update({"iraf":{}})
                if "adata" not in rc["iraf"]:
                    rc["iraf"].update({"adata":root}) 
        
        GEMINIPrimitives.init(self, rc)
        return rc

#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
#$$$$$$$$$$$$$$$$$$$$ NEW STUFF BY KYLE FOR: PREPARE $$$$$$$$$$$$$$$$$$$$$
    '''
    These primitives are now functioning and can be used, BUT are not set up to run with the current demo system.
    commenting has been added to hopefully assist those reading the code.
    Excluding validateWCS, all the primitives for 'prepare' are complete (as far as we know of at the moment that is)
    and so I am moving onto working on the primitives following 'prepare'.
    '''
    
    
    #------------------------------------------------------------------------    
    def validateInstrumentData(self,rc):
        '''
        This primitive is called by validateData to validate the instrument specific data checks for all input files.
        '''
        
        try:
            for ad in rc.getInputs(style="AD"):
                log.status('validating data for file = '+ad.filename,'status')
                log.debug('calling valInstData', 'status')
                valInstData(ad)
                #log.status('data validated for file = '+ad.filename,'status')
                
        except:
            log.critical("Problem preparing the image.",'critical')
            raise 
        
        yield rc       
        
    #-------------------------------------------------------------------------------
    def standardizeInstrumentHeaders(self,rc):
        '''
        This primitive is called by standardizeHeaders to makes the changes and additions to
        the headers of the input files that are instrument specific.
        '''
        try:            
            writeInt = rc['writeInt']
                               
            for ad in rc.getInputs(style="AD"): 
                log.debug('calling stdInstHdrs','status') 
                stdInstHdrs(ad) 
            
            if writeInt:
                log.debug('writing the outputs to disk')
                rc.run('writeOutputs(postpend=_instHdrs)')  #$$$$$$$$$$$$$this needs to accept arguments to work right!!!!!!!!!!!! currently hardcoded
                log.debug('writting complete')
                    
        except:
            log.critical("Problem preparing the image.",'critical')
            raise 
        
        yield rc

 #$$$$$$$$$$$$$$$$$$$$$$$$$$$$$ Prepare primitives end here $$$$$$$$$$$$$$$$$$$$$$$$$$$$
 
 #$$$$$$$$$$$$$$$$$$$$$$$$$$$$$ primitives following Prepare below $$$$$$$$$$$$$$$$$$$$  
    def overscanSubtract(self,rc):
        """
        This primitive uses the CL script gireduce to subtract the overscan from the input images.
        """
        try:
            log.status('*STARTING* to subtract the overscan from the input data','status')
            # writing input files to disk with prefixes onto their file names so they can be deleted later easily 
            clm = CLManager(rc)
            clm.LogCurParams()
            
            # params set by the CLManager or the definition of the prim 
            clPrimParams={
                          'inimages'    :clm.inputsAsStr(),
                          'gp_outpref'  :clm.uniquePrefix(),
                          'fl_over'     :yes, #yes=pyraf.iraf.yes and no=pyraf.iraf.no globally set
                          'Stdout'      :IrafStdout(), #this is actually in the default dict but wanted to show it again
                          'Stderr'      :IrafStdout(), #this is actually in the default dict but wanted to show it again
                          'logfile'    :'', # this is actually in the default dict but wanted to show it again
                          'verbose'    :yes # this is actually in the default dict but wanted to show it again
                          }
            # params from the Parameter file adjustable by the user
            clSoftcodedParams={
                               'fl_trim'    :pyrafBoolean(rc["fl_trim"]),
                               'outpref'    :rc["outpref"],
                               'fl_vardq'   :pyrafBoolean(rc['fl_vardq'])
                               }
            # grabbing the default params dict and updating it with the two above dicts
            clParamsDict=CLDefaultParamsDict('gireduce')
            clParamsDict.update(clPrimParams)
            clParamsDict.update(clSoftcodedParams)
            
            log.fullinfo('calling the gireduce CL script', 'status')
            
            gemini.gmos.gireduce(**clParamsDict)
            
            #gemini.gmos.gireduce(clm.inputsAsStr(), gp_outpref=clm.uniquePrefix(),fl_over=pyrafBoolean(True), \
            #        fl_trim=pyrafBoolean(rc["fl_trim"]), fl_bias=no, \
            #        fl_flat=no, outpref=rc["outpref"], fl_vardq=pyrafBoolean(rc['fl_vardq']), \
            #        Stdout = IrafStdout(), Stderr = IrafStdout())

            if gemini.gmos.gireduce.status:
                log.critical('gireduce failed','critical') 
                raise "gireduce exception"
            else:
                log.fullinfo('exited the gireduce CL script successfully', 'status')
         
            # renaming CL outputs and loading them back into memory and cleaning up the intermediate tmp files written to disk
            clm.finishCL()
            i=0
            for ad in rc.getOutputs(style="AD"):
                if ad.phuGetKeyValue('GIREDUCE'): # varifies gireduce was actually ran on the file
                    log.fullinfo('file '+clm.preCLNames()[i]+' had its overscan subracted successfully', 'status')
                    log.fullinfo('new file name is: '+ad.filename, 'status')
                i=i+1
                ut = ad.historyMark()  
                #$$$$$ should we also have a OVERSUB UT time stame in the PHU???
                log.fullinfo('****************************************************','header')
                log.fullinfo('file = '+ad.filename,'header')
                log.fullinfo('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~','header')
                log.fullinfo('PHU keywords updated/added:\n', 'header')
                log.fullinfo('GEM-TLM = '+str(ut)+'\n','header' )
            
            log.status('*FINISHED* subtracting the overscan from the input data','status')
        except:
            log.critical("Problem preparing the image.",'critical')
            raise 
        
        yield rc    
    #--------------------------------------------------------------------------------------------    
    def overscanTrim(self,rc):
        """
        This primitive uses pyfits and AstroData to trim the overscan region from the input images
        and update their headers.
        """
        try:
            log.status('*STARTING* to trim the overscan region from the input data','status')
            
            for ad in rc.getInputs(style='AD'):
                ad.phuSetKeyValue('TRIMMED','yes','Overscan sectiUIADVANCEDon trimmed')
                for sciExt in ad['SCI']:
                    datasecStr=sciExt.data_section()
                    datasecList=secStrToIntList(datasecStr) 
                    dsl=datasecList
                    log.stdinfo('\nfor '+ad.filename+' extension '+str(sciExt.extver())+\
                                                            ', keeping the data from the section '+datasecStr,'science')
                    sciExt.data=sciExt.data[dsl[2]-1:dsl[3],dsl[0]-1:dsl[1]]
                    sciExt.header['NAXIS1']=dsl[1]-dsl[0]+1
                    sciExt.header['NAXIS2']=dsl[3]-dsl[2]+1
                    newDataSecStr='[1:'+str(dsl[1]-dsl[0]+1)+',1:'+str(dsl[3]-dsl[2]+1)+']' 
                    sciExt.header['DATASEC']=newDataSecStr
                    sciExt.extSetKeyValue(('SCI',int(sciExt.header['EXTVER'])),'TRIMSEC', datasecStr, "Data section prior to trimming")
                    ## updating logger with updated/added keywords to each SCI frame
                    log.fullinfo('****************************************************','header')
                    log.fullinfo('file = '+ad.filename,'header')
                    log.fullinfo('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~','header')
                    log.fullinfo('SCI extension number '+str(sciExt.extver())+' keywords updated/added:\n', 'header')
                    log.fullinfo('NAXIS1= '+str(sciExt.header['NAXIS1']),'header' )
                    log.fullinfo('NAXIS2= '+str(sciExt.header['NAXIS2']),'header' )
                    log.fullinfo('DATASEC= '+newDataSecStr,'header' )
                    log.fullinfo('TRIMSEC= '+datasecStr,'header' )
                    
                # updating the GEM-TLM value and reporting the output to the RC    
                ut = ad.historyMark()
                #$$$$$ should we also have a OVERTRIM UT time same in the PHU???
                ad.filename=fileNameUpdater(ad.filename,postpend=rc["outsuffix"], strip=False)
                rc.reportOutput(ad)
                
                # updating logger with updated/added keywords to the PHU
                log.fullinfo('****************************************************','header')
                log.fullinfo('file = '+ad.filename,'header')
                log.fullinfo('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~','header')
                log.fullinfo('PHU keywords updated/added:\n', 'header')
                log.fullinfo('GEM-TLM = '+str(ut)+'\n','header' ) 
                
            log.status('*FINISHED* trimming the overscan region from the input data','status')
        except:
            log.critical("Problem preparing the image.",'critical')
            raise 
        
        yield rc
    #---------------------------------------------------------------------------    
    def storeProcessedBias(self,rc):
        '''
        this should be a primitive that interacts with the calibration system (MAYBE) but that isn't up and running yet
        thus, this will just strip the extra postfixes to create the 'final' name for the makeProcessedBias outputs
        and write them to disk.
        '''
        
        try:
                
            log.status('*STARTING* to store the processed bias by writing it to disk','status')
            for ad in rc.getInputs(style='AD'):
                ad.filename=fileNameUpdater(ad.filename, postpend="_preparedBias", strip=True)
                ad.historyMark(key='GBIAS',comment='fake key to trick CL that GBIAS was ran')
                log.fullinfo('filename written to = '+rc["storedbiases"]+"/"+ad.filename,'fullinfo')
                ad.write(os.path.join(rc['storedbiases'],ad.filename),clobber=rc['clob'])
            log.status('*FINISHED* storing the processed bias on disk','status')
        except:
            log.critical("Problem preparing the image.",'critical')
            raise 
        
        yield rc
    
    
     #+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++    
    def storeProcessedFlat(self,rc):
        '''
        this should be a primitive that interacts with the calibration system (MAYBE), but that isn't up and running yet
        thus, this will just strip the extra postfixes to create the 'final' name for the makeProcessedBias outputs
        and write them to disk.
        '''
        
        try:
                
            log.status('*STARTING* to store the processed bias by writing it to disk','status')
            for ad in rc.getInputs(style='AD'):
                ad.filename=fileNameUpdater(ad.filename, postpend="_preparedFlat", strip=True)
                log.fullinfo('filename written to = '+rc["storedflats"]+"/"+ad.filename,'fullinfo')
                ad.write(os.path.join(rc['storedflats'],ad.filename),clobber=rc['clob'])
            log.status('*FINISHED* storing the processed bias on disk','status')
        except:
            log.critical("Problem preparing the image.",'critical')
            raise 
        
        yield rc
    #+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    def getProcessedBias(self,rc):
        '''
        a prim that works with the calibration system (MAYBE), but as it isn't written yet this simply
        copies the bias file from the stored processed bias directory and reports its name to the
        reduction context. this is the basic form that the calibration system will work as well but 
        with proper checking for what the correct bias file would be rather than my oversimplified checking
        the binning alone.
        '''
        try:
            packagePath=sys.argv[0].split('gemini_python')[0]
            calPath='gemini_python/test_data/test_cal_files/processed_biases/'
            
            for ad in rc.getInputs(style='AD'):
                if ad.extGetKeyValue(1,'CCDSUM')=='1 1':
                    log.error('NO 1x1 PROCESSED BIAS YET TO USE','error')
                    raise 'error'
                elif ad.extGetKeyValue(1,'CCDSUM')=='2 2':
                    biasfilename = 'N20020214S022_preparedBias.fits'
                    if not os.path.exists(os.path.join('.reducecache/storedcals/retrievedbiases',biasfilename)):
                        shutil.copy(packagePath+calPath+biasfilename, '.reducecache/storedcals/retrievedbiases')
                    rc.addCal(ad,'bias',os.path.join('.reducecache/storedcals/retrievedbiases',biasfilename))
                else:
                    log.error('CCDSUM is not 1x1 or 2x2 for the input flat!!', 'error')
           
        except:
            log.critical("Problem preparing the image.",'critical')
            raise 
        
        yield rc
            
    #-----------------------------------------------------------------------
    
    def biasCorrect(self, rc):
        '''
        This primitive will subtract the biases from the inputs using the CL script gireduce.
        
        WARNING: The gireduce script used here replaces the previously calculated DQ frames with
        its own versions.  This may be corrected in the future by replacing the use of the gireduce
        with a Python routine to do the bias subtraction.
        '''
       
        try:
            log.status('*STARTING* to subtract the bias from the input flats','status')
            
            clm=CLManager(rc)
            clm.LogCurParams()
            
            # getting the bias file for the first file of the inputs and assuming it is the same for all the inputs.
            # This should be corrected in the future to be more intelligent and get the correct bias for each input
            # individually if they are not all the same. Then gireduce can be called in a loop with one flat and one bias,
            # this will work well with the CLManager as that was how i wrote this prim originally.
            ad=rc.getInputs(style='AD')[0]
            processedBias=rc.getCal(ad,'bias')
            
             # params set by the CLManager or the definition of the prim 
            clPrimParams={
                          'inimages'    :clm.inputList(),
                          'gp_outpref'  :clm.uniquePrefix(),
                          'fl_bias'     :yes,
                          'Stdout'      :IrafStdout(), # this is actually in the default dict but wanted to show it again
                          'Stderr'      :IrafStdout(), # this is actually in the default dict but wanted to show it again
                          'logfile'     :'', # this is actually in the default dict but wanted to show it again
                          'verbose'     :yes # this is actually in the default dict but wanted to show it again
                          }
            # params from the Parameter file adjustable by the user
            clSoftcodedParams={
                               'fl_trim'    :pyrafBoolean(rc["fl_trim"]),
                               'outpref'    :rc["outpref"],
                               'fl_over'    :pyrafBoolean(rc["fl_over"]),
                               'bias'       :processedBias, #possibly add a easier way for the user to pass in a bias in the future??
                               'fl_vardq'   :pyrafBoolean(rc['fl_vardq'])
                               }
            # grabbing the default params dict and updating it with the two above dicts
            clParamsDict=CLDefaultParamsDict('gireduce')
            clParamsDict.update(clPrimParams)
            clParamsDict.update(clSoftcodedParams)
            
            log.fullinfo('calling the gireduce CL script', 'status')
            
            gemini.gmos.gireduce(**clParamsDict)
            
            #gemini.gmos.gireduce(clm.inputList(), fl_over=pyrafBoolean(rc["fl_over"]),\
            #    fl_trim=pyrafBoolean(rc["fl_trim"]), fl_bias=yes,bias=processedBias,\
            #    fl_flat=no, outpref=rc["outpref"],bpm='',fl_vardq=pyrafBoolean(True),\
            #  Stdout = IrafStdout(), Stderr = IrafStdout())
            
            if gemini.gmos.gireduce.status:
                 log.critical('gireduce failed','critical') 
                 raise
            else:
                 log.fullinfo('exited the gireduce CL script successfully', 'status')
            
            # renaming CL outputs and loading them back into memory and cleaning up the intermediate tmp files written to disk
            clm.finishCL()
            i=0
            for ad in rc.getOutputs(style="AD"):
                if ad.phuGetKeyValue('GIREDUCE'): # varifies gireduce was actually ran on the file
                    log.fullinfo('file '+clm.preCLNames()[i]+' was bias subracted successfully', 'status')
                    log.fullinfo('new file name is: '+ad.filename, 'status')
                i=i+1
                ut = ad.historyMark()  
                #$$$$$ should we also have a OVERSUB UT time stame in the PHU???
                log.fullinfo('****************************************************','header')
                log.fullinfo('file = '+ad.filename,'header')
                log.fullinfo('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~','header')
                log.fullinfo('PHU keywords updated/added:\n', 'header')
                log.fullinfo('GEM-TLM = '+str(ut)+'\n','header' )
                
            log.warning('The CL script gireduce REPLACED the previously calculated DQ frames','warning')
            log.status('*FINISHED* subtracting the bias from the input flats','status')
        except:
            print "Problem subtracting bias"
            raise
            
        yield rc
    #---------------------------------------------------------------------------
    def makeNormalizedFlat(self,rc):
        '''
        This primitive will combine the input flats and then normalize them using the CL script giflat.
        
        Warning: giflat calculates its own DQ frames and thus replaces the previously produced ones in calculateDQ.
        This may be fixed in the future by replacing giflat with a Python equivilent with more appropriate options
        for the recipe system.
        '''
        
        try:
            
            log.status('*STARTING* to combine and normalize the input flats','status')
            ## writing input files to disk with prefixes onto their file names so they can be deleted later easily 
            clm = CLManager(rc)
            clm.LogCurParams()

            # params set by the CLManager or the definition of the prim 
            clPrimParams={
                          'inflats'    :clm.inputList(),
                          'outflat'    :clm.combineOutname(),
                          'Stdout'      :IrafStdout(), # this is actually in the default dict but wanted to show it again
                          'Stderr'      :IrafStdout(), # this is actually in the default dict but wanted to show it again
                          'logfile'     :'', # this is actually in the default dict but wanted to show it again
                          'verbose'     :yes # this is actually in the default dict but wanted to show it again
                          }
            # params from the Parameter file adjustable by the user
            clSoftcodedParams={
                               'fl_bias'    :rc['fl_bias'],
                               'fl_vardq'   :rc["fl_vardq"],
                               'fl_over'    :rc["fl_over"],
                               'fl_trim'    :rc["fl_trim"]
                               }
            # grabbing the default params dict and updating it with the two above dicts
            clParamsDict=CLDefaultParamsDict('giflat')
            clParamsDict.update(clPrimParams)
            clParamsDict.update(clSoftcodedParams)
            
            log.fullinfo('calling the giflat CL script', 'status')
            
            gemini.giflat(**clParamsDict)
            
           # gemini.giflat(clm.inputList(), outflat=clm.combineOutname(),\
           #     fl_bias=rc['fl_bias'],fl_vardq=rc["fl_vardq"],\
           #     fl_over=rc["fl_over"], fl_trim=rc["fl_trim"], \
           #     Stdout = IrafStdout(), Stderr = IrafStdout(),\
           #     verbose=pyrafBoolean(True))
            
            if gemini.giflat.status:
                log.critical('giflat failed','critical')
                raise 
            else:
                log.fullinfo('exited the giflat CL script successfully', 'status')
                
            # renaming CL outputs and loading them back into memory and cleaning up the intermediate tmp files written to disk
            clm.finishCL(combine=True) 
            
            ad = rc.getOutputs(style='AD')[0] #there is only one after above combination, so no need to perform a loop
                
            ut = ad.historyMark()
            ad.historyMark(key='GIFLAT',stomp=False)
            
            log.fullinfo('****************************************************','header')
            log.fullinfo('file = '+ad.filename,'header')
            log.fullinfo('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~','header')
            log.fullinfo('PHU keywords updated/added:\n', 'header')
            log.fullinfo('GEM-TLM = '+str(ut),'header' )
            log.fullinfo('GIFLAT = '+str(ut),'header' )
            log.fullinfo('---------------------------------------------------','header')    
                
                
            log.status('*FINISHED* combining and normalizing the input flats', 'status')
        except:
            print "Problem subtracting bias"
            raise
            
        yield rc
        
def CLDefaultParamsDict(CLscript):
    '''
    A function to return a dictionary full of all the default parameters for each CL script used so far in the Recipe System.
    '''
    if CLscript=='gireduce':
        defaultParams={
                           'inimages'    :'',
                           'outpref'    :'DEFAULT',
                           'outimages'  :"",
                           'fl_over'    :no,
                           'fl_trim'    :no,
                           'fl_bias'    :no,
                           'fl_dark'    :no, 
                           'fl_flat'    :no,
                           'fl_vardq'   :no,
                           'fl_addmdf'  :no,
                           'bias'       :'',
                           'dark'       :'',
                           'flat1'      :'',
                           'flat2'      :'',
                           'flat3'      :'',
                           'flat4'      :'',
                           'key_exptime':'EXPTIME',
                           'key_biassec':'BIASSEC',
                           'key_datasec':'DATASEC',
                           'rawpath'    :'',
                           'gp_outpref' :'g',
                           'sci_ext'    :'SCI',
                           'var_ext'    :'VAR',
                           'dq_ext'     :'DQ',
                           'key_mdf'    :'MASKNAME',
                           'mdffile'    :'',
                           'mdfdir'     :'',
                           'bpm'        :'',
                           #'giandb'     :'default',
                           'sat'        :65000,
                           'key_nodcount':"NODCOUNT",
                           'key_nodpix' :"NODPIX",
                           'key_filter' :"FILTER2",
                           'key_ron'    :"RDNOISE",
                           'key_gain'   :"GAIN",
                           'ron'        :3.5,
                           'gain'       :2.2,
                           'fl_mult'    :yes, #$$$$$$$$$
                           'fl_inter'   :no,
                           'median'     :no,
                           'function'   :"chebyshev",
                           'nbiascontam':4, #$$$$$$$$$$$$$$$$$$$$$$$$
                           'biasrows'   :"default",
                           'order'      :1,
                           'low_reject' :3.0,
                           'high_reject':3.0,
                           'niterate'   :2,
                           'logfile'    :'',
                           'verbose'    :yes,
                           'status'     :0,
                           'Stdout'      :IrafStdout(),
                           'Stderr'      :IrafStdout()
                           }
    if CLscript=='giflat':
        defaultParams={ 
                       'inflats'    :'',
                       'outflat'    :"",
                       'normsec'    :'default',
                       'fl_scale'   :yes,
                       'sctype'     :"mean",
                       'statsec'    :"default",
                       'key_gain'   :"GAIN",
                       'fl_stamp'   :no,
                       'sci_ext'    :'SCI',
                       'var_ext'    :'VAR',
                       'dq_ext'     :'DQ',
                       'fl_vardq'   :no,
                       'sat'        :65000,
                       'verbose'    :yes,
                       'logfile'    :'',
                       'status'     :0,
                       'combine'    :"average",
                       'reject'     :"avsigclip",
                       'lthreshold' :'INDEF',
                       'hthreshold' :'INDEF',
                       'nlow'       :0,
                       'nhigh'      :1,
                       'nkeep'      :1,
                       'mclip'      :yes,
                       'lsigma'     :3.0,
                       'hsigma'     :3.0,
                       'sigscale'   :0.1,
                       'grow'       :0.0,
                       'gp_outpref' :'g',
                       'rawpath'    :'',
                       'key_ron'    :"RDNOISE",
                       'key_datasec':'DATASEC',
                       #'giandb'     :'default',
                       'bpm'        :'',
                       'gi_outpref' :'r',
                       'bias'       :'',
                       'fl_over'    :no,
                       'fl_trim'    :no,
                       'fl_bias'    :no,
                       'fl_inter'   :no,
                       'nbiascontam':4, #$$$$$$$$$$$$$$$$$$$$$$$$
                       'biasrows'   :"default",
                       'key_biassec':'BIASSEC',
                       'median'     :no,
                       'function'   :"chebyshev",
                       'order'      :1,
                       'low_reject' :3.0,
                       'high_reject':3.0,
                       'niterate'   :2,
                       'Stdout'      :IrafStdout(),
                       'Stderr'      :IrafStdout()
                       }      
    return defaultParams    
        
        
   
    #$$$$$$$$$$$$$$$$$$$$$$$ END OF KYLES NEW STUFF $$$$$$$$$$$$$$$$$$$$$$$$$$