#!python.exe

# PSRC SoundCast Model Runner
# ===========================
import datetime, re
import subprocess
import inro.emme.database.emmebank as _eb
import json
from shutil import copy2 as shcopy
from distutils import dir_util
import re
import mmap
import os, sys
sys.path.append(os.path.join(os.getcwd(),"inputs"))
from input_configuration import *

# Create text file to log model performance
logfile = open(main_log_file, 'wb')

time_start = datetime.datetime.now()
print "\nSoundCast run: start time:", time_start


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
    emmebank_dimensions_dict = json.load(open(os.path.join('inputs','skim_params', 'emme_bank_dimensions.json')))
    
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
    
    shcopy(base_inputs+'/etc/daysim_outputs_seed_trips.h5','Inputs/')
    dir_util.copy_tree(base_inputs+'/networks','Inputs/networks')
    dir_util.copy_tree(base_inputs+'/trucks','Inputs/trucks')
    # the configuration does not currently use the node_node distance file
    #shcopy(base_inputs+'/etc/psrc_node_node_distances_2010.h5','Inputs')
    shcopy(base_inputs+'/etc/psrc_parcel_decay.dat','Inputs/')
    shcopy(base_inputs+'/landuse/hh_and_persons.h5','Inputs/')
    shcopy(base_inputs+'/etc/survey.h5','scripts/summarize')
    shcopy(base_inputs+'/4k/trips_auto_4k.h5','Inputs/4k')
    shcopy(base_inputs+'/4k/trips_transit_4k.h5','Inputs/4k')
    time_copy = datetime.datetime.now()
    print '###### Finished copying files:', time_copy - time_start

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
     run_R_summary('DaysimDestChoice',iter)
     run_R_summary('DaysimTimeChoice',iter)
     run_Rcsv_summary('DaysimReport_District', iter)
     move_files_to_outputs(iter)
     delete_tex_files()

def rename_network_outs(iter):
    for summary_name in network_summary_files:
        csv_output = os.path.join(os.getcwd(), 'outputs',summary_name+'.csv')
        if os.path.isfile(csv_output):
            shcopy(csv_output, os.path.join(os.getcwd(), 'outputs',summary_name+str(iter)+'.csv'))
            os.remove(csv_output)

def daysim_sample(iter):
    try: 
     config= open('configuration.xml','a+b')
     mem_config= mmap.mmap(config.fileno(),0, access=mmap.ACCESS_WRITE)
     mem_config.seek(0)
     loc_sample_str=re.search('HouseholdSamplingRateOneInX', mem_config)
     sample_size=str(pop_sample[iter])
     mem_config[loc_sample_str.end()+2]= sample_size[0:1]
     mem_config[loc_sample_str.end()+3]= '\"'
     mem_config[loc_sample_str.end()+4]= ' ' 
     if len(sample_size)>1:
        mem_config[loc_sample_str.end()+3] = sample_size[1:2]
        mem_config[loc_sample_str.end()+4]= '\"'
     mem_config.flush()
     mem_config.close()
     config.close()
    except:
     config.close()
     mem_config.close()

##########################
# Main Script:
main_dict = {"copy_daysim_code" : run_copy_daysim_code, 
             "setup_emme_project_folders" : run_setup_emme_project_folders,
             "setup_emme_bank_folders" : run_setup_emme_bank_folders,
             "copy_large_inputs" : run_copy_inputs}

sorted_main_dict = sorted(main_dict.iteritems())

for i in range(len(sorted_main_dict)):
    if sorted_main_dict[i][1] == True:
        function = sorted_main_dict[i][0]
        locals()[function]()

### IMPORT NETWORKS ###############################################################\
if run_import_networks == True:
    time_copy = datetime.datetime.now()
    returncode = subprocess.call([sys.executable,
        'scripts/network/network_importer.py', base_inputs])
    time_network = datetime.datetime.now()
    print '###### Finished Importing Networks:', str(time_network - time_copy)

    if returncode != 0:
        sys.exit(1)



### BUILD SKIMS ###############################################################
if run_skims_and_paths == True:
    print "Processing skims and paths."
    time_copy = datetime.datetime.now()
    returncode = subprocess.call([sys.executable,
        'scripts/skimming/SkimsAndPaths.py',
        '-use_daysim_output_seed_trips'])
    time_skims = datetime.datetime.now()
    print '###### Finished skimbuilding:', str(time_skims - time_copy)
    if returncode != 0:
        sys.exit(1)

for iteration in range(0,num_iter):
     print "We're on iteration %d" % (iteration)
     logfile.write("We're on iteration %d\r\n" % (iteration))
     time_start = datetime.datetime.now()
     logfile.write("starting run %s" %str((time_start)))

      ### RUN Truck Model ################################################################
     if run_truck_model == True:
         returncode = subprocess.call([sys.executable,'scripts/trucks/truck_model.py'])
         if returncode != 0:
            sys.exit(1)
     
     ### RUN DAYSIM ################################################################
     if run_daysim == True:
         daysim_sample(iteration)
         returncode = subprocess.call('./Daysim/Daysim.exe -c configuration.xml')
         if returncode != 0:
             sys.exit(1)

         time_daysim = datetime.datetime.now()
         print time_daysim
         logfile.write("ending daysim %s\r\n" %str((time_daysim)))   
     #### ASSIGNMENTS ###############################################################
     if run_skims_and_paths == True:
         returncode = subprocess.call([sys.executable, 'scripts/skimming/SkimsAndPaths.py'])
         if returncode != 0:
             sys.exit(1)

     if iteration > 0:
        con_file = open('inputs/' + scenario_name + '/converge.txt', 'r')
        converge = json.load(con_file)
        if converge == 'stop':
            print "done"
            con_file.close()
            break
        print 'keep going'
        con_file.close()

     
     time_assign = datetime.datetime.now()
     print time_assign
     logfile.write("ending assignment %s\r\n" %str((time_assign)))

     #print '###### Finished running assignments:',time_assign - time_daysim

     ### ASSIGNMENT SUMMARY###############################################################
     if run_network_summary == True:
         returncode = subprocess.call([sys.executable, 'scripts/summarize/network_summary.py'])
         returncode = subprocess.call([sys.executable, 'scripts/summarize/topsheet.py'])
         time_assign_summ = datetime.datetime.now()
         if returncode != 0:
             sys.exit(1)
         ##print '###### Finished running assignment summary:',time_assign_summ - time_assign


logfile.close()
##### SUMMARIZE DAYSIM##########################################################
iteration = 'last'

if run_r_summaries == True:
    run_all_R_summaries(iteration)
#### ALL DONE ##################################################################
print '###### OH HAPPY DAY!  ALL DONE. (go get a pickle.)'
##print '    Total run time:',time_assign_summ - time_start
#f.close()



