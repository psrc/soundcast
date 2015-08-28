import pandas as pd
import time
import h5py
import math
import itertools
import collections
import h5toDF
import xlsxwriter
import os, sys
import numpy as np
sys.path.append(os.path.join(os.getcwd(),"inputs"))
sys.path.append(os.path.join(os.getcwd(),"scripts"))
import input_configuration
import inro.emme.desktop.app as app
import inro.modeller as _m
from EmmeProject import *
import datetime
from benefit_cost_configuration import *
from input_configuration import *




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

def calculate_park_costs(parcel_decay_file, trips):
    parcels = pd.read_table(parcel_decay_file, sep=' ')
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

def nonmotorized_benefits(trips, mode):
    nonmotorized_trips_dist=  trips.loc[trips['mode']== mode]
    trips_people = nonmotorized_trips_dist.groupby(['hhno', 'pno_x']).agg({'travtime' :[np.sum]})
    people_times = {'Time': trips_people.mean(), 'People': trips_people.count()}
    return  people_times


def group_vmt_speed(my_project):
    speed_bins = [-10, 0, 10, 20, 30, 40, 50, 60, 70]
    speed_dict = {}
    max_speed  = 60

    for item in speed_bins:
        speed_dict[item] = {'Car' : 0, 'Light Truck' : 0,  'Medium Truck' : 0, 'Heavy Truck': 0}

    for key, value in sound_cast_net_dict.iteritems():

        print 'Getting VMT by Speed bin for time period ' + key
        
        my_project.change_active_database(key)
        network = my_project.current_scenario.get_network()

        for link in network.links():
            speed = link['length']* MINS_HR/link['auto_time']
            #speed = int(round(speed, -1))
            speed = int(speed - speed%10)
            if speed == 70:
                speed = max_speed
            
             
            if speed > 0 and speed <100:

               speed_dict[speed]['Car'] = speed_dict[speed]['Car'] + (link['@svtl1']+ link['@svtl2'] + link['@svtl3'] + link['@svnt1'] +  link['@svnt2'] + link['@svnt3'] + link['@h2tl1'] + link['@h2tl2'] +
               link['@h2tl3'] + link['@h2nt1'] + link['@h2nt2'] + link['@h2nt3'] + link['@h3tl1'] +
               link['@h3tl2'] + link['@h3tl3'] + link['@h3nt1'] + link['@h3nt2'] + link['@h3nt3'])*link['length']

               speed_dict[speed]['Light Truck'] = speed_dict[speed]['Light Truck'] + link['@lttrk'] * link['length']
               speed_dict[speed]['Medium Truck'] = speed_dict[speed]['Medium Truck'] + link['@mveh'] * link['length']/MED_TRUCK_FACTOR
               speed_dict[speed]['Heavy Truck'] = speed_dict[speed]['Heavy Truck'] + link['@hveh'] * link['length']/HV_TRUCK_FACTOR

                    
    return speed_dict

def group_vmt_class(my_project):
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

    vmt_fc_df = pd.DataFrame(vmt_func_class.items())
    vmt_fc_df.columns = ['Functional Class', 'VMT']
    return vmt_fc_df


def emissions_calc(vmt_speed_dict):
    pollutant_rates = pd.DataFrame.from_csv(pollutant_file)
    vehicle_type_tons = {'Car': {'Carbon Dioxide': 0, 'Carbon Monoxide': 0, 'Nitrogen Oxide':0 , 'Volatile Organic Compound': 0, 'Particulate Matter': 0},
                         'Light Truck':{'Carbon Dioxide': 0, 'Carbon Monoxide': 0, 'Nitrogen Oxide':0 , 'Volatile Organic Compound': 0, 'Particulate Matter': 0},
                         'Medium Truck': {'Carbon Dioxide': 0, 'Carbon Monoxide': 0, 'Nitrogen Oxide':0 , 'Volatile Organic Compound': 0, 'Particulate Matter': 0},
                         'Heavy Truck': {'Carbon Dioxide': 0, 'Carbon Monoxide': 0, 'Nitrogen Oxide':0 , 'Volatile Organic Compound': 0, 'Particulate Matter': 0}}

    for index, row in pollutant_rates.iterrows():
        vehicle_type_tons['Car'][row.name] += vmt_speed_dict[row['Speed Class']]['Car'] * row['Car']
        vehicle_type_tons['Light Truck'][row.name] += vmt_speed_dict[row['Speed Class']]['Light Truck'] * row['Light Truck']
        vehicle_type_tons['Medium Truck'][row.name] += vmt_speed_dict[row['Speed Class']]['Medium Truck'] * row['Medium Truck']
        vehicle_type_tons['Heavy Truck'][row.name]  += vmt_speed_dict[row['Speed Class']]['Heavy Truck'] * row['Heavy Truck']

    df_veh_type_tons = pd.DataFrame(vehicle_type_tons)
    df_veh_type_tons = df_veh_type_tons/1000000
    df_veh_type_dollars = pd.DataFrame([df_veh_type_tons.loc['Carbon Dioxide']*CO2_COST, df_veh_type_tons.loc['Carbon Monoxide']*CO_COST,
                           df_veh_type_tons.loc['Nitrogen Oxide']*NO_COST,df_veh_type_tons.loc['Volatile Organic Compound']*VOC_COST,
                           df_veh_type_tons.loc['Particulate Matter']*PM_COST])
    df_emissions = pd.concat([df_veh_type_tons, df_veh_type_dollars])
    return df_emissions


def noise_calc(vmt_speed_dict):
    noise_vmt = {'Car VMT': 0, 'Truck VMT' : 0}
    for speed, vmt in vmt_speed_dict.iteritems():
        noise_vmt['Car VMT'] += vmt['Car']
        noise_vmt['Truck VMT'] += vmt['Light Truck']+ vmt['Medium Truck']+ vmt['Heavy Truck']
    
    return pd.DataFrame(noise_vmt, index = [0])

def injury_calc(injury_file, my_project):
    # For collisions, we assume a rate of collisions per VMT by facility type.
    # To do: We should also include PMT by walking and biking
    injury_rates = pd.DataFrame.from_csv(injury_file)
    vmt_func_class = group_vmt_class(my_project)

    injury_rates_vmt = pd.merge(injury_rates, vmt_func_class, on = 'Functional Class')
    injury_rates_vmt['Property Damage Total'] = injury_rates_vmt['Property Damage Rate']*injury_rates_vmt['VMT']/SAFETY_FACTOR
    injury_rates_vmt['Injury Total'] = injury_rates_vmt['Injury Rate']*injury_rates_vmt['VMT']/SAFETY_FACTOR
    injury_rates_vmt['Fatality Total'] = injury_rates_vmt['Fatality Rate']*injury_rates_vmt['VMT']/SAFETY_FACTOR
    injury_rates_vmt['Property Damage Cost'] = injury_rates_vmt['Property Damage Total']* PROPERTYD_COST
    injury_rates_vmt['Injury Cost'] = injury_rates_vmt['Injury Rate']*injury_rates_vmt['VMT']*INJURY_COST
    injury_rates_vmt['Fatality Cost'] = injury_rates_vmt['Fatality Rate']*injury_rates_vmt['VMT']*FATALITY_COST
    return injury_rates_vmt


def main():
    bc_assumptions = {}

    # Write out the assumptions
    bc_assumptions['Household Value of Time'] = HOUSEHOLD_VOT
    bc_assumptions['Truck Value of Time'] = TRUCK_VOT
    bc_assumptions[' Household File Location'] = h5_results_file


    ############# Calculate Impacts#######################################################################
    bc_outputs = {}
    bc_time_outputs = {}
    bc_low_inc_outputs = {}
    bc_health_outputs = {}

    ## Read in Dayim Outputs########
    trip_variables = ['otaz', 'dtaz', 'travtime', 'travcost', 'pno', 'mode', 'tour_id', 'opcl', 'dpcl', 'dorp']
    hh_variables = ['hhno', 'hhincome', 'hhvehs', 'hhtaz']
    person_variables = ['hhno', 'pno', 'pagey', 'pgend']

    outputs = h5toDF.convert(h5_results_file,guidefile, output_name)
    trips = get_variables_trips(outputs, trip_variables, hh_variables, person_variables)


    ##### TRAVEL TIME######################################3
    # Calculate Auto Travel Time Impacts
    # To Do - Calculate for different groups of people - young and old, more income
    # groups
    # Calculate by home origin
    # Should we include walking and biking costs?

    # Time is calculated in PathTypeModel.cs
    # For Walking and Biking, time is just the walk or bike time
    # For Auto the time is just in-vehicle time var
    # For transit: path.Time = outboundInVehicleTime + initialWaitTime +
    # transferWaitTime + WalkTime
    print "Calculating Auto Travel Time Impacts"

    bc_time_outputs['Total Auto Household Time'] = impedance_inc_mode(trips, MAX_INC, "auto", "travtime") / MINS_HR
    bc_time_outputs[' Auto Low Income Household Time'] = impedance_inc_mode(trips, LOW_INC_MAX, "auto", "travtime") / MINS_HR
    #bc_outputs['Truck Time'] = calculate_truck_time(truck_file)
    bc_outputs['Total Auto Household Time Cost'] = bc_time_outputs['Total Auto Household Time'] * HOUSEHOLD_VOT


    #bc_outputs['Total Value of Auto Time'] = HOUSEHOLD_VOT*bc_outputs['Base
    #Total Auto Household Time'] + TRUCK_VOT*bc_outputs['Truck Time']

    # Calculate Transit Travel Time Impacts
    print "Calculating Transit Travel Time Impacts"
    bc_time_outputs['Total Household Transit Time'] = impedance_inc_mode(trips, MAX_INC,"transit", "travtime") / MINS_HR
    bc_time_outputs['Low Income Household Transit Time'] = impedance_inc_mode(trips, LOW_INC_MAX, "transit", "travtime") / MINS_HR
    bc_outputs['Total Transit Household Time Cost'] = bc_time_outputs['Total Household Transit Time'] * HOUSEHOLD_VOT
   

    # Calculate Reliability Impacts
    # Reliability is already included in travel times in our vdfs - may want to
    # revisit

    #TRAVEL COST ################################################
    # Calculate Out-of-Pocket User Costs
    # in the field Travcost on the trip records
    # For Auto the travel cost is: the Toll cost in the skims + Auto Operatin?
    # For transit, the cost is the fare
    print "Calculating Out-of-Pocket and Ownership Costs"
    bc_outputs['Total Auto Household Toll and Auto Operating Cost'] = impedance_inc_mode(trips, MAX_INC, "auto", "travcost")
    bc_low_inc_outputs['Low Income Household Tolls  and Auto Operating Cost'] = impedance_inc_mode(trips, LOW_INC_MAX, "auto", "travcost")
    
    bc_outputs['Total Transit Fares'] = impedance_inc_mode(trips, MAX_INC, "transit", "travcost")
    bc_low_inc_outputs['Low Income Transit Fares'] = impedance_inc_mode(trips, MAX_INC, "transit", "travcost")
   
    # Calculate Parking Cost
    ##Find this by joining the trips with the buffered parcel data and getting parking cost value
    # Reasonability check - In 2010, number of hourly parking spaces in the region = 90,000
    # Mean Cost per space per hour $8.22, Assume that occupied 10 hours per day -would be a cost of 7.4 million per day
    bc_outputs['Parking Costs'] = calculate_park_costs(parcel_decay_file, trips)

    # Calculate Auto Ownership and Operating Costs
    # Auto Ownership Cost = Number of Autos Owned * Average Ownership Cost
    bc_outputs['Auto Ownership Costs'] = auto_own_cost(outputs)
  
    # Calculate Health Costs
    # For this we need average distance walked and biked per person
    # Total number of people walking and biking
    # http://www.heatwalkingcycling.org/
    # query out walkers and bikers

    # Currently the average time walked per walker is quite high.  We should fix
    # this. I think the problem is capturing the short walk trips and we should be able
    # to get this with the 2014 dataset.
    walk_times = nonmotorized_benefits(trips, 'Walk')
    bike_times = nonmotorized_benefits(trips, 'Bike')
    bc_health_outputs['Average Time Walked per Walker'] = walk_times['Time'].values[0]
    bc_health_outputs['Total Number of Walkers'] = walk_times['People'].values[0]
    bc_health_outputs['Average Time Biked per Biker'] = bike_times['Time'].values[0]
    bc_health_outputs['Total Number of Bikers'] = bike_times['People'].values[0]
    
    
    ### Get EMME project set up##############
    emme_project = EmmeProject(project)
    # Calculate link level benefits
    vmt_speed_dict = group_vmt_speed(emme_project)
    df_emissions = emissions_calc(vmt_speed_dict)
    noise_vmt = noise_calc(vmt_speed_dict)
    injury_rates_vmt = injury_calc(injury_file, emme_project)
   

    # Aggregate Logsum based Time measure

    # Optionally calculate Project Costs, operating and maintenance cost

    # Outputs and Visualization

    bc_writer = pd.ExcelWriter(bc_outputs_file, engine = 'xlsxwriter')
    START_ROW = 1
    pd.DataFrame(bc_outputs.items(), columns= ['Cost', 'Value']).sort_index(by=['Cost']).to_excel(excel_writer = bc_writer, sheet_name =  'Raw Costs', na_rep = 0, startrow = START_ROW)
    START_ROW = START_ROW + REPORT_ROW_GAP
    pd.DataFrame(bc_time_outputs.items(), columns= ['Time', 'Value']).sort_index(by=['Time']).to_excel(excel_writer = bc_writer, sheet_name = 'Raw Costs', na_rep = 0, startrow = START_ROW)
    START_ROW = START_ROW + REPORT_ROW_GAP
    pd.DataFrame(bc_health_outputs.items(), columns= ['Measure', 'Value']).sort_index(by=['Measure']).to_excel(excel_writer = bc_writer, sheet_name ='Raw Costs', na_rep = 0, startrow = START_ROW)
    START_ROW = START_ROW + REPORT_ROW_GAP
    pd.DataFrame(bc_assumptions.items(), columns= ['Assumption', 'Value']).sort_index(by=['Assumption']).to_excel(excel_writer = bc_writer, sheet_name ='Raw Costs', na_rep = 0, startrow = START_ROW)
    START_ROW = START_ROW + REPORT_ROW_GAP
    df_emissions.to_excel(excel_writer = bc_writer, sheet_name = 'Raw Costs', na_rep = 0, startrow =START_ROW)
    START_ROW = START_ROW + REPORT_ROW_GAP
    noise_vmt.to_excel(excel_writer = bc_writer, sheet_name = 'Raw Costs', na_rep = 0, startrow =START_ROW)
    START_ROW = START_ROW + REPORT_ROW_GAP
    injury_rates_vmt.to_excel(excel_writer = bc_writer, sheet_name = 'Raw Costs', na_rep = 0, startrow =START_ROW)
    
    bc_writer.close()

if __name__ == "__main__":
        main()