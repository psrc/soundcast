import array as _array
import inro.emme.desktop.app as app
import inro.modeller as _m
import inro.emme.matrix as ematrix
import inro.emme.database.matrix
import inro.emme.database.emmebank as _eb
import json
import numpy as np
import pandas as pd
import time
import os,sys
import Tkinter, tkFileDialog
import multiprocessing as mp
import subprocess
from multiprocessing import Pool
import h5py
import collections
sys.path.append(os.path.join(os.getcwd(),"inputs"))

# Load trip rate inputs for households and attractors
hh_trip_loc = 'R:/SoundCast/Inputs/2010/supplemental/generation/rates/hh_triprates.in'
nonhh_trip_loc = 'R:/SoundCast/Inputs/2010/supplemental/generation/rates/nonhh_triprates.in'
puma_taz_loc = 'R:/SoundCast/Inputs/2010/supplemental/generation/ensembles/puma00.ens'
taz_data_loc = 'R:/SoundCast/Inputs/2010/supplemental/generation/landuse/tazdata.in'
pums_data_loc = 'R:/SoundCast/Inputs/2010/supplemental/generation/pums/' 
externals_loc = 'R:/SoundCast/Inputs/2010/supplemental/generation/externals.csv'
trip_table_loc = 'D:/soundcast/soundcat/outputs/prod_att.csv'

inc_size_workers_dict = {"inc1_size_workers" : {"start" : 14, "end" : 26,
                                                "hhs" : [], "share" : [], 
                                                "factored": [], "inc" : "inc1"},
                         "inc2_size_workers" : {"start" : 27, "end" : 39,
                                                "hhs" : [], "share" : [], 
                                                "factored": [], "inc" : "inc2"},
                         "inc3_size_workers" : {"start" : 40, "end" : 52,
                                                "hhs" : [], "share" : [], 
                                                "factored": [], "inc" : "inc3"},
                         "inc4_size_workers" : {"start" : 53, "end" : 65,
                                                "hhs" : [], "share" : [], 
                                                "factored": [], "inc" : "inc4"}}

inc_k12_dict = {"inc1_k12" : {"start" : 70, "end" : 73, 
                              "hhs" : [], "share" : [], 
                              "factored": [], "inc" : "inc1"},
                "inc2_k12" : {"start" : 74, "end" : 77, 
                              "hhs" : [], "share" : [], 
                              "factored": [], "inc" : "inc2"},
                "inc3_k12" : {"start" : 78, "end" : 81, 
                              "hhs" : [], "share" : [], 
                              "factored": [], "inc" : "inc3"},
                "inc4_k12" : {"start" : 82, "end" : 85, 
                              "hhs" : [], "share" : [], 
                              "factored": [], "inc" : "inc4"}}

inc_college_dict = {"inc1_college" : {"start" : 89, "end" : 91, 
                                      "hhs" : [], "share" : [], 
                                      "factored": [], "inc" : "inc1"},
                    "inc2_college" : {"start" : 92, "end" : 94, 
                                      "hhs" : [], "share" : [], 
                                      "factored": [], "inc" : "inc2"},
                    "inc3_college" : {"start" : 95, "end" : 97, 
                                      "hhs" : [], "share" : [], 
                                      "factored": [], "inc" : "inc3"},
                    "inc4_college" : {"start" : 98, "end" : 100, 
                                      "hhs" : [], "share" : [], 
                                      "factored": [], "inc" : "inc4"}}

inc_veh_dict = {"inc1_veh" : {"start" : 201, "end" : 264, 
                                      "hhs" : [], "share" : [], 
                                      "factored": [], "inc" : "inc1"},
                    "inc2_veh" : {"start" : 265, "end" : 328, 
                                      "hhs" : [], "share" : [], 
                                      "factored": [], "inc" : "inc2"},
                    "inc3_veh" : {"start" : 329, "end" : 392, 
                                      "hhs" : [], "share" : [], 
                                      "factored": [], "inc" : "inc3"},
                    "inc4_veh" : {"start" : 393, "end" : 456, 
                                      "hhs" : [], "share" : [], 
                                      "factored": [], "inc" : "inc4"}}

hhs_by_income = {"inc1" : { "column" : "102", "hhs" : []},
                 "inc2" : { "column" : "103", "hhs" : []},
                 "inc3" : { "column" : "104", "hhs" : []},
                 "inc4" : { "column" : "105", "hhs" : []}}

trip_col = ["hbwpro", "colpro", "hsppro", "hbopro",
            "schpro", "wkopro", "otopro", "empty1",
            "hbwatt", "colatt", "hspatt", "hboatt", 
            "schatt", "wkoatt", "otoatt", "empty2",
            "hbwpr1", "hbwpr2", "hbwpr3", "hbwpr4", 
            "hbwat1", "hbwat2", "hbwat3", "hbwat4"]

trip_purp_col = {"hbwpro": "hbwatt", "colpro": "colatt", "hsppro": "hspatt",
                 "hbopro": "hboatt", "schpro": "schatt", "wkopro": "wkoatt",
                  "otopro": "otoatt", "empty1": "empty2", "hbwpr1": "hbwat1", 
                  "hbwpr2": "hbwat2", "hbwpr3": "hbwat3", "hbwpr4": "hbwat4"}

def process_inputs(file_loc, start_row, col_names, clean_column, pivot_fields, reorder):
    ''' Load Emme-formated input files as cleaned dataframe '''
    df = pd.read_csv(file_loc, delim_whitespace=True, skiprows=start_row, names=col_names)
    df[clean_column] = [each.strip(":") for each in df[clean_column]]
    # Reformat input from 'long' to 'wide' format
    if pivot_fields:
        df = df.pivot(pivot_fields[0], pivot_fields[1])
    # Reorder dataframe rows in numerical order
    if reorder:
        df = pd.DataFrame(df, index = [str(i) for i in xrange(reorder[0], reorder[1] + 1)])
    return df

# Load household and attractors trip rates
rate_cols = ['hhtype', 'purpose', 'rate']
pivot_fields = ["purpose", "hhtype"]
hh_trip = process_inputs(hh_trip_loc, 7, rate_cols, "purpose", 
                         pivot_fields, reorder = [1,24])
nonhh_trip = process_inputs(nonhh_trip_loc, 7, rate_cols, "purpose", 
                            pivot_fields, reorder = [1,24])

# Create PUMS-TAZ lookup table
puma_taz = process_inputs(puma_taz_loc, 0, ['scrap', 'puma'], "puma",
                          pivot_fields=False, reorder=False)
puma_taz = pd.DataFrame(puma_taz["puma"])

# Correct PUMS formatting to match cross-class data (add extra '0' in field name)
for x in xrange(1,3701):
    puma_taz["puma"].loc[x] = puma_taz["puma"].loc[x].replace('gp', 'gp0')

# Import TAZ household and employment data
rate_cols = ["taz","purpose", "value"]
taz_data = process_inputs(taz_data_loc, 5, rate_cols, "purpose",
               pivot_fields=['taz', 'purpose'], reorder=False)
# Convert column names to string to join with PUMA data
taz_data.columns = [str(i) for i in xrange(101,125)]

# Join PUMA data to TAZ data
master_taz = taz_data.join(puma_taz)

#Load PUMS data
pums_list = ['pumshhxc_income-collegestudents.in',
             'pumshhxc_income-k12students.in',
             'pumshhxc_income-size-workers.in',
             'pumshhxc_income-size-workers-vehicles.in']

pums_df = pd.DataFrame()
list = []
pums_cols = ['puma', 'hhtype', 'num_hhs']

for file in pums_list:
    df = process_inputs(pums_data_loc + file, 6, pums_cols, 
                        'hhtype', pivot_fields=False, reorder=False)
    list.append(df)
pums_df = pd.concat(list)

# Pivot columns and re-order columns (outside of loop)
pums_df = pums_df.pivot('puma', 'hhtype')
pums_df = pums_df["num_hhs"][[str(i) for i in xrange(1,100+1)]+[str(i) for i in xrange(201,456+1)]]

# Join PUMS to TAZ data, using lookup column
master_taz = master_taz.join(pums_df,"puma")

# Create a new data frame for results
results_df = pd.DataFrame()

#Calculate total number of households per PUMA
for key, value in hhs_by_income.iteritems():
    value['hhs'] = pd.DataFrame(master_taz[value['column']])

for cross_class in [inc_size_workers_dict, inc_k12_dict, inc_college_dict, inc_veh_dict]:
    for key, value in cross_class.iteritems():
        result = master_taz[[str(i) for i in xrange(value['start'], value['end'] + 1)]]
        value['hhs'] = pd.DataFrame(result).sum(axis=1)
        taz_hh = pd.DataFrame(hhs_by_income[value['inc']]['hhs'])
        taz_hh.columns = ["col"]
        pums_hh = pd.DataFrame(value['hhs'],columns=["col"])
        share = pd.DataFrame(taz_hh/pums_hh)
        share.columns = ['col']
        for id in xrange(value['start'], value['end']+1):
            new_col = pd.DataFrame(master_taz[str(id)])
            new_col.columns = ['col']
            master_taz[str(id)] = share * new_col

# Create a dataframe that includes only the household cross-classes
hhs = master_taz[[str(i) for i in xrange(1, 101)]]
# Create a dataframe that includes only the employment cross-classes
nonhhs = taz_data[[str(i) for i in xrange(109, 125)]]

# Create an empty data frame to hold results
trips_by_purpose = pd.DataFrame(np.zeros([3700, 24]), 
                                columns = [str(i) for i in xrange(1, 24 + 1)])
nonhh_trips_by_purp = pd.DataFrame(np.zeros([3700,24]), 
                                columns = [str(i) for i in xrange(1, 24 + 1)])

# Compute household trip rates by TAZ and by purpose
for purpose in xrange(1, 24 + 1):
    trip_rate = pd.DataFrame(hh_trip['rate'].loc[str(purpose)])
    nh_trip_rate = pd.DataFrame(nonhh_trip.loc[str(purpose)])
    trip_rate.index = [str(i) for i in xrange(1, 100 + 1)]
    nh_trip_rate.index = [str(i) for i in xrange(109, 124 + 1)]
    trip_rate.columns = ['col']
    nh_trip_rate.columns = ['col']
    for zone in xrange(1,3700 + 1):
        hhs1 = pd.DataFrame(hhs.iloc[zone-1])
        nonhhs1 = pd.DataFrame(nonhhs.iloc[zone-1])
        hhs1.index = [str(i) for i in xrange(1, 100 + 1)]
        nonhhs1.index = [str(i) for i in xrange(109, 124 + 1)]
        hhs1.columns = ['col']
        nonhhs1.columns = ['col']
        # make sure to select only a single column, can't have more than one array selected per frame
        dot1 = trip_rate['col'].dot(hhs1['col'])
        dot2 = nh_trip_rate['col'].dot(nonhhs1['col'])
        trips_by_purpose[str(purpose)].loc[zone-1] = dot1
        nonhh_trips_by_purp[str(purpose)].loc[zone-1] = dot2
        trip_table = trips_by_purpose + nonhh_trips_by_purp
        #print "Trip purpose: " + str(purpose)
        #print "Zone number: " + str(zone)

# Rename columns
trip_table.columns = trip_col

# Add in special generators
# Note: This assumes 75% of airport trips are home-based and 25% are work-based trips
spg_airport = {983: 101838}
spg_general = {3110: 1682, 631: 7567, 438: 14013}
airport_hb_share = 0.75
airport_wb_share = 1 - airport_hb_share

# Add special generator home-based (spghbo) other and 75% of airport (spgapt) trips
# to general home-based attractions (hboatt)
for key, value in spg_general.iteritems():
    trip_table.iloc[key - 1]["hboatt"] += value

# Add 25% of airport trips to work-based attractions
trip_table.iloc[spg_airport.keys()[0] - 1]["hboatt"] += airport_hb_share * spg_airport.values()[0]
trip_table.iloc[spg_airport.keys()[0] - 1]["wkoatt"] += airport_wb_share * spg_airport.values()[0]

# Add (unbalanced) externals
externals = pd.DataFrame(pd.read_csv(externals_loc, index_col="taz"))
externals.columns = trip_col
trip_table = trip_table.append(externals)

# Balance Trips
bal_to_attractions = ["colpro"]
for key, value in trip_purp_col.iteritems():
    # Balance attractions to productions for most trip purposes
    if key not in bal_to_attractions:
        prod = trip_table[key].sum() ; att = trip_table[value].sum()
        ext = trip_table[value].iloc[3700:3749].sum()
        bal_factor = (prod - ext)/(att - ext)
        trip_table[value].loc[0:3699] *= bal_factor
        print "key " + key + ", " + value + ' ' + str(bal_factor)
    # Balance productions to attractions for college trips
    else:
        prod = trip_table[key].sum() ; att = trip_table[value].sum()
        ext = trip_table[key].iloc[3700:3749].sum()
        bal_factor = (att - ext)/(prod - ext)
        trip_table[key].loc[0:3699] *= bal_factor
        print "value " + value + ", " +key + ' ' + str(bal_factor)
   
# set zonal nhb work-other productions equal to zonal nhb work-other attractions
# set zonal nhb other-other productions equal to zonal nhb other-other attractions

trip_table = pd.DataFrame(trip_table,columns=["hbwpro", "colpro", "hsppro", "hbopro",
                "schpro", "wkoatt", "otoatt", "empty1",
                "hbwatt", "colatt", "hspatt", "hboatt", 
                "schatt", "wkoatt", "otoatt", "empty2",
                "hbwpr1", "hbwpr2", "hbwpr3", "hbwpr4", 
                "hbwat1", "hbwat2", "hbwat3", "hbwat4"])

# Add externals back in 
#trip_table = trip_table.append(externals)
trip_table.columns = trip_col

# Write results to CSV
trip_table.to_csv(trip_table_loc)