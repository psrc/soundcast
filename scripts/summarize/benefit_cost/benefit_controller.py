import os
import sys
import json
import numpy as np
import subprocess
sys.path.append(os.getcwd())



if __name__ == '__main__':
    with open('scripts/summarize/benefit_cost/benefit_configuration.json') as config_file:
      config = json.load(config_file)

    print 'writing out the skims for both the baseline and the alternative runs.'
    # write out skims to h5 for baseline
    returncode = subprocess.call([sys.executable,'scripts/summarize/benefit_cost/emme2h5.py', config['baseline']['filepath'],'scripts/summarize/benefit_cost/benefit_configuration.json', config['baseline']['inputpath']])
    if returncode != 0:
      print 'emme2h5.py failed for the baseline'
      sys.exit(1)

   # write out skims to h5 for alternative
    returncode = subprocess.call([sys.executable,'scripts/summarize/benefit_cost/emme2h5.py', config['alternative']['filepath'],'scripts/summarize/benefit_cost/benefit_configuration.json', config['alternative']['inputpath']])
    if returncode != 0:
      print 'emme2h5.py failed for the alternative'
      sys.exit(1)

    print 'doing consumer surplus calculations on the skims.'
    # do consumer surplus calculations on skims and trips
    returncode = subprocess.call([sys.executable,'scripts/summarize/benefit_cost/bc2.py'])
    if returncode != 0:
      print 'bc2.py failed'
      sys.exit(1)

    print 'doing air quality and crash calculations with the emme networks.'
    # do air quality and crash calculations
    returncode = subprocess.call([sys.executable,config['baseline']['inputpath']+'/scripts/summarize/benefit_cost/aq_crash_calcs.py', config['baseline']['aqoutputpath']])
    if returncode != 0:
      print 'aq_crash_calcs.py failed for the baseline'
      sys.exit(1)
    
    returncode = subprocess.call([sys.executable,config['alternative']['inputpath']+'/scripts/summarize/benefit_cost/aq_crash_calcs.py', config['alternative']['aqoutputpath']])
    if returncode != 0:
      print 'aq_crash_calcs.py failed for the alternative'
      sys.exit(1)
