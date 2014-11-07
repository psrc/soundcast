#!python.exe
# PSRC SoundCast Model Runner
# ===========================
import os
import sys
import datetime
import re
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
from data_wrangling import *

# Create text file to log model performance
logfile = open(main_log_file, 'wb')

time_start = datetime.datetime.now()
print "\nSoundCast run: start time:", time_start

def parcel_buffering():
    copy_parcel_buffering_files()
    print 'adding military jobs to regular jobs'
    returncode=subprocess.call([sys.executable, 'scripts/supplemental/military_parcel_loading.py'])
    if returncode != 0:
        print 'Military Job loading failed'
        sys.exit(1)
    print 'military jobs loaded'
    create_buffer_xml()
    print 'running buffer tool'
    main_dir = os.path.abspath('')
    returncode = subprocess.call(main_dir + '/scripts/parcel_buffer/DSBuffTool.exe')
    os.remove(main_dir + '/inputs/parcel_buffer/parcel_buff_network_inputs.7z')

def build_seed_skims():
    print "Processing skims and paths."
    time_copy = datetime.datetime.now()
    returncode = subprocess.call([sys.executable,
        'scripts/skimming/SkimsAndPaths.py',
        '-use_daysim_output_seed_trips'])
    if returncode != 0:
             returncode = subprocess.call([sys.executable,
                           'scripts/skimming/SkimsAndPaths.py',
                            '-use_daysim_output_seed_trips'])
                  
    time_skims = datetime.datetime.now()
    print '###### Finished skimbuilding:', str(time_skims - time_copy)
    if returncode != 0:
        sys.exit(1)

def modify_config(config_vals):
    config_template = open('configuration_template.properties','r')
    config = open('configuration.properties','w')
  
    try:
        for line in config_template:
            for config_temp, config_update in config_vals:
                if config_temp in line:
                    line = line.replace(config_temp, str(config_update))
            config.write(line)
               
        config_template.close()
        config.close()

    except:
     config_template.close()
     config.close()
     print ' Error creating configuration template file'
     sys.exit(1)
    

def build_shadow_only():
     for shad_iter in range(0, len(shadow_work)):
         if run_daysim:
            modify_config([("$SHADOW_PRICE", "true"),("$SAMPLE",shadow_work[shad_iter]),("$RUN_ALL", "false")])
            returncode = subprocess.call('./Daysim/Daysim.exe -c configuration.properties')
            if returncode != 0:
               send_error_email(recipients, returncode)
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
         logfile.write("ending daysim %s\r\n" % str((time_daysim)))


def run_truck_supplemental(iteration):
      ### RUN Truck Model ################################################################
     if run_truck_model:
         returncode = subprocess.call([sys.executable,'scripts/trucks/truck_model.py'])
         if returncode != 0:
            send_error_email(recipients, returncode)
            sys.exit(1)

      ### RUN Supplemental Trips
      ### ################################################################
    ###Adds external, special generator, and group quarters trips to DaySim
    ###outputs.'''
     if run_supplemental_trips:
         # Only run generation script once - does not change with feedback
        if iteration == 0:
            returncode = subprocess.call([sys.executable,'scripts/supplemental/generation.py'])
            if returncode != 0:
                sys.exit(1)
        returncode = subprocess.call([sys.executable,'scripts/supplemental/distribution.py'])
        if returncode != 0:
           sys.exit(1)

def daysim_assignment(iteration):
     
     ### RUN DAYSIM ################################################################
     if run_daysim:
         returncode = subprocess.call('./Daysim/Daysim.exe -c configuration.properties')
         if returncode != 0:
             #send_error_email(recipients, returncode)
             sys.exit(1)

         time_daysim = datetime.datetime.now()
         print time_daysim
         logfile.write("ending daysim %s\r\n" % str((time_daysim)))   
     
     ### ADD SUPPLEMENTAL TRIPS
     ### ####################################################
     run_truck_supplemental(iteration)
     #### ASSIGNMENTS
     #### ###############################################################
     if run_skims_and_paths:
         returncode = subprocess.call([sys.executable, 'scripts/skimming/SkimsAndPaths.py'])
         print 'return code from skims and paths is ' + str(returncode)
         if returncode != 0:
             returncode = subprocess.call([sys.executable, 'scripts/skimming/SkimsAndPaths.py'])
             if returncode != 0: 
                  #send_error_email(recipients, returncode)
                  sys.exit(1)
                  
     
     time_assign = datetime.datetime.now()
     print time_assign
     logfile.write("ending assignment %s\r\n" % str((time_assign)))


def check_convergence(iteration, recipr_sample):
    converge = "not yet"
    if iteration > 0 and recipr_sample == 1:
            con_file = open('inputs/converge.txt', 'r')
            converge = json.load(con_file)   
            con_file.close()
    return converge

def run_all_summaries():

   if run_network_summary:
      subprocess.call([sys.executable, 'scripts/summarize/network_summary.py'])
      subprocess.call([sys.executable, 'scripts/summarize/net_summary_simplify.py'])

   if run_soundcast_summary:
      subprocess.call([sys.executable, 'scripts/summarize/SCsummary.py'])

   if run_travel_time_summary:
      subprocess.call([sys.executable, 'scripts/summarize/TravelTimeSummary.py'])

   if run_network_summary and run_soundcast_summary and run_travel_time_summary:
      subprocess.call([sys.executable, 'scripts/summarize/topsheet.py'])


##################################################################################################### ###################################################################################################### 
# Main Script:
def main():
## SET UP INPUTS ##########################################################

    if run_parcel_buffering:
        parcel_buffering()

    if not os.path.exists('outputs'):
        os.makedirs('outputs')

    if run_copy_daysim_code:
        copy_daysim_code()

    if run_setup_emme_bank_folders:
        setup_emme_bank_folders()

    if run_setup_emme_project_folders:
        setup_emme_project_folders()

    if run_copy_large_inputs:
        copy_large_inputs()

    if run_update_parking:
        if base_year == scenario_name:
            print("----- This is a base-year analysis. Parking parcels are NOT being updated! Input for 'run_update_parking' is over-ridden. -----")
        else:
            returncode = subprocess.call([sys.executable,
                                      'scripts/utils/ParcelBuffering/update_parking.py', base_inputs])

### IMPORT NETWORKS
### ###############################################################
    if run_import_networks:
        time_copy = datetime.datetime.now()
        returncode = subprocess.call([sys.executable,
        'scripts/network/network_importer.py', base_inputs])
        time_network = datetime.datetime.now()
        print '###### Finished Importing Networks:', str(time_network - time_copy)
        if returncode != 0:
           sys.exit(1)

### BUILD SKIMS ###############################################################
    if run_skims_and_paths_seed_trips == True:
        build_seed_skims()
    
### RUN DAYSIM AND ASSIGNMENT TO CONVERGENCE-- MAIN LOOP
### ##########################################

    for iteration in range(len(pop_sample)):
        print "We're on iteration %d" % (iteration)
        logfile.write("We're on iteration %d\r\n" % (iteration))
        time_start = datetime.datetime.now()
        logfile.write("starting run %s" % str((time_start)))
  
  # set up your Daysim configuration depending on if you are building shadow
  # prices or not
        if not should_build_shadow_price or pop_sample[iteration] > 2:
            ####we are not using shadow pricing during initial skim building for now. Shadow prices are built 
            #from scratch below if should_build_shadow_price = true. Keeping old code in case we want to switch back. 
            #copy_shadow_price_file()####
            modify_config([("$SHADOW_PRICE" ,"false"),("$SAMPLE",pop_sample[iteration]),("$RUN_ALL", "true")])
        else:
         modify_config([("$SHADOW_PRICE", "false"),("$SAMPLE",pop_sample[iteration]),("$RUN_ALL", "true")])
        
        # RUN THE MODEL finally
        daysim_assignment(iteration)

        converge=check_convergence(iteration, pop_sample[iteration])
        if converge == 'stop':
            print "System converged! The universe is in equilbrium for just one moment."
            con_file.close()
            break
        print 'The system is not yet converged. Daysim and Assignment will be re-run.'

    # when building shadow prices we get the skims to convergence and then we run work and school models only
    # then we run one round of daysim -final assignment.
    if should_build_shadow_price:
        build_shadow_only()
        modify_config([("$SHADOW_PRICE" ,"true"),("$SAMPLE","1"), ("$RUN_ALL", "true")])
        daysim_assignment()

### SUMMARIZE
### ##################################################################
    run_all_summaries()

#### ALL DONE
#### ##################################################################
    clean_up()
    send_completion_email(recipients)
    print '###### OH HAPPY DAY!  ALL DONE. GO GET A ' + random.choice(good_thing)
##print '    Total run time:',time_assign_summ - time_start

if __name__ == "__main__":
    main()
