from __future__ import print_function

import numpy as np
from astropy.stats import sigma_clip
from functools import wraps
from astrodata import NDAstroData
from geminidr.gemini.lookups import DQ_definitions as DQ

import inspect

def take_along_axis(arr, ind, axis):
    # Swiped from stackoverflow
    if axis < 0:
       if axis >= -arr.ndim:
           axis += arr.ndim
       else:
           raise IndexError('axis out of range')
    ind_shape = (1,) * ind.ndim
    ins_ndim = ind.ndim - (arr.ndim - 1)   #inserted dimensions

    dest_dims = list(range(axis)) + [None] + list(range(axis+ins_ndim, ind.ndim))

    # could also call np.ix_ here with some dummy arguments, then throw those results away
    inds = []
    for dim, n in zip(dest_dims, arr.shape):
        if dim is None:
            inds.append(ind)
        else:
            ind_shape_dim = ind_shape[:dim] + (-1,) + ind_shape[dim+1:]
            inds.append(np.arange(n).reshape(ind_shape_dim))
    return arr[tuple(inds)]

# This code was shamelessly stolen from StackOverflow (user Ants Aasma)
# It allows a decorator to be used on a function *or* a method, hiding
# the class instance from the decorator, which can simply assume it's been
# given a function. This is important for us because we plan to have our
# averaging functions as __call__ methods of classes.
class _MethodDecoratorAdaptor(object):
    def __init__(self, decorator, func):
        self.decorator = decorator
        self.func = func
    def __call__(self, *args, **kwargs):
        return self.decorator(self.func)(*args, **kwargs)
    def __get__(self, instance, owner):
        return self.decorator(self.func.__get__(instance, owner))

def auto_adapt_to_methods(decorator):
    """Allows you to use the same decorator on methods and functions,
    hiding the self argument from the decorator."""
    def adapt(func):
        return _MethodDecoratorAdaptor(decorator, func)
    return adapt

@auto_adapt_to_methods
def unpack_nddata(fn):
    # This decorator wraps a function that takes a sequence of NDAstroData
    # objects and stacks them into data, mask, and variance arrays of one
    # higher dimension, which get passed to the wrapped function.
    # It also applies a set of scale factors and/or offsets, if supplied,
    # to the raw data before stacking and passing them on.
    # The returned arrays are then stuffed back into an NDAstroData object.
    @wraps(fn)
    def wrapper(sequence, scale=None, zero=None, *args, **kwargs):
        nddata_list = [element for element in sequence]
        if scale is None:
            scale = [1.0] * len(nddata_list)
        if zero is None:
            zero = [0.0] * len(nddata_list)
        data = np.stack(ndd.data*s+z for ndd, s, z in zip(nddata_list, scale, zero))
        mask = None if any(ndd.mask is None for ndd in nddata_list) \
            else np.stack(ndd.mask for ndd in nddata_list)
        variance = None if any(ndd.variance is None for ndd in nddata_list) \
            else np.stack(ndd.variance*s*s for ndd, s in zip(nddata_list, scale))
        out_data, out_mask, out_var = fn(data=data, mask=mask,
                                    variance=variance, *args, **kwargs)

        # Can't instantiate NDAstroData with variance
        ret_value = NDAstroData(out_data, mask=out_mask)
        ret_value.variance = out_var
        return ret_value
    return wrapper

# Decorators to identify methods for combining and rejecting. Note that
# NDStacker.<method>.required_args will return a list of required arguments
def combiner(fn):
    fn.is_combiner = True
    args = inspect.getargspec(fn).args[3:]
    fn.required_args = list(args)
    return fn

def rejector(fn):
    fn.is_rejector = True
    args = inspect.getargspec(fn).args[3:]
    fn.required_args = list(args)
    return fn


class NDStacker(object):
    # Base class from which all stacking functions should subclass.
    # Put helper functions here so they can be inherited.
    def __init__(self, combine='mean', reject='none', log=None, **kwargs):
        self._log = log
        try:
            combiner = getattr(self, combine)
            assert getattr(combiner, 'is_combiner')
        except AttributeError:
            self._logmsg("No such combiner as {}. Using mean instead.".format(combine),
                         level='warning')
            combiner = self.mean
        req_args = getattr(combiner, 'required_args', [])
        #try:
        #    assert all(arg in kwargs for arg in req_args)
        #except AssertionError:
        #    self._logmsg("Not all required arguments have been provided for {}."
        #                 " Using mean instead.".format(combine), level='warning')
        #    combiner = self.mean
        self._combiner = combiner
        self._dict = {k: v for k, v in kwargs.items() if k in req_args}

        try:
            rejector = getattr(self, reject)
            assert getattr(rejector, 'is_rejector')
        except AttributeError:
            self._logmsg('No such rejector as {}. Using none instead.'.format(reject),
                         level='warning')
            rejector = self.none
        req_args = getattr(rejector, 'required_args', [])
        #try:
        #    assert all(arg in kwargs for arg in req_args)
        #except AssertionError:
        #    self._logmsg("Not all required arguments have been provided for "
        #                 "rejection algorithm {}. Using none instead.".format(reject),
        #                 level='warning')
        #    rejector = self.none
        self._rejector = rejector
        self._dict.update({k: v for k, v in kwargs.items() if k in req_args})

    def _logmsg(self, msg, level='stdinfo'):
        if self._log is None:
            print(msg)
        else:
            getattr(self._log, level)(msg)

    @staticmethod
    def _process_mask(mask, ignore_bits=0):
        # This manipulates the mask array so we use it to do the required
        # calculations. It creates the output mask (where bits are set only
        # if all the input pixels are flagged) and then unflags pixels in
        # the inputs when they are all bad (because it's better to provide a
        # number than stick a NaN in the output).
        # TODO: Smarter handling of nonlinear/saturation flags
        if mask is None:
            return None, None
        mask = (mask & (65535-ignore_bits)) > 0
        out_mask = np.all(mask, axis=0)
        # XOR: mask unaffected where out_mask=False but where out_mask=True
        # all the input pixels (which are all True) will become False
        mask = mask ^ out_mask
        return mask, out_mask

    @staticmethod
    def calculate_variance(data, mask, out_data):
        # gemcombine-style estimate of variance about the returned value
        ngood = data.shape[0] if mask is None else NDStacker._num_good(mask)
        return NDStacker._divide0(np.ma.masked_array(np.square(data - out_data),
                                            mask=mask).sum(axis=0), ngood*(ngood-1))

    @staticmethod
    def _num_good(mask):
        # Return the number of unflagged pixels at each output pixel
        return mask.shape[0] - np.sum(mask, axis=0)

    @staticmethod
    def _divide0(numerator, denominator):
        # Division with divide-by-zero catching
        return np.divide(numerator, denominator,
                         out=np.zeros_like(numerator), where=(denominator!=0))

    @unpack_nddata
    def __call__(self, data, mask=None, variance=None):
        rej_args = {arg: self._dict[arg] for arg in self._rejector.required_args
                    if arg in self._dict}
        data, mask, variance = self._rejector(data, mask, variance, **rej_args)
        comb_args = {arg: self._dict[arg] for arg in self._combiner.required_args
                     if arg in self._dict}
        out_data, out_mask, out_var = self._combiner(data, mask, variance, **comb_args)
        return out_data, out_mask, out_var

    #------------------------ COMBINER METHODS ----------------------------
    @staticmethod
    @combiner
    def mean(data, mask=None, variance=None):
        # Regular arithmetic mean
        mask, out_mask = NDStacker._process_mask(mask)
        out_data = np.ma.masked_array(data, mask=mask).mean(axis=0).data
        ngood = data.shape[0] if mask is None else NDStacker._num_good(mask)
        if variance is None:  # IRAF gemcombine calculation
            out_var = NDStacker.calculate_variance(data, mask, out_data)
        else:
            out_var = np.ma.masked_array(variance, mask=mask).mean(axis=0).data / ngood
        return out_data, out_mask, out_var

    average = mean  # Formally, these are all averages

    @staticmethod
    @combiner
    def wtmean(data, mask=None, variance=None):
        # Inverse-variance weighted mean
        if variance is None:
            return NDStacker.mean(data, mask, variance)
        mask, out_mask = NDStacker._process_mask(mask)
        out_data = (np.ma.masked_array(data/variance, mask=mask).sum(axis=0).data /
                    np.ma.masked_array(1.0/variance, mask=mask).sum(axis=0).data)
        out_var = 1.0 / np.ma.masked_array(1.0/variance, mask=mask).sum(axis=0).data
        return out_data, out_mask, out_var

    @staticmethod
    @combiner
    def median(data, mask=None, variance=None):
        # Median
        mask, out_mask = NDStacker._process_mask(mask)
        out_data = np.ma.median(np.ma.masked_array(data, mask=mask), axis=0)
        out_var = NDStacker.calculate_variance(data, mask, out_data)
        return out_data, out_mask, out_var

    @staticmethod
    @combiner
    def lmedian(data, mask=None, variance=None):
        # Low median: i.e., if even number, take lower of 2 middle items
        mask, out_mask = NDStacker._process_mask(mask)
        num_img = data.shape[0]
        if mask is None:
            index = (num_img - 1) // 2
            out_data = np.partition(data, index)[index]
        else:
            # Because I'm sorting, I'll put large dummy values in a numpy array
            # np.choose() can't handle more than 32 input images
            data = np.where(mask, np.inf, data)
            data.sort(axis=0)
            index = (NDStacker._num_good(mask) - 1) // 2
            out_data = take_along_axis(data, index, axis=0)
            #out_data = np.empty(data.shape[1:], dtype=np.float32)
            #for i in range((num_img-1) // 2 + 1):
            #    out_data[index==i] = data[i][index==i]
        out_var = NDStacker.calculate_variance(data, mask, out_data)
        return out_data, out_mask, out_var

    #------------------------ REJECTOR METHODS ----------------------------
    @staticmethod
    @rejector
    def none(data, mask=None, variance=None):
        # No rejection: That's easy!
        return data, mask, variance

    @staticmethod
    @rejector
    def minmax(data, mask=None, variance=None, nmin=0, nmax=0):
        # minmax rejection, following IRAF rules when pixels are rejected
        if mask is None:
            nlo = int(nmin+0.001)
            nhi = data.shape[0] - int(nmax+0.001)
            # Sorts variance with data
            arg = np.argsort(data, axis=0)
            data = take_along_axis(data, arg, axis=0)
            variance = take_along_axis(variance, arg, axis=0)
            mask = np.zeros_like(data, dtype=bool)
            mask[:nlo] = True
            mask[nhi:] = True
        else:
            num_img = data.shape[0]
            # Because I'm sorting, I'll put large dummy values in a numpy array
            # Have to keep all values if all values are masked!
            # Sorts variance and mask with data
            arg = np.argsort(np.where(mask, np.inf, data), axis=0)
            data = take_along_axis(data, arg, axis=0)
            variance = take_along_axis(variance, arg, axis=0)
            mask = take_along_axis(mask, arg, axis=0)
            # IRAF imcombine maths
            num_good = NDStacker._num_good(mask)
            nlo = (num_good * float(nmin) / num_img + 0.001).astype(int)
            nhi = num_good - (num_good * float(nmax) / num_img + 0.001).astype(int) - 1
            mask = np.zeros_like(data, dtype=bool)
            for i in range(num_img):
                mask[i][i<nlo] = True
                mask[i][i>nhi] = True
        return data, mask, variance

    @staticmethod
    @rejector
    def sigclip(data, mask=None, variance=None, mclip=True, lsigma=3.0, hsigma=3.0):
        # Iterative sigma-clipping based on input pixel scatter
        cenfunc = np.ma.median if mclip else np.ma.mean
        data = np.ma.masked_array(data, mask=mask)
        clipped_data = sigma_clip(data, sigma_lower=lsigma, sigma_upper=hsigma,
                                  cenfunc=cenfunc, iters=None, axis=0, copy=False)
        return clipped_data.data, clipped_data.mask, variance

    @staticmethod
    @rejector
    def varclip(data, mask=None, variance=None, mclip=True, lsigma=3.0, hsigma=3.0):
        # Iterative sigma-clipping where the input variance array provides
        # the statistical properties of the data
        if variance is None:  # Need variance array for this!
            return NDStacker.sigclip(data, mask=mask, variance=None, mclip=mclip,
                                     lsigma=lsigma, hsigma=hsigma)

        cenfunc = np.ma.median  # Always median for first pass
        clipped_data = np.ma.masked_array(data, mask=mask)
        nmasked = np.sum(clipped_data.mask)
        while True:  # Write it this way in case we decide to have maxiters
            avg = cenfunc(clipped_data, axis=0)
            sigmas = (clipped_data - avg) / np.sqrt(variance)
            clipped_data.mask |= np.logical_or(sigmas > hsigma, sigmas < -lsigma)
            new_nmasked = np.sum(clipped_data.mask)
            if new_nmasked == nmasked:
                break
            cenfunc = np.ma.median if mclip else np.ma.mean
            nmasked = new_nmasked

        return clipped_data.data, clipped_data.mask, variance