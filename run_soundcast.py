#!python.exe
# Beta One
# PSRC SoundCast Model Runner
# ===========================

import os,sys,datetime,re
import subprocess
import json
from shutil import copy2 as shcopy
from distutils import dir_util
import re
import inro.emme.database.emmebank as _eb
import random
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
    shcopy(daysim_code +'/svn_stamp_out.txt', 'daysim')

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
        
 
    main_dir = os.path.abspath('')
    unzip_net_ins = '7z.exe x  ' + main_dir+'/inputs/parcel_buffer/parcel_buff_network_inputs.7z ' + "-o"+ main_dir+'/inputs/parcel_buffer/'
    returncode= subprocess.call(unzip_net_ins)
    if returncode!=0:
        print 'Could not unzip parcel buffer file from '+ main_dir+'/inputs/parcel_buffer/parcel_buff_network_inputs.7z' + ' to ' +main_dir+'/inputs/parcel_buffer/'
        sys.exit(0)
    
    print 'Copying UrbanSim parcel file'
    shcopy(base_inputs+'/landuse/parcels_urbansim.txt','Inputs/parcel_buffer')

    print 'Copying Parcel Buffering Code'
    dir_util.copy_tree(network_buffer_code,'scripts/parcel_buffer')



    
    
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
    dir_util.copy_tree(base_inputs+'/tolls','Inputs/tolls')
    dir_util.copy_tree (base_inputs+'/supplemental/trips','outputs/supplemental')
    shcopy(base_inputs+'/etc/buffered_parcels.dat','Inputs')
    shcopy(base_inputs+'/landuse/hh_and_persons.h5','Inputs')
    shcopy(base_inputs+'/etc/survey.h5','scripts/summarize')
    shcopy(base_inputs+'/4k/auto.h5','Inputs/4k')
    shcopy(base_inputs+'/4k/transit.h5','Inputs/4k')
    if run_parcel_buffering == False:
        shcopy(base_inputs+'/etc/buffered_parcels.dat','Inputs')

def copy_shadow_price_file():
    print 'Copying shadow price file.' 
    if not os.path.exists('working'):
       os.makedirs('working')
    shcopy(base_inputs+'/shadow_prices/shadow_prices.txt','working')



def rename_network_outs(iter):
    for summary_name in network_summary_files:
        csv_output = os.path.join(os.getcwd(), 'outputs',summary_name+'.csv')
        if os.path.isfile(csv_output):
            shcopy(csv_output, os.path.join(os.getcwd(), 'outputs',summary_name+str(iter)+'.csv'))
            os.remove(csv_output)

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
       
def daysim_sample(recipr_sample, config_name):
    try:
     config_template= open(config_name,'r')
     config= open('configuration.properties','w')

     for line in config_template:
         config.write(line.replace("$REPLACEME", str(recipr_sample)))

     config_template.close()
     config.close()

    except:
     config_template.close()
     config.close()

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

def daysim_assignment(iteration, recipr_sample, copy_shadow, configuration_template):
     print "We're on iteration %d" % (iteration)
     logfile.write("We're on iteration %d\r\n" % (iteration))
     time_start = datetime.datetime.now()
     logfile.write("starting run %s" %str((time_start)))

      ### RUN Truck Model ################################################################
     if run_truck_model == True:
         returncode = subprocess.call([sys.executable,'scripts/trucks/truck_model.py'])
         if returncode != 0:
            sys.exit(1)

      ### RUN Supplemental Trips ################################################################
    #''' Adds external, special generator, and group quarters trips to DaySim outputs.'''
     if run_supplemental_trips:
        returncode = subprocess.call([sys.executable,'scripts/supplemental/generation.py'])
        if returncode != 0:
           sys.exit(1)
        returncode = subprocess.call([sys.executable,'scripts/supplemental/distribution.py'])
        if returncode != 0:
           sys.exit(1)
     
     ### RUN DAYSIM ################################################################
     if run_daysim == True:
         if copy_shadow:
             copy_shadow_price_file()

         daysim_sample(recipr_sample, configuration_template)
         returncode = subprocess.call('./Daysim/Daysim.exe -c configuration.properties')
         if returncode != 0:
             sys.exit(1)

         time_daysim = datetime.datetime.now()
         print time_daysim
         logfile.write("ending daysim %s\r\n" %str((time_daysim)))   

     #### ASSIGNMENTS ###############################################################
     if run_skims_and_paths == True:
         returncode = subprocess.call([sys.executable, 'scripts/skimming/SkimsAndPaths.py'])
         print 'return code from skims and paths is ' + str(returncode)
         if returncode != 0:
             returncode=subprocess.call([sys.executable, 'scripts/skimming/SkimsAndPaths.py'])
             if returncode != 0: 
                  sys.exit(1)
                  print 'EMME problems! Why?'

     if iteration > 0 & recipr_sample == 1:
        con_file = open('inputs/converge.txt', 'r')
        converge = json.load(con_file)
        if converge == 'stop':
            print "done"
            con_file.close()
        print 'keep going'
        con_file.close()

     
     time_assign = datetime.datetime.now()
     print time_assign
     logfile.write("ending assignment %s\r\n" %str((time_assign)))

     ##print '###### Finished running assignments:',time_assign - time_daysim

#####################################################################################################
######################################################################################################
# Main Script:
## RUN PARCEL BUFFERING ON URBANSIM OUTPUTS ##########################################################
if run_parcel_buffering == True:
    copy_parcel_buffering_files()
    create_buffer_xml()
    print 'running buffer tool'
    main_dir = os.path.abspath('')
    returncode = subprocess.call(main_dir+'/scripts/parcel_buffer/DSBuffTool.exe')
    os.remove(main_dir+ '/inputs/parcel_buffer/parcel_buff_network_inputs.7z')

    
### SET UP OTHER INPUTS ###############################################################################

run_list = [("copy_daysim_code" , run_copy_daysim_code), 
             ("setup_emme_project_folders", run_setup_emme_project_folders),
             ("setup_emme_bank_folders" , run_setup_emme_bank_folders),
             ("copy_large_inputs" , run_copy_inputs)]

if not os.path.exists('outputs'):
        os.makedirs('outputs')

for i in range(0,len(run_list)):
  if run_list[i][1]==True:
    function = run_list[i][0]
    locals()[function]()

svn_file =open('daysim/svn_stamp_out.txt','r')
svn_info=svn_file.read()
logfile.write(svn_info)



### UPDATE PARCEL PARKING #############################################
if run_update_parking == True:
    if base_year == scenario_name:
        print("----- This is a base-year analysis. Parking parcles are NOT being updated! Input for 'run_update_parking' is over-ridden. -----")
    else:
        returncode = subprocess.call([sys.executable,
                                      'scripts/utils/ParcelBuffering/update_parking.py', base_inputs])
    #if returncode != 0:
    #    sys.exit(1)
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
if run_skims_and_paths_seed_trips == True:
    print "Processing skims and paths."
    time_copy = datetime.datetime.now()
    returncode = subprocess.call([sys.executable,
        'scripts/skimming/SkimsAndPaths.py',
        '-use_daysim_output_seed_trips'])
    if returncode != 0:
             returncode = subprocess.call([sys.executable,
                           'scripts/skimming/SkimsAndPaths.py',
                            '-use_daysim_output_seed_trips'])
             if returncode != 0: 
                  sys.exit(1)
                  print 'EMME problems! Why?'
    time_skims = datetime.datetime.now()
    print '###### Finished skimbuilding:', str(time_skims - time_copy)
    if returncode != 0:
        sys.exit(1)




### RUN DAYSIM AND ASSIGNMENT TO CONVERGENCE ##########################################

# We are building good initial skims.
if should_build_shadow_price:
      #We are building shadow prices, do not copy and delete if file exists
      for iteration in range(0,len(pop_sample)):
        if pop_sample[iteration] <= 2 and os.path.isfile('working/shadow_prices.txt'):
            os.remove('working/shadow_prices.txt')
        copy_shadow = False
        daysim_assignment(iteration, pop_sample[iteration], copy_shadow, 'configuration_template.properties')

        if iteration > 0 & recipr_sample == 1:
            con_file = open('inputs/converge.txt', 'r')
            converge = json.load(con_file)
        if converge == 'stop':
            print "done"
            con_file.close()
            break
        print 'keep going'
        con_file.close()
### BUILDING SHADOW PRICE FILE ########################################################

    #Done some full iterations, now do some shadow prices
    ### BUILD SHADOW PRICE FILES FOR WORK ###################################################
      for shad_iter in range(0, len(shadow_work)):
         #if shad_iter== 0: #Checks if the file exists on the first iteration and deletes it
            #if os.path.isfile('inputs/shadow_rmse.txt'):
            #    os.remove('inputs/shadow_rmse.txt')
         if run_daysim == True:
            daysim_sample(shadow_work[shad_iter], 'configuration_template_work.properties')
            returncode = subprocess.call('./Daysim/Daysim.exe -c configuration.properties')
            if returncode != 0:
               sys.exit(1)
            returncode = subprocess.call([sys.executable, 'scripts/summarize/shadow_pricing_check.py'])
            shadow_con_file = open('inputs/shadow_rmse.txt', 'r')
            rmse_list = shadow_con_file.readlines()
            iteration_number = len(rmse_list)
            current_rmse = float(rmse_list[iteration_number - 1].rstrip("\n"))
         if current_rmse < shadow_con:
            print "done with shadow prices"
            shadow_con_file.close()
            break

         time_daysim = datetime.datetime.now()
         print time_daysim
         logfile.write("ending daysim %s\r\n" %str((time_daysim)))     
         
### Shadow prices converged, need to run full daysim/assignents one more time. Daysim cannot see updated skims again- because it will throw off workplace location/
### shadow pricing. If we could turn off Daysim workplace location and use workplace location from the previous(converged) run, we  could do more full iterations 
### here to get skims converged, knowing that our employee targets would mactch job availability. 
      daysim_assignment(len(pop_sample) + 1, 1, False, 'configuration_template.properties') 
      returncode = subprocess.call([sys.executable, 'scripts/summarize/shadow_pricing_check.py'])


else:
    # we are always using the old shadow price file (for testing)
    copy_shadow = True

    for iteration in range(0,len(pop_sample)):
        #copy_shadow = False
        daysim_assignment(iteration, pop_sample[iteration], copy_shadow, 'configuration_template.properties')
        if iteration > 0 & recipr_sample == 1:
            con_file = open('inputs/converge.txt', 'r')
            converge = json.load(con_file)
        if converge == 'stop':
            print "done"
            con_file.close()
            break
        print 'keep going'
        con_file.close()
        #copy_shadow = False


### ASSIGNMENT SUMMARY ###############################################################
if run_network_summary == True:
   returncode = subprocess.call([sys.executable, 'scripts/summarize/network_summary.py'])
   #returncode = subprocess.call([sys.executable, 'scripts/summarize/topsheet.py'])
   time_assign_summ = datetime.datetime.now()
   if returncode != 0:
      sys.exit(1)
#print '###### Finished running assignment summary:',time_assign_summ - time_assign

logfile.close()

##### SUMMARIZE SOUNDCAST ##########################################################
if run_soundcast_summary == True:
   returncode = subprocess.call([sys.executable, 'scripts/summarize/SCsummary.py'])

#### ALL DONE ##################################################################
clean_up()
print '###### OH HAPPY DAY!  ALL DONE. GO GET A ' + random.choice(good_thing)
##print '    Total run time:',time_assign_summ - time_start




