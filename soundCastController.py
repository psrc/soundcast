#!python.exe

# PSRC SoundCast Model Runner
# ===========================

import sys,datetime 
import subprocess
from shutil import copy2 as shcopy

base_inputs = 'r:/soundcast/inputs'

time_start = datetime.datetime.now()
print "SoundCast run: start time:", time_start

### COPY LARGE INPUT FILES ####################################################
print 'Copying large inputs...'

shcopy(base_inputs+'/etc/seed_trips.h5','Inputs')
shcopy(base_inputs+'/etc/psrc_node_node_distances_binary.dat','Inputs')
shcopy(base_inputs+'/etc/psrc_parcel_decay_2006.dat','Inputs')
shcopy(base_inputs+'/landuse/hhs_and_persons.h5','Inputs')

time_copy = datetime.datetime.now()
print '###### Finished copying files:', time_copy - time_start

### BUILD SKIMS ###############################################################
returncode = subprocess.call([sys.executable, 
    '/EmmeDaysimIntegration/src/EmmeDaysimIntegration.py',
    '-use_seed_trips'])

if returncode != 0:
    sys.exit(1)

time_skims = datetime.datetime.now()
print '###### Finished skimbuilding:', time_skims - time_copy

### RUN DAYSIM ################################################################
returncode = subprocess.call('./Daysim/Daysim.exe')
if returncode != 0:
    sys.exit(1)

time_daysim = datetime.datetime.now()
print '###### Finished running Daysim:',time_daysim - time_skims

### ASSIGNMENTS ###############################################################
subprocess.call([sys.executable, 
		'/EmmeDaysimIntegration/src/EmmeDaysimIntegration.py'])

time_assign = datetime.datetime.now()
print '###### Finished running assignments:',time_assign - time_daysim

### ALL DONE ##################################################################
print '###### OH HAPPY DAY!  ALL DONE. (go get a cookie.)'
print '    Total run time:',time_assign - time_start

