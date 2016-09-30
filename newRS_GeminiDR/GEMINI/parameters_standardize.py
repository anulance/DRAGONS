# This parameter file contains the parameters related to the primitives located
# in the primitives_GEMINI.py file, in alphabetical order.

from parameters_CORE import ParametersCORE

class ParametersStandardize(ParametersCORE):
    addDQ = {
        "suffix"            : "_dqAdded",
        "bpm"               : None,
        "illum_mask"        : False,
    }
    addMDF = {
        "suffix"            : "_mdfAdded",
        "mdf"               : None,
    }
    addVAR = {
        "suffix"            : "_varAdded",
        "read_noise"        : False,
        "poisson_noise"     : False,
    }
    markAsPrepared = {
        "suffix"            : "_prepared",
    }