import array as _array
import inro.emme.desktop.app as app
import inro.modeller as _m
import inro.emme.matrix as ematrix
import inro.emme.database.matrix
import inro.emme.database.emmebank as _eb
import json
import numpy as np
import time
import os
import sys
import h5py
import Tkinter
import tkFileDialog
import gc
import multiprocessing as mp
import subprocess
from multiprocessing import Pool

# This script converts the 4k emmebank skims into HDF5 skims to be used in Daysim for model estimation.

# Location of 4k emmebanks
transit4k_path = 'R:/ABModelDevelopment/FinalSkimsForEstimation/skims/transit/'
auto4k_path = 'R:/ABModelDevelopment/FinalSkimsForEstimation/skims/auto/'
non_motorized_4k_path = 'R:/ABModelDevelopment/FinalSkimsForEstimation/skims/nonmotorized/'

# Output File Location
transit_h5_file = 'R:/ABModelDevelopment/FinalSkimsForEstimation/skims/transit.h5'
auto_h5_file = 'R:/ABModelDevelopment/FinalSkimsForEstimation/skims/auto.h5'
non_motorized_h5_file = 'R:/ABModelDevelopment/FinalSkimsForEstimation/skims/nonmotorized.h5'

def open_h5_file(h5_file_name):
    try:
        my_store = h5py.File(h5_file_name, "w-")
        
        print 'HDF5 File was successfully created'
        my_store.close()
        my_store = h5py.File(h5_file_name, "r+")
    except IOError:
        print 'HDF5 File already exists - no file was created'
        my_store = h5py.File(h5_file_name, "r+")
    return my_store


def create_h5_group(my_store, hdf5_name):
    #create containers for TOD skims
    

    #IOError will occur if file already exists with "w-", so in this case just prints it exists
    #If file does not exist, opens new hdf5 file and create groups based on the subgroup list above.

    #Create a sub groups with the same name as the container, e.g. 5to6, 7to8
    #These facilitate multi-processing and will be imported to a master HDF5 file at the end of the run
    try:
        my_store.create_group(hdf5_name)
        print 'HDF5 Group was successfully created'
        #my_store.close()

    except IOError:
        print 'HDF5 Group already exists'
        #my_store.close()

def convert_transit_skims():
    my_store = open_h5_file(transit_h5_file)
    transit_paths_dict = {'am':'am/all_mode/emmebank', 'md':'md/all_mode/emmebank'}
   
    #Transit
    transit_skim_matrix_names = {'ivtwa': 'in vehicle time', 'auxwa': 'walk time','twtwa': 'total wait time',
                                 'farwa': 'fare', 'nbdwa': "average boardings"}
    
    for key, value in transit_paths_dict.iteritems():
        e = key in my_store
        if e:
            del my_store[key]
            create_h5_group(my_store, key)
            print "Group Skims Exists. Group deleted then created"
            #If not there, create the group
        else:
            create_h5_group(my_store, key)
            print "Group Skims Created"
  
        emmebank_4ktransit = _eb.Emmebank(transit4k_path + value)
        list_of_matrices = emmebank_4ktransit.matrices()
        # First get out the iwtwa matrix
        for emme_matrix in list_of_matrices:
            if 'iwtwa' in emme_matrix.name:
                initial_wait_value = np.matrix(emme_matrix.raw_data) * 100 
                initial_wait_value = np.where(initial_wait_value > np.iinfo('uint16').max, np.iinfo('uint16').max, initial_wait_value)
                # keep track of the initial wait matrix to use for later calcs
                my_store[key].create_dataset(emme_matrix.name, data=initial_wait_value.astype('uint16'), compression='gzip')
                print emme_matrix.name

        list_of_matrices2 = emmebank_4ktransit.matrices()
        for emme_matrix2 in list_of_matrices2:
         for key1 in transit_skim_matrix_names:
            if key1 in emme_matrix2.name:
               print key1
               print emme_matrix2.name
               if key1 != 'farwa':
                matrix_value = np.matrix(emme_matrix2.raw_data) * 100
 
               # fare is already in cents
               else:
                 matrix_value = np.matrix(emme_matrix2.raw_data)
 
               matrix_value = np.where(matrix_value > np.iinfo('uint16').max, np.iinfo('uint16').max, matrix_value)   
               print matrix_value[0,0]
               print np.amin(matrix_value)
               print np.amax(matrix_value)
               print np.mean(matrix_value)
                # the transfer time matrix comes from subtracting the total

               if key1=='twtwa':
                 matrix_value2 = np.subtract(matrix_value,initial_wait_value)
                 print matrix_value[0,0]
                 print np.amin(matrix_value)
                 print np.amax(matrix_value)
                 print np.mean(matrix_value)
                 my_store[key].create_dataset(emme_matrix2.name,data=matrix_value2.astype('uint16'), compression='gzip')
               else:
                  my_store[key].create_dataset(emme_matrix2.name, data=matrix_value.astype('uint16'), compression='gzip')

    my_store.close()
     
def convert_auto_skims(): 
    auto_paths_dict = {'ni':'ni/emmebank', 'am':'am/emmebank', 'md':'md/emmebank', 'pm':'pm/emmebank', 'ev':'ev/emmebank'}
    #auto
    my_store = open_h5_file(auto_h5_file)
    auto_skim_matrix_names = {'au1tm':'au1cs', 'au2tm':'au2cs','au3tm':'au3cs', 
                              'a1tm1':'a1cs1','a1tm2':'a1cs2','a1tm3':'a1cs3','a1tm4':'a1cs4'}
   # auto_cost_skim_matrix_names = ('au1cs', 'au2cs', 'au3cs','a1cs1','a1cs2','a1cs3','a1cs4')
    distance_skim_matrix_names = ('au1ds', 'au2ds', 'au3ds','a1ds1','a1ds2','a1ds3', 'a1ds4')

    value_of_time = (19.835,28.981,34.003,12.106,22.315,32.523,42.162)
    value_of_time_hov2 = (38.127, 24.402, 28.981, 25.933, 35.548)
    value_of_time_hov3 = (48.184, 26.919, 34.003, 25.933, 35.548)
    tod_dict = {"am":0, "md":1, "pm":2, "ev":3, "ni":4}


    # keep of a list of the time matrices to calculate costs from
    

    for key_time, value in auto_paths_dict.iteritems():
        #my_store=h5py.File(hdf5_filename, "r+")
        e = key_time in my_store
        if e:
            del my_store[key_time]
            create_h5_group(my_store, key_time)
            print "Group Skims Exists. Group deleted then created"
            #If not there, create the group
        else:
            create_h5_group(my_store, key_time)
            print "Group Skims Created"

        #time_matrices = {}
        emmebank_4kauto = _eb.Emmebank(auto4k_path + value)
        list_of_matrices = emmebank_4kauto.matrices()
        
        this_time = tod_dict[key_time]
        list_of_matrices2 = emmebank_4kauto.matrices()
        which_class = 0
        #TIME SKIMS AND TOLL SKIMS
        #Loop once over names to get the time skim matrices and a second time to get the toll skims
        for emme_matrix in list_of_matrices:
            for emme_matrix2 in list_of_matrices2:
                for key1 in auto_skim_matrix_names:
                    if key1 in emme_matrix.name and auto_skim_matrix_names[key1] in emme_matrix2.name:
                        matrix_value = np.matrix(emme_matrix.raw_data) * 100 
                        matrix_value = np.where(matrix_value > np.iinfo('uint16').max, np.iinfo('uint16').max, matrix_value)
                        print emme_matrix.name
                        print matrix_value[0,0]
                        print np.amin(matrix_value)
                        print np.amax(matrix_value)
                        print np.mean(matrix_value)
                        my_store[key_time].create_dataset(emme_matrix.name, data=matrix_value.astype('uint16'), compression='gzip')
                        
                         #TOLL COST SKIMS for the same corresponding time skims
                        print emme_matrix2.name
                        matrix_value_gen_cost = np.matrix(emme_matrix2.raw_data) * 100
                        matrix_value_gen_cost = np.where(matrix_value_gen_cost > np.iinfo('uint16').max, np.iinfo('uint16').max, matrix_value_gen_cost)
                        print emme_matrix2.name
                        print which_class
                        if(which_class != 1 and which_class !=2):
                            print value_of_time[which_class]
                            toll_cost = (value_of_time[which_class] / 60)*(np.subtract(matrix_value_gen_cost ,matrix_value))
                        elif(which_class == 1):
                            toll_cost = (value_of_time_hov2[this_time] / 60) *(np.subtract(matrix_value_gen_cost ,matrix_value))
                        else:
                            toll_cost = (value_of_time_hov3[this_time] / 60) *(np.subtract(matrix_value_gen_cost ,matrix_value))
               
                        print "toll"
                        print np.amin(toll_cost)
                        print np.amax(toll_cost)
                        print np.mean(toll_cost)
                        my_store[key_time].create_dataset(emme_matrix2.name, data=toll_cost.astype('uint16'), compression='gzip')
                        which_class+=1
            list_of_matrices2 = emmebank_4kauto.matrices()
        list_of_matrices = emmebank_4kauto.matrices()

        # DISTANCE SKIMS           
        list_of_matrices3 = emmebank_4kauto.matrices()
        for emme_matrix in list_of_matrices3:
            for key1 in distance_skim_matrix_names:
               if key1 in emme_matrix.name:
                   matrix_value = np.matrix(emme_matrix.raw_data) * 100 
                   matrix_value = np.where(matrix_value > np.iinfo('uint16').max, np.iinfo('uint16').max, matrix_value)
                   my_store[key_time].create_dataset(emme_matrix.name, data=matrix_value.astype('uint16'), compression='gzip')
                   print matrix_value[0,0]
                   print np.amin(matrix_value)
                   print np.amax(matrix_value)
                   print np.mean(matrix_value)
                   print emme_matrix.name         
    my_store.close()

def convert_non_motorized_skims():
    nonmotorized_paths_dict = {'am':'am/emmebank'}
    #Non Motorized
    my_store = open_h5_file(non_motorized_h5_file)
    non_motorized_skim_matrix_names = {'wlkds': 'walk distance', 'bkeds': 'bike distance'}
    for key, value in nonmotorized_paths_dict.iteritems():
        #my_store=h5py.File(hdf5_filename, "r+")
        e = key in my_store
        if e:
            del my_store[key]
            create_h5_group(my_store, key)
            print "Group Skims Exists. Group deleted then created"
            #If not there, create the group
        else:
            create_h5_group(my_store, key)
            print "Group Skims Created"
            
        emmebank_4knm = _eb.Emmebank(non_motorized_4k_path + value)
        list_of_matrices = emmebank_4knm.matrices()
        for emme_matrix in list_of_matrices:
              for key1 in non_motorized_skim_matrix_names:
               if key1 in emme_matrix.name:
                   matrix_value = np.matrix(emme_matrix.raw_data) * 100 
                   matrix_value = np.where(matrix_value > np.iinfo('uint16').max, np.iinfo('uint16').max, matrix_value)
                   my_store[key].create_dataset(emme_matrix.name, data=matrix_value.astype('uint16'), compression='gzip')
                   print emme_matrix.name
                   print matrix_value[0,0]
                   print np.amin(matrix_value)
                   print np.amax(matrix_value)
                   print np.mean(matrix_value)
    my_store.close()


def main():
    convert_transit_skims()
    convert_auto_skims()
    convert_non_motorized_skims()



if __name__ == "__main__":
    main()
        

