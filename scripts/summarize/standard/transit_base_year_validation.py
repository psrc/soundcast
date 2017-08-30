
import os, sys
import pandas as pd
sys.path.append(os.getcwd())
from standard_summary_configuration import *
from input_configuration import *
from pandas import ExcelWriter
pd.options.mode.chained_assignment = None  # mute chained assignment warnings


def compare_boardings(modeled, observed, time_groups, route_groups, time_group_name, type):

    line_by_line = compare_all(modeled, observed, time_groups, time_group_name)
    # the last row is the field hour
    line_by_line.drop(line_by_line.index[len(line_by_line)-1], inplace=True)

    if type == 'grouped':
        line_by_line['RouteGroupID'] = (line_by_line['route_code'].astype(int) /1000).astype(int)
    else:
        line_by_line['RouteGroupID'] = line_by_line['route_code']
        route_groups['RouteGroupID'] = route_groups['route_code']
    
    line_groups = pd.merge(line_by_line, route_groups, on = 'RouteGroupID')

    grouped_transit = line_groups.groupby('RouteGroupName').sum()
    grouped_transit.reset_index(inplace=True)
    return grouped_transit


    
def compare_all(modeled, observed, time_groups, time_group_name):

    modeled_grouped = modeled.groupby('route_code').sum()
    modeled_grouped_t = modeled_grouped.transpose()
    modeled_grouped_t.reset_index(inplace=True)

    
    modeled_time = pd.merge(modeled_grouped_t, time_groups, left_on = 'index', right_on= 'ModelPeriod')
    modeled_time = modeled_time.groupby('ModelPeriod').first()
    modeled_time_s = modeled_time.groupby(time_group_name).sum().transpose()
    modeled_time_s.reset_index(inplace=True)

    observed = observed.groupby('PSRC_Rte_ID').sum()
    observed_t = observed.transpose()
    observed_t.reset_index(inplace=True)
    observed_t['index']=pd.to_numeric(observed_t['index'], errors = coerce)

    observed_time = pd.merge(observed_t, time_groups, left_on = 'index', right_on= 'Hour')
    observed_time_s = observed_time.groupby(time_group_name).sum().transpose()
    observed_time_s.reset_index(inplace=True)

    modeled_observed = pd.merge(modeled_time_s, observed_time_s, left_on = 'route_code', right_on= 'PSRC_Rte_ID', suffixes=('_model', '_observed'))
  
    return modeled_observed


def main():
    transit_df = pd.io.excel.read_excel(net_summary_detailed, sheetname = 'Transit Summaries')
    observed_df = pd.read_csv(observed_boardings_file)
    net_summary = pd.ExcelWriter(transit_summary_out,engine='xlsxwriter')

    time_groups = pd.read_csv(transit_time_group_file)
    route_groups = pd.read_csv(route_group_file)
    special_routes = pd.read_csv(special_routes_file)

    big_time_group = compare_boardings(transit_df, observed_df, time_groups, route_groups,  'BigTimeGroup', 'grouped')
    small_time_group = compare_boardings(transit_df, observed_df, time_groups, route_groups,'TimeGroup', 'grouped')
    
    big_time_group.to_excel(net_summary, 'By Agency and Big Time')
    small_time_group.to_excel(net_summary, 'By Agency and Small Time')


    special_summ = compare_boardings(transit_df, observed_df, time_groups, special_routes, 'All', 'none')
    special_summ.to_excel(net_summary, 'Special Routes')

    line_by_line = compare_all(transit_df, observed_df, time_groups,  'All')
    line_by_line.to_excel(net_summary, 'Line by Line')
    net_summary.close()

if __name__ == "__main__":
    main()