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
import xlautofit
import sqlite3 as lite
from datetime import datetime
from EmmeProject import *
from multiprocessing import Pool
from pyproj import Proj, transform
import pandas as pd
sys.path.append(os.path.join(os.getcwd(),"inputs"))
sys.path.append(os.path.join(os.getcwd(),"scripts"))
sys.path.append(os.getcwd())
from standard_summary_configuration import *
from input_configuration import *
from emme_configuration import *
pd.options.mode.chained_assignment = None  # mute chained assignment warnings

daily_network_fname = 'outputs/network/daily_network_results.csv'

## Input Files:
aadt_counts_file = 'soundcast_aadt.csv'
tptt_counts_file = 'soundcast_tptt.csv'

def json_to_dictionary(dict_name):

    #Determine the Path to the input files and load them
    skim_params_loc = os.path.abspath(os.path.join(os.getcwd(),"inputs/model/skim_parameters"))    # Assumes the cwd is @ run_soundcast.py; always run this script from run_soundcast.py
    input_filename = os.path.join(skim_params_loc,dict_name+'.json').replace("\\","/")
    my_dictionary = json.load(open(input_filename))

    return(my_dictionary)
 
def calc_vmt_vht_delay_by_ft(EmmeProject):
    ###calculates vmt, vht, and delay for all links and returns a nested dictionary with key=metric(e.g. 'vmt') 
    #and value = dictionary where dictionary has key = facility type(e.g. 'highway') and value = sum of metric 
    #for that facility type
  
     #medium trucks
     EmmeProject.network_calculator("link_calculation", result = '@mveh', expression = '@metrk/1.5')
     
     #heavy trucks:
     EmmeProject.network_calculator("link_calculation", result = '@hveh', expression = '@hvtrk/2.0')
     
     #busses:
     EmmeProject.network_calculator("link_calculation", result = '@bveh', expression = '@trnv3/2.0')
     ####################still need to do*****************************
     #hdw- number of buses:
     #mod_spec = network_calc_spec
     #mod_spec["result"] = "@hdw"
     #mod_spec["expression"] = 'hdw'
     #network_calc(mod_spec)
     
     #calc total vehicles, store in @tveh 
     str_expression = '@svtl1 + @svtl2 + @svtl3 + @h2tl1 + @h2tl2 + @h2tl3 + @h3tl1\
                                + @h3tl2 + @h3tl3 + @lttrk + @mveh + @hveh + @bveh'
     EmmeProject.network_calculator("link_calculation", result = '@tveh', expression = str_expression)
     #a dictionary to hold vmt/vht/delay values:
     results_dict = {}
     #dictionary to hold vmts:
     vmt_dict = {}
     #calc vmt for all links by factilty type and get sum by ft. 
     for key, value in fac_type_dict.iteritems():    
        EmmeProject.network_calculator("link_calculation", result = "@vmt", expression = "@tveh * length", selections_by_link = value)
        #total vmt by ft: 
        vmt_dict[key] = EmmeProject.network_calc_result['sum']
     #add to results dictionary
     results_dict['vmt'] = vmt_dict
    
     #Now do the same for VHT:
     vht_dict = {}
     for key, value in fac_type_dict.iteritems():    
        EmmeProject.network_calculator("link_calculation", result = "@vht", expression = "@tveh * timau / 60", selections_by_link = value)
        vht_dict[key] = EmmeProject.network_calc_result['sum']
     results_dict['vht'] = vht_dict

     #Delay:
     delay_dict = {}
     for key, value in fac_type_dict.iteritems():    
        EmmeProject.network_calculator("link_calculation",result = None, expression =  "@tveh*(timau-(length*60/ul2))/60", selections_by_link = value)
        delay_dict[key] = EmmeProject.network_calc_result['sum']
     
     results_dict['delay'] = delay_dict
     return results_dict

def vmt_by_user_class(EmmeProject):
    #uc_list = ['@svtl1', '@svtl2', '@svtl3', '@svnt1', '@h2tl1', '@h2tl2', '@h2tl3', '@h2nt1', '@h3tl1', '@h3tl2', '@h3tl3', '@h3nt1', '@lttrk', '@mveh', '@hveh', '@bveh']
    uc_vmt_list = []
    for item in uc_list:
        EmmeProject.network_calculator("link_calculation", result = None, expression = item + ' * length')
        #total vmt by ft: 
        uc_vmt_list.append(EmmeProject.network_calc_result['sum'])
    return uc_vmt_list

def delay_by_user_class(EmmeProject):
    #uc_list = ['@svtl1', '@svtl2', '@svtl3', '@svnt1', '@h2tl1', '@h2tl2', '@h2tl3', '@h2nt1', '@h3tl1', '@h3tl2', '@h3tl3', '@h3nt1', '@lttrk', '@mveh', '@hveh', '@bveh']
    uc_delay_list = []
    link_selection = 'ul3 = 1 or ul3 = 2 or ul3 = 3 or ul3 = 4 or ul3 = 5 or ul3 = 6'
    for item in uc_list:
        EmmeProject.network_calculator("link_calculation", result = None, expression = item + "*(timau-(length*60/ul2))/60", selections_by_link=link_selection)
        uc_delay_list.append(EmmeProject.network_calc_result['sum'])
    return uc_delay_list

def get_link_counts(EmmeProject, loop_id_df, tod):
    #get the network for the active scenario
     network = EmmeProject.current_scenario.get_network()
     scenario = EmmeProject.current_scenario
     list_model_vols = []
     # Add/refresh screenline ID link attribute
     if scenario.extra_attribute('@loop'):
            scenario.delete_extra_attribute('@loop')
     attr = scenario.create_extra_attribute('LINK', '@loop')
     for row in loop_id_df.iterrows():
         i = row[1].NewINode
         j = row[1].NewJNode
         link = network.link(i, j)
         x = {}
         #x['NewINode'] = i
         #x['NewJNode'] = j
         x['CountID'] = row[1].CountID
         if link <> None:
            #link['@loop'] = row[1].CountID
            x['vol' + tod] = link['@tveh']   
         else:
            x['vol' + tod] = None
         list_model_vols.append(x)
     #print len(list_model_vols)
     #scenario.publish_network(network)
     df =  pd.DataFrame(list_model_vols)
     df.set_index(['CountID'], inplace = True)
     #df = df.set_index(['loop_INode', 'loop_JNode'])
     #print df.head(10)
     return df

def get_aadt_volumes(EmmeProject, df_aadt_counts, vol_dict):
    network = EmmeProject.current_scenario.get_network()
    for index, row in df_aadt_counts.iterrows():
        x = {}
        id = row['MIN_ID']
        i = row['MIN_NewINode']
        j = row['MIN_NewJNode']
        if row['MIN_Oneway'] == 2:
            link1 = network.link(i,j)
            link2 = network.link(j, i)
            if link1<>None and link2<> None:
                vol = link1['@tveh'] + link2['@tveh']
            elif link1 == None and link2 == None:
                vol = 0
                #print i, j
            elif link1 <> None and link2 == None:
                vol = link1['@tveh'] 
                #print j, i
            elif link1 == None and link2 <> None:
                vol = link2['@tveh'] 

        elif row['MIN_Oneway'] == 0:
            link1 = network.link(i,j)
            if link1 <> None:
                vol = link1['@tveh']
        else:
            link1 = network.link(j,i)
            if link1 <> None:
                vol = link1['@tveh']

        #hov
        if row['MIN_HOV_I'] > 0:
            i = row['MIN_HOV_I'] + 4000
            j = row['MIN_HOV_J'] + 4000
            #both directions:
            if row['MIN_Oneway'] == 2:
                link1 = network.link(i,j)
                link2 = network.link(j, i)
                if link1<>None and link2<> None:
                    vol = vol +link1['@tveh'] + link2['@tveh']
                elif link1 == None and link2 == None:
                    vol = vol + 0
                    #print i, j
                elif link1 <> None and link2 == None:
                    vol = vol + link1['@tveh'] 
                    #print j, i
                elif link1 == None and link2 <> None:
                    vol = vol + link2['@tveh'] 
            #IJ
            elif row['MIN_Oneway'] == 0:
                link1 = network.link(i,j)
                if link1 <> None:
                    vol = vol + link1['@tveh']
            #JI
            else:
                link1 = network.link(j,i)
                if link1 <> None:
                    vol = vol + link1['@tveh']


        if id in vol_dict.keys():
            vol_dict[id]['EstVol'] = vol_dict[id]['EstVol'] + vol
        else:
            x['ID'] = id
            x['PSRCEdgeID'] = row['PSRCEdgeID']
            x['ObsVol'] = row['MEAN_AADT']
            #x['RteID'] = row['First_Route_ID']
            x['EstVol'] = vol
            vol_dict[id] = x
    return vol_dict

def get_tptt_volumes(EmmeProject, df_tptt_counts, vol_dict):
    network = EmmeProject.current_scenario.get_network()
    for index, row in df_tptt_counts.iterrows():
        x = {}
        id = row ['ID']
        i = row['NewINode']
        j = row['NewJNode']
        if row['Direction_'] == 'Bothways':
            link1 = network.link(i,j)
            link2 = network.link(j, i)
            if link1<>None and link2<> None:
                vol = link1['@tveh'] + link2['@tveh']
            elif link1 == None and link2 == None:
                vol = 0
                #print i, j
            elif link1 <> None and link2 == None:
                vol = link1['@tveh'] 
                #print j, i
            elif link1 == None and link2 <> None:
                vol = link2['@tveh'] 

        elif row['Oneway'] == 0:
            link1 = network.link(i,j)
            if link1 <> None:
                vol = link1['@tveh']
        else:
            link1 = network.link(j,i)
            if link1 <> None:
                vol = link1['@tveh']

        if id in vol_dict.keys():
            vol_dict[id]['EstVol'] = vol_dict[id]['EstVol'] + vol
        else:
            x['ID'] = id
            x['SRID'] = row['SRID']
            x['ObsVol'] = row['Year_2010']
            x['Location'] = row['Location']
            x['EstVol'] = vol
            vol_dict[id] = x
    return vol_dict

def get_unique_screenlines(EmmeProject):
    network = EmmeProject.current_scenario.get_network()
    unique_screenlines = []
    for link in network.links():
        if link.type <> 90 and link.type not in unique_screenlines:
            unique_screenlines.append(str(link.type))
    return unique_screenlines

def get_screenline_volumes(screenline_dict, EmmeProject):

    for screen_line in screenline_dict.iterkeys():
        EmmeProject.network_calculator("link_calculation",result = None, expression = "@tveh", selections_by_link = screen_line)
        screenline_dict[screen_line] = screenline_dict[screen_line] + EmmeProject.network_calc_result['sum']

def calc_transit_line_atts(EmmeProject):
    #calc boardings and transit line time
     EmmeProject.transit_line_calculator(result = '@board', expression = 'board')
     EmmeProject.transit_line_calculator(result = '@timtr', expression = 'timtr')

def get_transit_boardings_time(EmmeProject):
    network = EmmeProject.current_scenario.get_network()
    #df_transit_atts = pd.DataFrame(columns=('id', EmmeProject.tod + '_boardings', EmmeProject.tod + '_boardings''_time'))
    line_list = []
    atts = []
    for transit_line in network.transit_lines():
        x = {}
        
        #company_code = transit_line['@ut3']
        atts.append({'id' : transit_line.id, 'route_code' : transit_line.data1, 'mode' : str(transit_line.mode), 'description' : transit_line.description})
        x['id'] = transit_line.id
        x[EmmeProject.tod + '_board'] = transit_line['@board']
        x[EmmeProject.tod + '_time']= transit_line['@timtr']
        line_list.append(x)
    df = pd.DataFrame(line_list)
    df = df.set_index(['id'])
    return [df, atts]

def calc_transit_link_volumes(EmmeProject):
    total_hours = transit_tod[EmmeProject.tod]['num_of_hours']
    my_expression = str(total_hours) + ' * vauteq * (60/hdw)'
    
    EmmeProject.transit_segment_calculator(result = '@trnv', expression = my_expression, aggregation = "+")
    
def writeCSV(fileNamePath, listOfTuples):
    myWriter = csv.writer(open(fileNamePath, 'wb'))
    for l in listOfTuples:
        myWriter.writerow(l)

def dict_to_df(input_dict, measure):
    '''converts triple-nested dict into Dataframe for a given facility type'''
    mydict = {}
    for tod in tods:
        mydict[tod] = {}
        for facility in fac_type_dict.keys():
            mydict[tod][facility] = input_dict[tod][measure][facility]
    return pd.DataFrame(mydict)

def get_runid(table, con):
    '''Update run ID from existing database'''
    try:
        return len(pd.read_sql('select * from ' + table, con))
    except:
        return 0

def get_date():
    '''Get last time stamp from run log.
       Log time stamps are consistently formatted & exist for each line in the log
       For runs without a log, or on error, get current time. '''
    try:
        timestamp = str(pd.read_csv(main_log_file).iloc[-1]).split(' ')
        logdate = timestamp[0] + " " + timestamp[1] + " " + timestamp[2]
    except:
        logdate = datetime.now().strftime("%m/%d/%Y %I:%M:%S %p")
    summarydate = datetime.now().strftime("%m/%d/%Y %I:%M:%S %p")
    return logdate, summarydate

def stamp(df, con, table):
    '''Add run information to a table row'''
    df['scenario_name'],df['runid'],df['logdate'],df['summarydate'] = \
    [scenario_name,get_runid(table, con),get_date()[0],get_date()[1]]
    return df

def process_h5(data_table, h5_file, columns):
    ''' Convert DaySim tables (e.g., person, household files) to dataframe ''' 
    h5_file = h5py.File(h5_file)    # read h5 data
    df = pd.DataFrame()     # initialize empty data frame
    
    for col in columns:
        df[col] = h5_file[data_table][col].value
    return df

def process_screenlines(screenline_dict):
    '''Convert screenline volume dictionary to dataframe in SQL format (single row of columns)'''
    
    # Load screenline lookup between location name and network value
    screenline_names = pd.read_json('inputs/base_year/screenline_dict.json',orient='values')
    screenline_names['id'] = screenline_names.index

    # Load screenline volumes from the network and merge with names lookup
    screenline_data = pd.DataFrame(screenline_dict.values(), index=screenline_dict.keys(),columns=['volume'])
    screenline_data['id'] = screenline_data.index.astype('float64')
    screenline_data = pd.merge(screenline_data, screenline_names)

    # Create a single column of screenline volumes 
    screenline_data.fillna('',inplace=True) 
    screenline_data.index = screenline_data['Primary']+screenline_data['Secondary']
    
    # Combine the 2 Auburn screenlines; can't have duplicate column names in SQL
    screenline_data = screenline_data.groupby(screenline_data.index).sum()[['volume']].T    # transpose to convert to single row
    
    return screenline_data

def get_link_attribute(network, attr):
    ''' Return dataframe of link attribute and link ID'''
    link_dict = {}
    for i in network.links():
        link_dict[i.id] = i[attr]
    df = pd.DataFrame({'link_id': link_dict.keys(), attr: link_dict.values()})
    return df


def calc_total_vehicles(my_project):
     '''For a given time period, calculate link level volume, store as extra attribute on the link'''
    
     #medium trucks
     my_project.network_calculator("link_calculation", result = '@mveh', expression = '@metrk/1.5')
     
     #heavy trucks:
     my_project.network_calculator("link_calculation", result = '@hveh', expression = '@hvtrk/2.0')
     
     #buses:
     my_project.network_calculator("link_calculation", result = '@bveh', expression = '@trnv3/2.0')
     
     #calc total vehicles, store in @tveh 
     str_expression = '@svtl1 + @svtl2 + @svtl3 + @h2tl1 + @h2tl2 + @h2tl3 + @h3tl1 + @h3tl2 + @h3tl3 + @lttrk + @mveh + @hveh + @bveh'
     my_project.network_calculator("link_calculation", result = '@tveh', expression = str_expression)


def get_aadt_trucks(my_project):
    '''Calculate link level daily total truck passenger equivalents for medium and heavy, store in a DataFrame'''
    
    link_list = []

    for key, value in sound_cast_net_dict.iteritems():
        my_project.change_active_database(key)
        
        # Create extra attributes to store link volume data
        for name, desc in extra_attributes_dict.iteritems():
            my_project.create_extra_attribute('LINK', name, desc, 'True')
        
        ## Calculate total vehicles for each link
        calc_total_vehicles(my_project)
        
        # Loop through each link, store length and truck pce
        network = my_project.current_scenario.get_network()
        for link in network.links():
            link_list.append({'link_id' : link.id, '@mveh' : link['@mveh'], '@hveh' : link['@hveh'], 'length' : link.length})
            
    df = pd.DataFrame(link_list, columns = link_list[0].keys())       
    grouped = df.groupby(['link_id'])
    df = grouped.agg({'@mveh':sum, '@hveh':sum, 'length':min})
    df.reset_index(level=0, inplace=True)
    
    return df
    
def truck_summary(df_counts, my_project, writer):
    """ Export medium and heavy truck results where observed data is available """
    
    truck_volumes = get_aadt_trucks(my_project)
    truck_compare = pd.merge(df_counts, truck_volumes, left_on='ij_id', right_on='link_id')
    truck_compare['modeledTot'] = truck_compare['@mveh']+truck_compare['@hveh']
    truck_compare['modeledMed'] = truck_compare['@mveh']
    truck_compare['modeledHvy'] = truck_compare['@hveh']
    truck_compare_grouped_sum = truck_compare.groupby(['CountID']).sum()[['modeledTot', 'modeledMed', 'modeledHvy']]
    truck_compare_grouped_sum.reset_index(level=0, inplace=True)
    truck_compare_grouped_min = truck_compare.groupby(['CountID']).min()[['Location', 'LocationDetail', 'FacilityType', 'length', 'observedMed',
                                                                        'observedHvy', 'observedTot','county','LARGE_AREA','lat','lon']]
    truck_compare_grouped_min.reset_index(level=0, inplace=True)
    trucks_out= pd.merge(truck_compare_grouped_sum, truck_compare_grouped_min, on= 'CountID')
    trucks_out.to_excel(excel_writer=writer, sheet_name='Truck Counts')

def daily_counts(writer, my_project):
    """Export daily network volumes and compare to observed."""

    # Load observed data
    count_id_df = pd.read_csv(r'inputs/base_year/screenline_count_ids.txt', sep = ' ', header = None, names = ['NewINode', 'NewJNode','ScreenLineID'])
    observed_count_df =  pd.read_csv(r'inputs/base_year/observed_daily_counts.csv')
    count_id_df = count_id_df.merge(observed_count_df, how = 'left', on = 'ScreenLineID')
    # add daily bank to project if it exists
    if os.path.isfile(r'Banks/Daily/emmebank'):
        bank = _eb.Emmebank(r'Banks/Daily/emmebank')
        scenario = bank.scenario(1002)

        # Add/refresh screenline ID link attribute
        if scenario.extra_attribute('@scrn'):
            scenario.delete_extra_attribute('@scrn')
        attr = scenario.create_extra_attribute('LINK', '@scrn')

        # Add/refresh screenline count value from assignment results
        if scenario.extra_attribute('@count'):
            scenario.delete_extra_attribute('@count')
        attr_count = scenario.create_extra_attribute('LINK', '@count')

        network = scenario.get_network()

        inode_list = []
        jnode_list = []
        scrn_id = []
        facility_list = []
        observed_volume = []
        model_volume = []

        for row in count_id_df.iterrows():
            inode = int(row[1].NewINode) 
            jnode = int(row[1].NewJNode) 
            if network.link(inode, jnode):
                link = network.link(inode, jnode)
                link['@scrn'] = row[1]['ScreenLineID']
                link['@count'] = row[1]['Year_2014']

                inode_list.append(inode)
                jnode_list.append(jnode)
                facility_list.append(link['data3'])
                scrn_id.append(link['@scrn'])
                observed_volume.append(link['@count'])
                model_volume.append(link['@tveh'])

        scenario.publish_network(network)

        df = pd.DataFrame([inode_list,jnode_list,facility_list,model_volume,scrn_id,observed_volume]).T
        df.columns=['i','j','ul3','@tveh','@scrn','count']

        df.to_excel(excel_writer=writer, sheet_name='Daily Counts')

        # Export truck trip tables
        # for matrix_name in ['mfmetrk','mfhvtrk']:
        #     matrix_id = bank.matrix(matrix_name).id
        #     emme_matrix = bank.matrix(matrix_id)
        #     matrix_data = emme_matrix.get_data()
        #     np_matrix = np.matrix(matrix_data.raw_data)
        #     df = pd.DataFrame(np_matrix)
        #     # Attach zone numbers
        #     # Look up zone ID from index location
        #     zones = my_project.current_scenario.zone_numbers
        #     dictZoneLookup = dict((index,value) for index,value in enumerate(zones))
        #     df.columns = [dictZoneLookup[i] for i in df.columns]
        #     df.index = [dictZoneLookup[i] for i in df.index.values]

        #     df.to_csv('outputs/'+matrix_name+'.csv')
    else:
        raise Exception('no daily bank found')

def bike_volumes(writer, my_project, tod):
    '''Write bike link volumes to file for comparisons to counts '''

    my_project.change_active_database(tod)

    network = my_project.current_scenario.get_network()

    # Load bike count data from file
    bike_counts = pd.read_csv(bike_count_data)

    # Load edges file to join proper node IDs
    edges_df = pd.read_csv(edges_file)

    df = bike_counts.merge(edges_df, 
        on=['INode','JNode'])
    
    # if the link is twoway, also get the other directoin IJ and JI and append to original df
    twoway_links_df = df[df['Oneway'] == 2]

    # Replace I with J node for twoway links, for Emme IJ and geodatabase IJ pairs
    twoway_links_df.loc[:,'tempINode'] = twoway_links_df.loc[:,'JNode']
    twoway_links_df.loc[:,'tempJNode'] = twoway_links_df.loc[:,'INode']
    twoway_links_df.loc[:,'tempNewINode'] = twoway_links_df.loc[:,'NewJNode']
    twoway_links_df.loc[:,'tempNewJNode'] = twoway_links_df.loc[:,'NewINode']
    # remove old IJ values and replace with the new swapped values
    twoway_links_df.drop(['INode','JNode','NewINode','NewJNode'],axis=1,inplace=True)
    twoway_links_df.loc[:,'INode'] = twoway_links_df.loc[:,'tempINode']
    twoway_links_df.loc[:,'JNode'] = twoway_links_df.loc[:,'tempJNode']
    twoway_links_df.loc[:,'NewINode'] = twoway_links_df.loc[:,'tempNewINode']
    twoway_links_df.loc[:,'NewJNode'] = twoway_links_df.loc[:,'tempNewJNode']
    twoway_links_df.drop(['tempINode','tempJNode','tempNewINode','tempNewJNode'],axis=1,inplace=True)

    df = pd.concat([df,twoway_links_df])
    df = df.reset_index()
    list_model_vols = []

    for row in df.index:
        i = df.iloc[row]['NewINode']
        j = df.loc[row]['NewJNode']
        link = network.link(i, j)
        x = {}
        x['EmmeINode'] = i
        x['EmmeJNode'] = j
        x['gdbINode'] = df.iloc[row]['INode']
        x['gdbJNode'] = df.iloc[row]['JNode']
        x['LocationID'] = df.iloc[row]['LocationID']
        if link != None:
            x['bvol' + tod] = link['@bvol']
        else:
            x['bvol' + tod] = None
        list_model_vols.append(x)

    df_count =  pd.DataFrame(list_model_vols)
    sheet_name = 'Bike Volumes'
    summary_file_dir = 'outputs/network/network_summary_detailed.xlsx'
    if os.path.exists(summary_file_dir):
        xl = pd.ExcelFile(summary_file_dir)
        if sheet_name in xl.sheet_names:
            '''append column to existing TOD results'''
            # df = pd.read_csv(bike_link_vol)
            df = pd.read_excel(io=xl, sheetname=sheet_name)
            df['bvol'+tod] = df_count['bvol'+tod]
            # df.to_csv(bike_link_vol,index=False)
            df.to_excel(excel_writer=writer, sheet_name=sheet_name, index=False) 
        else:
            # df_count.to_csv(bike_link_vol,index=False)
            df_count.to_excel(excel_writer=writer, sheet_name=sheet_name, index=False)

def light_rail(df, writer):

    # load lookup table for observed boardings and station names
    observed = pd.read_csv(light_rail_boardings)
    
    # # Join total and initial boardings & sum for all hours

    # # Join station information for set of nodes; report only for station in observed file
    df = pd.merge(df, observed, left_on='inode', right_on='id', how='inner')
    df['transfer_rate'] = df['transfers']/df['total_boardings']
    if model_year == base_year:
        df = df.loc[(df.observed_boardings>0)]
    df.to_excel(excel_writer=writer, sheet_name='Light Rail')

def export_corridor_results(my_project, writer):
    ''' Evaluate corridor travel time for a single AM and PM period'''
    tod = {'am': '7to8', 'pm': '16to17'}
    am_df = corridor_results(tod=tod['am'], my_project=my_project)
    pm_df = corridor_results(tod=tod['pm'], my_project=my_project)

    # combine am and pm into single CSV and export
    df = pd.concat(objs=[am_df, pm_df])
    df.to_excel(excel_writer=writer, sheet_name='Corridors')

def corridor_results(tod, my_project):
    corridor_count = 12    # number of input corridor files

    # filepath = r'projects\\' + tod + '\\' + tod + '.emp'
    # my_project = EmmeProject(filepath)
    my_project.change_active_database(tod)

    # Access the nework link data
    network = my_project.current_scenario.get_network()

    # Get the auto time and length of each link
    

    # Get dataframes for time and length
    time_df = get_link_attribute(network=network, attr='auto_time')
    length_df = get_link_attribute(network=network, attr='length')    

    # combine link time and length data into single dataframe
    link_df = pd.merge(time_df, length_df)

    corridor_flags_df = pd.DataFrame()
    for i in range(1, corridor_count+1):    # +1 because python is zero-based
        corridor_df = pd.read_table(r'inputs/corridors/corridor_' + str(i) + '.in', skiprows=1, skipinitialspace=True, sep=' ')
        corridor_df['link_id'] = corridor_df['inode'].astype('str') + '-' + corridor_df['jnode'].astype('str')
        corridor_flags_df = pd.concat(objs=[corridor_flags_df, corridor_df])

    corridor_flags_df.fillna(0, inplace=True)

    # join corridor flags to link travel time
    corridor_times_df = pd.merge(link_df, corridor_flags_df)

    # corridor_times_df.to_csv('temp.csv')

    # sum corridor travel time and length for each corridor
    link_trav_time = pd.DataFrame()
    for i in range(1, corridor_count+1):    # +1 because python is zero-based
        if i < 10:
            code = '@corr'
        else:
            code = '@cor'

        corridor_sum = pd.DataFrame(corridor_times_df.groupby(code + str(i)).sum()[['auto_time', 'length']])
        
        # add a corridor id tag for analysis
        corridor_sum['Corridor Input File'] = i
        corridor_sum['Local ID'] = corridor_sum.index
        link_trav_time = pd.concat([link_trav_time, corridor_sum])        

    # remove all the 0-index results (these are travel times on non-tagged links)
    link_trav_time = link_trav_time.query('index > 0')

    # Add a column that concatenates the corridor file number and the corridor tag ID 
    # for processessing in Excel
    link_trav_time['full_id'] = link_trav_time['Corridor Input File'].astype('str') + link_trav_time['Local ID'].astype('str')
    link_trav_time['full_id'] = link_trav_time['full_id'].astype('float')

    # Add a column for time of day
    link_trav_time['tod'] = tod

    # Write out to CSV
    df_out = link_trav_time[['tod', 'Corridor Input File', 'Local ID', 
                'full_id', 'auto_time', 'length']]

    return df_out

def freeflow_skims(my_project):
    """
    Attach "freeflow" (20to5) SOV skims to daysim_outputs
    """

    # Load daysim_outputs as dataframe
    daysim = h5py.File('outputs/daysim/daysim_outputs.h5', 'r+')
    df = pd.DataFrame()
    for field in ['travtime','otaz','dtaz']:
        df[field] = daysim['Trip'][field][:]
    df['od']=df['otaz'].astype('str')+'-'+df['dtaz'].astype('str')

    # Look up zone ID from index location
    zones = my_project.current_scenario.zone_numbers
    dictZoneLookup = dict((index,value) for index,value in enumerate(zones))

    skim_vals = h5py.File(r'outputs/skims/20to5.h5')['Skims']['svtl3t'][:]

    skim_df = pd.DataFrame(skim_vals)
    # Reset index and column headers to match zone ID
    skim_df.columns = [dictZoneLookup[i] for i in skim_df.columns]
    skim_df.index = [dictZoneLookup[i] for i in skim_df.index.values]

    skim_df = skim_df.stack().reset_index()
    skim_df.columns = ['otaz','dtaz','ff_travtime']
    skim_df['od']=skim_df['otaz'].astype('str')+'-'+skim_df['dtaz'].astype('str')
    skim_df.index = skim_df['od']

    df = df.join(skim_df,on='od', lsuffix='_cong',rsuffix='_ff')

    # Write to h5, create dataset if 
    if 'sov_ff_time' in daysim['Trip'].keys():
        del daysim['Trip']['sov_ff_time']
    try:
        daysim['Trip'].create_dataset("sov_ff_time", data=df['ff_travtime'].values, compression='gzip')
    except:
        print 'could not write freeflow skim to h5'
    daysim.close()

def jobs_transit(writer):
    buf = pd.read_csv(r'outputs/landuse/buffered_parcels.txt', sep=' ')
    buf.index = buf.parcelid

    # distance to any transit stop
    df = buf[['parcelid','dist_lbus','dist_crt','dist_fry','dist_lrt',
              u'hh_p', u'stugrd_p', u'stuhgh_p', u'stuuni_p', u'empedu_p',
           u'empfoo_p', u'empgov_p', u'empind_p', u'empmed_p', u'empofc_p',
           u'empret_p', u'empsvc_p', u'empoth_p', u'emptot_p']]

    # Use minimum distance to any transit stop
    newdf = pd.DataFrame(df[['dist_lbus','dist_crt','dist_fry','dist_lrt']].min(axis=1))
    newdf['parcelid'] = newdf.index
    newdf.rename(columns={0:'nearest_transit'}, inplace=True)
    df = pd.merge(df,newdf[['parcelid','nearest_transit']])

    # only sum for parcels closer than quarter mile to stop
    quarter_mile_jobs = pd.DataFrame(df[df['nearest_transit'] <= 0.25].sum())
    quarter_mile_jobs.rename(columns={0:'quarter_mile_transit'}, inplace=True)
    all_jobs = pd.DataFrame(df.sum())
    all_jobs.rename(columns={0:'total'}, inplace=True)

    df = pd.merge(all_jobs,quarter_mile_jobs, left_index=True, right_index=True)
    df.drop(['parcelid','dist_lbus','dist_crt','dist_fry','dist_lrt','nearest_transit'], inplace=True)

    df.to_excel(excel_writer=writer, sheet_name='Transit Job Access')


def project_to_wgs84(longitude, latitude, ESPG = "+init=EPSG:2926", conversion = 0.3048006096012192):
    '''
    Converts the passed in coordinates from their native projection (default is state plane WA North-EPSG:2926)
    to wgs84. Returns a two item tuple containing the longitude (x) and latitude (y) in wgs84. Coordinates
    must be in meters hence the default conversion factor- PSRC's are in state plane feet.  
    '''
    #print longitude, latitude
    # Remember long is x and lat is y!
    prj_wgs = Proj(init='epsg:4326')
    prj_sp = Proj(ESPG)
    
    # Need to convert feet to meters:
    longitude = longitude * conversion
    latitude = latitude * conversion
    x, y = transform(prj_sp, prj_wgs, longitude, latitude)
    
    return x, y

def export_network_shape(tod):
    """
    Loop through network components and export shape points
    """

    if os.path.isfile(r'Banks/'+tod+'/emmebank'):
        bank = _eb.Emmebank(r'Banks/'+tod+'/emmebank')
        scenario = bank.scenario(1002)
        network = scenario.get_network()

        inode_list = []
        jnode_list = []
        shape_x = []
        shape_y = []
        shape_loc = []

        for link in network.links():
            local_index = 0
            for point in link.shape:
                inode_list.append(link.i_node)
                jnode_list.append(link.j_node)
                shape_x.append(point[0])
                shape_y.append(point[1])
                shape_loc.append(local_index)
                local_index += 1

        df = pd.DataFrame([inode_list,jnode_list,shape_loc,shape_x,shape_y]).T
        df.columns=['i','j','shape_local_index','x','y']

        df['ij'] = df['i'].astype('str') + '-' + df['j'].astype('str')

        # convert to lat-lon
        df['lat_lon'] = df[['x','y']].apply(lambda row: project_to_wgs84(row['x'], row['y']), axis=1)
        df['lon'] = df['lat_lon'].apply(lambda row: row[0])
        df['lat'] = df['lat_lon'].apply(lambda row: row[-1])

        df.to_csv('outputs/network/network_shape.csv', index=False)

def main():
    ft_summary_dict = {}
    transit_summary_dict = {}
    transit_atts = []
    my_project = EmmeProject(project)

    export_network_shape('7to8')

    writer = pd.ExcelWriter('outputs/network/network_summary_detailed.xlsx', engine='xlsxwriter')    

    # export_corridor_results(my_project, writer)
    jobs_transit(writer)
       
    # Read observed count data
    loop_ids = pd.read_csv(r'inputs/scenario/networks/count_ids.txt', sep = ' ', header = None, names = ['NewINode', 'NewJNode','CountID'])
    loop_counts = pd.read_csv(r'inputs/base_year/loop_counts_2014.csv')
    loop_counts.set_index(['CountID_Type'], inplace = True)
    #loop_ids = pd.read_csv('scripts/summarize/inputs/network_summary/' + counts_file, index_col=['loop_INode', 'loop_JNode'])
    df_counts = pd.read_csv('scripts/summarize/inputs/network_summary/' + counts_file, index_col=['loop_INode', 'loop_JNode'])
    df_aadt_counts = pd.read_csv('scripts/summarize/inputs/network_summary/' + aadt_counts_file)
    df_tptt_counts = pd.read_csv('scripts/summarize/inputs/network_summary/' + tptt_counts_file)
    df_truck_counts = pd.read_csv(truck_counts_file)

    daily_counts(writer, my_project)

    freeflow_skims(my_project)

    if run_truck_summary:
    	truck_summary(df_counts=df_truck_counts, my_project=my_project, writer=writer)



    counts_dict = {}
    uc_vmt_dict = {}
    uc_delay_dict = {}
    aadt_counts_dict = {}
    
    tptt_counts_dict = {}

    # write out stop-level boardings
    stop_df = pd.DataFrame()

    # write out transit segment boardings (line and stop specific)
    seg_df = pd.DataFrame()
    
    #get a list of screenlines from the bank/scenario
    screenline_list = get_unique_screenlines(my_project) 
    screenline_dict = {}
    
    for item in screenline_list:
        #dict where key is screen line id and value is 0
        screenline_dict[item] = 0

   #  #loop through all tod banks and get network summaries
    for key, value in sound_cast_net_dict.iteritems():
        my_project.change_active_database(key)
        for name, desc in extra_attributes_dict.iteritems():
            my_project.create_extra_attribute('LINK', name, desc, 'True')

        network = my_project.current_scenario.get_network()

        tveh = []
        i_list = []
        j_list = []
        speed_limit = []
        facility_type = []
        capacity = []
        length = []
        time = []
        metrk = []
        hvtrk = []
        bvol = []

        # Link volumes
        for link in network.links():
            i_list.append(link.i_node)
            j_list.append(link.j_node)
            tveh.append(link.auto_volume)
            metrk.append(link['@metrk'])
            hvtrk.append(link['@hvtrk'])
            speed_limit.append(link.data2)
            facility_type.append(link.data3)
            capacity.append(link.data1)
            length.append(link['length'])
            time.append(link.auto_time)
            try:
                bvol.append(link['@bvol'])
            except:
                # print 'no bvol ' + key
                pass

        df = pd.DataFrame([i_list,j_list,tveh,metrk,hvtrk,speed_limit,facility_type,
            capacity,length,time,bvol]).T
        df.columns = ['i','j','tveh','metrk','hvtrk','speed_limit','facility_type',
        'capacity','ij_length','time','bvol']
        df['tod'] = key
        df['ij'] = df['i'].astype('str') + '-' + df['j'].astype('str')

        network_results_path = r'outputs/network/network_results.csv'
        if os.path.exists(network_results_path):
            df.to_csv(network_results_path, mode='a', index=False, header=False)
        else:
            df.to_csv(network_results_path, index=False)

        #TRANSIT:
        if my_project.tod in transit_tod.keys():
            for name, desc in transit_extra_attributes_dict.iteritems():
                my_project.create_extra_attribute('TRANSIT_LINE', name, desc, 'True')
            #calc_transit_link_volumes(my_project)
            calc_transit_line_atts(my_project)
            transit_results = get_transit_boardings_time(my_project)
            transit_summary_dict[key] = transit_results[0]
            transit_atts.extend(transit_results[1])
            #transit_atts = list(set(transit_atts))
        
            network = my_project.current_scenario.get_network()
            ons = {}
            offs = {}
            
            for node in network.nodes():
                ons[int(node.id)] = node.initial_boardings
                offs[int(node.id)] = node.final_alightings
            
            df = pd.DataFrame() # temp dataFrame to append to stop_df
            df['inode'] = ons.keys()
            df['initial_boardings'] = ons.values()
            df['final_alightings'] = offs.values()
            df['tod'] = my_project.tod

            stop_df = stop_df.append(df)

            # Transit segment values
            # boardings = {}
            # line = {}

            boardings = []
            line = []
            inode = []

            for tseg in network.transit_segments():
                boardings.append(tseg.transit_boardings)
                line.append(tseg.line.id)
                inode.append(tseg.i_node.number)

                # boardings[tseg.i_node.number] = tseg.transit_boardings
                # line[tseg.i_node.number] = tseg.line.id
            
            df = pd.DataFrame([inode,boardings,line]).T
            df.columns = ['inode','total_boardings','line']
            df['tod'] = my_project.tod
            # df['inode'] = boardings.keys()
            # df['line'] = line.values()
            # df['total_boardings'] = boardings.values()
            

            seg_df = seg_df.append(df)

          
        net_stats = calc_vmt_vht_delay_by_ft(my_project)

        #store tod network summaries in dictionary where key is tod:
        ft_summary_dict[key] = net_stats
        #store vmt by user class in dict:
        uc_vmt_dict[key] = vmt_by_user_class(my_project)
        uc_delay_dict[key] = delay_by_user_class(my_project)

        #counts:
        df_tod_vol = get_link_counts(my_project, loop_ids, key)
        counts_dict[key] = df_tod_vol
        
        #AADT Counts:

        get_aadt_volumes(my_project, df_aadt_counts, aadt_counts_dict)
        
        #TPTT:
        get_tptt_volumes(my_project, df_tptt_counts, tptt_counts_dict)
        
        
        #screen lines
        get_screenline_volumes(screenline_dict, my_project)

        # bike volumes
        if key in ['5to6','7to8','8to9','9to10','10to14','14to15','15to16','16to17',
                        '17to18']:
            bike_volumes(writer=writer, my_project=my_project, tod=key)
        
    list_of_measures = ['vmt', 'vht', 'delay']

    # write total boardings by inode, transit line, and tod
    # seg_df.to_excel(excel_writer=writer, sheet_name='Segments')
    
    # combine initial and final boardings for transfers
    seg_df = seg_df.groupby('inode').sum().reset_index()
    seg_df = seg_df.drop(['tod','line'], axis=1)
    stop_df = stop_df.groupby('inode').sum().reset_index()
    transfer_df = pd.merge(stop_df, seg_df, on='inode')
    transfer_df['transfers'] = transfer_df['total_boardings'] - transfer_df['initial_boardings']
    transfer_df.to_excel(excel_writer=writer, sheet_name='Transfers by Stop')

    # Compute daily boardings for light-rail and major stops    
    light_rail(df=transfer_df, writer=writer)

   #write out transit:
    # print uc_vmt_dict
    col = 0
    transit_df = pd.DataFrame()

    for tod, df in transit_summary_dict.iteritems():
        
       workbook = writer.book
       index_format = workbook.add_format({'align': 'left', 'bold': True, 'border': True})
       transit_df = pd.merge(transit_df, df, 'outer', left_index = True, right_index = True)
       #transit_df[tod + '_board'] = df[tod + '_board']
       #transit_df[tod + '_time'] = df[tod + '_time']
    
    transit_df = transit_df[['5to6_board', '5to6_time', '6to7_board', '6to7_time', '7to8_board', '7to8_time', '8to9_board', '8to9_time', '9to10_board', \
        '9to10_time', '10to14_board', '10to14_time', '14to15_board', '14to15_time', '15to16_board', '15to16_time', '16to17_board', '16to17_time', \
        '17to18_board', '17to18_time', '18to20_board', '18to20_time']]
    transit_atts_df = pd.DataFrame(transit_atts)
    transit_atts_df = transit_atts_df.drop_duplicates(['id'], take_last=True)
    transit_df.reset_index(level=0, inplace=True)
    transit_atts_df = transit_atts_df.merge(transit_df, 'inner', right_on=['id'], left_on=['id'])
    transit_atts_df.to_excel(excel_writer = writer, sheet_name = 'Transit Summaries')
       

    #*******write out counts:
    for value in counts_dict.itervalues():
        loop_counts = loop_counts.merge(value, left_index = True, right_index = True)
    #loop_counts = loop_counts.drop_duplicates()
    
    #write counts out to xlsx:
    #loops
    loop_counts.to_excel(excel_writer = writer, sheet_name = 'Counts Output')
    
    #aadt:
    aadt_df = pd.DataFrame.from_dict(aadt_counts_dict, orient="index")
    aadt_df.to_excel(excel_writer = writer, sheet_name = 'Arterial Counts Output')

    #tptt:
    tptt_df = pd.DataFrame.from_dict(tptt_counts_dict, orient="index")
    tptt_df.to_excel(excel_writer = writer, sheet_name = 'TPTT Counts Output')

    

    #*******write out network summaries
    soundcast_tods = sound_cast_net_dict.keys
    list_of_FTs = fac_type_dict.keys()
    row_list = []
    list_of_rows = []
    header = ['tod', 'TP_4k']
    
    #create the header
    for measure in list_of_measures:
        for factype in list_of_FTs:
            header.append(factype + '_' + measure)
    list_of_rows.append(header)

    net_summary_df = pd.DataFrame(columns = header)
    net_summary_df['tod'] = ft_summary_dict.keys()    
    net_summary_df['TP_4k'] = net_summary_df['tod'].map(sound_cast_net_dict)
    net_summary_df = net_summary_df.set_index('tod')
    for key, value in ft_summary_dict.iteritems():
        for measure in list_of_measures:
            for factype in list_of_FTs:
                net_summary_df[factype + '_' + measure][key] = value[measure][factype]
    net_summary_df.to_excel(excel_writer = writer, sheet_name = 'Network Summary')

    #*******write out screenlines
    screenline_df = pd.DataFrame()
    screenline_df['Screenline'] = screenline_dict.keys()
    screenline_df['Volumes'] = screenline_dict.values()
    screenline_df.to_excel(excel_writer = writer, sheet_name = 'Screenline Volumes')

    uc_vmt_df = pd.DataFrame(columns = uc_list, index = uc_vmt_dict.keys())
    for colnum in range(len(uc_list)):
        for index in uc_vmt_dict.keys():
            uc_vmt_df[uc_list[colnum]][index] = uc_vmt_dict[index][colnum]
    uc_vmt_df = uc_vmt_df.sort_index()
    uc_vmt_df.to_excel(excel_writer = writer, sheet_name = 'UC VMT')

    uc_delay_df = pd.DataFrame(columns = uc_list, index = uc_delay_dict.keys())
    for colnum in range(len(uc_list)):
        for index in uc_delay_dict.keys():
            uc_delay_df[uc_list[colnum]][index] = uc_delay_dict[index][colnum]
    uc_delay_df = uc_delay_df.sort_index()
    uc_delay_df.to_excel(excel_writer = writer, sheet_name = 'UC Delay')

    writer.save()

if __name__ == "__main__":
    main()



 





               
