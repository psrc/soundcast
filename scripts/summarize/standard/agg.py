import numpy as np
import pandas as pd
import h5py
import os, sys, shutil
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(CURRENT_DIR))
sys.path.append(os.path.join(os.getcwd(),"inputs"))
sys.path.append(os.path.join(os.getcwd(),"scripts"))
sys.path.append(os.getcwd())
import re
import math
from collections import OrderedDict
from input_configuration import base_year
import time

# Define relationships between daysim files
daysim_merge_fields = {'Trip': 
                            {'Tour': ['hhno','pno','tour'],
                            'Person': ['hhno','pno'],
                            'Household': ['hhno']},
                        'Person':
                            {'Household': ['hhno']},
                        'Tour':
                            {'Person': ['hhno','pno'],
                            'Household': ['hhno']
                            }
                        }


dash_table_list = ['vmt_facility','vht_facility','delay_facility','vmt_user_class','vht_user_class','delay_user_class']

def get_dict_values(d):
    """Return unique dictionary values for a 2-level dictionary"""

    _list = []
    for k, v in d.iteritems():
        if isinstance(v, dict):
            for _k, _v in v.iteritems():
                _list += _v
        else:
            _list += v
        _list = list(np.unique(_list))

    return(_list)

def create_dir(_dir):
    if os.path.exists(_dir):
        shutil.rmtree(_dir)
    os.makedirs(_dir)

def get_row_col_list(row, full_col_list):
    row_list = ['agg_fields','values']
    for field_type in ['filter_fields']:
        if type(row[field_type]) != np.float:
            row_list += [field_type]
    col_list = list(row[row_list].values)
    col_list = [i.split(',') for i in col_list]
    col_list = list(np.unique([item.strip(' ') for sublist in col_list for item in sublist]))

    # Identify column values from query field with regular expressions
    if type(row['query']) != np.float:
        # query_fields_cols = [i.strip() for i in re.split(',|>|==|>=|<|<=|!=|&',row['query'])]
        regex = re.compile('[^a-zA-Z]')
        query_fields_cols = [regex.sub('', i).strip() for i in re.split(',|>|==|>=|<|<=|!=|&',row['query'])]
        for query in query_fields_cols:
            if query in full_col_list and query not in col_list:
                col_list += [query]

    return col_list

def merge_geography(df, df_geog, parcel_geog):
    for _index, _row in df_geog.iterrows():
        right_df = pd.eval(_row['right_table'] + "[" + str(list(_row[['right_index','right_column']].values)) + "]", engine='python')
        df = df.merge(right_df, left_on=_row['left_index'], right_on=_row['right_index'], how='left')
        df.rename(columns={_row['right_column']: _row['right_column_rename']}, inplace=True)
        df.drop(_row['right_index'], axis=1, inplace=True)
    
    return df

def execute_eval(df, row, col_list, fname):

    # Process query field
    query = ''
    if type(row['query']) != np.float:
        query = """.query('"""+ str(row['query']) + """')"""

    agg_fields_cols = [i.strip() for i in row['agg_fields'].split(',')]
    values_cols = [i.strip() for i in row['values'].split(',')]

    if type(row['filter_fields']) == np.float:
        expr = 'df' + str(col_list) + query + ".groupby(" + str(agg_fields_cols) + ")." + row['aggfunc'] + "()[" + str(values_cols) + "]"

        # Write results to target output    
        df_out = pd.eval(expr, engine='python').reset_index()
        _labels_df = labels_df[labels_df['field'].isin(df_out.columns)]
        for field in _labels_df['field'].unique():
            _df = _labels_df[_labels_df['field'] == field]
            local_series = pd.Series(_df['text'].values, index=_df['value'])
            df_out[field] = df_out[field].map(local_series)

        df_out.to_csv(fname+'.csv', index=False)
    else:
        filter_cols = np.unique([i.strip() for i in row['filter_fields'].split(',')])
        for _filter in filter_cols:
            unique_vals = np.unique(df[_filter].values.astype('str'))
            for filter_val in unique_vals:
                expr = 'df[' + str(col_list) + "][df['" + str(_filter) + "'] == '" + str(filter_val) + "']" + \
                               ".groupby(" + str(agg_fields_cols) + ")." + row['aggfunc'] + "()[" + str(values_cols) + "]"

                # Write results to target output    
                df_out = pd.eval(expr, engine='python').reset_index()

                # # Apply labels
                _labels_df = labels_df[labels_df['field'].isin(df_out.columns)]
                for field in _labels_df['field'].unique():
                    _df = _labels_df[_labels_df['field'] == field]
                    local_series = pd.Series(_df['text'].values, index=_df['value'])
                    df_out[field] = df_out[field].map(local_series)

                df_out.to_csv(fname+'_'+str(_filter)+'_'+str(filter_val)+'.csv', index=False)                


def h5_df(h5file, table, col_list):
    df = pd.DataFrame()
    for col in col_list:
        df[col] = h5file[table][col][:].astype('float32')

    return df

def create_agg_outputs(path_dir_base, base_output_dir, survey=False):

    # Load the expression file
    expr_df = pd.read_csv(os.path.join(os.getcwd(),r'inputs/model/summaries/agg_expressions.csv'))
    # expr_df = expr_df.fillna('__remove__')    # Fill NA with string signifying data to be ignored
    geography_lookup = pd.read_csv(os.path.join(os.getcwd(),r'inputs/model/summaries/geography_lookup.csv'))
    variables_df = pd.read_csv(os.path.join(os.getcwd(),r'inputs/model/summaries/variables.csv'))
    global labels_df
    labels_df = pd.read_csv(os.path.join(os.getcwd(),'inputs/model/lookup/variable_labels.csv'))
    

    geog_cols = list(np.unique(geography_lookup[['right_column','right_index']].values))
    # Add geographic lookups at parcel level; only load relevant columns
    parcel_geog = pd.read_sql_table('parcel_'+base_year+'_geography', 'sqlite:///inputs/db/soundcast_inputs.db',
        columns=geog_cols)

    # Create output folder for flattened output
    if survey:
        survey_str = 'survey'
        # Get a list of headers for all daysim records so we can load data in as needed

    else:
        survey_str = ''
        # create h5 table of daysim outputs
        daysim_h5 = h5py.File(os.path.join(path_dir_base, 'daysim_outputs.h5'), 'r')
        # daysim_h5 = h5py.File()
    
    for dirname in pd.unique(expr_df['output_dir']):
        if survey:
            create_dir(os.path.join(base_output_dir,dirname,'survey'))
        else:
            create_dir(os.path.join(base_output_dir,dirname))

    # Expression log
    expr_log_path = r'outputs/agg/expr_log.csv'
    if os.path.exists(expr_log_path):
        os.remove(expr_log_path)

    hh_full_col_list = pd.read_csv(os.path.join(path_dir_base,'_household.tsv'), delim_whitespace=True, nrows=0)
    person_full_col_list = pd.read_csv(os.path.join(path_dir_base,'_person.tsv'), delim_whitespace=True, nrows=0)
    trip_full_col_list = pd.read_csv(os.path.join(path_dir_base,'_trip.tsv'), delim_whitespace=True, nrows=0)
    tour_full_col_list = pd.read_csv(os.path.join(path_dir_base,'_tour.tsv'), delim_whitespace=True, nrows=0)


    var_list = list(variables_df['new_variable'])

    # Full list of potential columns
    full_col_list = list(hh_full_col_list) + list(person_full_col_list) + list(trip_full_col_list) + list(tour_full_col_list) + geog_cols + var_list

    #####################
    ## Household 
    #####################

    df_agg = expr_df[expr_df['table'] == 'household']

    # Loop through each expression and evaluat result
    # only load the necessary columns and data  for this row
    for index, row in df_agg.iterrows():
        data_tables = {}
        col_list = get_row_col_list(row, full_col_list)

        # load the required data for the main df (houeshold)
        load_cols = [i for i in col_list if i in hh_full_col_list] + ['hhparcel']
        # Also account for any added user variables
        user_var_cols = [i for i in col_list if i in variables_df['new_variable'].values]
        if len(user_var_cols) > 0:
            df_var = variables_df[variables_df['new_variable'].isin(col_list)]
            load_cols += df_var['modified_variable'].values.tolist()
        # Account for any geography cols used to join

        if survey:
            household = pd.read_csv(os.path.join(path_dir_base,'_household.tsv'), delim_whitespace=True, usecols=load_cols)
        else:
            household = h5_df(daysim_h5, 'Household', load_cols)
    
        # merge geography and other variables
        geog_cols = [i for i in col_list if i in geography_lookup['right_column_rename'].values]
        if len(geog_cols) > 0:
            df_geog = geography_lookup[geography_lookup['right_column_rename'].isin(col_list)]
            household = merge_geography(household, df_geog, parcel_geog)

        # Calculate user variables
        if len(user_var_cols) > 0:
            # df_var = variables_df[variables_df['new_variable'].isin(col_list)]
            for _index, _row in df_var.iterrows():
                household[_row['new_variable']] = eval(_row['expression'])
            del df_var

        fname = os.path.join(base_output_dir, str(row['output_dir']),survey_str,str(row['target']))
        execute_eval(household, row, col_list, fname)

        del [household]

    #################################
    # Person
    #################################

    df_agg = expr_df[expr_df['table'] == 'person']

    # Loop through each expression and evaluat result
    # only load the necessary columns and data  for this row
    for index, row in df_agg.iterrows():
        data_tables = {}
        col_list = get_row_col_list(row, full_col_list)

        # load the required data for the main df (houeshold)
        load_cols = [i for i in col_list if i in person_full_col_list] + ['hhno','pwpcl','psexpfac']
        # Also account for any added user variables
        user_var_cols = [i for i in col_list if i in variables_df['new_variable'].values]
        if len(user_var_cols) > 0:
            df_var = variables_df[variables_df['new_variable'].isin(col_list)]
            load_cols += df_var['modified_variable'].values.tolist()
        # also load any columns needed for geographic join
        df_geog = geography_lookup[geography_lookup['left_table'] == 'Person']
        df_geog = df_geog[df_geog['right_column_rename'].isin(col_list)]
        load_cols += df_geog['left_index'].values.tolist()
        if survey:
            person = pd.read_csv(os.path.join(path_dir_base,'_person.tsv'), delim_whitespace=True, usecols=load_cols)
        else:
            person = h5_df(daysim_h5, 'Person', load_cols)

        # households
        # Also account for any added user variables
        load_cols = [i for i in col_list if i in hh_full_col_list] + ['hhno','hhparcel']
        if survey:
            household = pd.read_csv(os.path.join(path_dir_base,'_household.tsv'), delim_whitespace=True, usecols=load_cols)
        else:
            household = h5_df(daysim_h5, 'Household', load_cols)
            
        if len(household) > 0:
            person = person.merge(household, on='hhno')

        # merge geography and other variables
        geog_cols = [i for i in col_list if i in geography_lookup['right_column_rename'].values]
        if len(geog_cols) > 0:
            df_geog = geography_lookup[geography_lookup['right_column_rename'].isin(col_list)]
            person = merge_geography(person, df_geog, parcel_geog)


        # Calculate user variables
        if len(user_var_cols) > 0:
            for _index, _row in df_var.iterrows():
                person[_row['new_variable']] = pd.eval(_row['expression'],engine='python')
            del df_var

        fname = os.path.join(base_output_dir, str(row['output_dir']),survey_str,str(row['target']))
        execute_eval(person, row, col_list, fname)
        
        del [household, person]


    #################################
    # Trips
    #################################

    df_agg = expr_df[expr_df['table'] == 'trip']

    # Loop through each expression and evaluate result
    # only load the necessary columns and data  for this row
    for index, row in df_agg.iterrows():
        data_tables = {}
        col_list = get_row_col_list(row, full_col_list)

        # households
        # Also account for any added user variables
        load_cols = [i for i in col_list if i in hh_full_col_list] + ['hhno','hhparcel']
        if survey:
            household = pd.read_csv(os.path.join(path_dir_base,'_household.tsv'), delim_whitespace=True, usecols=load_cols)
        else:
            household = h5_df(daysim_h5, 'Household', load_cols)

        # persons
        # Also account for any added user variables
        load_cols = [i for i in col_list if i in person_full_col_list] + ['hhno','pno','psexpfac']
        if survey:
            person = pd.read_csv(os.path.join(path_dir_base,'_person.tsv'), delim_whitespace=True, usecols=load_cols)
        else:
            person = h5_df(daysim_h5, 'Person', load_cols)

        # trips
        # Also account for any added user variables
        load_cols = list(np.unique([i for i in col_list if i in trip_full_col_list] + ['pno','hhno','tour','trexpfac']))
        # only load user variables that are related to this table
        user_var_cols = [i for i in col_list if i in variables_df['new_variable'].values]
        if len(user_var_cols) > 0:
            df_var = variables_df[variables_df['new_variable'].isin(col_list)]
            load_cols += df_var['modified_variable'].values.tolist()
        # also load any columns needed for geographic join
        geog_cols = [i for i in col_list if i in geography_lookup['right_column_rename'].values]
        if len(geog_cols) > 0:
            df_geog = geography_lookup[geography_lookup['left_table'] == 'Trip']
            df_geog = df_geog[df_geog['right_column_rename'].isin(col_list)]
            load_cols += df_geog['left_index'].values.tolist()

        if survey:
            trip = pd.read_csv(os.path.join(path_dir_base,'_trip.tsv'), delim_whitespace=True, usecols=load_cols)
        else:
            trip = h5_df(daysim_h5, 'Trip', load_cols)
    
        # tours
        # Also account for any added user variables
        load_cols = [i for i in col_list if i in tour_full_col_list] + ['pno','hhno','tour']
        tour = pd.read_csv(os.path.join(path_dir_base,'_tour.tsv'), delim_whitespace=True, usecols=load_cols)

        # merge geography and other variables
        geog_cols = [i for i in col_list if i in geography_lookup['right_column_rename'].values]
        if len(geog_cols) > 0:
            trip = merge_geography(trip, df_geog, parcel_geog)

        # merge geography based on household info
        df_geog = geography_lookup[geography_lookup['left_table'] == 'Household']
        df_geog = df_geog[df_geog['right_column_rename'].isin(col_list)]
        if len(geog_cols) > 0:
            household = merge_geography(household, df_geog, parcel_geog)

        trip = trip.merge(household, on=['hhno'])
        if len([i for i in col_list if i in person_full_col_list]) > 0:
            trip = trip.merge(person, on=['hhno','pno'])
        if len([i for i in col_list if i in tour_full_col_list]) > 0:
            trip = trip.merge(tour, on=['pno','hhno','tour'])

        # Calculate user variables
        if len(user_var_cols) > 0:
            for _index, _row in df_var.iterrows():
                trip[_row['new_variable']] = pd.eval(_row['expression'],engine='python')

        fname = os.path.join(base_output_dir, str(row['output_dir']),survey_str,str(row['target']))
        execute_eval(trip, row, col_list, fname)

        del [tour, trip, person, household, df_geog]

    ############################
    # Tour
    ############################

    df_agg = expr_df[expr_df['table'] == 'tour']

    # Loop through each expression and evaluate result
    # only load the necessary columns and data  for this row
    for index, row in df_agg.iterrows():
        data_tables = {}
        col_list = get_row_col_list(row, full_col_list)

        # households
        # Also account for any added user variables
        load_cols = [i for i in col_list if i in hh_full_col_list] + ['hhno','hhparcel']
        if survey:
            household = pd.read_csv(os.path.join(path_dir_base,'_household.tsv'), delim_whitespace=True, usecols=load_cols)
        else:
            household = h5_df(daysim_h5, 'Household', load_cols)

        # persons
        # Also account for any added user variables
        load_cols = [i for i in col_list if i in person_full_col_list] + ['hhno','pno']
        if survey:
            person = pd.read_csv(os.path.join(path_dir_base,'_person.tsv'), delim_whitespace=True, usecols=load_cols)
        else:
            person = h5_df(daysim_h5, 'Person', load_cols)

        # tours
        # Also account for any added user variables
        load_cols = list(np.unique([i for i in col_list if i in tour_full_col_list] + ['pno','hhno','tour','toexpfac']))
        # only load user variables that are related to this table
        user_var_cols = [i for i in col_list if i in variables_df['new_variable'].values]

        if len(user_var_cols) > 0:
            df_var = variables_df[variables_df['new_variable'].isin(col_list)]
            load_cols += df_var['modified_variable'].values.tolist()
        # also load any columns needed for geographic join
        geog_cols = [i for i in col_list if i in geography_lookup['right_column_rename'].values]
        if len(geog_cols) > 0:
            df_geog = geography_lookup[geography_lookup['left_table'] == 'Tour']
            df_geog = df_geog[df_geog['right_column_rename'].isin(col_list)]
            load_cols += df_geog['left_index'].values.tolist()

        if survey:
            tour = pd.read_csv(os.path.join(path_dir_base,'_tour.tsv'), delim_whitespace=True, usecols=load_cols)
        else:
            tour = h5_df(daysim_h5, 'Tour', load_cols)

        # merge geography and other variables
        geog_cols = [i for i in col_list if i in geography_lookup['right_column_rename'].values]
        df_geog = geography_lookup[geography_lookup['left_table'] == 'Tour']
        df_geog = df_geog[df_geog['right_column_rename'].isin(col_list)]
        if len(geog_cols) > 0:
            tour = merge_geography(tour, df_geog, parcel_geog)

        # merge geography based on household info
        df_geog = geography_lookup[geography_lookup['left_table'] == 'Household']
        df_geog = df_geog[df_geog['right_column_rename'].isin(col_list)]
        if len(geog_cols) > 0:
            household = merge_geography(household, df_geog, parcel_geog)

        tour = tour.merge(household, on=['hhno'])
        if len(person) > 0:
            tour = tour.merge(person, on=['hhno','pno'])

        # Calculate user variables
        if len(user_var_cols) > 0:
            for _index, _row in df_var.iterrows():
                tour[_row['new_variable']] = pd.eval(_row['expression'],engine='python')

        fname = os.path.join(base_output_dir, str(row['output_dir']),survey_str,str(row['target']))
        execute_eval(tour, row, col_list, fname)

        del [tour, person, household, df_geog]
   

def copy_dash_tables(dash_table_list):
    """Copy outputs from validation and network_summary scripts required for Dash."""

    for fname in dash_table_list:
        shutil.copy(os.path.join(r'outputs/network',fname+'.csv'), r'outputs/agg/dash')

def main():

    output_dir_base = os.path.join(os.getcwd(),'outputs/agg')
    create_dir(output_dir_base)

    input_dir = os.path.join(os.getcwd(),r'outputs/daysim')
    create_agg_outputs(input_dir, output_dir_base, survey=False)

    survey_input_dir = os.path.join(os.getcwd(),r'inputs/base_year/survey')
    create_agg_outputs(survey_input_dir, output_dir_base, survey=True)

    copy_dash_tables(dash_table_list)
        
if __name__ == '__main__':
    start_time = time.time()
    main()
    print("--- %s seconds ---" % (time.time() - start_time))