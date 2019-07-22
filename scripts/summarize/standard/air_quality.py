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

import os
import sys
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
#CURRENT_DIR = r'D:\stefan\soundcast_2014_aq'
sys.path.append(os.path.dirname(CURRENT_DIR))
import array as _array
import inro.emme.desktop.app as app
import inro.modeller as _m
import inro.emme.matrix as ematrix
import inro.emme.database.matrix
import inro.emme.database.emmebank as _eb
import json
import numpy as np
import time
import h5py
import Tkinter, tkFileDialog
import multiprocessing as mp
import subprocess
import csv
import xlsxwriter
#import xlautofit
import sqlite3 as lite
from datetime import datetime
import os
sys.path.append(CURRENT_DIR)
sys.path.append(os.path.join(os.getcwd(),"inputs"))
sys.path.append(os.path.join(os.getcwd(),"scripts"))
from EmmeProject import *
from multiprocessing import Pool
import pandas as pd
import collections
from standard_summary_configuration import *
from input_configuration import *
from emme_configuration import *
#os.chdir(r'D:\stefan\soundcast_2014_aq')


#Intrazonals
#Need to get intrazonal distances
my_project = EmmeProject(project)
my_project.change_active_database('7to8')
np_iz_dist = my_project.bank.matrix('izdist').get_numpy_data().diagonal()


writer = pd.ExcelWriter('outputs/aq_' + model_year + '.xlsx', engine='xlsxwriter')

county_flag_df = pd.read_csv('scripts/summarize/inputs/network_summary/county_flags_' + model_year + '.csv', dtype = {'inode' : str, 'jnode' : str })
county_flag_df['ij'] = county_flag_df.inode + '-' + county_flag_df.jnode
county_taz_df = pd.read_csv('scripts/summarize/inputs/county_taz.csv')

emission_rates_df = pd.read_csv(r'scripts\summarize\inputs\network_summary\emission_rates_' + str(model_year) + '.csv')


zones = my_project.current_scenario.zone_numbers
dictZoneLookup = dict((index,value) for index,value in enumerate(zones))

tod_lookup = {'5to6' : 5, '6to7' : 6, '7to8' : 7, '8to9' : 8, '9to10' : 9, '10to14' : 10, 
                     '14to15' : 14, '15to16' : 15, '16to17' : 16, '17to18' : 17, '18to20' : 18, '20to5' : 20}

speed_bins = [-999999, 2.5, 7.5, 12.5, 17.5, 22.5, 27.5, 32.5, 37.5, 42.5, 47.5, 52.5, 57.5, 62.5, 67.5, 72.5, 999999] 
speed_bins_labels =  range(1, len(speed_bins))

fac_type_lookup = {1:4, 2:4, 3:5, 4:5, 5:5, 6:3, 7:5, 8:0}

months_recode = {0:1, 1:7}

pollutant_type_list = [1,2,3,5,6,79,87,90,91,98,100,106,107,110,112,115,116,117,118,119]
pollutant_type_lookup = dict(zip(range(0, len(pollutant_type_list)), pollutant_type_list))



def get_intrazonal_vol(emme_project, trip_table_name):
    vot_list = [1,2,3]
    matrix_dict = {}
    np_iz_volume = emme_project.bank.matrix(trip_table_name + '1').get_numpy_data() + emme_project.bank.matrix(trip_table_name + '2').get_numpy_data() + emme_project.bank.matrix(trip_table_name + '3').get_numpy_data()
    return np_iz_volume.diagonal()


df_dict = {}
for key, value in sound_cast_net_dict.iteritems():
    my_project.change_active_database(key)
    #Intrazonal volume and vmt:
    taz_index = np.asarray(dictZoneLookup.values())
    sov_iz_vol = get_intrazonal_vol(my_project, 'svtl')
    sov_iz_vmt = sov_iz_vol * np_iz_dist
    hov2_iz_vol = get_intrazonal_vol(my_project, 'h2tl')
    hov2_iz_vmt = hov2_iz_vol * np_iz_dist
    hov3_iz_vol = get_intrazonal_vol(my_project, 'h3tl')
    hov3_iz_vmt = hov3_iz_vol * np_iz_dist
    med_truck_vol = my_project.bank.matrix('metrk').get_numpy_data().diagonal()
    med_truck_vmt = med_truck_vol* np_iz_dist
    hvy_truck_vol = my_project.bank.matrix('hvtrk').get_numpy_data().diagonal()
    hvy_truck_vmt = hvy_truck_vol * np_iz_dist

    data = collections.OrderedDict()
    data['taz']=taz_index
    data['sov_iz_vol'] = sov_iz_vol
    data['sov_iz_vmt'] = sov_iz_vmt
    data['hov2_iz_vol'] = hov2_iz_vol
    data['hov2_iz_vmt'] = hov2_iz_vmt
    data['hov3_iz_vol'] = hov3_iz_vol
    data['hov3_iz_vmt'] = hov3_iz_vmt
    data['med_truck_vol'] = med_truck_vol
    data['med_truck_iz_vmt'] = med_truck_vmt
    data['hvy_truck_iz_vol'] = hvy_truck_vol
    data['hvy_truck_iz_vmt'] = hvy_truck_vmt

    iz_df = pd.DataFrame(data)
    merged = county_taz_df.merge(iz_df, left_on = 'taz', right_on = 'taz', how = 'left')
    sum_counties_df = pd.DataFrame(merged.groupby('geog_name').sum())
    sum_counties_df.drop(['taz', 'lat_1', 'lon_1'], axis=1, inplace=True)

    # write out intrazonal data 
    sum_counties_df.to_excel(excel_writer=writer, sheet_name=my_project.tod + '_intrazonal')
    
    # now get each link, for each time period
    network = my_project.current_scenario.get_network()
    records = []
    for link in network.links():
        if link.data3 <> 0:
            sov = link['@svtl1'] + link['@svtl2'] + link['@svtl3']
            hov2 = link['@h2tl1'] + link['@h2tl2'] + link['@h2tl3']
            hov3 = link['@h3tl1'] + link['@h3tl2'] + link['@h3tl3']
            sov_vmt = sov * link.length
            hov2_vmt = hov2 * link.length
            hov3_vmt = hov3 * link.length
            if my_project.tod in transit_tod.keys():
                bus_vol = link['@bveh']
                bus_vmt = link['@bveh'] * link.length
            else:
                bus_vol = 0
                bus_vmt = 0

            med_truck_vmt = link['@mveh'] * link.length
            hev_truck_vmt = link['@hveh'] * link.length
            row = collections.OrderedDict()
            row['inode'] = link.i_node.id
            row['jnode'] = link.j_node.id
            row['ij'] = link.i_node.id + '-' + link.j_node.id
            row['length'] = link.length
            row['posted_speed'] = link.data2
            row['congested_speed'] = (link.length/link.auto_time) * 60
            row['facility_type'] = link.data3
            row['total_volume'] = link['@tveh']
            row['sov_vol'] = sov
            row['hov2_vol'] = hov2
            row['hov3_vol'] = hov3
            row['bus_vol'] = bus_vol
            row['med_truck_vol'] = link['@mveh']
            row['hev_truck_vol'] = link['@hveh']
            row['sov_vmt'] = sov_vmt
            row['hov2_vmt'] = hov2_vmt
            row['hov3_vmt'] = hov3_vmt
            row['bus_vmt'] = bus_vmt
            row['med_truck_vmt'] = med_truck_vmt
            row['hev_truck_vmt'] = hev_truck_vmt

            records.append(row)

    df = pd.DataFrame(records, columns = row.keys())
    df = df.merge(county_flag_df, how = 'left', on = 'ij')
    df['countyId'] = df.flag 
    df.drop(['inode_y', 'jnode_y'], axis=1, inplace=True)
    df['sound_cast_tod'] = key
    df['hourId'] = tod_lookup[key]
    df_dict[key] = df

# merge all the link data into one table
df = pd.concat(df_dict.values(), axis = 0, ignore_index=True)


#******Now create attributes to join emissions data******

# get model year
df['yearid'] = model_year

# recode speed into moves bins
df['avgspeedbinId'] = pd.cut(df['congested_speed'], speed_bins, labels=speed_bins_labels)
df['roadtypeId'] = df["facility_type"].map(fac_type_lookup)

# print(out min and max values for each speed bin to show if recode is working correctly
print(df.groupby(df.avgspeedbinId)['congested_speed'].min())
print(df.groupby(df.avgspeedbinId)['congested_speed'].max())

# replicate each row for each month (1 & 7)
df = pd.concat([df]*2)
df['monthId']= df.groupby(['ij', 'hourId']).cumcount()
df['monthId'] = df['monthId'].map(months_recode)

# replicate each link (row) for each pollutant type
# dont want to overwrite df here since we need it later
df1 = pd.concat([df]*len(pollutant_type_list))
df1['pollutantId']= df1.groupby(['ij', 'monthId',  'hourId']).cumcount()
df1['pollutantId'] = df1['pollutantId'].map(pollutant_type_lookup)

# sort the df
df1.sort_values(['ij', 'monthId',  'hourId'], inplace=True)

# merge with emission rates table
df1 = df1.merge(emission_rates_df, how = 'left', on = ['countyId','monthId', 'hourId', 'pollutantId', 'roadtypeId', 'avgspeedbinId'])
df1 = df1[['ij', 'monthId',  'hourId', 'pollutantId', 'gramsPerMile']]
df1.reset_index(level = None, inplace=True)

# pivot the table so that emission factors are columns
p = df1.pivot_table(index =['ij', 'monthId',  'hourId'], columns='pollutantId', values='gramsPerMile') 
p = p.rename_axis(None, axis = 1)
p.reset_index(inplace = True)

# join back to df
df = df.merge(p, how='left', on = ['ij', 'monthId',  'hourId'])

# seperate by month
df_jan = df[(df.monthId==1)]
df_july = df[(df.monthId==7)]

# wrute out to disk
df_jan.to_csv('outputs/aq_' + model_year + '_jan.csv')
df_july.to_csv('outputs/aq_' + model_year + '_july.csv')





