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
import logging
sys.path.append(os.path.join(os.getcwd(),"inputs"))
sys.path.append(os.path.join(os.getcwd(),"scripts"))
import logcontroller
import inro.emme.database.emmebank as _eb
import random
import datetime
import pandas as pd
import shutil 
from input_configuration import *
from emme_configuration import *
from data_wrangling import *

@timed
def accessibility_calcs():
    copy_accessibility_files()
    print 'adding military jobs to regular jobs'
    returncode=subprocess.call([sys.executable, 'scripts/supplemental/military_parcel_loading.py'])
    if returncode != 0:
        print 'Military Job loading failed'
        sys.exit(1)
    print 'military jobs loaded'

    if run_update_parking:
        if base_year == scenario_name:
            print("----- This is a base-year analysis. Parking parcels are NOT being updated! Input for 'run_update_parking' is over-ridden. -----")
        else:
            print 'Starting to update UrbanSim parcel data with 4k parking data file'
            returncode = subprocess.call([sys.executable,
                                      'scripts/utils/update_parking.py', base_inputs])
            if returncode != 0:
                print 'Update Parking failed'
                sys.exit(1)
            print 'Finished updating parking data on parcel file'

    print 'Beginning Accessibility Calculations'
    returncode = subprocess.call([sys.executable, 'scripts/accessibility/accessibility.py'])
    if returncode != 0:
        print 'Accessibility Calculations Failed For Some Reason :('
        sys.exit(1)
    print 'Done with accessibility calculations'

@timed    
def build_seed_skims(max_iterations):
    print "Processing skims and paths."
    time_copy = datetime.datetime.now()
    returncode = subprocess.call([sys.executable,
        'scripts/skimming/SkimsAndPaths.py',
        str(max_iterations),
        '-use_daysim_output_seed_trips'])
    if returncode != 0:
        sys.exit(1)
                  
    time_skims = datetime.datetime.now()
    print '###### Finished skimbuilding:', str(time_skims - time_copy)
 
@timed   
def modify_config(config_vals):
    script_path = os.path.abspath(__file__)
    script_dir = os.path.split(script_path)[0] #<-- absolute dir the script is in
    config_template_path = "daysim_configuration_template.properties"
    config_path = "Daysim/daysim_configuration.properties"

    abs_config_path_template = os.path.join(script_dir, config_template_path)
    abs_config_path_out =os.path.join(script_dir, config_path)
    print abs_config_path_template
    config_template = open(abs_config_path_template,'r')
    config = open(abs_config_path_out,'w')
  
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
    
@timed
def build_shadow_only():
     for shad_iter in range(0, len(shadow_work)):
        modify_config([("$SHADOW_PRICE", "true"),("$SAMPLE",shadow_work[shad_iter]),("$RUN_ALL", "false")])
        logger.info("Start of%s iteration of work location for shadow prices", str(shad_iter))
        returncode = subprocess.call('Daysim/Daysim.exe -c Daysim/daysim_configuration.properties')
        logger.info("End of %s iteration of work location for shadow prices", str(shad_iter))
        if returncode != 0:
            #send_error_email(recipients, returncode)
            sys.exit(1)
        returncode = subprocess.call([sys.executable, 'scripts/utils/shadow_pricing_check.py'])
        shadow_con_file = open('inputs/shadow_rmse.txt', 'r')
        rmse_list = shadow_con_file.readlines()
        iteration_number = len(rmse_list)
        current_rmse = float(rmse_list[iteration_number - 1].rstrip("\n"))
        if current_rmse < shadow_con:
            print "done with shadow prices"
            shadow_con_file.close()
            return

def run_truck_supplemental(iteration):
      ### RUN Truck Model ################################################################
     if run_truck_model:
         returncode = subprocess.call([sys.executable,'scripts/trucks/truck_model.py'])
         if returncode != 0:
            #send_error_email(recipients, returncode)
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
@timed
def daysim_assignment(iteration):
     
     ### RUN DAYSIM ################################################################
     if run_daysim:
         logger.info("Start of %s iteration of Daysim", str(iteration))
         returncode = subprocess.call('Daysim/Daysim.exe -c Daysim/daysim_configuration.properties')
         logger.info("End of %s iteration of Daysim", str(iteration))
         if returncode != 0:
             #send_error_email(recipients, returncode)
             sys.exit(1)
     
     ### ADD SUPPLEMENTAL TRIPS
     ### ####################################################
     run_truck_supplemental(iteration)
     #### ASSIGNMENTS
     #### ###############################################################
     if run_skims_and_paths:
         logger.info("Start of %s iteration of Skims and Paths", str(iteration))
         num_iterations = str(max_iterations_list[iteration])
         returncode = subprocess.call([sys.executable, 'scripts/skimming/SkimsAndPaths.py', num_iterations])
         logger.info("End of %s iteration of Skims and Paths", str(iteration))
         print 'return code from skims and paths is ' + str(returncode)
         if returncode != 0:
            sys.exit(1)

     if run_bike_model:
         returncode = subprocess.call([sys.executable,'scripts/bikes/bike_model.py'])
         if returncode != 0:
            sys.exit(1)


@timed
def check_convergence(iteration, recipr_sample):
    converge = "not yet"
    if iteration > 0 and recipr_sample <= min_pop_sample_convergence_test:
            con_file = open('inputs/converge.txt', 'r')
            converge = json.load(con_file)   
            con_file.close()
    return converge

@timed
def run_all_summaries():

   if run_network_summary:
      subprocess.call([sys.executable, 'scripts/summarize/standard/network_summary.py'])
      # this summary is producing erronous results, we don't want people to think they are correct.
      subprocess.call([sys.executable, 'scripts/summarize/standard/net_summary_simplify.py'])

   if run_soundcast_summary:
      subprocess.call([sys.executable, 'scripts/summarize/calibration/SCsummary.py'])

   #Create a daily network with volumes. Will add counts and summary emme project. 
   if run_create_daily_bank:
      subprocess.call([sys.executable, 'scripts/summarize/standard/daily_bank.py'])

   if run_ben_cost:
      subprocess.call([sys.executable, 'scripts/summarize/benefit_cost/benefit_cost.py'])

##################################################################################################### ###################################################################################################### 
# Main Script:
def main():
## SET UP INPUTS ##########################################################

    if run_accessibility_calcs:
        accessibility_calcs()

    if run_accessibility_summary:
        subprocess.call([sys.executable, 'scripts/summarize/standard/parcel_summary.py'])

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

    if  run_convert_hhinc_2000_2010:
        subprocess.call([sys.executable, 'scripts/utils/convert_hhinc_2000_2010.py'])

### IMPORT NETWORKS
### ###############################################################
    if run_import_networks:
        time_copy = datetime.datetime.now()
        logger.info("Start of network importer")
        returncode = subprocess.call([sys.executable,
        'scripts/network/network_importer.py', base_inputs])
        logger.info("End of network importer")
        time_network = datetime.datetime.now()
        if returncode != 0:
           sys.exit(1)

### BUILD OR COPY SKIMS ###############################################################
    if run_skims_and_paths_seed_trips:
        build_seed_skims(10)
    # either you build seed skims or you copy them, or neither, but it wouldn't make sense to do both
    elif run_copy_seed_skims:
        copy_seed_skims()
    # Check all inputs have been created or copied
    check_inputs()
    
### RUN DAYSIM AND ASSIGNMENT TO CONVERGENCE-- MAIN LOOP
### ##########################################
    
    if(run_daysim or run_skims_and_paths or run_skims_and_paths_seed_trips):
        
        for iteration in range(len(pop_sample)):
            print "We're on iteration %d" % (iteration)
            logger.info(("We're on iteration %d\r\n" % (iteration)))
            time_start = datetime.datetime.now()
            logger.info("starting run %s" % str((time_start)))

            # Copy shadow pricing? Need to know what the sample size of the previous iteration was:
            if not should_build_shadow_price:
                print 'here'
                if iteration == 0 or pop_sample[iteration-1] > 2:
                    print 'here'
                    try:
                                                        
                            if not os.path.exists('working'):
                                os.makedirs('working')
                            shcopy(base_inputs+'/shadow_pricing/shadow_prices.txt','working/shadow_prices.txt')
                            print "copying shadow prices" 
                    except:
                            print ' error copying shadow pricing file from shadow_pricing at ' + base_inputs+'/shadow_pricing/shadow_prices.txt'
                            sys.exit(1)
                # Set up your Daysim Configration
                modify_config([("$SHADOW_PRICE" ,"true"),("$SAMPLE",pop_sample[iteration]),("$RUN_ALL", "true")])

            else:
                # We are building shadow prices from scratch, only use shadow pricing if pop sample is 2 or less
                if pop_sample[iteration-1] > 2:
                    modify_config([("$SHADOW_PRICE" ,"false"),("$SAMPLE",pop_sample[iteration]),("$RUN_ALL", "true")])
                else:
                    modify_config([("$SHADOW_PRICE" ,"true"),("$SAMPLE",pop_sample[iteration]),("$RUN_ALL", "true")])
            ## Run Skimming and/or Daysim

            daysim_assignment(iteration)
           
            converge=check_convergence(iteration, pop_sample[iteration])
            if converge == 'stop':
                print "System converged!"
                break
            print 'The system is not yet converged. Daysim and Assignment will be re-run.'

# UPDATING WORK AND SCHOOL SHADOW PRICES USING CONVERGED SKIMS FROM CURRENT RUN, THEN DAYSIM + ASSIGNMENT ############################
    build_shadow_only()
    modify_config([("$SHADOW_PRICE" ,"true"),("$SAMPLE","1"), ("$RUN_ALL", "true")])
    #This function needs an iteration parameter. Value of 1 is fine. 
    daysim_assignment(1)

### SUMMARIZE
### ##################################################################
    run_all_summaries()

#### ALL DONE
#### ##################################################################
    clean_up()
    print '###### OH HAPPY DAY!  ALL DONE. GO GET A ' + random.choice(good_thing)
##print '    Total run time:',time_assign_summ - time_start

if __name__ == "__main__":
    logger = logcontroller.setup_custom_logger('main_logger')
    logger.info('------------------------NEW RUN STARTING----------------------------------------------')
    start_time = datetime.datetime.now()


    main()

    end_time = datetime.datetime.now()
    elapsed_total = end_time - start_time
    logger.info('------------------------RUN ENDING_----------------------------------------------')
    logger.info('TOTAL RUN TIME %s'  % str(elapsed_total))