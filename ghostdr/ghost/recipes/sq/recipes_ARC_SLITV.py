"""
Recipes available to data with tags ['GHOST', 'CAL', 'SLITV', 'ARC'].
Default is "makeProcessedSlitArc".
"""
recipe_tags = set(['GHOST', 'CAL', 'SLITV', 'ARC'])

def makeProcessedSlitArc(p):
    """
    This recipe performs the standardization and corrections needed to convert
    the raw input arc images into a single stacked arc image. This output
    processed arc is stored on disk using storeProcessedArc and has a name
    equal to the name of the first input arc image with "_arc.fits" appended.

    Parameters
    ----------
    p : Primitives object
        A primitive set matching the recipe_tags.
    """

    p.prepare()
    p.addDQ()
    p.addVAR(read_noise=True)
    p.biasCorrect()
    p.addVAR(poisson_noise=True)
    # TODO? p.ADUToElectrons()
    p.darkCorrect()
    #p.correctSlitCosmics()
    p.stackSlitFrames(operation='median', reject_method=None)
    p.storeProcessedArc()
    return

default = makeProcessedSlitArc
