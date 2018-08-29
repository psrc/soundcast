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

import os, sys
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(CURRENT_DIR))
sys.path.append(os.path.join(os.getcwd(),"inputs"))
sys.path.append(os.path.join(os.getcwd(),"scripts"))
sys.path.append(os.getcwd())
import inro.emme.database.emmebank as _eb
import pandas as pd
import numpy as np
import json
import h5py
from pyproj import Proj, transform
import nbformat
from nbconvert.preprocessors import ExecutePreprocessor
from EmmeProject import *
from standard_summary_configuration import *
from input_configuration import *
from emme_configuration import *
pd.options.mode.chained_assignment = None  # mute chained assignment warnings

def json_to_dictionary(dict_name):
    """ Read skim parameter JSON inputs as dictionary """

    skim_params_loc = os.path.abspath(os.path.join(os.getcwd(),"inputs/model/skim_parameters")) 
    input_filename = os.path.join(skim_params_loc,dict_name+'.json').replace("\\","/")
    my_dictionary = json.load(open(input_filename))

    return(my_dictionary)
 
def get_link_counts(EmmeProject, loop_id_df, tod):
    """ Collect network total vehicle and loop data for given time-of-day """

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
        x['CountID'] = row[1].CountID
        if link != None:
            x['vol' + tod] = link['@tveh']   
        else:
            x['vol' + tod] = None
        list_model_vols.append(x)

    df =  pd.DataFrame(list_model_vols)
    df.set_index(['CountID'], inplace = True)

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
            if link1!=None and link2!= None:
                vol = link1['@tveh'] + link2['@tveh']
            elif link1 == None and link2 == None:
                vol = 0

            elif link1 != None and link2 == None:
                vol = link1['@tveh'] 

            elif link1 == None and link2 != None:
                vol = link2['@tveh'] 

        elif row['MIN_Oneway'] == 0:
            link1 = network.link(i,j)
            if link1 != None:
                vol = link1['@tveh']
        else:
            link1 = network.link(j,i)
            if link1 != None:
                vol = link1['@tveh']

        #hov
        if row['MIN_HOV_I'] > 0:
            i = row['MIN_HOV_I'] + 4000
            j = row['MIN_HOV_J'] + 4000
            #both directions:
            if row['MIN_Oneway'] == 2:
                link1 = network.link(i,j)
                link2 = network.link(j, i)
                if link1!=None and link2!= None:
                    vol = vol +link1['@tveh'] + link2['@tveh']
                elif link1 == None and link2 == None:
                    vol = vol + 0
                    #print i, j
                elif link1 != None and link2 == None:
                    vol = vol + link1['@tveh'] 
                    #print j, i
                elif link1 == None and link2 != None:
                    vol = vol + link2['@tveh'] 
            #IJ
            elif row['MIN_Oneway'] == 0:
                link1 = network.link(i,j)
                if link1 != None:
                    vol = vol + link1['@tveh']
            #JI
            else:
                link1 = network.link(j,i)
                if link1 != None:
                    vol = vol + link1['@tveh']


        if id in vol_dict.keys():
            vol_dict[id]['EstVol'] = vol_dict[id]['EstVol'] + vol
        else:
            x['ID'] = id
            x['PSRCEdgeID'] = row['PSRCEdgeID']
            x['ObsVol'] = row['MEAN_AADT']
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
            if link1!=None and link2!= None:
                vol = link1['@tveh'] + link2['@tveh']
            elif link1 == None and link2 == None:
                vol = 0
            elif link1 != None and link2 == None:
                vol = link1['@tveh'] 
            elif link1 == None and link2 != None:
                vol = link2['@tveh'] 

        elif row['Oneway'] == 0:
            link1 = network.link(i,j)
            if link1 != None:
                vol = link1['@tveh']
        else:
            link1 = network.link(j,i)
            if link1 != None:
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
        if link.type != 90 and link.type not in unique_screenlines:
            unique_screenlines.append(str(link.type))
    return unique_screenlines

def get_screenline_volumes(screenline_dict, EmmeProject):

    for screen_line in screenline_dict.iterkeys():
        EmmeProject.network_calculator("link_calculation",result=None, expression="@tveh", selections_by_link=screen_line)
        screenline_dict[screen_line] = screenline_dict[screen_line] + EmmeProject.network_calc_result['sum']

def calc_transit_line_atts(EmmeProject):
    """ Calculate boardings and transit line time """

    EmmeProject.transit_line_calculator(result='@board', expression='board')
    EmmeProject.transit_line_calculator(result='@timtr', expression='timtr')

def get_transit_boardings_time(EmmeProject):

    network = EmmeProject.current_scenario.get_network()
    line_list = []
    atts = []
    for transit_line in network.transit_lines():
        x = {}
        atts.append({'id' : transit_line.id, 'route_code' : transit_line.data1, 'mode' : str(transit_line.mode), 'description' : transit_line.description})
        x['id'] = transit_line.id
        x[EmmeProject.tod + '_board'] = transit_line['@board']
        x[EmmeProject.tod + '_time']= transit_line['@timtr']
        line_list.append(x)
    df = pd.DataFrame(line_list)
    df = df.set_index(['id'])

    return [df, atts]

def calc_total_vehicles(my_project):
    """For a given time period, calculate link level volume, store as extra attribute on the link."""

    my_project.network_calculator("link_calculation", result='@mveh', expression='@metrk/1.5') # medium trucks       
    my_project.network_calculator("link_calculation", result='@hveh', expression='@hvtrk/2.0') #heavy trucks     
    my_project.network_calculator("link_calculation", result='@bveh', expression='@trnv3/2.0') # buses
     
    # Calculate total vehicles as @tveh 
    str_expression = '@svtl1 + @svtl2 + @svtl3 + @h2tl1 + @h2tl2 + @h2tl3 + @h3tl1 + @h3tl2 + @h3tl3 + @lttrk + @mveh + @hveh + @bveh'
    my_project.network_calculator("link_calculation", result='@tveh', expression=str_expression)

def get_aadt_trucks(my_project):
    """Calculate link level daily total truck passenger equivalents for medium and heavy, store in a DataFrame."""
    
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
    """ Export daily network volumes and compare to observed."""

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

    else:
        raise Exception('no daily bank found')

def bike_volumes(writer, my_project, tod):
    """Write bike link volumes to file for comparisons to counts """

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
    if os.path.exists(network_summary_dir):
        xl = pd.ExcelFile(network_summary_dir)
        if sheet_name in xl.sheet_names:
            """append column to existing TOD results"""
            df = pd.read_excel(io=xl, sheetname=sheet_name)
            df['bvol'+tod] = df_count['bvol'+tod]
            df.to_excel(excel_writer=writer, sheet_name=sheet_name) 
        else:
            df_count.to_excel(excel_writer=writer, sheet_name=sheet_name)

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

def freeflow_skims(my_project):
    """ Attach "freeflow" (20to5) SOV skims to daysim_outputs """

    # Load daysim_outputs as dataframe
    daysim = h5py.File('outputs/daysim/daysim_outputs.h5', 'r+')
    df = pd.DataFrame()
    for field in ['travtime','otaz','dtaz']:
        df[field] = daysim['Trip'][field][:]
    df['od']=df['otaz'].astype('str')+'-'+df['dtaz'].astype('str')

    # Look up zone ID from index location
    zones = my_project.current_scenario.zone_numbers
    dictZoneLookup = dict((index,value) for index,value in enumerate(zones))

    skim_vals = h5py.File(r'inputs/model/roster/20to5.h5')['Skims']['svtl3t'][:]

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

    # Write to TSV files
    trip_df = pd.read_csv(r'outputs/daysim/_trip.tsv', delim_whitespace=True)
    trip_df['od'] = trip_df['otaz'].astype('str')+'-'+trip_df['dtaz'].astype('str')
    skim_df['sov_ff_time'] = skim_df['ff_travtime']
    # Delete sov_ff_time if it already exists
    if 'sov_ff_time' in trip_df.columns:
        trip_df.drop('sov_ff_time', axis=1, inplace=True)
    trip_df = pd.merge(trip_df, skim_df[['od','sov_ff_time']], on='od', how='left')
    trip_df.to_csv(r'outputs/daysim/_trip.tsv', sep='\t', index=False)

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
    """
    Converts the passed in coordinates from their native projection (default is state plane WA North-EPSG:2926)
    to wgs84. Returns a two item tuple containing the longitude (x) and latitude (y) in wgs84. Coordinates
    must be in meters hence the default conversion factor- PSRC's are in state plane feet.  
    """
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
    """ Loop through network components and export shape as points """

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

def export_network_attributes(network, tod_hour, filepath):
    """ Calculate link-level results by time-of-day, append to csv """

    network_data = {k: [] for k in ['auto_volume','data2','data3','data1',
                                    'num_lanes','length','auto_time','@metrk','@hvtrk','@tveh','@svtl1','@svtl2',
                                    '@svtl3','@h2tl1','@h2tl2','@h2tl3','@h3tl1','@h3tl2','@h3tl3','@bvol',
                                    '@lttrk','@mveh','@hveh','@bveh','type','num_lanes','volume_delay_func']}

    network_nodes = {k: [] for k in ['i','j']}

    i_list = []
    j_list = []

    for link in network.links():
        for colname, array in network_data.iteritems():
            try:
                network_data[colname].append(link[colname])  
            except:
                network_data[colname].append(0)

        i_list.append(link.i_node)
        j_list.append(link.j_node)

    df = pd.DataFrame.from_dict(network_data)
    df['i'] = i_list
    df['j'] = j_list
    df['ij'] = df['i'].astype('str') + '-' + df['j'].astype('str')
    df['tod'] = tod_hour  

    # Append hourly results to output file
    if os.path.exists(filepath):
        df.to_csv(filepath, mode='a', index=False, header=False)
    else:
        df.to_csv(filepath, index=False)

def sort_df(df, sort_list, sort_column):
    """ Sort a dataframe based on user-defined list of indices """

    df[sort_column] = df[sort_column].astype('category')
    df[sort_column].cat.set_categories(sort_list, inplace=True)
    df = df.sort_values(sort_column)

    return df

def summarize_network(filepath, excel_writer):
    """ Calculate VMT, VHT, and Delay from link-level results """

    df = pd.read_csv(filepath)

    # Exclude trips taken on non-designated facilities (facility_type == 0)
    # These are artificial (weave lanes to connect HOV) or for non-auto uses 
    df = df[df['data3'] != 0]    # data3 represents facility_type

    # calculate total link VMT and VHT
    df['VMT'] = df['@tveh']*df['length']
    df['VHT'] = df['@tveh']*df['auto_time']/60

    # Define facility type
    df.loc[df['data3'].isin([1,2]), 'facility_type'] = 'highway'
    df.loc[df['data3'].isin([3,4,6]), 'facility_type'] = 'arterial'
    df.loc[df['data3'].isin([5]), 'facility_type'] = 'connector'

    # Calculate delay
    df['freeflow_time'] = (60*df['length'])/df['data2']    # data2 represents link speed limit
    df['delay'] = ((df['auto_time']-df['freeflow_time'])*df['@tveh'])/60    # sum of (volume)*(travtime diff from freeflow)

    # Add time-of-day group (AM, PM, etc.)
    tod_df = pd.read_json(r'inputs/model/skim_parameters/time_of_day_crosswalk_ab_4k_dictionary.json', orient='index')
    tod_df = tod_df[['TripBasedTime']].reset_index()
    tod_df.columns = ['tod','period']
    df = pd.merge(df,tod_df,on='tod',how='left')

    sort_list = tods    # list of ordered time periods defined in emme_configuration.py

    # Totals by functional classification
    for metric in ['VMT','VHT','delay']:
        _df = pd.pivot_table(df, values=metric, index=['tod','period'],columns='facility_type', aggfunc='sum').reset_index()
        _df = sort_df(df=_df, sort_list=sort_list, sort_column='tod')
        _df = _df.reset_index(drop=True)
        _df.to_excel(excel_writer=excel_writer, sheet_name=metric+' by FC')

    # Totals by user classification
    
    # VMT
    _df = df.copy()
    for uc in uc_list:
        _df[uc] = df[uc]*df['length']
    _df = _df[uc_list+['tod']].groupby('tod').sum().reset_index()
    _df = sort_df(df=_df, sort_list=sort_list, sort_column='tod')
    _df.to_excel(excel_writer=excel_writer, sheet_name="VMT by UC")

    # VHT
    _df = df.copy()
    for uc in uc_list:
        _df[uc] = df[uc]*df['auto_time']/60
    _df = _df[uc_list+['tod']].groupby('tod').sum().reset_index()
    _df = sort_df(df=_df, sort_list=sort_list, sort_column='tod')
    _df = _df.reset_index(drop=True)
    _df.to_excel(excel_writer=excel_writer, sheet_name="VHT by UC")

    # Delay
    _df = df.copy()
    for uc in uc_list:
        _df[uc] = ((_df['auto_time']-_df['freeflow_time'])*_df[uc])/60
    _df = _df[uc_list+['tod']].groupby('tod').sum().reset_index()
    _df = sort_df(df=_df, sort_list=sort_list, sort_column='tod')
    _df = _df.reset_index(drop=True)
    _df.to_excel(excel_writer=excel_writer, sheet_name="Delay by UC")

    # Summarize by county
    try:
        county_df = pd.read_csv(r'inputs/scenario/networks/county_flag_' + model_year + '.csv')
        df = pd.merge(df,county_df,how='left',left_on='ij',right_on='ID')
        for metric in ['VMT','VHT','delay']:
            _df = df.groupby('NAME').sum()[[metric]]
            _df.to_excel(excel_writer=excel_writer, sheet_name=metric+' by County')
    except:
        OSError('county flag unavailable')

def transit_summary(project, seg_df, transit_summary_dict, transit_atts, stop_df):
    """ For each time period and transit line, calculate total boarding and alighting"""

    for name, desc in transit_extra_attributes_dict.iteritems():
        project.create_extra_attribute('TRANSIT_LINE', name, desc, 'True')
        calc_transit_line_atts(project)
        transit_results = get_transit_boardings_time(project)
        transit_summary_dict[project.tod] = transit_results[0]
        transit_atts.extend(transit_results[1])

        network = project.current_scenario.get_network()
        ons = {}
        offs = {}
        
        for node in network.nodes():
            ons[int(node.id)] = node.initial_boardings
            offs[int(node.id)] = node.final_alightings
        
        df = pd.DataFrame() # temp dataFrame to append to stop_df
        df['inode'] = ons.keys()
        df['initial_boardings'] = ons.values()
        df['final_alightings'] = offs.values()
        df['tod'] = project.tod

        stop_df = stop_df.append(df)

        boardings = []
        line = []
        inode = []

        for tseg in network.transit_segments():
            boardings.append(tseg.transit_boardings)
            line.append(tseg.line.id)
            inode.append(tseg.i_node.number)
        
        df = pd.DataFrame([inode,boardings,line]).T
        df.columns = ['inode','total_boardings','line']
        df['tod'] = project.tod           
        seg_df = seg_df.append(df)

        return stop_df, seg_df

def export_transit_summary(transit_summary_dict, transit_atts, writer):
    """ Write transit boardings and travel times to Excel. """

    transit_df = pd.DataFrame()

    for tod, df in transit_summary_dict.iteritems():
       workbook = writer.book
       index_format = workbook.add_format({'align': 'left', 'bold': True, 'border': True})
       transit_df = pd.merge(transit_df, df, 'outer', left_index = True, right_index = True)

    transit_df = transit_df[['5to6_board', '5to6_time', '6to7_board', '6to7_time', '7to8_board', '7to8_time', '8to9_board', '8to9_time', '9to10_board', \
        '9to10_time', '10to14_board', '10to14_time', '14to15_board', '14to15_time', '15to16_board', '15to16_time', '16to17_board', '16to17_time', \
        '17to18_board', '17to18_time', '18to20_board', '18to20_time']]
    transit_atts_df = pd.DataFrame(transit_atts)
    transit_atts_df = transit_atts_df.drop_duplicates(['id'], keep='last')
    transit_df.reset_index(level=0, inplace=True)
    transit_atts_df = transit_atts_df.merge(transit_df, 'inner', right_on=['id'], left_on=['id'])
    transit_atts_df.to_excel(excel_writer=writer, sheet_name='Transit Line Activity')

def transfers(seg_df, stop_df, writer):
    """ Summarize stop-level transit results. """

    seg_df = seg_df.groupby('inode').sum().reset_index()
    seg_df = seg_df.drop(['tod','line'], axis=1)
    stop_df = stop_df.groupby('inode').sum().reset_index()
    transfer_df = pd.merge(stop_df, seg_df, on='inode')
    transfer_df['transfers'] = transfer_df['total_boardings'] - transfer_df['initial_boardings']
    transfer_df.to_excel(excel_writer=writer, sheet_name='Transit Stop Activity')

    return transfer_df

def write_topsheet(sheet):
    """ Write jupyter notebook to HTML as topsheet """

    with open("scripts/summarize/notebooks/"+sheet+".ipynb") as f:
        nb = nbformat.read(f, as_version=4)
        ep = ExecutePreprocessor(timeout=600, kernel_name='python2')
        ep.preprocess(nb, {'metadata': {'path': 'scripts/summarize/notebooks/'}})
        with open('scripts/summarize/notebooks/'+sheet+'.ipynb', 'wt') as f:
            nbformat.write(nb, f)
        os.system("jupyter nbconvert --to HTML scripts/summarize/notebooks/"+sheet+".ipynb")
        # Move these files to output
        if os.path.exists(r"outputs/"+sheet+".html"):
            os.remove(r"outputs/"+sheet+".html")
        os.rename(r"scripts/summarize/notebooks/"+sheet+".html", r"outputs/"+sheet+".html")

def main():

    # Initialize output dictionaries
    transit_summary_dict = {}
    counts_dict = {}
    aadt_counts_dict = {}
    tptt_counts_dict = {}
    transit_atts = []

    # Access global Emme project with all time-of-day banks available
    my_project = EmmeProject(project)

    # Create engines for writing Excel outputs, for network summary and count comparisons
    network_writer = pd.ExcelWriter(network_summary_dir, engine='xlsxwriter')    
    validation_writer = pd.ExcelWriter(validation_summary_dir, engine='xlsxwriter')
    transit_writer = pd.ExcelWriter(transit_summary_dir, engine='xlsxwriter')    
       
    # Import observed count data
    loop_ids = pd.read_csv(r'inputs/scenario/networks/count_ids.txt', sep=' ', header=None, names=['NewINode', 'NewJNode','CountID'])
    loop_counts = pd.read_csv(r'inputs/base_year/loop_counts_2014.csv')
    loop_counts.set_index(['CountID_Type'], inplace=True)
    df_counts = pd.read_csv(counts_file, index_col=['loop_INode', 'loop_JNode'])
    df_aadt_counts = pd.read_csv(aadt_counts_file)
    df_tptt_counts = pd.read_csv(tptt_counts_file)
    df_truck_counts = pd.read_csv(truck_counts_file)

    # Store stop- and segment-level transit boarding
    stop_df = pd.DataFrame()
    seg_df = pd.DataFrame()
    
    # get a list of screenlines from the bank/scenario
    screenline_list = get_unique_screenlines(my_project) 
    screenline_dict = {}

    for item in screenline_list:
        #dict where key is screen line id and value is 0
        screenline_dict[item] = 0

    # Initialize link-level network results
    network_results_path = r'outputs/network/network_results.csv'
    if os.path.exists(network_results_path):
        os.remove(network_results_path)

    # Loop through all TOD banks to get network summaries
    for tod_hour, tod_segment in sound_cast_net_dict.iteritems():
        my_project.change_active_database(tod_hour)
        for name, desc in extra_attributes_dict.iteritems():
            my_project.create_extra_attribute('LINK', name, desc, 'True')

        # Add total vehicle sum for each link (@tveh)
        calc_total_vehicles(my_project)

        network = my_project.current_scenario.get_network()

        # Calculate link-level results
        export_network_attributes(network, tod_hour, network_results_path)

        # Calculate transit results for time periods with transit assignment:
        if my_project.tod in transit_tod.keys():
            stop_df, seg_df = transit_summary(project=my_project, seg_df=seg_df, 
                transit_summary_dict=transit_summary_dict, transit_atts=transit_atts,
                stop_df=stop_df)
        
        # Calculate volumes to compare to observed counts
        df_tod_vol = get_link_counts(my_project, loop_ids, tod_hour)
        counts_dict[tod_hour] = df_tod_vol
        
        # AADT Counts
        get_aadt_volumes(my_project, df_aadt_counts, aadt_counts_dict)
        
        # TPTT
        get_tptt_volumes(my_project, df_tptt_counts, tptt_counts_dict)
        
        # Screenlines
        get_screenline_volumes(screenline_dict, my_project)

        # Bike volumes
        if tod_hour in transit_skim_tod:  # Bikes only assigned where transit network available
            try:
                bike_volumes(writer=validation_writer, my_project=my_project, tod=tod_hour)
            except:
                print 'bike volumes not written for: ' + str(tod_hour)

    # Export high-level network summaries by time of day to Excel 
    summarize_network(filepath=network_results_path, excel_writer=network_writer)

    # Write transit transfer results to Excel
    transfer_df = transfers(seg_df=seg_df, stop_df=stop_df, writer=transit_writer)

    # Daily boardings for light rail
    light_rail(df=transfer_df, writer=transit_writer)

    # Write transit results
    export_transit_summary(transit_summary_dict, transit_atts, writer=transit_writer)

    # Write count data to Excel
    for value in counts_dict.itervalues():
        loop_counts = loop_counts.merge(value, left_index=True, right_index=True)
    loop_counts.to_excel(excel_writer=validation_writer, sheet_name='Loop Counts')
    
    # AADT
    df = pd.DataFrame.from_dict(aadt_counts_dict, orient="index")
    df.to_excel(excel_writer=validation_writer, sheet_name='Arterial Counts Output')

    # TPTT
    df = pd.DataFrame.from_dict(tptt_counts_dict, orient="index")
    df.to_excel(excel_writer=validation_writer, sheet_name='TPTT Counts Output')   

    # Screenlines
    df = pd.DataFrame.from_dict(screenline_dict, orient='index').reset_index()
    df.columns = ['Screenline','Volumes']
    df.to_excel(excel_writer=network_writer, sheet_name='Screenline Volumes')

    # Export a shapefile of the AM network
    export_network_shape('7to8')

    # Export daily counts
    daily_counts(validation_writer, my_project)

    # Write freeflow skims to Daysim trip records to calculate individual-level delay
    freeflow_skims(my_project)

    # Export number of jobs near transit stops
    jobs_transit(transit_writer)

    if run_truck_summary:
        truck_summary(df_counts=df_truck_counts, my_project=my_project, writer=validation_writer)

    # Finalize Excel output
    network_writer.save()
    validation_writer.save()
    transit_writer.save()

    # Write notebooks based on these outputs to HTML

    for sheet in ['topsheet','metrics']:
        write_topsheet(sheet)

if __name__ == "__main__":
    main()