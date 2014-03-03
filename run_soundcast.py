#!python.exe

# PSRC SoundCast Model Runner
# ===========================

# Daysim executable is also not on Git
daysim_code = 'r:/soundcast/daysim'
master_project = 'LoadTripTables'
# Large input files are not in Git; copy them from:
base_inputs = 'r:/soundcast/inputs'
# make this configurable later
network_summary_files=['6to7_transit', '7to8_transit', '8to9_transit', '9to10_transit',
                       'counts_output', 'network_summary']

import os,sys,datetime,re
import subprocess
import inro.emme.database.emmebank as _eb
import json
from shutil import copy2 as shcopy
from distutils import dir_util

time_start = datetime.datetime.now()
# location of the daysim exe
print "\nSoundCast run: start time:", time_start

f = open('d:/Soundcast_log.txt', 'wb')

def multipleReplace(text, wordDict):
    for key in wordDict:
        text = text.replace(key, wordDict[key])
    return text

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

def setup_emme_bank_folders():
    emmebank_dimensions_dict = json.load(open(os.path.join('inputs', 'skim_params', 'emme_bank_dimensions.json')))
    
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
    
    shcopy(base_inputs+'/etc/daysim_outputs_seed_trips.h5','Inputs')
    dir_util.copy_tree(base_inputs+'/networks','Inputs/networks')
    dir_util.copy_tree(base_inputs+'/trucks','Inputs/trucks')
    # the configuration does not currently use the node_node distance file
    #shcopy(base_inputs+'/etc/psrc_node_node_distances_2010.h5','Inputs')
    shcopy(base_inputs+'/etc/psrc_parcel_decay_2010.dat','Inputs')
    shcopy(base_inputs+'/landuse/hh_and_persons.h5','Inputs')
    shcopy(base_inputs+'/etc/survey.h5','scripts/summarize')
    shcopy(base_inputs+'/4k/trips_auto_4k.h5','Inputs/4k')
    shcopy(base_inputs+'/4k/trips_transit_4k.h5','Inputs/4k')

def run_R_summary(summary_name,iter):
     R_path=os.path.join(os.getcwd(),'scripts/summarize/' + summary_name +'.Rnw')
     tex_path=os.path.join(os.getcwd(),'scripts/summarize/'+ summary_name +'.tex')
     run_R ='R --max-mem-size=50000M CMD Sweave --pdf ' + R_path
     returncode = subprocess.check_call(run_R)
     shcopy(os.path.join(os.getcwd(), summary_name+'.pdf'), os.path.join(os.getcwd(), 'outputs',summary_name+str(iter)+'.pdf'))
     shcopy(os.path.join(os.getcwd(), 'Rplots.pdf'), os.path.join(os.getcwd(), 'outputs',summary_name+ str(iter)+'_Plot.pdf'))
     os.remove(os.path.join(os.getcwd(), summary_name+'.pdf'))
     os.remove(os.path.join(os.getcwd(), 'Rplots.pdf'))

def run_Rcsv_summary(summary_name,iter):
    R_path=os.path.join(os.getcwd(),'scripts/summarize/' + summary_name +'.Rnw')
    tex_path=os.path.join(os.getcwd(),'scripts/summarize/'+ summary_name +'.tex')
    run_R ='R --max-mem-size=50000M CMD Sweave --pdf ' + R_path
    returncode = subprocess.check_call(run_R)

def move_files_to_outputs(iter):
    # this is hard-coded please fix later.
    shcopy(os.path.join(os.getcwd(), 'scripts/summarize/ModelTripsDistrict.csv'), os.path.join(os.getcwd(), 'outputs/ModelTripsDistrict'+str(iter)+'.csv'))
    shcopy(os.path.join(os.getcwd(), 'scripts/summarize/ModelWorkFlow.csv'), os.path.join(os.getcwd(), 'outputs/ModelWorkFlow'+str(iter)+'.csv'))
    os.remove(os.path.join(os.getcwd(), 'scripts/summarize/ModelTripsDistrict.csv'))
    os.remove(os.path.join(os.getcwd(), 'scripts/summarize/ModelWorkFlow.csv'))
    
def delete_tex_files():
    for root, dirs, files in os.walk(os.getcwd()):
        for currentFile in files:
            print "processing file: " + currentFile
            if currentFile.endswith('tex'):
                os.remove(os.path.join(root, currentFile))

def run_all_R_summaries(iter):
     run_R_summary('DaySimReport',iter)
     run_R_summary('DaysimReportLongTerm',iter)
     run_R_summary('DaysimReportDayPattern',iter)
     run_R_summary('ModeChoiceReport',iter)
     # these are commented out because you don't need them on each
     # run but you may wish to run them sometimes
     #run_R_summary('DaysimDestChoice',iter)
     #run_R_summary('DaysimTimeChoice',iter)
     #run_Rcsv_summary('DaysimReport_District', iter)
     move_files_to_outputs(iter)
     delete_tex_files()

def rename_network_outs(iter):
    for summary_name in network_summary_files:
        shcopy(os.path.join(os.getcwd(), 'outputs',summary_name+'.csv'), os.path.join(os.getcwd(), 'outputs',summary_name+str(iter)+'.csv'))
        os.remove(os.path.join(os.getcwd(), 'outputs',summary_name+'.csv'))
##########################
# Main Script:
copy_daysim_code()
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
#print '###### Finished skimbuilding:', time_skims - time_copy

# We are arbitrarily looping 3 times

for iteration in range(0,3):
     print "We're on iteration %d" % (iteration)
     f.write("We're on iteration %d\r\n" % (iteration))
     time_start = datetime.datetime.now()
     f.write("starting run %s" %str((time_start)))

     ### RUN Truck Model ################################################################
     returncode = subprocess.call([sys.executable,'scripts/trucks/truck_model.py'])
     if returncode != 0:
      sys.exit(1)

     time_trucks = datetime.datetime.now()
     print time_trucks
     f.write("ending daysim %s\r\n" %str((time_trucks)))
     
     ### RUN DAYSIM ################################################################
     returncode = subprocess.call('./Daysim/Daysim.exe -c configuration.xml')
     if returncode != 0:
      sys.exit(1)

     time_daysim = datetime.datetime.now()
     print time_daysim
     f.write("ending daysim %s\r\n" %str((time_daysim)))

     #### SUMMARIZE DAYSIM##########################################################
     run_all_R_summaries(iteration)

      ### ASSIGNMENTS ###############################################################
     time_startassign = datetime.datetime.now()
     f.write("starting assignment %s\r\n" %str((time_startassign)))
     
     subprocess.call([sys.executable, 'scripts/skimming/SkimsAndPaths.py'])


     time_assign = datetime.datetime.now()
     print time_assign
     f.write("ending assignment %s\r\n" %str((time_assign)))
     

     #print '###### Finished running assignments:',time_assign - time_daysim

     ### ASSIGNMENT SUMMARY###############################################################
     subprocess.call([sys.executable, 'scripts/summarize/network_summary.py'])
     rename_network_outs(iteration)
     time_assign_summ = datetime.datetime.now()
     print '###### Finished running assignment summary:',time_assign_summ - time_assign

### ALL DONE ##################################################################
print '###### OH HAPPY DAY!  ALL DONE. (go get a pickle.)'
#print '    Total run time:',time_assign_summ - time_start
f.close()



