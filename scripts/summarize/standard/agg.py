import numpy as np
import pandas as pd
import os, shutil
import math
from collections import OrderedDict
from input_configuration import base_year

# Define relationships between daysim files
daysim_merge_fields = {'Trip': 
                            {'Tour': ['tour'],
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

def create_agg_outputs(path_dir_base, output_dir_base):

    # Load the expression file
    expr_df = pd.read_csv(os.path.join(os.getcwd(),r'inputs/model/summaries/agg_expressions.csv'))

    print(output_dir_base)
    # Create output folder for flattened output
    if os.path.exists(output_dir_base):
        shutil.rmtree(output_dir_base)
    os.makedirs(output_dir_base)

    # Expression log
    expr_log_path = r'outputs/agg/expr_log.csv'
    if os.path.exists(expr_log_path):
        os.remove(expr_log_path)

    # Add geographic lookups; add TAZ-level geog lookups for work and home TAZs
    parcel_geog = pd.read_sql_table('parcel_'+base_year+'_geography', 'sqlite:///inputs/db/soundcast_inputs.db') 

    # Load daysim outputs

    trip = pd.read_csv(os.path.join(path_dir_base,'_trip.tsv'), delim_whitespace=True)
    tour = pd.read_csv(os.path.join(path_dir_base,'_tour.tsv'), delim_whitespace=True)
    person = pd.read_csv(os.path.join(path_dir_base,'_person.tsv'), delim_whitespace=True)
    household = pd.read_csv(os.path.join(path_dir_base,'_household.tsv'), delim_whitespace=True)
    person_day = pd.read_csv(os.path.join(path_dir_base,'_person_day.tsv'), delim_whitespace=True)
    household_day = pd.read_csv(os.path.join(path_dir_base,'_household_day.tsv'), delim_whitespace=True)
    # Add departure time hour to trips and tours
    trip['deptm_hr'] = trip['deptm'].fillna(-1).apply(lambda row: int(math.floor(row/60)))
    trip['arrtm_hr'] = trip['arrtm'].fillna(-1).apply(lambda row: int(math.floor(row/60)))
    # Create integer bins for travel time, distance, and cost
    trip[['travtime_bin','travcost_bin','travdist_bin']] = trip[['travtime','travcost','travdist']].apply(np.floor).astype('int')

    # tour start/end hours; tour time, cost, and distance bins
    tour['tlvorg_hr'] = tour['tlvorig'].fillna(-1).apply(lambda row: int(math.floor(row/60)))
    tour['tardest_hr'] = tour['tardest'].fillna(-1).apply(lambda row: int(math.floor(row/60)))
    tour['tlvdest_hr'] = tour['tlvdest'].fillna(-1).apply(lambda row: int(math.floor(row/60)))
    tour['tarorig_hr'] = tour['tarorig'].fillna(-1).apply(lambda row: int(math.floor(row/60)))
    tour[['tautotime_bin','tautocost_bin','tautodist_bin']] = tour[['tautotime','tautocost','tautodist']].apply(np.floor).astype('int')

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
    
    # Get a list of all used columns; drop all others to save memory
    # Required columns come from agg_expressions file and geography_lookup
    minimum_col_list = []
    for expr_col in ['agg_fields','values']:
        col_values_as_list = [i.split(',') for i in expr_df[expr_col]]
        minimum_col_list += list(np.unique([item for sublist in col_values_as_list for item in sublist]))
        minimum_col_list += list(geography_lookup['left_index'].values)    # Add the lookup cols for geographic joins
        # Also keep the columns from the Daysim merge fields dictionary - these are keys used for common joins
        minimum_col_list += get_dict_values(daysim_merge_fields)
    minimum_col_list = [i.strip(' ') for i in minimum_col_list]

    # Join household and person attributes to trip and tour records, but only join required fields

    
    # Apply field labels and geographic lookups 
    for tablename, table in daysim_dict.iteritems():

        ############################################################
        # Identify minimal set of relevant columns for this table
        ############################################################

        # Get the difference between the standard fields and those used in agg_expressions
        table_col_list = table.columns[table.columns.isin(minimum_col_list)]
        _table_cols = [i.split(',') for i in expr_df[expr_df['table'] == tablename.lower()]['agg_fields']]
        _table_cols = list(np.unique([item for sublist in _table_cols for item in sublist]))
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

    del daysim_dict

    for index, row in expr_df.iterrows():

        # Reduce dataframe to minumum relevant columns, for aggregation and value fields; notation follows pandas pivot table definitions
        agg_fields_cols = [i.strip() for i in row['agg_fields'].split(',')]
        values_cols = [i.strip() for i in row['values'].split(',')]
        col_list = "[" + str(agg_fields_cols + values_cols) + "]"
        # Pass expression string to eval method
        expr = row['table'] + col_list + ".groupby(" + str(agg_fields_cols) + ")." + row['aggfunc'] + "()[" + str(values_cols) + "]"

        # Create log of expressions executed for error checking
        expr_log_dict[row['target']] = expr
        # print expr_log_df
        pd.DataFrame.from_dict(expr_log_dict, orient='index').to_csv(expr_log_path, header=False)

        # Write results to target output    
        df = pd.eval(expr)
        df.to_csv(os.path.join(output_dir_base,str(row['target'])+'.csv'))

        del df

def main():

    dir_dict = OrderedDict()
    dir_dict[os.path.join(os.getcwd(),r'outputs/daysim')] = os.path.join(os.getcwd(),r'outputs/agg')
    dir_dict[os.path.join(os.getcwd(),r'inputs/base_year/survey')] = os.path.join(os.getcwd(),r'outputs/agg/survey')

    for path_dir_base, output_dir_base in dir_dict.items():
        create_agg_outputs(path_dir_base, output_dir_base)
        
if __name__ == '__main__':
    main()