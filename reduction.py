#! /usr/bin/env python

"""Reduction program

This program is used to reduce fits files so that they are ready to be used for
science. The raw files are stored in the 'dat/' folder. The program utilises the
configparser module in order to read a 'config.ini' file. This file contains a
target ID, standard star ID, and observing bands. The program sorts the data
into lists of specific integration times and bands. The files are then reduced.
The program outputs reduced fits files.

"""

import math as m
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import mode

from pathlib import Path

from astropy.io import fits

from os import walk
import configparser

def get_lists(dir):
    """
    Sorts fits files into lists.
    Function to create lists of darks, flats, targets, and standard stars. Each
    list contains a dictionary and is constructed by the add_to_list method.
    The configparser package is used to read a .ini file containing settings
    that may be changed by the user in a text editor.

    The function loops through the specified directory and assigns .fits files
    to the lists if they match data in the config.ini file.

    Args:
        dir (str): The path of the directory to be used.
    Returns:
        dark_list (list): The list of 'dark' .fits files.
        flat_list (list): The list of 'flat' .fits files.
        target_list (list): The list of 'target' .fits files.
        standard_star_list (list): The list of 'standard stars' .fits files.
    """
    #: list: Initially empty lists for containing dicts
    dark_list = []
    flat_list = []
    target_list = []
    standard_star_list = []

    # Why is this function defined inside another? ~Wheaton
    def add_to_list(array, filename, **kwargs):
        """
        Adds file data to lists of dictionaries.

        Function to construct a dictionary for a fits file containing a filename
        key and keys for other optional information: integration time and band.
        The dictionary is appended to a specific list.

        Args:
            array (list): The list to append the dictionary to.
            filename (str): The name of the fits file.
            **kwargs: Arbitrary keyword arguments.
        """
        #: dict of str: Holds keys and values for filename and optional keys
        new_dict = {
            'filename': filename
        }
        for key, value in kwargs.items():
             new_dict[key] = value

        array.append(new_dict)

    #: ConfigParser: Contains setup data stored in .ini file.
    config = configparser.ConfigParser()
    config.read('config.ini')
    data_settings = config['DATA SETTINGS']

    _, _, filenames = next(walk(dir), (None, None, []))
    for filename in filenames:
        if filename.endswith('.fits'):
            name_str = filename.split('_')
            if name_str[0].lower() == 'dark':
                add_to_list(dark_list, filename, integration_time = name_str[1])
            elif name_str[0].lower() == 'flat':
                add_to_list(flat_list, filename, integration_time = name_str[2], band = name_str[1])
            elif name_str[0].lower() == data_settings['standard star a'] or name_str[0].lower() == data_settings['standard star b']:
                add_to_list(standard_star_list, filename, integration_time = name_str[2], band = name_str[1])
            elif name_str[0].lower() == data_settings['target id']:
                add_to_list(target_list, filename, integration_time = name_str[2], band = name_str[1])

    return dark_list, flat_list, target_list, standard_star_list

def median(list):
    """
    DEPRECATED
    Returns the median value of a given list. Used for averaging frames without
    the influence of outlier count values.
    """
    list.sort()
    if len(list)%2 == 0:
        index = int(m.floor(len(list)/2)) - 1
        median = int(m.floor((list[index] + list[index+1])/2))
    if len(list)%2 == 1:
        index = int(m.ceil(len(list)/2))
        median = list[index]
    return(median)

def average_frame(filelist, **kwargs):
    """
    Recieves a list of .fits images and returns either their mean or median as
    a HDUList object, depending upon the value of keyword argument "average=".
    Uses either the astropy or the pyraf module depending upon the value of the
    keyword argument "mode=".

    Args:
        filelist (list): list of HDUList.
        **kwargs: Arbitrary keyword arguments.
    Returns:
        average (HDUList): object containing HDUList that can be written to a
            file.
    """
    if kwargs.get('mode') == 'astropy':
        if kwargs.get('average') == 'mean':
            for file_object in filelist:
                average += file_object
            average = average / len(filelist)
        if kwargs.get('average') == 'median':
            # Check that all the images are of the same dimensions.
            ra_pix = len(filelist[0])
            dec_pix = len(filelist[0][0])
            for file_object in filelist:
                if ra_pix != len(file_object):
                    print('Warning! Image dimensions do not match!\n')
                    break
                if dec_pix != len(file_object[0]):
                    print('Warning! Image dimensions do not match!\n')
                    break
            # Initialise empty array and populates it with median values.
            average = np.zeros((ra_pix, dec_pix))
            for i in range(ra_pix):
                for j in range(dec_pix):
                    counts = []
                    for file_object in filelist:
                        counts.append(file_object[i][j])
                    average[i][j] = median(counts)
        return average
    if kwargs.get('mode') == 'pyraf':
        # lol, don't do this.
        return average

def write_out_fits(image, filename):
    hdu = fits.PrimaryHDU(image)
    hdul = fits.HDUList([hdu])
    hdul.writeto(filename, overwrite=True)

def normalise_flat(flat_array):
    normalised_flat = flat_array / mode(flat_array, axis=None)[0][0]
    return normalised_flat


def weighted_mean_2D(cutout,**kwargs):
    """
        Recieves an argument of type ndarray and returns a tuple of the weighted
        mean centroid of the object contained in the cutout.
    """
    x_sum = np.sum(cutout, axis=0)
    y_sum = np.sum(cutout, axis=1)
    x_avg = np.average(range(x_sum.size), weights=x_sum)
    y_avg = np.average(range(y_sum.size), weights=y_sum)
    if kwargs.get("floor") == True:
        return((np.floor(x_avg), np.floor(y_avg)))
    else:
        return((x_avg, y_avg))

def align(image_stack, **kwargs):
    """
    Recieves a list of image arrays and some "cutout" range containing a common
    objecct to use for alignment of the image stack.

    Returns a list of image arrays of different size, aligned, and with zero
    borders where the image has been shifted.
    """

    cutout_range = kwargs.get("cutout")

    # Get lists of all the x and y centroids.
    for image in image_stack:
        x_centroids.append(weighted_mean_2D(image[cutout_range])[0]):
        y_centroids.append(weighted_mean_2D(image[cutout_range])[1]):
    x_ref, y_ref = x_centroids.min(), y_centroids.min()
    x_max, y_max = x_centroids.max(), y_centroids.max()
    x_max_offset = x_max - x_ref
    y_max_offset = y_max - y_ref
    # Create new list of image arrays with offset.
    aligned_image_stack = []
    for image in image_stack:
        aligned_image = np.zeros(image.size[0]+x_max_offset, image.size[1]+y_max_offset)
        x_image_offset = weighted_mean_2D(image[cutout_range])[0] - x_ref
        y_image_offset = weighted_mean_2D(image[cutout_range])[1] - y_ref
        aligned_image[x_image_offset:,y_image_offset:] = image
        aligned_image_stack.append(aligned_image)
    return(aligned_image_stack)

def stack(aligned_image_stack):
    for image in aligned_image_stack:
        stacked_image += image
    return(stacked_image)

def main():
    """
    Grabs sorted lists of files from get_lists function. Creates a list of
    possible integration times from the dark files. Combines darks and flats
    into master HDUList objects. These objects are stored in dictionaries that
    have the integration times or bands as the keys.
    """

    data_folder = Path('dat/')
    science_folder = Path('sci/')
    temp_folder = Path('tmp/')

    #: list of dict: Lists contain dicts with filename (str) and other keys.
    raw_dark_list, raw_flat_list, raw_target_list, raw_std_star_list = get_lists(data_folder)
    #: list of str: Contains possible integration times. No duplicates.
    possible_int_times = list(set(sub['integration_time'] for sub in raw_dark_list))
    #: list of str: Possible bands. No duplicates.
    possible_bands = list(set(sub['band'] for sub in raw_flat_list))

    #: dict of ndarray: Contains master dark objects and integration_times.
    print("Creating dark frames..."),
    master_dark_frame = {}
    for pos_int_time in possible_int_times:
        #: list of ndarray: Contains filenames of dark files.
        sorted_dark_list = []
        for dark in raw_dark_list:
            if dark['integration_time'] == pos_int_time:
                with fits.open(data_folder / dark['filename']) as hdul:
                    #: ndarray: image data
                    data = hdul[0].data
                    sorted_dark_list.append(data)
        master_dark_frame[pos_int_time] = np.floor(np.median(sorted_dark_list, 0))
    print("Done!")

    #: dict of ndarray: Master flat objects, bands, and integration times.
    print("Creating flat frames..."),
    master_flat_frame = {}
    for pos_band in possible_bands:
        #: list of ndarray: Contains flat objects.
        sorted_flat_list = []
        for flat in raw_flat_list:
            if flat['band'] == pos_band:
                with fits.open(data_folder / flat['filename']) as hdul:
                    #: ndarray: dark subtracted image data
                    data = np.subtract(hdul[0].data, master_dark_frame[flat['integration_time']])
                    sorted_flat_list.append(data)
        master_flat_frame[pos_band] = normalise_flat(np.floor(np.median(sorted_flat_list, 0)))
    print("Done!")

    # Why is this function defined inside the main? ~Wheaton
    def reduce_raws(raw_list):
        """
        Reduces raw images into science images. This function loops through a
        list of raws. Each raw image is dark subtracted and then flat divided.

        Args:
            raw_list (list): List of raw ndarray objects.
        Returns:
            science_list (list): List of reduced ndarray objects.
        """
        #: list of ndarray: Empty list for reduced images.
        science_list = {}
        for raw in raw_list:
            print('Reducing ' + str(len(science_list)) +  ' of ' + str(len(raw_list)) + ' images.', end='\r'),
            with fits.open(data_folder / raw['filename']) as hdul:
                #: ndarray: Dark subtracted image data
                ds_data = np.subtract(hdul[0].data, master_dark_frame[raw['integration_time']])
                science_list[raw['filename']] = np.divide(ds_data, master_flat_frame[raw['band']])
        print("\nDone!")
        return science_list

    #: dictionary of ndarray objects: Reduced target image list.
    reduced_target_list = reduce_raws(raw_target_list)
    #: dictionary of ndarray objects: Reduced standard star image list.
    reduced_std_star_list = reduce_raws(raw_std_star_list)

    print("Writing out dark frames..."),
    for key, value in master_dark_frame.items():
        write_out_fits(value, "tmp/"+"dark_"+str(key))
    print("Done!")
    print("Writing out flat frames..."),
    for key, value in master_flat_frame.items():
        write_out_fits(value, "tmp/"+"flat_"+str(key))
    print("Done!")

    # Write out the reduced images for upload to astrometry.net.
    counter = 0
    total = len(reduced_std_star_list)
    for key, value in reduced_std_star_list.items():
        counter += 1
        # write_out_fits(frame, "sci/" + "somehow get filename here")
        print('Writing out ' + str(counter) +  ' of ' + str(total) + ' standard star images...', end='\r'),
        write_out_fits(value, "sci/"+str(key))
    print("\nDone!")

    # Create a list of reduced science frames for alignment.
    #
    # TODO: I think our next step is to upload to Astrometry.net and utilise:
    # https://docs.astropy.org/en/stable/wcs/
    #
    # Align images.
    # aligned_science_list = align_images(science_list)
    #
    # Stack the frames and write out.
    # stacked_science_frame = stack_images(aligned_science_list)
    # write_out_fits(stacked_science_frame, filename)

main()
