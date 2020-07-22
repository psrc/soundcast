import numpy as np
import pandas as pd
import os, shutil
import re
import math
from collections import OrderedDict
from input_configuration import base_year

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

def create_agg_outputs(path_dir_base, base_output_dir, survey=False):

    # Load the expression file
    expr_df = pd.read_csv(os.path.join(os.getcwd(),r'inputs/model/summaries/agg_expressions.csv'))
    expr_df = expr_df.fillna('__remove__')    # Fill NA with string signifying data to be ignored

    # Create output folder for flattened output
    if survey:
        survey_str = 'survey'
    else:
        survey_str = ''
    
    for dirname in pd.unique(expr_df['output_dir']):
        if survey:
            create_dir(os.path.join(base_output_dir,dirname,'survey'))
        else:
            create_dir(os.path.join(base_output_dir,dirname))

    # Expression log
    expr_log_path = r'outputs/agg/expr_log.csv'
    if os.path.exists(expr_log_path):
        os.remove(expr_log_path)

    # Add geographic lookups; add TAZ-level geog lookups for work and home TAZs
    parcel_geog = pd.read_sql_table('parcel_'+base_year+'_geography', 'sqlite:///inputs/db/soundcast_inputs.db') 

    # Load daysim outputs

    trip = pd.read_csv(os.path.join(path_dir_base,'_trip.tsv'), delim_whitespace=True)
    tour = pd.read_csv(os.path.join(path_dir_base,'_tour.tsv'), delim_whitespace=True)
    tour = tour[tour['tmodetp'] != -1]
    person = pd.read_csv(os.path.join(path_dir_base,'_person.tsv'), delim_whitespace=True)
    household = pd.read_csv(os.path.join(path_dir_base,'_household.tsv'), delim_whitespace=True)
    person_day = pd.read_csv(os.path.join(path_dir_base,'_person_day.tsv'), delim_whitespace=True)
    household_day = pd.read_csv(os.path.join(path_dir_base,'_household_day.tsv'), delim_whitespace=True)
    # Add departure time hour to trips and tours        
    trip['deptm_hr'] = trip['deptm'].fillna(-1).apply(lambda row: int(math.floor(row/60)))
    trip['arrtm_hr'] = trip['arrtm'].fillna(-1).apply(lambda row: int(math.floor(row/60)))
    # Create integer bins for travel time, distance, and cost
    trip[['travtime_bin','travcost_bin','travdist_bin']] = trip[['travtime','travcost','travdist']].apply(np.floor).fillna(-1).astype('int')

    # tour start/end hours; tour time, cost, and distance bins
    tour['tlvorg_hr'] = tour['tlvorig'].fillna(-1).apply(lambda row: int(math.floor(row/60)))
    tour['tardest_hr'] = tour['tardest'].fillna(-1).apply(lambda row: int(math.floor(row/60)))
    tour['tlvdest_hr'] = tour['tlvdest'].fillna(-1).apply(lambda row: int(math.floor(row/60)))
    tour['tarorig_hr'] = tour['tarorig'].fillna(-1).apply(lambda row: int(math.floor(row/60)))
    tour[['tautotime_bin','tautocost_bin','tautodist_bin']] = tour[['tautotime','tautocost','tautodist']].apply(np.floor).fillna(-1).astype('int')

    # Total tour time
    tour['tour_duration'] = tour['tarorig'] - tour['tlvorig']

    # Convert continuous income value to thousands
    # Value represents the low end range (e.g., 67,834 becomes 67,000, which represents the range 67,000 - 68,000)
    household['hhincome_thousands'] = household['hhincome'].apply(lambda x: int(str(x/1000).split('.')[0]+'000'))

    geography_lookup = pd.read_csv(os.path.join(os.getcwd(),r'inputs/model/summaries/geography_lookup.csv'))
    labels_df = pd.read_csv(os.path.join(os.getcwd(),'inputs/model/lookup/variable_labels.csv'))
    daysim_dict = {'Trip': trip,
                  'Household': household,
                  'Tour': tour,
                  'HouseholdDay': household_day,
                  'PersonDay': person_day,
                  'Person': person}

    # build master list of daysim columns
    master_col_list = []
    for key, value in daysim_dict.items():
        master_col_list += [i for i in value.columns.values]
    master_col_list += [i for i in geography_lookup['right_column_rename'].values]

    # Get a list of all used columns; drop all others to save memory
    # Required columns come from agg_expressions file and geography_lookup
    minimum_col_list = []
    for expr_col in ['agg_fields','values','filter_fields','query']:
        col_values_as_list = [re.split(',|>|==|>=|<|<=|!=',i) for i in expr_df[expr_col]]
        minimum_col_list += list(np.unique([item for sublist in col_values_as_list for item in sublist]))
        minimum_col_list += list(geography_lookup['left_index'].values)    # Add the lookup cols for geographic joins
        # Also keep the columns from the Daysim merge fields dictionary - these are keys used for common joins
        minimum_col_list += get_dict_values(daysim_merge_fields)
    minimum_col_list = [i.strip(' ') for i in minimum_col_list]

    minimum_col_list  = list(set(master_col_list) & set(minimum_col_list))

    # Join household and person attributes to trip and tour records, but only join required fields



    # Apply field labels and geographic lookups 
    for tablename, table in daysim_dict.iteritems():

        ############################################################
        # Identify minimal set of relevant columns for this table
        ############################################################

        # Get the difference between the standard fields and those used in agg_expressions and fitler fields
        table_col_list = table.columns[table.columns.isin(minimum_col_list)]
        _table_cols = []
        for colname in ['agg_fields','filter_fields','query']:
            _table_cols.append([re.split(',|>|==|>=|<|<=|!=',i) for i in expr_df[expr_df['table'] == tablename.lower()][colname]])
        
        _table_cols = list([item for sublist in _table_cols for item in sublist])
        _table_cols = np.unique([item for sublist in _table_cols for item in sublist])
        _table_cols = [i.strip(' ') for i in _table_cols]

        diff_cols = np.setdiff1d(_table_cols, table_col_list)


        # for the different columns, if they're in a Daysim file, merge the required columns
        join_cols = {'Trip': [], 'Tour': [], 'Household': [], 'Person': []}
        daysim_original_cols = {'Trip': trip.columns, 'Tour': tour.columns, 'Household': household.columns, 'Person': person.columns}
        for var in diff_cols:
            for _tablename, cols in daysim_original_cols.items():
                if _tablename != tablename:
                    if var in daysim_original_cols[_tablename]:
                        join_cols[_tablename].append(var)

        # Merge datasets to target
        for _tablename, _fields in join_cols.items():
            if len(_fields) > 0:
                _df = daysim_dict[_tablename][join_cols[_tablename]+daysim_merge_fields[tablename][_tablename]]
                daysim_dict[tablename] = daysim_dict[tablename].merge(_df, on=daysim_merge_fields[tablename][_tablename])

        # Select only required set of columns
        final_col_list = np.unique(list(table_col_list) + list(_table_cols))
        daysim_dict[tablename] = daysim_dict[tablename][daysim_dict[tablename].columns[daysim_dict[tablename].columns.isin(final_col_list)]]

        # Merge geographic data
        if len(daysim_dict[tablename].columns) > 0:          
            _df = geography_lookup[geography_lookup['left_table'] == tablename]
            for index, row in _df.iterrows():
                right_df = pd.eval(row['right_table'] + "[" + str(list(row[['right_index','right_column']].values)) + "]", engine='python')
                daysim_dict[tablename] = daysim_dict[row['left_table']].merge(right_df, left_on=row['left_index'], right_on=row['right_index'], how='left')
                daysim_dict[tablename].rename(columns={row['right_column']: row['right_column_rename']}, inplace=True)
                daysim_dict[tablename].drop(row['right_index'], axis=1, inplace=True)
        
            # Apply labels
            df = labels_df[labels_df['table'] == tablename]
            df = df[df['field'].isin(daysim_dict[tablename].columns)]
            for field in df['field'].unique():
                newdf = df[df['field'] == field]
                local_series = pd.Series(newdf['text'].values, index=newdf['value'])
                daysim_dict[tablename][field] = daysim_dict[tablename][field].map(local_series)
            
    expr_log_df = pd.DataFrame()

    expr_log_dict = {}

    trip = daysim_dict['Trip']
    tour = daysim_dict['Tour']
    person = daysim_dict['Person']
    household = daysim_dict['Household']
    person_day = daysim_dict['PersonDay']
    household_day = daysim_dict['HouseholdDay']

    tour.fillna(-1, inplace=True)

    del daysim_dict

    for index, row in expr_df.iterrows():

        # Reduce dataframe to minumum relevant columns, for aggregation and value fields; notation follows pandas pivot table definitions
        agg_fields_cols = [i.strip() for i in row['agg_fields'].split(',')]
        
        # filter_fields_cols = [i.strip() for i in row['filter_fields'].split(',')]
        values_cols = [i.strip() for i in row['values'].split(',')]
        total_cols = agg_fields_cols + values_cols
        filter_fields_cols = []
        if row['filter_fields'] != '__remove__':
            filter_fields_cols = [i.strip() for i in row['filter_fields'].split(',')]
            total_cols += filter_fields_cols
        

        # Apply a query
        _query = ''
        if row['query'] != '__remove__':

            _query = """.query('"""+ str(row['query']) + """')"""
            query_fields_cols = [i.strip() for i in re.split(',|>|==|>=|<|<=|!=',row['query'])]
            total_cols += query_fields_cols

        total_cols = list(set(total_cols) & set(minimum_col_list))
        col_list = "[" + str(total_cols) + "]"
        expr = row['table'] + col_list+ _query + ".groupby(" + str(agg_fields_cols) + ")." + row['aggfunc'] + "()[" + str(values_cols) + "]"

        # Create log of expressions executed for error checking
        expr_log_dict[row['target']] = expr

        pd.DataFrame.from_dict(expr_log_dict, orient='index').to_csv(expr_log_path, header=False)

        # Write results to target output    
        df = pd.eval(expr)
        df.to_csv(os.path.join(base_output_dir, str(row['output_dir']),survey_str,str(row['target'])+'.csv'))
 
        # If filter values are passed, write out a table for each unique value in the filter field
        if len(filter_fields_cols) > 0:
            for _filter in filter_fields_cols:
                
                if row['table'] == 'tour':
                    unique_vals = np.unique(tour[_filter].values)
                else:
                    unique_vals = np.unique(trip[_filter].values)
                for filter_val in unique_vals:
                    expr = row['table'] + col_list + "[" + row['table'] + "['" + str(_filter) + "'] == '" + str(filter_val) + "']" + \
                                   ".groupby(" + str(agg_fields_cols) + ")." + row['aggfunc'] + "()[" + str(values_cols) + "]"
                    # print(expr)
                    # Create log of expressions executed for error checking
                    expr_log_dict[row['target']] = expr
                    # print expr_log_df
                    pd.DataFrame.from_dict(expr_log_dict, orient='index').to_csv(expr_log_path, header=False)

                    # Write results to target output    
                    df = pd.eval(expr)

                    # Apply labels
                    df.to_csv(os.path.join(base_output_dir, str(row['output_dir']), survey_str,
                                str(row['target'])+"_"+str(_filter)+"_"+str(filter_val)+'.csv'))

        del df

def main():

    output_dir_base = os.path.join(os.getcwd(),'outputs/agg')
    create_dir(output_dir_base)

    input_dir = os.path.join(os.getcwd(),r'outputs/daysim')
    create_agg_outputs(input_dir, output_dir_base, survey=False)

    survey_input_dir = os.path.join(os.getcwd(),r'inputs/base_year/survey')
    create_agg_outputs(survey_input_dir, output_dir_base, survey=True)
        
if __name__ == '__main__':
    main()