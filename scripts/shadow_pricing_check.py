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

import pandas as pd
import h5toDF
import math
import os.path
from input_configuration import *
import sys
sys.path.append(os.path.join(os.getcwd(),"scripts"))
sys.path.append(os.getcwd())

def get_percent_rmse(urbansim_file, daysim_file, guide_file):
    urbansim_data = pd.io.parsers.read_table(urbansim_file, sep = ' ') #Read in UrbanSim data
    jobs_by_taz = urbansim_data[['taz_p', 'emptot_p']].groupby('taz_p').sum() #Get number of jobs by TAZ
    daysim_data = h5toDF.convert_single(daysim_file, guide_file, 'Daysim Outputs', 'Person') #Read in person file from DaySim data
    workers_by_taz = daysim_data['Person'][['pwtaz', 'psexpfac']].query('pwtaz > 0').groupby('pwtaz').sum() #Get number of workers by TAZ
    workers_jobs_by_taz = pd.merge(jobs_by_taz, workers_by_taz, left_index = True, right_index = True) #Merge them
    workers_jobs_by_taz['DaySim'] = workers_jobs_by_taz['psexpfac'] #Rename columns...
    workers_jobs_by_taz['UrbanSim'] = workers_jobs_by_taz['emptot_p']
    f = open("inputs/workers_jobs.csv", 'w')
    workers_jobs_by_taz.to_csv(f)
    f.close()
    del workers_jobs_by_taz['emptot_p']
    del workers_jobs_by_taz['psexpfac']
    workers_jobs_by_taz['Difference'] = workers_jobs_by_taz['DaySim'] - workers_jobs_by_taz['UrbanSim']
    workers_jobs_by_taz['Squared Difference'] = workers_jobs_by_taz['Difference']**2
    rms_error = math.sqrt(workers_jobs_by_taz['Squared Difference'].mean())
    percent_rmse = rms_error / workers_jobs_by_taz['DaySim'].mean() * 100
    print '%RMSE: ' + str(round(percent_rmse, 2)) + '%'
    return percent_rmse

def convergence_check(rmse_list, convergence_criterion, iteration): #Function not presently in use
    if iteration == 1:
        convergence = False
        return convergence #No comparison on the first iteration
    if abs(rmse_list[iteration - 1] - rmse_list[iteration - 2]) < convergence_criterion:
        convergence = True
    else:
        convergence = False
    return convergence

def main():
    if not os.path.isfile('inputs/shadow_rmse.txt'):
        open('inputs/shadow_rmse.txt', 'a').close()
    current_percent_rmse = get_percent_rmse(parcel_decay_file, h5_results_file, guidefile)
    shadow_rmse = open('inputs/shadow_rmse.txt', 'a')
    shadow_rmse.writelines(str(current_percent_rmse) + '\n')
    shadow_rmse.close()

main()