# This parameter file contains the parameters related to the primitives located
# in the primitives_calibdb_ghost.py file, in alphabetical order.

from geminidr.core.parameters_calibdb import ParametersCalibDB

class ParametersCalibDBGHOST(ParametersCalibDB):

    storeProcessedSlit = {
        "suffix"            : "_slit",
    }

    storeProcessedSlitBias = {
        "suffix"            : "_slitBias",
    }

    storeProcessedSlitDark = {
        "suffix"            : "_slitDark",
    }

    storeProcessedSlitFlat = {
        "suffix"            : "_slitFlat",
    }

    storeProcessedWavefit = {
        "suffix"            : "_wmodPolyfit",
    }

    storeProcessedXmod = {
        "suffix"            : "_xmodPolyfit"
    }