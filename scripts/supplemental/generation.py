import json
import numpy as np
import pandas as pd
import os,sys
import h5py
sys.path.append(os.path.join(os.getcwd(),"scripts"))
sys.path.append(os.path.join(os.getcwd(),"scripts/trucks"))
from emme_configuration import *
from EmmeProject import *
from truck_configuration import *

# Global variable to hold taz id/index; populated in main
dictZoneLookup = {}

# Initialize working dictionaries
hhs_by_income = {"inc1" : { "column" : "102", "hhs" : []},
                 "inc2" : { "column" : "103", "hhs" : []},
                 "inc3" : { "column" : "104", "hhs" : []},
                 "inc4" : { "column" : "105", "hhs" : []}}

# Trip purposes for column names
trip_col = ["hbwpro", "colpro", "hsppro", "hbopro", "schpro", "wkopro", "otopro", "empty1",
            "hbwatt", "colatt", "hspatt", "hboatt", "schatt", "wkoatt", "otoatt", "empty2",
            "hw1pro", "hw2pro", "hw3pro", "hw4pro", "hw1att", "hw2att", "hw3att", "hw4att"]

trip_purp_col = {"hbwpro": "hbwatt", "colpro": "colatt", "hsppro": "hspatt",
                 "hbopro": "hboatt", "schpro": "schatt", "wkopro": "wkoatt",
                 "otopro": "otoatt", "empty1": "empty2", "hw1pro": "hw1att", 
                 "hw2pro": "hw2att", "hw3pro": "hw3att", "hw4pro": "hw4att"}

# Order column titles so otopro and wkopro columns are filled with otoatt and wkoatt data
column_set = ["hbwpro", "colpro", "hsppro", "hbopro",
                "schpro", "wkoatt", "otoatt", "empty1",
                "hbwatt", "colatt", "hspatt", "hboatt", 
                "schatt", "wkoatt", "otoatt", "empty2",
                "hw1pro", "hw2pro", "hw3pro", "hw4pro", 
                "hw1att", "hw2att", "hw3att", "hw4att"]

rate_cols = ['hhtype', 'purpose', 'rate']
pivot_fields = ["purpose", "hhtype"]

pums_list = ['pumshhxc_income-collegestudents.in',
             'pumshhxc_income-k12students.in',
             'pumshhxc_income-size-workers.in',
             'pumshhxc_income-size-workers-vehicles.in']

bal_to_attractions = ["colpro"]

# Input locations
hh_trip_loc = 'inputs/supplemental/generation/rates/hh_triprates.in'
nonhh_trip_loc = 'inputs/supplemental/generation/rates/nonhh_triprates.in'
puma_taz_loc = 'inputs/supplemental/generation/ensembles/puma00.ens'
taz_data_loc = 'inputs/supplemental/generation/landuse/tazdata.in'
pums_data_loc = 'inputs/supplemental/generation/pums/' 
externals_loc = 'inputs/supplemental/generation/externals.csv'

# Number of header lines for input files (keep these standard for all scenarios)
tazdata_header_len = 5      
pums_header_len = 6

# Define column values for household and employment data
hh_cols = [1, 101]    # Begin and end column numbers for all household-related cross classification data in HHEMP
emp_cols = [109, 125]    # Begin and end columns for all employement-related cross class data in HHEMP

# Trip purpose columns
purp_cols = [1, 24] # Begin and end column numbers for 12 trip purposes (including productions and attractions)

def json_to_dictionary(dict_name):
    ''' loads JSON input as dictionary '''
    input_filename = os.path.join('inputs/supplemental/',dict_name+'.json').replace("\\","/")
    my_dictionary = json.load(open(input_filename))
    return(my_dictionary)

def network_importer(EmmeProject):
    for scenario in list(EmmeProject.bank.scenarios()):
            EmmeProject.bank.delete_scenario(scenario)
        #create scenario
    EmmeProject.bank.create_scenario(1002)
    EmmeProject.change_scenario()
        #print key
    EmmeProject.delete_links()
    EmmeProject.delete_nodes()
    EmmeProject.process_modes('inputs/networks/' + mode_file)
    EmmeProject.process_base_network('inputs/networks/' + truck_base_net_name)

def init_dir(filename):
    try:
        os.remove(filename)
    except OSError:
        pass

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

def puma_taz_lookup(puma_taz):
    ''' Create PUMS-TAZ lookup table '''
    # Correct PUMS formatting to match cross-class data (add extra '0' in field name)
    for x in xrange(1,3701):
        puma_taz["puma"].loc[x] = puma_taz["puma"].loc[x].replace('gp', 'gp0')

    # Import TAZ household and employment data
    rate_cols = ["taz","purpose", "value"]
    taz_data = process_inputs(taz_data_loc, start_row=tazdata_header_len, col_names=rate_cols, 
                              clean_column="purpose", pivot_fields=['taz', 'purpose'], 
                              reorder=False)
    # Convert column names to string to join with PUMA data
    taz_data.columns = [str(i) for i in xrange(101,125)]

    return taz_data

def load_pums():
    ''' Loads demographic PUMS data to dataframe '''
    pums_df = pd.DataFrame()
    list = []
    pums_cols = ['puma', 'hhtype', 'num_hhs']

    for file in pums_list:
        df = process_inputs(pums_data_loc + file, start_row=pums_header_len, col_names=pums_cols, 
                            clean_column='hhtype', pivot_fields=False, reorder=False)
        list.append(df)
    pums_df = pd.concat(list)

    # Pivot columns and re-order columns (outside of loop)
    pums_df = pums_df.pivot('puma', 'hhtype')
    pums_df = pums_df["num_hhs"][[str(i) for i in xrange(1,100+1)]+[str(i) for i in xrange(201,456+1)]]

    return pums_df

def calc_hhs(master_taz):
    ''' Calculates total number of households per PUMA '''
    for key, value in hhs_by_income.iteritems():
        value['hhs'] = pd.DataFrame(master_taz[value['column']])

    # Create a new data frame for results
    results_df = pd.DataFrame()

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

    return master_taz

def add_special_gen(trip_table):
    ''' Loads additional productions and attraction values for special generator zones. '''

    df = pd.read_csv(special_gen_trips)

    # Note: Airport trips are assumed 75% home-based and 25% work-based
    airport_hb_share = 0.75
    airport_wb_share = 1 - airport_hb_share

    # Add special generator home-based (spghbo) other and 75% of airport (spgapt) trips
    # to general home-based attractions (hboatt)
    for i in xrange(len(df)):
        taz = df.iloc[i]['taz']
        trips = df.iloc[i]['trips']
        if i not in airport_zone_list:
            trip_table.iloc[dictZoneLookup[taz]]["hboatt"] += trips
        else:
            # Add 25% of airport trips to work-based attractions
            trip_table.iloc[dictZoneLookup[taz]]["hboatt"] += airport_hb_share * trips
            trip_table.iloc[dictZoneLookup[taz]]["wkoatt"] += airport_wb_share * trips
 
    # Add (unbalanced) externals
    externals = pd.DataFrame(pd.read_csv(externals_loc, index_col="taz"))
    externals.columns = trip_col
    trip_table = trip_table.append(externals)

    return trip_table

# Balance Trips
def balance_trips(trip_table, bal_to_attractions, include_ext):
    for key, value in trip_purp_col.iteritems():
        
        print key

        # don't balance placeholder columns; avoid divide-by-zero error
        # hbwpro isn't used
        if key not in ['hbwpro', 'empty1']:

            # Balance attractions to productions for most trip purposes
            if key not in bal_to_attractions:
                prod = trip_table[key].sum() ; att = trip_table[value].sum()
                if include_ext:
                    #ext = trip_table[value].iloc[HIGH_TAZ:MAX_EXTERNAL-1].sum()
                    ext = trip_table[value].iloc[dictZoneLookup[MIN_EXTERNAL]:dictZoneLookup[MAX_EXTERNAL]].sum()
                    dictZoneLookup
                else:
                    ext = 0
                #ext = trip_table[value].iloc[HIGH_TAZ:MAX_EXTERNAL-1].sum()
                #ext = trip_table[value].iloc[dictZoneLookup[MIN_EXTERNAL]:dictZoneLookup[MAX_EXTERNAL]].sum()
                bal_factor = (prod - ext)/(att - ext)
                #trip_table[value].loc[0:HIGH_TAZ-1] *= bal_factor
                trip_table[value].loc[1:HIGH_TAZ] *= bal_factor
                print "key " + key + ", " + value + ' ' + str(bal_factor)
            # Balance productions to attractions for college trips
            else:
                prod = trip_table[key].sum() ; att = trip_table[value].sum()
                if include_ext:
                    #ext = trip_table[key].iloc[HIGH_TAZ:MAX_EXTERNAL-1].sum()
                    ext = trip_table[key].iloc[dictZoneLookup[MIN_EXTERNAL]:dictZoneLookup[MAX_EXTERNAL]].sum()
                else:
                    ext = 0
                bal_factor = (att - ext)/(prod - ext)
                #trip_table[key].loc[0:HIGH_TAZ-1] *= bal_factor
                trip_table[key].loc[1:HIGH_TAZ] *= bal_factor
                print "value " + value + ", " +key + ' ' + str(bal_factor)

# Load household PUMS data
inc_size_workers_dict = json_to_dictionary('inc_size_workers_dict')
inc_k12_dict = json_to_dictionary('inc_k12_dict')
inc_college_dict = json_to_dictionary('inc_college_dict')
inc_veh_dict = json_to_dictionary('inc_veh_dict')

my_project = EmmeProject(supplemental_project)   


def main():
    print "Calculating supplemental trips generated by exterals, special generators, and group quarters."
    global dictZoneLookup
     
    network_importer(my_project)


    #Create a dictionary lookup where key is the taz id and value is it's numpy index. 
    dictZoneLookup = dict((value,index) for index,value in enumerate(my_project.current_scenario.zone_numbers))
    # Initialize directory
    for file in [trip_table_loc, gq_trips_loc]:
        init_dir(file)

    # Load household and attractors trip rates
    hh_trip = process_inputs(hh_trip_loc, start_row=7, col_names=rate_cols, 
                             clean_column="purpose", pivot_fields=pivot_fields, reorder = [1,24])
    nonhh_trip = process_inputs(nonhh_trip_loc, start_row=7, col_names=rate_cols, 
                                clean_column="purpose", pivot_fields=pivot_fields, reorder = [1,24])
    puma_taz = process_inputs(puma_taz_loc, start_row=0, col_names=['scrap', 'puma'], 
                              clean_column="puma", pivot_fields=False, reorder=False)
    puma_taz = pd.DataFrame(puma_taz["puma"])

    # Join PUMA data to TAZ data
    taz_data = puma_taz_lookup(puma_taz)
    master_taz = taz_data.join(puma_taz)
    pums_df = load_pums()
    master_taz = master_taz.join(pums_df,"puma")
    
    # Calculate households by taz
    master_taz = calc_hhs(master_taz)

    # Compute household trip rates by TAZ and by purpose

    # Create a dataframe that includes only the household cross-classes
    hhs = master_taz[[str(i) for i in xrange(hh_cols[0], hh_cols[1])]]
    # Create a dataframe that includes only the employment cross-classes
    nonhhs = taz_data[[str(i) for i in xrange(emp_cols[0], emp_cols[1])]]
    # Create dataframe for only group quarter zones (columns 122 - 124, for dorm, military an other quarters)
    gq = nonhhs[['122','123','124']]

    # Create empty data frames to hold results
    trips_by_purpose = pd.DataFrame(np.zeros([HIGH_TAZ, 24]), 
                                    columns = [str(i) for i in xrange(1, 24 + 1)],
                                    index = taz_data.index)
    nonhh_trips_by_purp = pd.DataFrame(np.zeros([3700,24]), 
                                    columns = [str(i) for i in xrange(1, 24 + 1)],
                                    index = taz_data.index)
    gq_trips = pd.DataFrame(np.zeros([3700,24]), 
                                    columns = [str(i) for i in xrange(1, 24 + 1)],
                                    index = taz_data.index)

    # Compute household trip rates by TAZ and by purpose
    for purpose in xrange(purp_cols[0], purp_cols[1] + 1):
        print 'Computing trip rates by purpose (of 24): ' + str(purpose)
        trip_rate = pd.DataFrame(hh_trip['rate'].loc[str(purpose)])
        trip_rate.index = [str(i) for i in xrange(hh_cols[0], hh_cols[1])]
        trip_rate.columns = ['col']
        nh_trip_rate = pd.DataFrame(nonhh_trip.loc[str(purpose)])
        nh_trip_rate.index = [str(i) for i in xrange(emp_cols[0], emp_cols[1])]
        nh_trip_rate.columns = ['col']
        gq_trip_rate = pd.DataFrame(nh_trip_rate.loc[['122','123','124']])
        gq_trip_rate.index = [str(i) for i in xrange(122, 124 + 1)]
        gq_trip_rate.columns = ['col']
        for zone in xrange(1,HIGH_TAZ + 1):
            #print 'zone ' + str(zone)
            #hhs1 = pd.DataFrame(hhs.iloc[zone-1])
            hhs1 = pd.DataFrame(hhs.loc[zone])
            #nonhhs1 = pd.DataFrame(nonhhs.iloc[zone-1])
            nonhhs1 = pd.DataFrame(nonhhs.loc[zone])
            #gq1 = pd.DataFrame(gq.iloc[zone-1])
            gq1 = pd.DataFrame(gq.loc[zone])
            hhs1.index = [str(i) for i in xrange(hh_cols[0], hh_cols[1])]
            nonhhs1.index = [str(i) for i in xrange(emp_cols[0], emp_cols[1])]
            gq1.index = [str(i) for i in xrange(122, 124 + 1)]
            hhs1.columns = ['col']
            nonhhs1.columns = ['col']
            gq1.columns = ['col']
            # make sure to select only a single column, can't have more than one array selected per frame
            dot1 = trip_rate['col'].dot(hhs1['col'])
            dot2 = nh_trip_rate['col'].dot(nonhhs1['col'])
            dot3 = gq_trip_rate['col'].dot(gq1['col'])
            #trips_by_purpose[str(purpose)].loc[zone-1] = dot1
            trips_by_purpose[str(purpose)].loc[zone] = dot1
            #nonhh_trips_by_purp[str(purpose)].loc[zone-1] = dot2
            nonhh_trips_by_purp[str(purpose)].loc[zone] = dot2
            #gq_trips[str(purpose)].loc[zone-1] = dot3
            gq_trips[str(purpose)].loc[zone] = dot3
            trip_table = trips_by_purpose + nonhh_trips_by_purp

    # Rename columns
    trip_table.columns = trip_col
    gq_trips.columns = trip_col
    gq_trips.index = trip_table.index

    # Add attractions into group quarters trip table to balance trips
    gq_prod = pd.DataFrame(gq_trips[['hbwpro','colpro','hsppro','hbopro','schpro','wkopro',
                                            'otopro','empty1','hw1pro','hw2pro','hw3pro','hw4pro']])
    all_trips_att = pd.DataFrame(trip_table[['hbwatt','colatt','hspatt','hboatt','schatt',
                                                                'wkoatt','otoatt','empty2','hw1att','hw2att',
                                                                'hw3att','hw4att']])
    gq_append = pd.DataFrame(gq_prod.join(all_trips_att))

    trip_table = add_special_gen(trip_table)

    balance_trips(trip_table, bal_to_attractions = ['colpro'], include_ext=True)
    balance_trips(gq_append, bal_to_attractions = [], include_ext=False)

    # set zonal nhb work-other productions equal to zonal nhb work-other attractions
    # set zonal nhb other-other productions equal to zonal nhb other-other attractions

    trip_table = pd.DataFrame(trip_table,columns=column_set)
    trip_table.columns = trip_col

    # Fill empty rows with placeholder zeros
    externals = trip_table.loc[MIN_EXTERNAL:MAX_EXTERNAL]
    base = trip_table.loc[:HIGH_TAZ]
    placeholder_index = [str(i) for i in xrange(LOW_PNR,HIGH_PNR)]
    placeholder_rows = pd.DataFrame(index=placeholder_index,columns=trip_col)
    trip_table = base.append([placeholder_rows, externals])
    trip_table = trip_table.sort_index(axis=0)

    # Replace "NaN" values with zeros
    gq_append = gq_append.fillna(0)
    trip_table = trip_table.fillna(0)

    # Write results to CSV
    trip_table.to_csv(trip_table_loc, index_label="taz")
    gq_append.to_csv(gq_trips_loc, index_label="taz")

if __name__ == "__main__":
    main()
