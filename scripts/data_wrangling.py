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
from logcontroller import *
from input_configuration import *
from emme_configuration import *
import pandas as pd
import input_configuration # Import as a module to access inputs as a dictionary
from emme_configuration import *
import emme_configuration
import glob


def multipleReplace(text, wordDict):
    for key in wordDict:
        text = text.replace(key, wordDict[key])
    return text

@timed
def copy_daysim_code():
    print 'Copying Daysim executables...'
    if not os.path.exists(os.path.join(os.getcwd(), 'daysim')):
       os.makedirs(os.path.join(os.getcwd(), 'daysim'))
    try:
        dir_util.copy_tree(daysim_code, 'daysim')
    except Exception as ex:
        template = "An exception of type {0} occured. Arguments:\n{1!r}"
        message = template.format(type(ex).__name__, ex.args)
        print message
        sys.exit(1)


@timed
def copy_accessibility_files():
    if not os.path.exists('inputs/accessibility'):
        os.makedirs('inputs/accessibility')
    
    print 'Copying UrbanSim parcel file'
    try:
        if os.path.isfile(base_inputs+'/landuse/parcels_urbansim.txt'):
            shcopy(base_inputs+'/landuse/parcels_urbansim.txt','inputs/accessibility')
        # the file may need to be reformatted- like this coming right out of urbansim
        elif os.path.isfile(base_inputs+'/landuse/parcels.dat'):
            print 'the file is ' + base_inputs +'/landuse/parcels.dat'
            print "Parcels file is being reformatted to Daysim format"
            parcels = pd.DataFrame.from_csv(base_inputs+'/landuse/parcels.dat',sep=" " )
            print 'Read in unformatted parcels file'
            for col in parcels.columns:
                print col
                new_col = [x.upper() for x in col]
                new_col = ''.join(new_col)
                parcels=parcels.rename(columns = {col:new_col})
                print new_col
            parcels.to_csv(base_inputs+'/landuse/parcels_urbansim.txt', sep = " ")
            shcopy(base_inputs+'/landuse/parcels_urbansim.txt','inputs/accesibility')

    except Exception as ex:
        template = "An exception of type {0} occured. Arguments:\n{1!r}"
        message = template.format(type(ex).__name__, ex.args)
        print message
        sys.exit(1)


    print 'Copying Military parcel file'
    try:
        shcopy(base_inputs+'/landuse/parcels_military.csv','inputs/accessibility')
    except:
        print 'error copying military parcel file at ' + base_inputs+'/landuse/parcels_military.csv'
        sys.exit(1)

    try:
        shcopy(base_inputs+'/landuse/distribute_jblm_jobs.csv','Inputs/accessibility')
    except:
        print 'error copying military parcel file at ' + base_inputs+'/landuse/parcels_military.csv'
        sys.exit(1)


    print 'Copying Hourly and Daily Parking Files'
    if run_update_parking: 
        try:
            shcopy(base_inputs+'/landuse/hourly_parking_costs.csv','Inputs/accessibility')
            shcopy(base_inputs+'/landuse/daily_parking_costs.csv','Inputs/accessibility')
        except:
            print 'error copying parking file at' + base_inputs+'/landuse/' + ' either hourly or daily parking costs'
            sys.exit(1)

@timed
def copy_seed_skims():
    print 'You have decided to start your run by copying seed skims that Daysim will use on the first iteration. Interesting choice! This will probably take around 15 minutes because the files are big. Starting now...'
    if not(os.path.isdir(base_inputs+'/seed_skims')):
           print 'It looks like you do not hava directory called' + base_inputs+'/seed_skims, where the code is expecting the files to be. Please make sure to put your seed_skims there.'
    for filename in glob.glob(os.path.join(base_inputs+'/seed_skims', '*.*')):
        shutil.copy(filename, 'inputs')
    print 'Done copying seed skims.'

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
        emmebank.unit_of_length = unit_of_length
        emmebank.coord_unit_length = coord_unit_length  
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
    desktop = app.start_dedicated(False, "cth", project)
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
    dir_util.copy_tree(base_inputs+'/Fares','Inputs/Fares')
    dir_util.copy_tree(base_inputs+'/bikes','Inputs/bikes')
    dir_util.copy_tree(base_inputs+'/supplemental/distribution','inputs/supplemental/distribution')
    dir_util.copy_tree(base_inputs+'/supplemental/generation','inputs/supplemental/generation')
    dir_util.copy_tree(base_inputs+'/supplemental/trips','outputs/supplemental')
    dir_util.copy_tree(base_inputs+'/corridors','Inputs/corridors')
    shcopy(base_inputs+'/landuse/hh_and_persons.h5','Inputs')
    shcopy(base_inputs+'/etc/survey.h5','scripts/summarize')
    shcopy(base_inputs+'/4k/auto.h5','Inputs/4k')
    shcopy(base_inputs+'/4k/transit.h5','Inputs/4k')
    # node to node short distance files:
    shcopy(base_inputs+'/short_distance_files/node_index_2014.txt', 'Inputs')
    shcopy(base_inputs+'/short_distance_files/node_to_node_distance_2014.h5', 'Inputs')
    shcopy(base_inputs+'/short_distance_files/parcel_nodes_2014.txt', 'Inputs')

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
def clean_up():
    delete_files = ['working\\household.bin', 'working\\household.pk', 'working\\parcel.bin',
                   'working\\parcel.pk', 'working\\parcel_node.bin', 'working\\parcel_node.pk', 'working\\park_and_ride.bin',
                   'working\\park_and_ride_node.pk', 'working\\person.bin', 'working\\person.pk', 'working\\zone.bin',
                   'working\\zone.pk']

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

    # Build list of existing inputs from local inputs
    input_list = []
    find_inputs(os.getcwd(), input_list)    # local inputs

    # Compare lists and report inconsistenies
    missing_list = []
    for f in commonly_missing_files:
        if not any(f in input for input in input_list):
            missing_list.append(f)

    # Save missing file list to soundcast log and print to console
    if len(missing_list) > 0:
        logger.info('Warning: the following files are missing and may be needed to complete the model run:')
        print 'Warning: the following files are missing and may be needed to complete the model run:'
        for file in missing_list:
            logger.info('- ' + file)
            print file