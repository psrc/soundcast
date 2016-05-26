import os
import sys
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(CURRENT_DIR))
import pandas as pd
import time
import h5py
import math
import itertools
import collections
import xlsxwriter
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
from emme_configuration import *
from h5toDF import *



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

def impedance_inc_mode(trips, max_income, impedance_type):
    imp_inc_mode = trips.query('hhincome < @max_income').groupby('mode')
    return imp_inc_mode[impedance_type].sum()

def calculate_park_costs(parcel_decay_file, trips, max_income):
    parcels = pd.read_table(parcel_decay_file, sep=' ')
    # only get the trips where the person is driving
    drive_trips =  trips.loc[(trips['dorp']=='Driver')].query('hhincome < @max_income')
    park_cost = pd.merge(parcels, drive_trips, left_on = 'parcelid', right_on= 'dpcl')
    park_cost_tot = PAID_UNPAID_PARK_RATIO*HRS_PARKED_AVG* park_cost['pprichr1'].sum()/CENTS_DOLLAR
    # need to delete variables to not run out of memory
    del park_cost
    del parcels
    return park_cost_tot

def auto_own_cost(output_df, max_income):
    hh_data = output_df['Household']['hhvehs'].loc[output_df['Household']['hhincome']<max_income]
    hh_data.loc[hh_data== 4] = FOUR_PLUS_CAR_AVG
    return hh_data.sum()*ANNUAL_OWNERSHIP_COST/ANNUALIZATION

def nonmotorized_benefits(trips, mode, max_income):
    nonmotorized_trips_dist=  trips.loc[(trips['mode']== mode) & (trips['hhincome']<max_income)]
    if mode != 'Transit':
        trips_people = nonmotorized_trips_dist.groupby(['hhno', 'pno_x']).agg({'travtime' :[np.sum]})
    else:
        trips_people = nonmotorized_trips_dist.groupby(['hhno', 'pno_x']).agg({'dorp' :[np.sum]})
    people_times = {'Time': trips_people.mean(), 'People': trips_people.count()}
    return  people_times


def mode_users(trips, max_income):
    mode_user_totals= {'Bike': 0, 'Walk': 0, 'HOV2': 0, 'HOV3+': 0, 'SOV': 0, 'School Bus': 0, 'Transit' : 0, 'Walk': 0}
    for key, value in mode_user_totals.iteritems():
        trips_mode =  trips.loc[(trips['mode'] == key) & (trips['hhincome']<max_income)]
        trips_people= len(trips_mode.groupby('id').count())
        mode_user_totals[key] =  trips_people
    return  pd.DataFrame(mode_user_totals, index = ['Users'])

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
            if link['auto_time']:
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


   

    # for testing:
    #h5_results_file = 'C:/soundcastrepo/outputs/daysim_outputs.h5'
    #guidefile= 'C:/soundcastrepo/scripts/summarize/CatVarDict.xlsx'
    #parcel_decay_file = 'C:/soundcastrepo/inputs/buffered_parcels.dat'
    ############# Calculate Impacts#######################################################################
    bc_outputs_by_mode = {}
    bc_costs = {}
    bc_health_outputs = {}
    mode_users_dict = {}
    lw_mode_users_dict = {}
    bc_people ={}

    ## Read in Dayim Outputs########
    trip_variables = ['otaz', 'dtaz', 'travtime', 'travcost', 'pno', 'mode', 'tour_id', 'opcl', 'dpcl', 'dorp']
    hh_variables = ['hhno', 'hhincome', 'hhvehs', 'hhtaz']
    person_variables = ['hhno', 'pno', 'pagey', 'pgend', 'id']
    outputs = convert(h5_results_file,guidefile, output_name)
    trips = get_variables_trips(outputs, trip_variables, hh_variables, person_variables)


    ##### TRAVEL TIME######################################3
    # Calculate Auto Travel Time Impacts

    # Time is calculated in PathTypeModel.cs
    # For Walking and Biking, time is just the walk or bike time
    # For Auto the time is just in-vehicle time var
    # For transit: path.Time = outboundInVehicleTime + initialWaitTime +
    # transferWaitTime + WalkTime
    print 'Counting People'
    bc_people['Total People'] = outputs['Person']['pno'].count()
    merge_hh_person = pd.merge(outputs['Person'][person_variables], outputs['Household'][hh_variables], 'inner', on = 'hhno')
    bc_people['Low Income People'] =  merge_hh_person.query('hhincome < @LOW_INC_MAX').count()['id']

    print "Calculating Auto Travel Time Impacts"

    bc_outputs_by_mode['Total Household Time Impedances'] = impedance_inc_mode(trips, MAX_INC,"travtime") / MINS_HR
    bc_outputs_by_mode[' Household Low-Income Time'] = impedance_inc_mode(trips, LOW_INC_MAX, "travtime") / MINS_HR



   # Also break this down for Work only

   # per Trips
 
    # Calculate Reliability Impacts
    # Reliability is already included in travel times in our vdfs - may want to
    # revisit

    #TRAVEL COST ################################################
    # Calculate Out-of-Pocket User Costs
    # in the field Travcost on the trip records
    # For Auto the travel cost is: the Toll cost in the skims + Auto Operatin?
    # For transit, the cost is the fare
    print "Calculating Out-of-Pocket and Ownership Costs"
    bc_outputs_by_mode['Total Household Costs'] = impedance_inc_mode(trips, MAX_INC, "travcost")
    bc_outputs_by_mode['Total Low Income Household Costs'] = impedance_inc_mode(trips, LOW_INC_MAX,"travcost")
    

    # Calculate Parking Cost
    ##Find this by joining the trips with the buffered parcel data and getting parking cost value
    # Reasonability check - In 2010, number of hourly parking spaces in the region = 90,000
    # Mean Cost per space per hour $8.22, Assume that occupied 10 hours per day -would be a cost of 7.4 million per day
    bc_costs['Parking Costs'] = calculate_park_costs(parcel_decay_file, trips, MAX_INC)
    bc_costs['Parking Costs Low Income'] = calculate_park_costs(parcel_decay_file, trips, LOW_INC_MAX)

    # Calculate Auto Ownership and Operating Costs
    # Auto Ownership Cost = Number of Autos Owned * Average Ownership Cost
    bc_costs['Auto Ownership Costs'] = auto_own_cost(outputs, MAX_INC)
    bc_costs['Auto Ownership Costs Low Income'] = auto_own_cost(outputs, LOW_INC_MAX)
    # Calculate Health Costs
    # For this we need average distance walked and biked per person
    # Total number of people walking and biking
    # http://www.heatwalkingcycling.org/
    # query out walkers and bikers

    # Currently the average time walked per walker is quite high.  We should fix
    # this. I think the problem is capturing the short walk trips and we should be able
    # to get this with the 2014 dataset.

    print bc_costs
    walk_times = nonmotorized_benefits(trips, 'Walk', MAX_INC)
    bike_times = nonmotorized_benefits(trips, 'Bike', MAX_INC)
    transit_walk_times = nonmotorized_benefits(trips, 'Transit', MAX_INC)

    bc_health_outputs['Average Time Walked per Walker or Person Walking to Transit'] = walk_times['Time'].values[0] + transit_walk_times['Time'].values[0]
    bc_health_outputs['Total Number of Walkers or People Walking to Transit'] = walk_times['People'].values[0] + transit_walk_times['People'].values[0]
    bc_health_outputs['Average Time Biked per Biker'] = bike_times['Time'].values[0]
    bc_health_outputs['Total Number of Bikers'] = bike_times['People'].values[0]

    walk_times_low_inc = nonmotorized_benefits(trips, 'Walk', LOW_INC_MAX)
    bike_times_low_inc = nonmotorized_benefits(trips, 'Bike', LOW_INC_MAX)
    transit_walk_times_low_inc = nonmotorized_benefits(trips, 'Transit', LOW_INC_MAX)

    bc_health_outputs['Average Time Walked per Low Income Walker or Person Walking to Transit'] = walk_times_low_inc['Time'].values[0] + transit_walk_times_low_inc['Time'].values[0]
    bc_health_outputs['Total Number of Low Income Walkers or People Walking to Transit'] = walk_times_low_inc['People'].values[0] + transit_walk_times_low_inc['People'].values[0]
    bc_health_outputs['Average Time Biked per Low Income Biker'] = bike_times_low_inc['Time'].values[0]
    bc_health_outputs['Total Number of Low INcome Bikers'] = bike_times_low_inc['People'].values[0]
    
    
    ### Get EMME project set up##############
    emme_project = EmmeProject(project)
    # Calculate link level benefits
    vmt_speed_dict = group_vmt_speed(emme_project)
    df_emissions = emissions_calc(vmt_speed_dict)
    noise_vmt = noise_calc(vmt_speed_dict)
    injury_rates_vmt = injury_calc(injury_file, emme_project)
   
    # measures to add annual vehicle hours of delay

    # Average Distance and Travel Time to Work from Home Location

    # Aggregate Logsum based Time measure

    # Optionally calculate Project Costs, operating and maintenance cost

    # Outputs and Visualization

  

    bc_writer = pd.ExcelWriter(bc_outputs_file, engine = 'xlsxwriter')
    START_ROW = 1

    pd.DataFrame(bc_people, index = [0]).to_excel(excel_writer = bc_writer, sheet_name =  'Raw Costs', na_rep = 0, startrow = START_ROW)
    START_ROW = START_ROW + REPORT_ROW_GAP


    pd.DataFrame(bc_outputs_by_mode).to_excel(excel_writer = bc_writer, sheet_name =  'Raw Costs', na_rep = 0, startrow = START_ROW)
    START_ROW = START_ROW + REPORT_ROW_GAP


    mode_users(trips, MAX_INC).to_excel(excel_writer = bc_writer, sheet_name =  'Raw Costs', na_rep = 0, startrow = START_ROW)
    START_ROW = START_ROW + REPORT_ROW_GAP

    mode_users(trips, LOW_INC_MAX).to_excel(excel_writer = bc_writer, sheet_name =  'Raw Costs', na_rep = 0, startrow = START_ROW)
    START_ROW = START_ROW + REPORT_ROW_GAP

    pd.DataFrame(bc_costs.items(), columns= ['Measure', 'Value']).sort_index(by=['Measure']).to_excel(excel_writer = bc_writer, sheet_name ='Raw Costs', na_rep = 0, startrow = START_ROW)
    START_ROW = START_ROW + REPORT_ROW_GAP

    pd.DataFrame(bc_health_outputs.items(), columns= ['Measure', 'Value']).sort_index(by=['Measure']).to_excel(excel_writer = bc_writer, sheet_name ='Raw Costs', na_rep = 0, startrow = START_ROW)
    START_ROW = START_ROW + REPORT_ROW_GAP

    df_emissions.to_excel(excel_writer = bc_writer, sheet_name = 'Raw Costs', na_rep = 0, startrow =START_ROW)
    START_ROW = START_ROW + REPORT_ROW_GAP

    noise_vmt.to_excel(excel_writer = bc_writer, sheet_name = 'Raw Costs', na_rep = 0, startrow =START_ROW)

    START_ROW = START_ROW + REPORT_ROW_GAP
    injury_rates_vmt.to_excel(excel_writer = bc_writer, sheet_name = 'Raw Costs', na_rep = 0, startrow =START_ROW)


    bc_writer.close()

if __name__ == "__main__":
        main()