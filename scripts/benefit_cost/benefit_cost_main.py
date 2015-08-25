import numpy as np
import pandas as pd
import time
import h5py
import math
import itertools
import collections
import h5toDF
import xlsxwriter
import os, sys
sys.path.append(os.path.join(os.getcwd(),"inputs"))
sys.path.append(os.path.join(os.getcwd(),"scripts"))
import input_configuration
import inro.emme.desktop.app as app
import inro.modeller as _m
from EmmeProject import *
import datetime

# Read in Configuration Hard Code for now
model_dir = 'C:/soundcast/'
daysim_outputs_base_file = 'outputs/daysim_outputs3.h5'
base_output_name = 'EasyTravel'
daysim_outputs_scenario_file= 'outputs/daysim_outputs4.h5'
scenario_output_name= 'HighCost'
guidefile = 'scripts/summarize/CatVarDict.xlsx'
daysim_outputs_base_file= model_dir + daysim_outputs_base_file
daysim_outputs_scenario_file =  model_dir + daysim_outputs_scenario_file
guidefile = model_dir+'scripts/summarize/CatVarDict.xlsx'
bc_outputs_file = model_dir+'outputs/BenefitCost.xlsx'
parcels_file  =model_dir + '/inputs/buffered_parcels.dat'


#truck_base_file =somewhere
#truck_scenario_file = somewhereelse

HOUSEHOLD_VOT = 20
TRUCK_VOT = 50
MINS_HR= 60
CENTS_DOLLAR = 100

LOW_INC_MAX = 25000
MAX_INC = 10000000000

HRS_PARKED_AVG = 2
PAID_UNPAID_PARK_RATIO = 0.5
FOUR_PLUS_CAR_AVG = 4.3
ANNUALIZATION = 300
ANNUAL_OWNERSHIP_COST = 6290


def get_variables_trips(output_df,trip_variables, hh_variables, person_variables):
    trip_data = output_df['Trip'][trip_variables]
    hh_data = output_df['Household'][hh_variables]
    person_data = output_df['Person'][person_variables]
    tour_data = output_df['Tour'][['hhno', 'pno', 'id']]
    tour_data.rename(columns = {'id': 'tour_id'}, inplace = True)

    merge_hh_person = pd.merge(hh_data, person_data, 'inner', on = 'hhno')
    merge_hh_person.reset_index()
    tour_data.reset_index()
    merge_hh_tour = pd.merge(merge_hh_person, tour_data, 'inner', on =('hhno', 'pno'))
    merge_trip_hh = pd.merge(merge_hh_tour, trip_data, 'outer', on= 'tour_id')
    return merge_trip_hh  

def impedance_inc_mode(trips, max_income, mode, impedance_type):
    if mode == 'auto':
        imp_inc_mode = trips.query('hhincome < @max_income & (mode== "SOV" or mode == "HOV2" or mode == "HOV3+")')
    else:
        imp_inc_mode = trips.query('hhincome < @max_income & (mode== "Transit")')
    return imp_inc_mode[impedance_type].sum()


def calculate_park_costs(parcels, trips):
    parcels = pd.read_table(parcels_file, sep=' ')
    # only get the trips where the person is driving
    drive_trips =  trips.loc[trips['dorp']=='Driver']
    park_cost = pd.merge(parcels, drive_trips, left_on = 'parcelid', right_on= 'dpcl')
    park_cost_tot = PAID_UNPAID_PARK_RATIO*HRS_PARKED_AVG* park_cost['pprichr1'].sum()/CENTS_DOLLAR
    # need to delete variables to not run out of memory
    del park_cost
    del parcels
    return park_cost_tot

def auto_own_cost(output_df):
    hh_data = output_df['Household']['hhvehs']
    hh_data.loc[hh_data== 4] = FOUR_PLUS_CAR_AVG
    return hh_data.sum()*ANNUAL_OWNERSHIP_COST/ANNUALIZATION

def nonmotorized_benefits(trips, mode):
    nonmotorized_trips_dist=  trips.loc[trips['mode']== mode]
    trips_people = nonmotorized_trips_dist.groupby(['hhno', 'pno_x']).agg({'travtime' :[np.sum]})
    people_times = {'Time': trips_people.mean(), 'People': trips_people.count()}
    return  people_times


def group_vmt_speed(my_project):
    speed_bins = [-20, -10, 0, 10, 20, 30, 40, 50, 60, 70, 80, 90]
    speed_dict = {}

    for item in speed_bins:
        speed_dict[item] = {'car_vmt' : 0, 'lt_truck_vmt' : 0,  'med_truck_vmt' : 0, 'hv_truck_vmt' : 0}

    for key, value in sound_cast_net_dict.iteritems():

        print 'Getting VMT by Speed bin for time period ' + key
        
        my_project.change_active_database(key)
        network = my_project.current_scenario.get_network()

        for link in network.links():
            speed = link['length']* MINS_HR/link['auto_time']
            speed = int(round(speed, -1))
            if speed > 0 and speed <100:
                speed_dict[speed]['car_vmt'] = speed_dict[speed]['car_vmt'] + (link['@svtl1']+ link['@svtl2'] + link['@svtl3'] + link['@svnt1'] +  link['@svnt2'] + link['@svnt3'] + link['@h2tl1'] + link['@h2tl2'] +
                link['@h2tl3'] + link['@h2nt1'] + link['@h2nt2'] + link['@h2nt3'] + link['@h3tl1'] +
                link['@h3tl2'] + link['@h3tl3'] + link['@h3nt1'] + link['@h3nt2'] + link['@h3nt3'])*link['length']

                speed_dict[speed]['lt_truck_vmt'] = speed_dict[speed]['lt_truck_vmt'] + link['@lttrk'] * link['length']
                speed_dict[speed]['med_truck_vmt'] = speed_dict[speed]['med_truck_vmt'] + link['@mveh'] * link['length']
                speed_dict[speed]['hv_truck_vmt'] = speed_dict[speed]['hv_truck_vmt'] + link['@hveh'] * link['length']

    speed_df = pd.DataFrame.from_dict(speed_dict)                 
    return speed_df

def group_vmt_class(my_project):
    # Currently the assumptions do not vary the accident rates by VC range
    # if they did we could update this to include a VC class breakdwon.
    # for testing:
    network = my_project.current_scenario.get_network()

    # store vmt by functional class 1= Freeway, 3= Expressway, etc
    vmt_func_class= {1 : 0, 3 : 0,  5 : 0, 7 : 0}
    
    for key, value in sound_cast_net_dict.iteritems():

        print 'Getting VMT by Facility Type for Time Period ' + key
        my_project.change_active_database(key)
        network = my_project.current_scenario.get_network()

        for link in network.links():
            # Only bigger facility types are included
            if link['volume_delay_func'] in vmt_func_class.keys():
                vmt_func_class[link['volume_delay_func']]+=link['auto_volume']*link['length']

    vmt_fc_df = pd.DataFrame.from_dict(vmt_func_class)
    return vmt_fc_df       


def main():
    bc_assumptions = {}

    # Write out the assumptions
    bc_assumptions['Household Value of Time'] = HOUSEHOLD_VOT
    bc_assumptions['Truck Value of Time'] = TRUCK_VOT
    bc_assumptions['Base Household File Location'] = daysim_outputs_base_file
    bc_assumptions['Scenario Household File Location'] = daysim_outputs_scenario_file
    bc_assumptions['Base Truck File Location'] = daysim_outputs_base_file
    bc_assumptions['Scenario Truck File Location'] = daysim_outputs_scenario_file

    ############# Calculate Impacts#######################################################################
    bc_outputs = {}
    bc_time_outputs = {}
    bc_low_inc_outputs = {}
    bc_health_outputs = {}

    ## Read in Dayim Outputs########
    trip_variables = ['otaz', 'dtaz', 'travtime', 'travcost', 'pno', 'mode', 'tour_id', 'opcl', 'dpcl', 'dorp']
    hh_variables = ['hhno', 'hhincome', 'hhvehs', 'hhtaz']
    person_variables = ['hhno', 'pno', 'pagey', 'pgend']

    base_outputs = h5toDF.convert(daysim_outputs_base_file,guidefile, base_output_name)
    scenario_outputs = h5toDF.convert(daysim_outputs_scenario_file,guidefile, scenario_output_name)

    base_trips = get_variables_trips(base_outputs, trip_variables, hh_variables, person_variables)
    scenario_trips = get_variables_trips(scenario_outputs, trip_variables, hh_variables, person_variables)

    ### Get EMME project set up##############
    my_project = EmmeProject(project)

    ##### TRAVEL TIME######################################3
    # Calculate Auto Travel Time Impacts
    # To Do - Calculate for different groups of people - young and old, more income
    # groups
    # Calculate by home origin
    # Should we include walking and biking costs?

    # Time is calculated in PathTypeModel.cs
    # For Walking and Biking, time is just the walk or bike time
    # For Auto the time is just in-vehicle time var skimValue =
    #				useZones
    #					?  ImpedanceRoster.GetValue("ivtime", skimMode, pathType, votValue,
    #					_outboundTime, _originZoneId, _destinationZoneId)
    # For transit: path.Time = outboundInVehicleTime + initialWaitTime +
    # transferWaitTime + WalkTime

    print "Calculating Auto Travel Time Impacts"

    bc_time_outputs['Base Total Auto Household Time'] = impedance_inc_mode(base_trips, MAX_INC, "auto", "travtime") / MINS_HR
    bc_time_outputs['Base Auto Low Income Household Time'] = impedance_inc_mode(base_trips, LOW_INC_MAX, "auto", "travtime") / MINS_HR
    #bc_outputs['Base Truck Time'] = calculate_truck_time(truck_base_file)
    bc_time_outputs['Scenario Total Auto Household Time'] = impedance_inc_mode(scenario_trips, MAX_INC, "auto", "travtime") / MINS_HR
    bc_time_outputs['Scenario Auto Low Income Household Time'] = impedance_inc_mode(scenario_trips, LOW_INC_MAX, "auto", "travtime") / MINS_HR

    bc_outputs['Base Total Auto Household Time Cost'] = bc_time_outputs['Base Total Auto Household Time'] * HOUSEHOLD_VOT
    #bc_outputs['Base Truck Time'] = calculate_truck_time(truck_base_file)
    bc_time_outputs['Scenario Total Auto Household Time'] = impedance_inc_mode(scenario_trips, MAX_INC, "auto", "travtime") / MINS_HR
    bc_time_outputs['Scenario Auto Low Income Household Time'] = impedance_inc_mode(scenario_trips, LOW_INC_MAX, "auto", "travtime") / MINS_HR
    bc_outputs['Scenario Total Auto Household Time Cost'] = bc_time_outputs['Scenario Total Auto Household Time'] * HOUSEHOLD_VOT

    #bc_outputs['Scenario Truck Time'] = calculate_trucks_time(truck_scenario_file)

    #bc_outputs['Base Total Value of Auto Time'] = HOUSEHOLD_VOT*bc_outputs['Base
    #Total Auto Household Time'] + TRUCK_VOT*bc_outputs['Base Truck Time']

    #bc_outputs['Scenario Total Value of Auto Travel Time'] =
    #HOUSEHOLD_VOT*bc_outputs['Scenario Total Auto Household Time'] +\
    #HOUSEHOLD_VOT*bc_outputs['Scenario Auto Low Income Household Time'] +
    #TRUCK_VOT*bc_outputs['Scenario Truck Time']

    #bc_outputs['Equivalent Cost Difference in Auto Travel Time Scenario - Base']=
    #bc_outputs['Base Total Value of Auto Travel Time'] -\
    #bc_outputs['Scenario Total Value of Auto Travel Time']

    # Calculate Transit Travel Time Impacts
    print "Calculating Transit Travel Time Impacts"
    bc_time_outputs['Base Total Household Transit Time'] = impedance_inc_mode(base_trips, MAX_INC,"transit", "travtime") / MINS_HR
    bc_time_outputs['Base Low Income Household Transit Time'] = impedance_inc_mode(base_trips, LOW_INC_MAX, "transit", "travtime") / MINS_HR


    bc_time_outputs['Scenario Total Household Transit Time'] = impedance_inc_mode(scenario_trips, MAX_INC, "transit", "travtime") / MINS_HR
    bc_time_outputs['Scenario Low Income Household Transit Time'] = impedance_inc_mode(scenario_trips, LOW_INC_MAX, "transit", "travtime") / MINS_HR

    bc_outputs['Base Total Transit Household Time Cost'] = bc_time_outputs['Base Total Household Transit Time'] * HOUSEHOLD_VOT
    bc_outputs['Scenario Total Transit Household Time Cost'] = bc_time_outputs['Base Total Household Transit Time'] * HOUSEHOLD_VOT
    #bc_outputs['Scenario Truck Time'] = calculate_trucks_time(truck_scenario_file)

    # Calculate Reliability Impacts
    # Reliability is already included in travel times in our vdfs - may want to
    # revisit

    #TRAVEL COST ################################################
    # Calculate Out-of-Pocket User Costs
    # Toll cost
    # in the field Travcost on the trip records
    # For Auto the travel cost is: the Toll cost in the skims + Auto Operating
    # Costs
    #_pathCost[pathType] +=
    #					useZones
    #						?  ImpedanceRoster.GetValue("toll", skimMode, pathType, votValue,
    #						_returnTime, _destinationZoneId, _originZoneId).Variable
    #_pathCost[pathType] += skimValue.BlendVariable * centsPerMile / 100.0;
    # Is this cost scaled for occupancy?

    # For transit, the cost is the fare
    print "Calculating Out-of-Pocket and Ownership Costs"
    bc_outputs['Base Total Auto Household Toll and Auto Operating Cost'] = impedance_inc_mode(base_trips, MAX_INC, "auto", "travcost")
    bc_low_inc_outputs['Base Low Income Household Tolls  and Auto Operating Cost'] = impedance_inc_mode(base_trips, LOW_INC_MAX, "auto", "travcost")
    bc_outputs['Scenario Total Auto Household Tolls and Auto Operating Cost'] = impedance_inc_mode(scenario_trips, MAX_INC, "auto", "travcost")
    bc_low_inc_outputs['Scenario Low Income Household Tolls and Auto Operating Cost'] = impedance_inc_mode(scenario_trips, LOW_INC_MAX,"auto", "travcost")
    bc_outputs['Base Total Transit Fares'] = impedance_inc_mode(base_trips, MAX_INC, "transit", "travcost")
    bc_low_inc_outputs['Base Low Income Transit Fares'] = impedance_inc_mode(base_trips, MAX_INC, "transit", "travcost")
    bc_outputs['Scenario Total Transit Fares'] = impedance_inc_mode(base_trips, MAX_INC, "transit", "travcost")
    bc_low_inc_outputs['Scenario Low Income Transit Fares'] = impedance_inc_mode(base_trips, MAX_INC, "transit", "travcost")

    # Calculate Parking Cost
    ##Find this by joining the trips with the buffered parcel data and getting
    ##parking cost
    # to do - allow for different parcel files between base and scenario
    # Reasonability check - In 2010, number of hourly parking spaces in the region
    # = 90,000
    # Mean Cost per space per hour $8.22, Assume that occupied 10 hours per day -
    # would be a cost of 7.4 million per day
    bc_outputs['Base Parking Costs'] = calculate_park_costs(parcels_file, base_trips)
    bc_outputs['Scenario Parking Costs'] = calculate_park_costs(parcels_file, scenario_trips)


    # Calculate Auto Ownership and Operating Costs
    # Auto Ownership Cost = Number of Autos Owned * Average Ownership Cost
    bc_outputs['Base Auto Ownership Costs'] = auto_own_cost(base_outputs)
    bc_outputs['Scenario Auto Ownership Costs'] = auto_own_cost(scenario_outputs)


    # Calculate Emissions Impacts
    # The emissions impacts come from grouping VMT into speed groups and applying a factor per mile.
    vmt_speed_bin = group_vmt_speed(my_project)
   
    # Calculate Collision Impacts
    # For collisions, we assume a rate of collisions per VMT by facility type.
    vmt_func_class = group_vmt_class(my_project)
  

    # Calculate Health Costs
    # For this we need average distance walked and biked per person
    # Total number of people walking and biking
    # http://www.heatwalkingcycling.org/
    # query out walkers and bikers


    # Currently the average time walked per walker is quite high.  We should fix
    # this.
    # I think the problem is capturing the short walk trips and we should be able
    # to get this with the 2014 dataset
    base_walk_times = nonmotorized_benefits(base_trips, 'Walk')
    base_bike_times = nonmotorized_benefits(base_trips, 'Bike')
    bc_health_outputs['Base Average Time Walked per Walker'] = base_walk_times['Time'].values[0]
    bc_health_outputs['Base Total Number of Walkers'] = base_walk_times['People'].values[0]
    bc_health_outputs['Base Average Time Biked per Biker'] = base_bike_times['Time'].values[0]
    bc_health_outputs['Base Total Number of Bikers'] = base_bike_times['People'].values[0]

    scenario_walk_times = nonmotorized_benefits(scenario_trips, 'Walk')
    scenario_bike_times = nonmotorized_benefits(scenario_trips, 'Bike')
    bc_health_outputs['Scenario Average Time Walked per Walker'] = scenario_walk_times['Time'].values[0]
    bc_health_outputs['Scenario Total Number of Walkers'] = scenario_walk_times['People'].values[0]
    bc_health_outputs['Scenario Average Time Biked per Biker'] = scenario_bike_times['Time'].values[0]
    bc_health_outputs['Scenario Total Number of Bikers'] = scenario_bike_times['People'].values[0]


    # Aggregate Logsum based Time measure

    # Optionally calculate Project Costs, operating and maintenance cost

    # Outputs and Visualization
    writer = pd.ExcelWriter(bc_outputs_file, engine = 'xlsxwriter')
    pd.DataFrame(bc_outputs.items(), columns= ['Cost', 'Value']).sort_index(by=['Cost']).to_excel(excel_writer = writer, sheet_name = 'Costs', na_rep = 0, startrow = 1)
    pd.DataFrame(bc_time_outputs.items(), columns= ['Time', 'Value']).sort_index(by=['Time']).to_excel(excel_writer = writer, sheet_name ='Time', na_rep = 0, startrow = 1)
    pd.DataFrame(bc_health_outputs.items(), columns= ['Measure', 'Value']).sort_index(by=['Measure']).to_excel(excel_writer = writer, sheet_name ='Health', na_rep = 0, startrow = 1)
    pd.DataFrame(bc_assumptions.items(), columns= ['Assumption', 'Value']).sort_index(by=['Assumption']).to_excel(excel_writer = writer, sheet_name ='Assumptions', na_rep = 0, startrow = 1)
    vmt_speed_bin.to_excel(excel_writer = writer, sheet_name = 'AirQuality', na_rep = 0, startrow =1)
    vmt_func_bin.to_excel(excel_writer = writer, sheet_name = 'Collisions', na_rep = 0, startrow =1)
    writer.close()

if __name__ == "__main__":
    main()