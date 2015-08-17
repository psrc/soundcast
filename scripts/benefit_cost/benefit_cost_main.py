import numpy as np
import pandas as pd
import time
import h5py
import math
import itertools
import collections
import h5toDF
import xlsxwriter

# Read in Configuration Hard Code for now
model_dir = 'C:/soundcast/'
daysim_outputs_base_file = 'outputs/daysim_outputs.h5'
base_output_name = '2010'
daysim_outputs_scenario_file= 'outputs/daysim_outputs2040.h5'
scenario_output_name= '2040'
guidefile = 'scripts/summarize/CatVarDict.xlsx'
daysim_outputs_base_file= model_dir + daysim_outputs_base_file
daysim_outputs_scenario_file =  model_dir + daysim_outputs_scenario_file
guidefile = model_dir+'scripts/summarize/CatVarDict.xlsx'
bc_outputs_file = model_dir+'outputs/BenefitCost.xlsx'


#output

##################################

# Construct file location names

report_output_location = model_dir + report_output_location

household_VOT = 20
truck_VOT = 50

#truck_base_file =somewhere
#truck_scenario_file = somewhereelse



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
     

def time_inc_mode(trips, max_income, mode):

    if mode == 'auto':
        trips_inc_mode = trips.query('hhincome < @max_income & (mode== "SOV" or mode == "HOV2" or mode == "HOV3+")')
    else:
        trips_inc_mode = trips.query('hhincome < @max_income & (mode== "Transit")')

    return trips_inc_mode['travtime'].sum()

def calculate_hh_time(daysim_output, max_income, mode):

    trips = get_variables_trips(daysim_output, trip_variables_to_read, hh_variables_to_read, person_variables_to_read)
    the_time = time_inc_mode(trips, max_income, mode)

    return the_time



## To be main###########
bc_assumptions = {}

# Write out the assumptions
bc_assumptions['Household Value of Time'] = household_VOT
bc_assumptions['Truck Value of Time'] = truck_VOT
bc_assumptions['Base Household File Location'] = daysim_outputs_base_file
bc_assumptions['Scenario Household File Location'] = daysim_outputs_scenario_file
bc_assumptions['Base Truck File Location'] = daysim_outputs_base_file
bc_assumptions['Scenario Truck File Location'] = daysim_outputs_scenario_file

############# Calculate Impacts######################
bc_outputs = {}

## Read in Outputs########

trip_variables_to_read =['otaz', 'dtaz', 'travtime', 'pno', 'mode', 'tour_id']
hh_variables_to_read=['hhno', 'hhincome', 'hhvehs', 'hhtaz']
person_variables_to_read=['hhno', 'pno', 'pagey', 'pgend']

base_outputs = convert(daysim_outputs_base_file,guidefile, base_output_name)
scenario_outputs = convert(daysim_outputs_scenario_file,guidefile, scenario_output_name)

# Calculate Auto Travel Time Impacts
print "Calculating Auto Travel Time Impacts"

bc_outputs['Base Total Auto Household Time'] =  calculate_hh_time(base_outputs, 100000000, "auto")/60
bc_outputs['Base Auto Low Income Household Time'] = calculate_hh_time(base_outputs, 20000, "auto")/60
#bc_outputs['Base Truck Time'] = calculate_truck_time(truck_base_file)

bc_outputs['Scenario Total Auto Household Time'] =  calculate_hh_time(scenario_outputs,10000000000, "auto")/60
bc_outputs['Scenario Auto Low Income Household Time'] = calculate_hh_time(scenario_outputs, 20000, "auto")/60
#bc_outputs['Scenario Truck Time'] = calculate_trucks_time(truck_scenario_file)

bc_outputs['Base Total Value of Auto Travel Time'] = household_VOT*bc_outputs['Base Total Auto Household Time']  + truck_VOT*bc_outputs['Base Truck Time']

#bc_outputs['Scenario Total Value of Auto Travel Time'] = household_VOT*bc_outputs['Scenario Total Auto Household Time']  +\
#household_VOT*bc_outputs['Scenario Auto Low Income Household Time'] + truck_VOT*bc_outputs['Scenario Truck Time']

#bc_outputs['Equivalent Cost Difference in Auto Travel Time Scenario - Base']= bc_outputs['Base Total Value of Auto Travel Time'] -\
#bc_outputs['Scenario Total Value of Auto Travel Time']

# Calculate Transit Travel Time Impacts

bc_outputs['Base Total Household Transit Time'] =  calculate_hh_time(base_outputs, 100000000,"transit")
bc_outputs['Base Low Income Household Transit Time'] = calculate_hh_time(base_outputs, 20000, "transit")


bc_outputs['Scenario Total Household Transit Time'] =  calculate_hh_time(scenario_outputs,10000000000, "transit")
bc_outputs['Scenario Low Income Household  Transit Time'] = calculate_hh_time(scenario_outputs, 20000, "transit")
#bc_outputs['Scenario Truck Time'] = calculate_trucks_time(truck_scenario_file)

# Calculate Reliability Impacts
# Reliability is already included in travel times in our vdfs

# Calculate Emissions Impacts
# Particulate Matter
#Co2
#Other Air Quality

# Calculate Collision Impacts

# Calculate Out-of-Pocket User Costs

# Calculate Parking Cost

# Calculate Auto Ownership and Operating Costs

# Calculate Health Costs

# Calculate Noise Costs

# Optionally calculate Project Costs, operating and maintenance cost

# Outputs and Visualization
writer = pd.ExcelWriter(bc_outputs_file, engine = 'xlsxwriter')
pd.DataFrame(bc_assumptions.items(), columns= ['Assumption', 'Value']).sort_index(by=['Assumption']).to_excel(excel_writer = writer, sheet_name ='Assumptions', na_rep = 0, startrow = 1)
pd.DataFrame(bc_outputs.items(), columns= ['Measure', 'Value']).sort_index(by=['Measure']).to_excel(excel_writer = writer, sheet_name ='Benefits', na_rep = 0, startrow = 1)

writer.close()