import os, sys
import pandas as pd
sys.path.append(os.getcwd())
from standard_summary_configuration import *
from input_configuration import *
from pandas import ExcelWriter
   
def compare_fac_type(daily_df, out_summary):
    daily_df = pd.DataFrame([daily_df.groupby('@scrn').sum()['@tveh'].values,
                           daily_df.groupby('@scrn').min()['count'].values,
                           daily_df.groupby('@scrn').min()['ul3'].values,
                           daily_df.groupby('@scrn').first()['i'].values,
                           daily_df.groupby('@scrn').first()['j'].values,]).T
    daily_df.columns = ['model','observed','facility','i','j']  
    by_fac_type = daily_df.groupby('facility').sum()[['model','observed']]
    by_fac_type.reset_index(inplace = True)
    fac_type = pd.DataFrame({'ul3':[0,1,2,3,4,5,6], 
                       'Facility Type':['Other', 'Freeway', 'Expressway', 'Urban Arterial', 'Urban Arterial', 'Centroid', 'Rural Arterial']})
    compare_fac_type = pd.merge(by_fac_type, fac_type, left_on = 'facility', right_on='ul3')
    compare_fac_type['Difference'] = compare_fac_type['model'] - compare_fac_type['observed']
    compare_fac_type['% Difference'] = compare_fac_type['Difference'] / compare_fac_type['observed']
    compare_fac_type.to_excel(out_summary, sheet_name= 'Counts Facility Type', index=False)



def hourly_counts(tod_df, out_summary, order_df):
 
    # separate observed counts
    tod_df_observed = tod_df[tod_df.columns[['obs' in i for i in tod_df.columns]]]

    tod_df_obs = pd.DataFrame(tod_df_observed.stack()).reset_index()
    tod_df_obs.columns = ['count_id','tod','observed']
     
    # Trim time period from tod field
    tod_df_obs['tod'] = tod_df_obs['tod'].apply(lambda row: str(row.split('_')[-1]))
    # Drop total by time of day rows
    tod_df_obs = tod_df_obs[tod_df_obs['tod'] != 'obs_total']
 
    # separate model volumes
    tod_df_model = tod_df[tod_df.columns[['vol' in i for i in tod_df.columns]]]
    tod_df_model = pd.DataFrame(tod_df_model.stack()).reset_index()
    tod_df_model.columns = ['count_id','tod','model']
    tod_df_model['tod'] = tod_df_model['tod'].apply(lambda row: str(row.split('vol')[-1]))
 
    # Join model and observed data
    tod_df = pd.merge(tod_df_obs, tod_df_model, on =['count_id','tod'])

    # Link type (hov or general purpose)
    tod_df['link_type'] = tod_df['count_id'].apply(lambda row: str(row)[-1])
    tod_df_grouped = tod_df.groupby(['tod','link_type']).sum()
    tod_df_grouped['Difference'] = tod_df_grouped['model'] - tod_df_grouped['observed']
    tod_df_grouped['% Difference'] = tod_df_grouped['Difference'] / tod_df_grouped['observed']
    tod_df_grouped.reset_index(inplace=True)

    tod_df_sort = pd.merge(tod_df_grouped, order_df, on= 'tod')
    tod_df_sort.sort(['link_type','Order'], inplace= True)

    tod_df_sort.to_excel(out_summary, sheet_name= 'Time of Day Counts', index=False)

def compare_screenlines(screenline_df, obs_screenlines, net_summary):
    comp_screens = pd.merge(screenline_df, obs_screenlines, on='Screenline')
    comp_screens['Difference'] = comp_screens['Volumes'] - comp_screens['Observed_Volume']
    comp_screens['% Difference'] = comp_screens['Difference'] / comp_screens['Observed_Volume']
    comp_screens.sort(['Primary', 'Screenline'], inplace=True)
    comp_screens.to_excel(net_summary, sheet_name ='Screenlines', index=False)



def write_outputs(df_dict, sheet, out_book, spaces, index=True):
    n = 0
    for key, value in df_dict.items():
        key_df = pd.DataFrame(pd.Series(key))
        key_df.to_excel(out_book, sheet, startcol=0, startrow= n)
        pd.DataFrame(value).to_excel(out_book, sheet, startcol=0, startrow=n + 2, index=False)

        n += len(value.index) + spaces

def main():
    order_df = pd.DataFrame({'Order': range(1,13), 
                           'tod': ['5to6','6to7','7to8','8to9','9to10', '10to14', '14to15', '15to16', '16to17','17to18', '18to20', '20to5']})

    net_summary = pd.ExcelWriter(roadway_summary,engine = 'xlsxwriter')
    tod_df = pd.io.excel.read_excel(net_summary_detailed, sheetname='Counts Output', order_df=order_df)
    obs_screenlines = pd.read_csv(screenlines_file)
    screenline_df = pd.io.excel.read_excel(net_summary_detailed, sheetname = 'Screenline Volumes')
    vmt_df_class = pd.io.excel.read_excel(net_summary_detailed, sheetname = 'UC VMT')
    #VMT')
    daily_df = pd.io.excel.read_excel(net_summary_detailed, sheetname = 'Daily Counts')
    vmt_df_fac = pd.io.excel.read_excel(net_summary_detailed, sheetname='Network Summary')

    compare_fac_type(daily_df, net_summary)
    compare_screenlines(screenline_df, obs_screenlines, net_summary)
    hourly_counts(tod_df = tod_df, out_summary = net_summary, order_df = order_df)

    net_summary.close()
    net_summary.close()
   

if __name__ == "__main__":
    main()