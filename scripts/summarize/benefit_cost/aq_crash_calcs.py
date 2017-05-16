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
from aq_crash_configuration import *
from input_configuration import *
from emme_configuration import *
from h5toDF import *


def group_vmt_speed(my_project):
    speed_bins = [-10, 0, 10, 20, 30, 40, 50, 60, 70]
    speed_dict = {}
    max_speed  = 60

    for item in speed_bins:
        speed_dict[item] = {'Car' : 0, 'Light Truck' : 0,  'Medium Truck' : 0, 'Heavy Truck': 0}

    for key, value in sound_cast_net_dict.iteritems():

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

               speed_dict[speed]['Car'] = speed_dict[speed]['Car'] + (link['@svtl1']+ link['@svtl2'] + link['@svtl3'] + + link['@h2tl1'] + link['@h2tl2'] +
               link['@h2tl3'] + link['@h3tl1'] +link['@h3tl2'] + link['@h3tl3'] )*link['length']

               speed_dict[speed]['Light Truck'] = speed_dict[speed]['Light Truck'] + link['@lttrk'] * link['length']
               speed_dict[speed]['Medium Truck'] = speed_dict[speed]['Medium Truck'] + link['@mveh'] * link['length']
               speed_dict[speed]['Heavy Truck'] = speed_dict[speed]['Heavy Truck'] + link['@hveh'] * link['length']

                    
    return speed_dict

def group_vmt_class(my_project):
    network = my_project.current_scenario.get_network()

    # store vmt by functional class 1= Freeway, 3= Expressway, etc
    vmt_func_class= {1 : 0, 3 : 0,  5 : 0, 7 : 0}
    
    for key, value in sound_cast_net_dict.iteritems():
        my_project.change_active_database(key)
        network = my_project.current_scenario.get_network()

        for link in network.links():
            # Only bigger facility types are included
            if link['volume_delay_func'] in vmt_func_class.keys():
                vmt_func_class[link['volume_delay_func']]+=link['auto_volume']*link['length']

    vmt_fc_df = pd.DataFrame(vmt_func_class.items())
    vmt_fc_df.columns = ['Functional Class', 'VMT']
    return vmt_fc_df


def emissions_calc(vmt_speed_dict, model_year):
    if model_year == 2040:
       pollutant_rates = pd.DataFrame.from_csv(pollutant_file_2040)
    else:
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



def write_results(bc_writer, start_row, REPORT_ROW_GAP, output_dfs):
    for df in output_dfs:
        df.to_excel(excel_writer = bc_writer, sheet_name =  'Raw Costs', na_rep = 0, startrow = start_row)
        start_row = start_row + REPORT_ROW_GAP


def main():


    
    
    ### Get EMME project set up##############
    emme_project = EmmeProject(project)
    # Calculate link level benefits
    vmt_speed_dict = group_vmt_speed(emme_project)
    df_emissions = emissions_calc(vmt_speed_dict, model_year)
    noise_vmt = noise_calc(vmt_speed_dict)
    injury_rates_vmt = injury_calc(injury_file, emme_project)

    # Write it out
    output_dfs = [df_emissions, noise_vmt, injury_rates_vmt]

    bc_writer = pd.ExcelWriter(bc_outputs_file, engine = 'xlsxwriter')
    start_row = 1
    write_results(bc_writer, start_row, REPORT_ROW_GAP, output_dfs)
    bc_writer.close()

if __name__ == "__main__":
        main()