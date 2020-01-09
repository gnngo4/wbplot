import numpy as np
import nibabel as nib
from numpy import ndarray
from .. import constants, config
from . import plots
from os.path import sep, join
import xml.etree.cElementTree as eT
from matplotlib import colors as clrs
from matplotlib import cm

# Uncomment the line below to suppress console statements generated by nibabel
# nib.imageglobals.logger.disabled = True


def write_parcellated_image(
        data, fout, hemisphere=None, vrange=None, cmap=None):
    """
    Insert parcellated scalars into a dlabel file.

    Parameters
    ----------
    data : numpy.ndarray
    fout : str
    hemisphere : 'left' or 'right' or None, default None
        which hemisphere `pscalars` correspond to. for bilateral data use None
    vrange : tuple
    cmap : str

    Returns
    -------
    None

    Notes
    -----
    This function assumes that the ordering of parcels... TODO

    """
    check_hemisphere(hemisphere=hemisphere)
    pscalars_lr = map_unilateral_to_bilateral(
        pscalars=data, hemisphere=hemisphere)
    c = Cifti(constants.DLABEL_FILE)
    c.set_cmap(data=pscalars_lr, cmap=cmap, vrange=vrange)
    c.save(fout=fout)
    return


def map_unilateral_to_bilateral(pscalars, hemisphere):
    """

    Parameters
    ----------
    pscalars : numpy.ndarray
        unilateral parcellated scalars
    hemisphere : 'left' or 'right' or None

    Returns
    -------
    numpy.ndarray
        bilateral pscalars, with contralateral hemisphere padded with zeros

    """
    hemisphere = check_hemisphere(hemisphere=hemisphere)
    if hemisphere is None:
        return pscalars
    pscalars_lr = np.zeros(360)
    if hemisphere == 'right':
        pscalars_lr[180:] = pscalars
    elif hemisphere == 'left':
        pscalars_lr[:180] = pscalars
    return pscalars_lr


def check_hemisphere(hemisphere):
    """
    Check hemisphere argument for package compatibility.

    Parameters
    ----------
    hemisphere : 'left' or 'right' or None

    Returns
    -------
    'left' or 'right' or None

    """
    options = ['left', 'l', 'L', 'right', 'r', 'R', None, 'lr', 'LR']
    if hemisphere not in options:
        raise ValueError("{} if not a valid hemisphere".format(hemisphere))
    if hemisphere in ['left', 'l', 'L']:
        return 'left'
    if hemisphere in ['right', 'r', 'R']:
        return 'right'
    if hemisphere in ['None', 'lr', 'LR']:
        return None


def write_dense_image(dscalars, fout, savedir=constants.DATA_DIR):

    """
    Save dense scalars to a NIFTI neuroimaging file for visualization in
    Connectome Workbench.

    Parameters
    ----------
    dscalars : numpy.ndarray
        dense scalar data to write
    fout : str
        output filename. if an extension is provided, it must be .dscalar.nii
    savedir : str, default constants.DATA_DIR
        absolute path to directory in which to save the image. to use this
        function as part of the automated image-generating pipeline, it must be
        left as its default value

    Returns
    -------
    None

    """
    check_dscalars(dscalars)

    if fout[-12:] != ".dscalar.nii":
        fout += ".dscalar.nii"

    new_data = np.copy(dscalars)

    # Load template NIFTI file (from which to create a new file)
    of = nib.load(constants.DSCALAR_FILE)

    # Load data from the template file
    temp_data = np.array(of.get_data())

    # Reshape the new data appropriately
    data_to_write = new_data.reshape(np.shape(temp_data))

    # Create and save a new NIFTI2 image object
    new_img = nib.Nifti2Image(
        data_to_write, affine=of.affine, header=of.header)
    nib.save(new_img, join(savedir, fout))

    # TODO: look over this and integrate as needed, moved from wbplot.dscalars()
    # new_data = np.copy(dscalars)
    #
    # # Load template NIFTI file (into which `dscalars` will be inserted)
    # of = nib.load(constants.DSCALAR_FILE)
    #
    # # Load data from the template file
    # temp_data = np.array(of.get_data())
    #
    # # # Overwrite existing template data with `dscalars`
    #
    # # First, write new data to existing template file
    # data_to_write = new_data.reshape(np.shape(temp_data))
    # new_img = nib.Nifti2Image(data_to_write, affine=of.affine, header=of.header)
    # prefix = constants.DSCALAR_FILE.split(".dscalar.nii")[0]
    # nib.save(new_img, constants.DSCALAR_FILE)
    #
    # # Use Workbench's command line utilities to change the color palette. Note
    # # that this command requires saving to a new CIFTI file, which I will do
    # # before overwriting the old file
    # cifti_out = prefix + "_temp.dscalar.nii"
    # cifti_in = constants.DSCALAR_FILE
    # cmd = "wb_command -cifti-palette %s %s %s -palette-name %s" % (
    #     cifti_in, "MODE_AUTO_SCALE_PERCENTAGE", cifti_out, cmap)
    # system(cmd)
    #
    # # Delete existing template file; rename new file to replace old template
    # remove(cifti_in)
    # rename(cifti_out, cifti_in)

class Cifti(object):

    def __init__(self, image_file):
        """

        Parameters
        ----------
        image_file : str
            absolute path to neuroimaging file

        """
        of = nib.load(image_file)
        self.data = of.get_data()
        self.affine = of.affine
        self.header = of.header
        self.extensions = eT.fromstring(self.header.extensions[0].get_content())
        self.vrange = None
        self.ischanged = False

    def set_cmap(self, data, cmap=None, vrange=None, mappable=None):
        """
        Map scalar data to RGB values using the provided colormap.

        Parameters
        ----------
        data : numpy.ndarray
            scalar data
        cmap : str or None, default None
            colormap; if None, use DEFAULT_CMAP defined in wbplot.config
        vrange : tuple or None, default None
            data (min, max) for illustration
        mappable : Callable[float] or None, default None
            can be used to override arguments `cmap` and `vrange`, e.g. by
            specifying your own color mapping object

        Returns
        -------
        None

        """

        cmap = plots.check_cmap(cmap)
        vrange = plots.check_vrange(vrange)

        # Map data to colors
        if mappable is None:
            self.vrange = (
                np.min(data), np.max(data)) if vrange is None else vrange
            cnorm = clrs.Normalize(vmin=self.vrange[0], vmax=self.vrange[1])
            clr_map = cm.ScalarMappable(cmap=cmap, norm=cnorm)
            colors = clr_map.to_rgba(data)
        else:
            colors = np.array([mappable(d) for d in data])

        # Set zero values (i.e., masked values) to grey
        greys = cm.get_cmap('Greys')
        nullmap = greys(0.2 * np.ones(np.sum(data == 0.0)))
        colors[data == 0.0, :] = nullmap

        for ii in range(1, len(self.extensions[0][1][0][1])):
            self.extensions[0][1][0][1][ii].set(
                'Red', str(colors[ii - 1, 0]))
            self.extensions[0][1][0][1][ii].set(
                'Green', str(colors[ii - 1, 1]))
            self.extensions[0][1][0][1][ii].set(
                'Blue', str(colors[ii - 1, 2]))
            self.extensions[0][1][0][1][ii].set(
                'Alpha', str(colors[ii - 1, 3]))
        self.ischanged = True

    def write_extensions(self):
        self.header.extensions[0].content = eT.tostring(self.extensions)

    def save(self, fout):
        """

        Parameters
        ----------
        fout : str
            absolute path to output file

        Returns
        -------
        None

        """
        if self.ischanged:
            self.write_extensions()
        new_img = nib.Nifti2Image(
            self.data, affine=self.affine, header=self.header)
        nib.save(new_img, fout)


def check_pscalars_unilateral(pscalars):
    """

    Parameters
    ----------
    pscalars : array_like
        parcellated scalars

    Returns
    -------
    None

    """
    if type(pscalars) is not ndarray:
        raise RuntimeError("pscalars must be a NumPy array")
    if pscalars.ndim != 1:
        raise RuntimeError("pscalars must be one-dimensional")
    if pscalars.size != 180:
        raise RuntimeError("unilateral pscalars must be length 180")


def check_pscalars_bilateral(pscalars):
    """

    Parameters
    ----------
    pscalars : array_like
        parcellated scalars

    Returns
    -------
    None

    """
    if type(pscalars) is not ndarray:
        raise RuntimeError("pscalars must be a NumPy array")
    if pscalars.ndim != 1:
        raise RuntimeError("pscalars must be one-dimensional")
    if pscalars.size != 360:
        raise RuntimeError("bilateral pscalars must be length 360")


def check_dscalars(dscalars):
    """

    Parameters
    ----------
    dscalars : numpy.ndarray
        dense scalars

    Returns
    -------
    None

    """
    if type(dscalars) is not ndarray:
        raise RuntimeError("dscalars must be a NumPy array")
    if dscalars.ndim != 1:
        raise RuntimeError("dscalars must be one-dimensional")
    if dscalars.size != 91282:
        raise RuntimeError("bilateral dscalars must be length 91282")
