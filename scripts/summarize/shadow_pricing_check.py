import pandas as pd
import sys
import h5toDF
import math



daysim_file = 'R:/JOE/my_first_model_run_outputs.h5' #Daysim outputs
guide_file = 'R:/JOE/summarize/CatVarDict.xlsx' #To recode categorical variables in Daysim outputs
urbansim_file = 'R:/JOE/psrc_parcel_decay_2010.dat' #Urbansim Outputs

def get_percent_rmse(urbansim_file, daysim_file, guide_file, iteration_number):
    urbansim_data = pd.io.parsers.read_table(urbansim_file, sep = ' ') #Read in UrbanSim data
    jobs_by_taz = urbansim_data[['taz_p', 'emptot_p']].groupby('taz_p').sum() #Get number of jobs by TAZ
    daysim_data = h5toDF.convert_single(daysim_file, guide_file, 'Daysim Outputs', 'Person') #Read in person file from DaySim data
    workers_by_taz = daysim_data['Person'][['pwtaz', 'psexpfac']].query('pwtaz > 0').groupby('pwtaz').sum() #Get number of workers by TAZ
    workers_jobs_by_taz = pd.merge(jobs_by_taz, workers_by_taz, left_index = True, right_index = True) #Merge them
    workers_jobs_by_taz['DaySim'] = workers_jobs_by_taz['psexpfac'] #Rename columns...
    workers_jobs_by_taz['UrbanSim'] = workers_jobs_by_taz['emptot_p']
    del workers_jobs_by_taz['emptot_p']
    del workers_jobs_by_taz['psexpfac']
    workers_jobs_by_taz['Difference'] = workers_jobs_by_taz['DaySim'] - workers_jobs_by_taz['UrbanSim']
    workers_jobs_by_taz['Squared Difference'] = workers_jobs_by_taz['Difference']**2
    rms_error = math.sqrt(workers_jobs_by_taz['Squared Difference'].mean())
    percent_rmse = rms_error / workers_jobs_by_taz['DaySim'].mean() * 100
    print '%RMSE for iteration ' + str(iteration_number) + ': ' + str(round(percent_rmse, 2)) + '%'
    return percent_rmse

def convergence_check(rmse_list, convergence_criterion, iteration):
    if iteration == 1:
        convergence = False
        return convergence #No comparison on the first iteration
    if abs(rmse_list[iteration - 1] - rmse_list[iteration - 2]) < convergence_criterion:
        convergence = True
    else:
        convergence = False
    return convergence

get_percent_rmse(urbansim_file, daysim_file, guide_file, '[Insert Iteration Number Here]')