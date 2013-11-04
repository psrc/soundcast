#!python.exe

# PSRC SoundCast Model Runner
# ===========================

# Large input files are not in Git; copy them from:
base_inputs = 'r:/soundcast/inputs'
master_project = 'LoadTripTables'

import os,sys,datetime,re
import subprocess
import inro.emme.database.emmebank as _eb
import json
from shutil import copy2 as shcopy

time_start = datetime.datetime.now()

print "\nSoundCast run: start time:", time_start
#testesttest

def multipleReplace(text, wordDict):
    for key in wordDict:
        text = text.replace(key, wordDict[key])
    return text

def setup_emme_bank_folders():
    emmebank_dimensions_dict = json.load(open(os.path.join('inputs', 'skim_params', 'emme_bank_dimensions.txt')))
    
    if not os.path.exists('Banks'):
        os.makedirs('Banks')
    #gets time periods from the projects folder, so setup_emme_project_folder must be run first!
    time_periods = os.listdir('projects')
    
    for period in time_periods:
        if period == master_project:
            pass
        
        else:
            print period
            print "creating bank for time period %s" % period
            if not os.path.exists(os.path.join('Banks', period)):
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


def setup_emme_project_folders():
    'Copy, unzip, and prepare the Projects/ and Banks/ emme folders'

    # Unzip Projects/ templates using 7-zip (must be in path)
    unzip_cmd = '7z.exe x -y '+base_inputs+'/etc/emme_projects.7z'
    subprocess.call(unzip_cmd)

    # get timeperiod subfolders from os
    project_list = os.listdir('projects')
    print project_list

    # Subst current workdir into project files:
    only_time_periods = os.listdir('projects')
    only_time_periods.remove(master_project)
    print only_time_periods
    tod_bank_path_dict = {}
    
    for period in only_time_periods:
        print "munging",period
        emmebank = os.path.join(os.getcwd(),'Banks',period)
        emmebank = emmebank.replace('\\','/')
        tod_bank_path_dict.update({period : emmebank})
    print project_list
    for proj_name in project_list:
        template = os.path.join('projects',proj_name,proj_name+'.tmpl')
        project  = os.path.join('projects',proj_name,proj_name+'.emp')
        with open(template,'r') as source:
            lines = source.readlines()
        with open(project,'w') as source:
            for line in lines:
                line = str(line)
                line = multipleReplace(line, tod_bank_path_dict)
                source.write(line)
            source.close()



def copy_large_inputs():
    print 'Copying large inputs...'
    shcopy(base_inputs+'/networks','Inputs/networks') 
    shcopy(base_inputs+'/etc/daysim_outputs_seed_trips.h5','Inputs') 
    shcopy(base_inputs+'/etc/psrc_node_node_distances_binary_2010.dat','Inputs')
    shcopy(base_inputs+'/etc/psrc_parcel_decay_2010.dat','Inputs')
    shcopy(base_inputs+'/landuse/hh_and_persons.h5','Inputs')
    shcopy(base_inputs+'/etc/survey.h5','scripts/summarize')
    shcopy(base_inputs+'/4k/trips_auto_4k.h5','Inputs/4k')
    shcopy(base_inputs+'/4k/trips_transit_4k.h5','Inputs/4k')

##########################
# Main Script:
setup_emme_project_folders()
setup_emme_bank_folders()

copy_large_inputs()
time_copy = datetime.datetime.now()
print '###### Finished copying files:', time_copy - time_start

### IMPORT NETWORKS ###############################################################\
time_copy = datetime.datetime.now()
returncode = subprocess.call([sys.executable,
    'scripts/network/network_importer.py'])

if returncode != 0:
    sys.exit(1)

time_network = datetime.datetime.now()
print '###### Finished Importing Networks:', time_network - time_copy

### BUILD SKIMS ###############################################################
returncode = subprocess.call([sys.executable,
    'scripts/skimming/SkimsAndPaths.py',
    '-use_daysim_output_seed_trips'])

if returncode != 0:
    sys.exit(1)

time_skims = datetime.datetime.now()
print '###### Finished skimbuilding:', time_skims - time_copy

### RUN DAYSIM ################################################################
returncode = subprocess.call('./Daysim/Daysim.exe -c configuration.xml')
if returncode != 0:
    sys.exit(1)

time_daysim = datetime.datetime.now()
print '###### Finished running Daysim:',time_daysim - time_skims

### ASSIGNMENTS ###############################################################
subprocess.call([sys.executable, 'scripts/skimming/SkimsAndPaths.py'])

time_assign = datetime.datetime.now()
print '###### Finished running assignments:',time_assign - time_daysim

### ALL DONE ##################################################################
print '###### OH HAPPY DAY!  ALL DONE. (go get a cookie.)'
print '    Total run time:',time_assign - time_start




