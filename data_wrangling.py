#Copyright [2014] [Puget Sound Regional Council]

#Licensed under the Apache License, Version 2.0 (the "License");
#you may not use this file except in compliance with the License.
#You may obtain a copy of the License at

#    http://www.apache.org/licenses/LICENSE-2.0

#Unless required by applicable law or agreed to in writing, software
#distributed under the License is distributed on an "AS IS" BASIS,
#WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#See the License for the specific language governing permissions and
#limitations under the License.

import os,sys,datetime,re
import subprocess
import inro.emme.desktop.app as app
import json
from shutil import copy2 as shcopy
from distutils import dir_util
import re
import inro.emme.database.emmebank as _eb
import random
import shutil
sys.path.append(os.path.join(os.getcwd(),"inputs"))
from input_configuration import *
from sc_email import *
from logcontroller import *
from input_configuration import *
import input_configuration # Import as a module to access inputs as a dictionary


def multipleReplace(text, wordDict):
    for key in wordDict:
        text = text.replace(key, wordDict[key])
    return text

@timed
def copy_daysim_code():
    print 'Copying Daysim executables...'
    if not os.path.exists(os.path.join(os.getcwd(), 'daysim')):
       os.makedirs(os.path.join(os.getcwd(), 'daysim'))
    shcopy(daysim_code +'/Daysim.exe', 'daysim')
    shcopy(daysim_code +'/Daysim.Attributes.dll', 'daysim')
    shcopy(daysim_code +'/Daysim.Framework.dll', 'daysim')
    shcopy(daysim_code +'/Daysim.Interfaces.dll', 'daysim')
    shcopy(daysim_code +'/HDF5DotNet.dll', 'daysim')
    shcopy(daysim_code +'/NDesk.Options.dll', 'daysim')
    shcopy(daysim_code +'/Ninject.dll', 'daysim')
    shcopy(daysim_code +'/Ninject.xml', 'daysim')
    shcopy(daysim_code +'/msvcr100.dll', 'daysim')
    shcopy(daysim_code +'/szip.dll', 'daysim')
    shcopy(daysim_code +'/zlib.dll', 'daysim')
    shcopy(daysim_code +'/hdf5_hldll.dll', 'daysim')
    shcopy(daysim_code +'/hdf5dll.dll', 'daysim')
    shcopy(daysim_code +'/Ionic.Zip.dll', 'daysim')
    shcopy(daysim_code +'/msvcp100.dll', 'daysim')
    shcopy(daysim_code +'/svn_stamp_out.txt', 'daysim')

@timed
def copy_parcel_buffering_files():
    if not os.path.exists('Inputs/parcel_buffer'):
        os.makedirs('Inputs/parcel_buffer')
    if not os.path.exists('scripts/parcel_buffer'):
        os.makedirs('scripts/parcel_buffer')

    print 'Copying Parcel Buffering Network Inputs.  The file is about 2 GB so it could take a couple of minutes.'
    try: 
        shcopy(network_buffer_inputs, 'Inputs/parcel_buffer')
    except:
        print 'error copying network_buffer inputs at ' + network_buffer_inputs
        sys.exit(2)
 
    main_dir = os.path.abspath('')
    unzip_net_ins = '7z.exe x  ' + main_dir+'/inputs/parcel_buffer/parcel_buff_network_inputs.7z ' + "-o"+ main_dir+'/inputs/parcel_buffer/'
    returncode= subprocess.call(unzip_net_ins)
    if returncode!=0:
        print 'Could not unzip parcel buffer file from '+ main_dir+'/inputs/parcel_buffer/parcel_buff_network_inputs.7z' + ' to ' +main_dir+'/inputs/parcel_buffer/'
        sys.exit(2)
    
    print 'Copying UrbanSim parcel file'
    try:
        shcopy(base_inputs+'/landuse/parcels_urbansim.txt','Inputs/parcel_buffer')
    except:
        print ' error copying parcel file from urbansim at ' + base_inputs+'/landuse/parcels_urbansim.txt'
        sys.exit(1)

    print 'Copying Military parcel file'
    try:
        shcopy(base_inputs+'/landuse/parcels_military.csv','Inputs/parcel_buffer')
    except:
        print 'error copying military parcel file at ' + base_inputs+'/landuse/parcels_military.csv'
        sys.exit(1)

    print 'Copying Parcel Buffering Code'
    try:
        dir_util.copy_tree(network_buffer_code,'scripts/parcel_buffer')
    except:
        print 'error copying parcel buffering code at ' + network_buffer_code
        sys.exit(2)

def text_to_dictionary(dict_name):

    input_filename = os.path.join('inputs/skim_params/',dict_name+'.json').replace("\\","/")
    my_file=open(input_filename)
    my_dictionary = {}

    for line in my_file:
        k, v = line.split(':')
        my_dictionary[eval(k)] = v.strip()

    return(my_dictionary)

def json_to_dictionary(dict_name):

    #Determine the Path to the input files and load them
    input_filename = os.path.join('inputs/skim_params/',dict_name+'.json').replace("\\","/")
    my_dictionary = json.load(open(input_filename))

    return(my_dictionary)
    
@timed    
def setup_emme_bank_folders():
    tod_dict = text_to_dictionary('time_of_day')
    emmebank_dimensions_dict = json_to_dictionary('emme_bank_dimensions')
    
    if not os.path.exists('Banks'):
        os.makedirs('Banks')
    else:
        # remove it
        print 'deleting Banks folder'
        shutil.rmtree('Banks')

    #gets time periods from the projects folder, so setup_emme_project_folder must be run first!
    time_periods = list(set(tod_dict.values()))
    time_periods.append('TruckModel')
    time_periods.append('Supplementals')
    for period in time_periods:
        print period
        print "creating bank for time period %s" % period
        os.makedirs(os.path.join('Banks', period))
        path = os.path.join('Banks', period, 'emmebank')
        emmebank = _eb.create(path, emmebank_dimensions_dict)
        emmebank.title = period
        scenario = emmebank.create_scenario(1002)
        network = scenario.get_network()
        #need to have at least one mode defined in scenario. Real modes are imported in network_importer.py
        network.create_mode('AUTO', 'a')
        scenario.publish_network(network)
        emmebank.dispose()

@timed
def setup_emme_project_folders():
    #tod_dict = json.load(open(os.path.join('inputs', 'skim_params', 'time_of_day.json')))

    tod_dict = text_to_dictionary('time_of_day')
    tod_list = list(set(tod_dict.values()))

    if os.path.exists(os.path.join('projects')):
        print 'Delete Project Folder'
        shutil.rmtree('projects')

    # Create master project, associate with all tod emmebanks
    project = app.create_project('projects', master_project)
    desktop = app.start_dedicated(True, "cth", project)
    data_explorer = desktop.data_explorer()   
    for tod in tod_list:
        database = data_explorer.add_database('Banks/' + tod + '/emmebank')
    #open the last database added so that there is an active one
    database.open()
    desktop.project.save()
    desktop.close()

    # Create time of day projects, associate with emmebank
    tod_list.append('TruckModel') 
    tod_list.append('Supplementals')
    for tod in tod_list:
        project = app.create_project('projects', tod)
        desktop = app.start_dedicated(False, "cth", project)
        data_explorer = desktop.data_explorer()
        database = data_explorer.add_database('Banks/' + tod + '/emmebank')
        database.open()
        desktop.project.save()
        desktop.close()
        
   
@timed    
def copy_large_inputs():
    print 'Copying large inputs...' 
    shcopy(base_inputs+'/etc/daysim_outputs_seed_trips.h5','Inputs')
    dir_util.copy_tree(base_inputs+'/networks','Inputs/networks')
    dir_util.copy_tree(base_inputs+'/trucks','Inputs/trucks')
    dir_util.copy_tree(base_inputs+'/tolls','Inputs/tolls')
    dir_util.copy_tree (base_inputs+'/supplemental','Inputs/supplemental')
    shcopy(base_inputs+'/landuse/hh_and_persons.h5','Inputs')
    shcopy(base_inputs+'/etc/survey.h5','scripts/summarize')
    shcopy(base_inputs+'/4k/auto.h5','Inputs/4k')
    shcopy(base_inputs+'/4k/transit.h5','Inputs/4k')
    if run_parcel_buffering == False:
        shcopy(base_inputs+'/etc/buffered_parcels.dat','Inputs')
@timed
def copy_shadow_price_file():
    print 'Copying shadow price file.' 
    if not os.path.exists('working'):
       os.makedirs('working')
    shcopy(base_inputs+'/shadow_prices/shadow_prices.txt','working')


@timed
def rename_network_outs(iter):
    for summary_name in network_summary_files:
        csv_output = os.path.join(os.getcwd(), 'outputs',summary_name+'.csv')
        if os.path.isfile(csv_output):
            shcopy(csv_output, os.path.join(os.getcwd(), 'outputs',summary_name+str(iter)+'.csv'))
            os.remove(csv_output)
@timed
def create_buffer_xml():
    try:
     'Creating xml file for the parcel buffering script pointing to your inputs'
     buffer_template= open('scripts\parcel_buffer\parc_buff_template.xml','r')
     buffer_config = open('parc_buffer.xml', 'w+')
     
     main_dir = os.path.abspath('')
     
     in_dir = '\inputs\parcel_buffer'
     out_dir = '\inputs'
     code_dir = '\scripts\parcel_buffer'

     replace_dirs = {"$INDIR": main_dir+in_dir,
                     "$OUTDIR" : main_dir+out_dir,
                     "$CODEDIR": main_dir+code_dir}

     for line in buffer_template:
         print line
         for key in replace_dirs.keys():
            if key in line:
                line = line.replace(key, replace_dirs[key])
         buffer_config.write(line)
   
     buffer_template.close()
     buffer_config.close()

    except:
     print 'Error in Creating Parcel Buffer xml'
     buffer_template.close()
     buffer_config.close()

@timed          
def clean_up():
    delete_files = ['outputs\\_tour.tsv', 'outputs\\_trip.tsv','outputs\\_household.tsv','outputs\\_household_day.tsv',
                   'outputs\\_person.tsv', 'outputs\\_person_day.tsv','outputs\\tdm_trip_list.csv', 'outputs\\_full_half_tour.csv','outputs\\_joint_tour.csv',
                   'outputs\\_partial_half_tour.csv', 'working\\household.bin', 'working\\household.pk', 'working\\parcel.bin',
                   'working\\parcel.pk', 'working\\parcel_node.bin', 'working\\parcel_node.pk', 'working\\park_and_ride.bin',
                   'working\\park_and_ride_node.pk', 'working\\person.bin', 'working\\person.pk', 'working\\zone.bin',
                   'working\\zone.pk', 'inputs\\parcel_buffer\\intersection_node_correspondence.txt', 'inputs\\parcel_buffer\\open_spaces_correspondence.txt',
                   'inputs\\parcel_buffer\\parcels_urbansim.txt','inputs\\parcel_buffer\\psrc_node_node_shortest_path_out.txt',
                   'inputs\\parcel_buffer\\psrc_node_node_shortest_path_out.txt.bin', 'psrc_node_node_shortest_path_out.txt.index',
                   'inputs\\parcel_buffer\\stop_node_correspondence']

    for file in delete_files: 
        if(os.path.isfile(os.path.join(os.getcwd(), file))):
            os.remove(os.path.join(os.getcwd(), file))
        else:
            print file

def find_inputs(base_directory, save_list):
    for root, dirs, files in os.walk(base_directory):
        for file in files:
            if '.' in file:
                save_list.append(file)

def check_inputs():
    ''' Warn user if any inputs are missing '''

    logger = logging.getLogger('main_logger')

    # Get a list of input files from input_configuration.py
    config_list = []
    a = globals()
    for key, value in a.iteritems():
        if value not in output_list:    # Ignore outputs file names
            if type(value) is str and '.' in value:
                config_list.append(value.split('/')[-1])    # Save file name only, strip local directory

    # Build list of existing inputs from base_inputs (on shared network drive) and local inputs
    input_list = []
    find_inputs(base_inputs, input_list)    # shared network drive
    find_inputs(os.getcwd(), input_list)    # local inputs

    # Compare lists and report inconsistenies
    missing_list = []
    for f in config_list:
        if not any(f in input for input in input_list):
            missing_list.append(f)

    # Save missing file list to soundcast log and print to console
    if len(missing_list) > 0:
        logger.info('Warning: the following files are missing and may be needed to complete the model run:')
        print 'Warning: the following files are missing and may be needed to complete the model run:'
        for file in missing_list:
            logger.info('- ' + file)
            print file