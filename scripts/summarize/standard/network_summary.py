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

import os, sys, shutil
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
from sqlalchemy import create_engine
from nbconvert.preprocessors import ExecutePreprocessor
from EmmeProject import *
from standard_summary_configuration import *
from input_configuration import *
from emme_configuration import *
pd.options.mode.chained_assignment = None  # mute chained assignment warnings

def json_to_dictionary(dict_name):
    """ Read skim parameter JSON inputs as dictionary """

    skim_params_loc = os.path.abspath(os.path.join(os.getcwd(),"inputs/model/skim_parameters/transit")) 
    input_filename = os.path.join(skim_params_loc,dict_name+'.json').replace("\\","/")
    my_dictionary = json.load(open(input_filename))

    return(my_dictionary)
 
def get_intrazonal_vol(emmeproject, df_vol):
    """Calculate intrazonal volumes for all modes"""

    iz_uc_list = ['sov_inc','hov2_inc','hov3_inc']
    if include_av:
        iz_uc_list += 'av_sov_inc','av_hov2_inc','av_hov3_inc'
    iz_uc_list = [uc+str(1+i) for i in xrange(3) for uc in iz_uc_list]
    if include_tnc:
        iz_uc_list += ['tnc_inc1','tnc_inc2','tnc_inc3']
    iz_uc_list += ['medium_truck','heavy_truck']

    for uc in iz_uc_list:
        df_vol[uc+'_'+emmeproject.tod] = emmeproject.bank.matrix(uc).get_numpy_data().diagonal()

    return df_vol

def calc_total_vehicles(my_project):
    """For a given time period, calculate link level volume, store as extra attribute on the link."""

    my_project.network_calculator("link_calculation", result='@mveh', expression='@medium_truck/1.5') # medium trucks       
    my_project.network_calculator("link_calculation", result='@hveh', expression='@heavy_truck/2.0') #heavy trucks     
    my_project.network_calculator("link_calculation", result='@bveh', expression='@trnv3/2.0') # buses
     
    # Calculate total vehicles as @tveh, depending on which modes are included
    str_base = '@sov_inc1 + @sov_inc2 + @sov_inc3 + @hov2_inc1 + @hov2_inc2 + @hov2_inc3 + ' + \
                      '@hov3_inc1 + @hov3_inc2 + @hov3_inc3 + @mveh + @hveh + @bveh '
    av_str = '+ @av_sov_inc1 + @av_sov_inc2 + @av_sov_inc3 + @av_hov2_inc1 + @av_hov2_inc2 + @av_hov2_inc3 + ' + \
                      '@av_hov3_inc1 + @av_hov3_inc2 + @av_hov3_inc3 '
    tnc_str = '+ @tnc_inc1 + @tnc_inc2 + @tnc_inc3 '

    str_expression = str_base
    if include_av:
        str_expression += av_str
    if include_tnc:
        str_expression += tnc_str

    my_project.network_calculator("link_calculation", result='@tveh', expression=str_expression)
    
def freeflow_skims(my_project, dictZoneLookup):
    """ Attach "freeflow" (20to5) SOV skims to daysim_outputs """

    # Load daysim_outputs as dataframe
    daysim = h5py.File('outputs/daysim/daysim_outputs.h5', 'r+')
    df = pd.DataFrame()
    for field in ['travtime','otaz','dtaz']:
        df[field] = daysim['Trip'][field][:]
    df['od']=df['otaz'].astype('str')+'-'+df['dtaz'].astype('str')

    skim_vals = h5py.File(r'inputs/model/roster/20to5.h5')['Skims']['sov_inc3t'][:]

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

def jobs_transit(output_path):
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

    df.to_csv(output_path)

def export_network_attributes(network):
    """ Calculate link-level results by time-of-day, append to csv """

    _attribute_list = network.attributes('LINK')  

    network_data = {k: [] for k in _attribute_list}
    i_node_list = []
    j_node_list = []
    network_data['modes'] = []
    for link in network.links():
        for colname, array in network_data.iteritems():
            if colname != 'modes':
                try:
                    network_data[colname].append(link[colname])  
                except:
                    network_data[colname].append(0)
        i_node_list.append(link.i_node.id)
        j_node_list.append(link.j_node.id)
        network_data['modes'].append(link.modes)

    network_data['i_node'] = i_node_list
    network_data['j_node'] = j_node_list
    df = pd.DataFrame.from_dict(network_data)
    df['modes'] = df['modes'].apply(lambda x: ''.join(list([j.id for j in x])))    
    df['modes'] = df['modes'].astype('str').fillna('')
    df['ij'] = df['i_node'].astype('str') + '-' + df['j_node'].astype('str')
   
    return df
    
def sort_df(df, sort_list, sort_column):
    """ Sort a dataframe based on user-defined list of indices """

    df[sort_column] = df[sort_column].astype('category')
    df[sort_column].cat.set_categories(sort_list, inplace=True)
    df = df.sort_values(sort_column)

    return df

def summarize_network(df, writer):
    """ Calculate VMT, VHT, and Delay from link-level results """

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
    # Select links from overnight time of day
    delay_df = df.loc[df['tod'] == '20to5'][['ij','auto_time']]
    delay_df.rename(columns={'auto_time':'freeflow_time'}, inplace=True)

    # Merge delay field back onto network link df
    df = pd.merge(df, delay_df, on='ij', how='left')

    # Calcualte hourly delay
    df['delay'] = ((df['auto_time']-df['freeflow_time'])*df['@tveh'])/60    # sum of (volume)*(travtime diff from freeflow)

    # Add time-of-day group (AM, PM, etc.)
    tod_df = pd.read_json(r'inputs/model/skim_parameters/lookup/time_of_day_crosswalk_ab_4k_dictionary.json', orient='index')
    tod_df = tod_df[['TripBasedTime']].reset_index()
    tod_df.columns = ['tod','period']
    df = pd.merge(df,tod_df,on='tod',how='left')

    # Totals by functional classification
    for metric in ['VMT','VHT','delay']:
        _df = pd.pivot_table(df, values=metric, index=['tod','period'],columns='facility_type', aggfunc='sum').reset_index()
        _df = sort_df(df=_df, sort_list=tods , sort_column='tod')
        _df = _df.reset_index(drop=True)
        _df.to_excel(excel_writer=writer, sheet_name=metric+' by FC')
        _df.to_csv(r'outputs/network/' + metric.lower() +'_facility.csv', index=False)

    # Totals by user classification

    # Update uc_list based on inclusion of TNC and AVs
    new_uc_list = []

    if (not include_tnc) & (not include_av):
        for uc in uc_list:
            if ('@tnc' not in uc) & ('@av' not in uc):
                new_uc_list.append(uc)
                
    if (include_tnc) & (not include_av):
        for uc in uc_list:
            if '@av' not in uc:
                new_uc_list.append(uc)
                
    if (not include_tnc) & (include_av):
        for uc in uc_list:
            if '@tnc' not in uc:
                new_uc_list.append(uc)
                

    # VMT
    _df = df.copy()
    for uc in new_uc_list:
        _df[uc] = df[uc]*df['length']
    _df = _df[new_uc_list+['tod']].groupby('tod').sum().reset_index()
    _df = sort_df(df=_df, sort_list=tods, sort_column='tod')
    _df.to_excel(excel_writer=writer, sheet_name="VMT by UC")
    _df.to_csv(r'outputs/network/vmt_user_class.csv', index=False)

    # VHT
    _df = df.copy()
    for uc in new_uc_list:
        _df[uc] = df[uc]*df['auto_time']/60
    _df = _df[new_uc_list+['tod']].groupby('tod').sum().reset_index()
    _df = sort_df(df=_df, sort_list=tods, sort_column='tod')
    _df = _df.reset_index(drop=True)
    _df.to_excel(excel_writer=writer, sheet_name="VHT by UC")
    _df.to_csv(r'outputs/network/vht_user_class.csv', index=False)

    # Delay
    _df = df.copy()
    for uc in new_uc_list:
        _df[uc] = ((_df['auto_time']-_df['freeflow_time'])*_df[uc])/60
    _df = _df[new_uc_list+['tod']].groupby('tod').sum().reset_index()
    _df = sort_df(df=_df, sort_list=tods, sort_column='tod')
    _df = _df.reset_index(drop=True)
    _df.to_excel(excel_writer=writer, sheet_name="Delay by UC")
    _df.to_csv(r'outputs/network/delay_user_class.csv', index=False)

    # Results by County
    
    df['county_name'] = df['@countyid'].map(county_map)
    _df = df.groupby('county_name').sum()[['VMT','VHT','delay']].reset_index()
    _df.to_excel(excel_writer=writer, sheet_name='County Results')
    _df.to_csv(r'outputs/network/county_network.csv', index=False)

    writer.save()

def transit_summary(emme_project, df_transit_line, df_transit_node, df_transit_segment):
    """Export transit line, segment, and mode attributes"""

    network = emme_project.current_scenario.get_network()
    tod = emme_project.tod

    # Extract Transit Line Data
    transit_line_data = []
    for line in network.transit_lines():
        transit_line_data.append({'line_id': line.id, 
                                  'route_code': line.data1,
                                  'agency_code': line.data3,
                                  'mode': str(line.mode),
                                  'description': line.description,
                                  'boardings': line['@board'], 
                                  'time': line['@timtr']})
    _df_transit_line = pd.DataFrame(transit_line_data)
    _df_transit_line['tod'] = tod
   
    # Extract Transit Node Data
    transit_node_data = []
    for node in network.nodes():
        transit_node_data.append({'node_id': int(node.id), 
                                  'initial_boardings': node.initial_boardings,
                                  'final_alightings': node.final_alightings})

    _df_transit_node = pd.DataFrame(transit_node_data)
    _df_transit_node['tod'] = tod
    
    # Extract Transit Segment Data
    transit_segment_data = []
    for tseg in network.transit_segments():
        transit_segment_data.append({'line_id': tseg.line.id, 
                                  'segment_boarding': tseg.transit_boardings, 
                                  'i_node': tseg.i_node.number})
    
    _df_transit_segment = pd.DataFrame(transit_segment_data)
    _df_transit_segment['tod'] = tod

    return _df_transit_line, _df_transit_node, _df_transit_segment

def summarize_transit_detail(df_transit_line, df_transit_node, df_transit_segment, conn):
    """Sumarize various transit measures."""

    df_transit_line['agency_code'] = df_transit_line['agency_code'].astype('int')
    df_transit_line['route_code'] = df_transit_line['route_code'].astype('int')

    # Boardings by agency
    df_transit_line['agency_name'] = df_transit_line['agency_code'].map(agency_lookup)
    df_daily = df_transit_line.groupby('agency_name').sum()[['boardings']].reset_index().sort_values('boardings', ascending=False)
    df_daily.to_csv(boardings_by_agency_path, index=False)

    # Boardings for special routes
    df_special = df_transit_line[df_transit_line['route_code'].isin(special_route_lookup.keys())].groupby('route_code').sum()[['boardings']].sort_values('boardings', ascending=False)
    df_special = df_special.reset_index()
    df_special['description'] = df_special['route_code'].map(special_route_lookup)
    df_special[['route_code','description','boardings']].to_csv(special_routes_path, index=False)

    # Boardings by Time of Day
    df_tod_agency  = df_transit_line.pivot_table(columns='tod',index='agency_name',values='boardings',aggfunc='sum')
    df_tod_agency = df_tod_agency[transit_tod_list]
    df_tod_agency = df_tod_agency.sort_values('7to8', ascending=False).reset_index()
    df_tod_agency.to_csv(boardings_by_tod_agency_path, index=False)

    # Daily Boardings by Stop
    df_transit_segment = pd.read_csv(r'outputs\transit\transit_segment_results.csv')
    df_transit_node = pd.read_csv(r'outputs\transit\transit_node_results.csv')
    df_transit_segment = df_transit_segment.groupby('i_node').sum().reset_index()
    df_transit_node = df_transit_node.groupby('node_id').sum().reset_index()
    df = pd.merge(df_transit_node, df_transit_segment, left_on='node_id', right_on='i_node')
    df.rename(columns={'segment_boarding': 'total_boardings'}, inplace=True)
    df['transfers'] = df['total_boardings'] - df['initial_boardings']
    df.to_csv(boardings_by_stop_path)

    # Light rail station boardings
    df = pd.read_csv(boardings_by_stop_path)
    df_obs = pd.read_sql("SELECT * FROM light_rail_station_boardings", con=conn)
    df_obs['year'] = df_obs['year'].fillna(0).astype('int')
    df_obs = df_obs[(df_obs['year'] == int(base_year)) | (df_obs['year'] == 0)]

    # Translate daily boardings to 5 to 20
    df_line_obs = pd.read_sql("SELECT * FROM observed_transit_boardings WHERE year=" + str(base_year), con=conn)
    df_line_obs['route_id'] = df_line_obs['route_id'].astype('int')
    light_rail_list = [6996]
    daily_factor = df_line_obs[df_line_obs['route_id'].isin(light_rail_list)]['daily_factor'].values[0]
    df_obs['observed_5to20'] = df_obs['boardings']/daily_factor

    df = df[df['i_node'].isin(df_obs['emme_node'])]
    df = df.merge(df_obs, left_on='i_node', right_on='emme_node')
    df.rename(columns={'total_boardings':'modeled_5to20'},inplace=True)

    df['modeled_5to20'] = df['modeled_5to20'].astype('float')
    df.index = df['station_name']
    df_total = df.copy()[['observed_5to20','modeled_5to20']]
    df_total.ix['Total',['observed_5to20','modeled_5to20']] = df[['observed_5to20','modeled_5to20']].sum().values
    df_total.to_csv(light_rail_boardings_path)


def main():

    conn = create_engine('sqlite:///inputs/db/soundcast_inputs.db')

    # Delete any existing files
    for _path in [transit_line_path,transit_node_path,transit_segment_path,network_results_path]:
        if os.path.exists(_path ):
            os.remove(_path )

    ## Access Emme project with all time-of-day banks available
    my_project = EmmeProject(network_summary_project)
    network = my_project.current_scenario.get_network()
    zones = my_project.current_scenario.zone_numbers
    dictZoneLookup = dict((index,value) for index,value in enumerate(zones))

        # Initialize result dataframes
    df_transit_line = pd.DataFrame()
    df_transit_node = pd.DataFrame()
    df_transit_segment = pd.DataFrame()
    network_df = pd.DataFrame()
    df_iz_vol = pd.DataFrame()
    df_iz_vol['taz'] = dictZoneLookup.values()
    


    dir = r'outputs/transit/line_od'
    if os.path.exists(dir):
        shutil.rmtree(dir)
    os.makedirs(dir)
    
    transit_line_od_period_list = ['7to8']

    # Loop through all Time-of-Day banks to get network summaries
    # Initialize extra network and transit attributes
    for tod_hour, tod_segment in sound_cast_net_dict.iteritems():
        print('processing network summary for time period: ' + str(tod_hour))
        my_project.change_active_database(tod_hour)
        
        for name, description in extra_attributes_dict.iteritems():
            my_project.create_extra_attribute('LINK', name, description, 'True')
        # Calculate transit results for time periods with transit assignment:
        if my_project.tod in transit_tod.keys():
            for name, desc in transit_extra_attributes_dict.iteritems():
                my_project.create_extra_attribute('TRANSIT_LINE', name, desc, 'True')
                my_project.transit_line_calculator(result=name, expression=name[1:])
            _df_transit_line, _df_transit_node, _df_transit_segment = transit_summary(emme_project=my_project, 
                                                                                    df_transit_line=df_transit_line,
                                                                                    df_transit_node=df_transit_node, 
                                                                                    df_transit_segment=df_transit_segment)
            df_transit_line = df_transit_line.append(_df_transit_line)
            df_transit_node = df_transit_node.append(_df_transit_node)
            df_transit_segment = df_transit_segment.append(_df_transit_segment)
        
            # Calculate transit line OD table for select lines
            if tod_hour in transit_line_od_period_list:         
                for line_id, name in transit_line_dict.items():
                    # Calculate results for all path types
                    for class_name in ['trnst','commuter_rail','ferry','litrat','passenger_ferry']:
                        for matrix in my_project.bank.matrices():
                            if matrix.name == 'eline':
                                my_project.delete_matrix(matrix)
                                my_project.delete_extra_attribute('@eline')
                        my_project.create_extra_attribute('TRANSIT_LINE', '@eline', name, 'True')
                        my_project.create_matrix('eline', 'Demand from select transit line', "FULL")

                        # Add an identifier to the chosen line
                        my_project.network_calculator("link_calculation", result='@eline', expression='1',
                                                      selections={'transit_line': str(line_id)})

                        # Transit path analysis
                        transit_path_analysis = my_project.m.tool('inro.emme.transit_assignment.extended.path_based_analysis')
                        _spec = json_to_dictionary("transit_path_analysis")
                        transit_path_analysis(_spec, class_name=class_name)
                        
                        # Write this path OD table to sparse CSV
                        my_project.export_matrix('mfeline', 'outputs/transit/line_od/'+str(line_id)+'_'+class_name+'.csv')

        # Add total vehicle sum for each link (@tveh)
        calc_total_vehicles(my_project)

        # Calculate intrazonal VMT
        _df_iz_vol = pd.DataFrame(my_project.bank.matrix('izdist').get_numpy_data().diagonal(),columns=['izdist'])
        _df_iz_vol['taz'] = dictZoneLookup.values()
        _df_iz_vol = get_intrazonal_vol(my_project, _df_iz_vol)
        if 'izdist' in df_iz_vol.columns:
            _df_iz_vol = _df_iz_vol.drop('izdist', axis=1)
        df_iz_vol = df_iz_vol.merge(_df_iz_vol, on='taz', how='left')

        # Export link-level results for multiple attributes
        network = my_project.current_scenario.get_network()
        _network_df = export_network_attributes(network)
        _network_df['tod'] = my_project.tod
        network_df = network_df.append(_network_df)




    output_dict = {network_results_path: network_df, iz_vol_path: df_iz_vol,
                    transit_line_path: df_transit_line,
                    transit_node_path: df_transit_node,
                    transit_segment_path: df_transit_segment}

    # Append hourly results to file output
    for filepath, df in output_dict.iteritems():
       df.to_csv(filepath, index=False)

    ## Write freeflow skims to Daysim trip records to calculate individual-level delay
    freeflow_skims(my_project, dictZoneLookup)

    # Export number of jobs near transit stops
    jobs_transit('outputs/transit/transit_access.csv')

    # Create basic spreadsheet summary of network
    writer = pd.ExcelWriter(r'outputs/network/network_summary.xlsx', engine='xlsxwriter')
    summarize_network(network_df, writer)

    # Create detailed transit summaries
    summarize_transit_detail(df_transit_line, df_transit_node, df_transit_segment, conn)

if __name__ == "__main__":
    main()