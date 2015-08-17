import numpy as np
import pandas as pd
import time
import h5py
import math
import itertools
import collections
import h5toDF
from summary_functions import *


# where are your files?
# this should be a run or config parameter
model_dir = 'C:/soundcast/'

h5_base_file = 'outputs/daysim_outputs.h5'
h5_base_name = 'Base'
h5_scen_file = 'outputs/daysim_outputs2040.h5'
h5_scen_name = 'Scenario'
report_output_location = 'outputs/time_zone.csv'
guidefile = 'scripts/summarize/CatVarDict.xlsx'
zone_dim = 4000 #hard code should be in the config
#output

##################################

# Construct file location names
h5_base_file = model_dir + h5_base_file
h5_scen_file =  model_dir + h5_scen_file
guidefile = model_dir+'scripts/summarize/CatVarDict.xlsx'
report_output_location = model_dir + report_output_location

         
def get_variables_trips(output_df,trip_variables_to_read, hh_variables_to_read, person_variables_to_read):
    trip_data = output_df['Trip'][trip_variables_to_read]
    hh_data = output_df['Household'][hh_variables_to_read]
    person_data = output_df['Person'][person_variables_to_read]
    tour_data = output_df['Tour'][['hhno', 'pno', 'id']]
    tour_data.rename(columns = {'id': 'tour_id'}, inplace = True)

    merge_hh_person = pd.merge(hh_data, person_data, 'inner', on = 'hhno')
    merge_hh_person.reset_index()
    tour_data.reset_index()
    merge_hh_tour = pd.merge(merge_hh_person, tour_data, 'inner', on =('hhno', 'pno'))
    merge_trip_hh = pd.merge(merge_hh_tour, trip_data, 'outer', on= 'tour_id')
    return merge_trip_hh
     


def write_results(trav_time_base, trav_time_scen):
    compare_times = pd.merge(trav_time_base, trav_time_scen, on =['hhtaz', 'income_group'] )
    compare_times['TimeIncreaseScenario']= compare_times['travtime_y']-compare_times['travtime_x']

    results = pd.DataFrame(data=compare_times)
    results.to_csv(report_output_location)

def times_hh_income(trips, breakpoints):

    trips['income_group'] = pd.cut(trips['hhincome'], breakpoints)
    avg_time_by_income_hhtaz = trips.groupby(['hhtaz', 'income_group']).mean()
    avg_time_inc = avg_time_by_income_hhtaz[['travtime']]

    return avg_time_inc

def main():
    trip_variables_to_read =['otaz', 'dtaz', 'travtime', 'pno', 'mode', 'tour_id']
    hh_variables_to_read=['hhno', 'hhincome', 'hhvehs', 'hhtaz']
    person_variables_to_read=['hhno', 'pno', 'pagey', 'pgend']
    income_breakpoints = [0, 15000, 35000, 75000, 150000]

    

    # break this down by mode

if __name__ == "__main__":
    main()