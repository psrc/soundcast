#!python.exe

# PSRC SoundCast Model Runner
# ===========================

# Large input files are not in Git; copy them from:
base_inputs = 'r:/soundcast/inputs'

import os,sys,datetime,re
import subprocess
from shutil import copy2 as shcopy

time_start = datetime.datetime.now()

print "\nSoundCast run: start time:", time_start

def setup_emme_project_folders():
    'Copy, unzip, and prepare the Projects/ and Banks/ emme folders'

    # Unzip Projects/ templates using 7-zip (must be in path)
    unzip_cmd = '7z.exe x -y '+base_inputs+'/etc/emme_projects.7z'
    subprocess.call(unzip_cmd)

    # get timeperiod subfolders from os
    time_periods = os.listdir('projects')

    # Subst current workdir into project files
    for period in time_periods:
        print "munging",period
        template = os.path.join('projects',period,period+'.tmpl')
        project  = os.path.join('projects',period,period+'.emp')
        emmebank = os.path.join(os.getcwd(),'Banks',period)
        emmebank = emmebank.replace('\\','/')

        with open(template,'r') as source:
            lines = source.readlines()
        with open(project,'w') as source:
            for line in lines:
                source.write(re.sub(r'\{\$BANKPATH\}',
                             emmebank,
                             line))

def copy_large_inputs():
    print 'Copying large inputs...'

    shcopy(base_inputs+'/etc/seed_trips.h5','Inputs')
    shcopy(base_inputs+'/etc/psrc_node_node_distances_binary.dat','Inputs')
    shcopy(base_inputs+'/etc/psrc_parcel_decay_2006.dat','Inputs')
    shcopy(base_inputs+'/landuse/hhs_and_persons.h5','Inputs')



##########################
# Main Script:

setup_emme_project_folders()

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
    '-use_seed_trips'])

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

