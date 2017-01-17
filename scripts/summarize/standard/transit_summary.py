import os
import sys


###########################


import pandas as pd
from standard_summary_configuration import *
from input_configuration import *
from pandas import ExcelWriter

   

def compare_boardings(modeled, observed, time_groups, route_groups, time_group_name, type):

    if type == 'grouped':
        modeled['RouteGroupID'] = (modeled['route_code']/1000).astype(int)
        observed['RouteGroupID'] = (observed['PSRC_Rte_ID']/1000).astype(int)

    else:
        modeled['RouteGroupID'] = modeled['route_code']
        observed['RouteGroupID'] = observed['PSRC_Rte_ID']
        route_groups['RouteGroupID'] = route_groups['route_code']
        

    modeled_by_time =  group_transit(False, modeled, time_groups, route_groups, time_group_name, 'index', 'ModelPeriod', 'RouteGroupName', 'RouteGroupID')
    observed_by_time =  group_transit(True, observed, time_groups, route_groups, time_group_name, 'index', 'Hour', 'RouteGroupName', 'RouteGroupID')
    
    # Differences
    time_diff=modeled_by_time - observed_by_time
    percent_time_diff = (time_diff/observed_by_time*100)

    #### Put together
    output =dict([('Observed Boardings by Route and Time Group', observed_by_time),  
                        ( 'Modeled Boardings by Route and Time Group', modeled_by_time),
                        ('Difference in Boardings', time_diff), 
                        ('Percent Difference', percent_time_diff)])
    

    return output
   
def group_transit(observed, dataset, time_groups, route_groups, time_group_name, time_group_id_dataset, time_group_id_g, route_group_name, route_group_id):
    dataset_groups = pd.merge(dataset, route_groups, on = route_group_id)
    dataset_by_route_group = dataset_groups.groupby(route_group_name).sum()
    dataset_route_group_t = dataset_by_route_group.transpose()
    dataset_route_group_t.reset_index(inplace = True)

    #Group by Time Period

    if observed:
        dataset_route_group_t[time_group_id_dataset]=pd.to_numeric(dataset_route_group_t[time_group_id_dataset], errors = coerce)
    dataset_time_group = pd.merge(dataset_route_group_t, time_groups, left_on = time_group_id_dataset, right_on = time_group_id_g).dropna()
    dataset_time_route_group_val = dataset_time_group.groupby(time_group_id_dataset).first()
    dataset_time_route_group = dataset_time_route_group_val.groupby(time_group_name).sum()
    dataset_time_route_group = dataset_time_route_group.drop('Hour', 1)
    dataset_time_route_group = dataset_time_route_group.transpose()

    return dataset_time_route_group
    
def compare_all(modeled, observed, time_groups, time_group_name):
    
    
    modeled_grouped = modeled.groupby('route_code').sum()
    modeled_grouped_t = modeled_grouped.transpose()
    modeled_grouped_t.reset_index(inplace=True)

    
    modeled_time = pd.merge(modeled_grouped_t, time_groups, left_on = 'index', right_on= 'ModelPeriod')
    modeled_time = modeled_time.groupby('ModelPeriod').first()
    print modeled_time
    modeled_time_s = modeled_time.groupby(time_group_name).sum().transpose()
    print modeled_time_s
    modeled_time_s.reset_index(inplace=True)
    modeled_time_s.columns = ['route_id', 'modeled_boardings']


    observed = observed.groupby('PSRC_Rte_ID').sum()
    observed_t = observed.transpose()
    observed_t.reset_index(inplace=True)
    observed_t['index']=pd.to_numeric(observed_t['index'], errors = coerce)


    observed_time = pd.merge(observed_t, time_groups, left_on = 'index', right_on= 'Hour')
    observed_time_s = observed_time.groupby(time_group_name).sum().transpose()
    observed_time_s.reset_index(inplace=True)
    observed_time_s.columns = ['route_id', 'observed_boardings']

 
   
    modeled_observed = pd.merge(modeled_time_s, observed_time_s, on = 'route_id')
  

    modeled_observed['Difference'] = modeled_observed['modeled_boardings'] - modeled_observed['observed_boardings']
    modeled_observed['Percent_Diff']= modeled_observed['Difference']/modeled_observed['observed_boardings']
    modeled_ob_dict = dict([('All Routes', modeled_observed)])

    return modeled_ob_dict

    

def write_outputs(df_dict, sheet, out_book, spaces):
 
   n=0
   for key, value in df_dict.items():

        key_df =pd.DataFrame(pd.Series(key))
        key_df.to_excel(out_book, sheet, startcol=0, startrow= n)
        pd.DataFrame(value).to_excel(out_book, sheet, startcol=0, startrow=n+2)

        n += len(value.index) + spaces

def main():
    transit_df = pd.io.excel.read_excel(net_summary_detailed, sheetname = 'Transit Summaries')
    observed_df = pd.read_csv(observed_boardings_file)
    net_summary = pd.ExcelWriter(transit_summary_out,engine='xlsxwriter')

    time_groups = pd.read_csv(transit_time_group_file)
    route_groups = pd.read_csv(route_group_file)
    special_routes = pd.read_csv(special_routes_file)

    
    big_time_group = compare_boardings(transit_df, observed_df, time_groups, route_groups,  'BigTimeGroup', 'grouped')
    small_time_group = compare_boardings(transit_df, observed_df, time_groups, route_groups,'TimeGroup', 'grouped')
    write_outputs(big_time_group, 'By Agency and Big Time',net_summary,  8)
    write_outputs(small_time_group, 'By Agency and Small Time',net_summary,  8)

    special_summ = compare_boardings(transit_df, observed_df, time_groups, special_routes, 'BigTimeGroup', 'none')
    write_outputs(special_summ, 'Special Routes by Time Group', net_summary,  8)

    
    line_by_line = compare_all(transit_df, observed_df, time_groups,  'All')
    write_outputs(line_by_line, 'All Routes',net_summary,  8)

    net_summary.close()
   

if __name__ == "__main__":
    main()