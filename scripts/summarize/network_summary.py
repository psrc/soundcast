import array as _array
import inro.emme.desktop.app as app
import inro.modeller as _m
import inro.emme.matrix as ematrix
import inro.emme.database.matrix
import inro.emme.database.emmebank as _eb
import json
import numpy as np
import time
import os,sys
import h5py
import Tkinter, tkFileDialog
import multiprocessing as mp
import subprocess
import csv
import xlsxwriter
import xlautofit 
from multiprocessing import Pool
import pandas as pd
sys.path.append(os.path.join(os.getcwd(),"inputs"))
from input_configuration import *

network_summary_project = 'Projects/LoadTripTables/LoadTripTables.emp'
fac_type_dict = {'highway' : 'ul3 = 1 or ul3 = 2',
                 'arterial' : 'ul3 = 3 or ul3 = 4 or ul3 = 6',
                 'connectors' : 'ul3 = 5'}

extra_attributes_dict = {'@tveh' : 'total vehicles', 
                         '@mveh' : 'medium trucks', 
                         '@hveh' : 'heavy trucks', 
                         '@vmt' : 'vmt',\
                         '@vht' : 'vht', 
                         '@trnv' : 'buses in auto equivalents',
                         '@ovol' : 'observed volume', 
                         '@bveh' : 'number of buses'}

transit_extra_attributes_dict = {'@board' : 'total boardings', '@timtr' : 'transit line time'}

transit_tod = {'6to7' : {'4k_tp' : 'am', 'num_of_hours' : 1}, 
               '7to8' :  {'4k_tp' : 'am', 'num_of_hours' : 1}, 
               '8to9' :  {'4k_tp' : 'am', 'num_of_hours' : 1}, 
               '9to10' : {'4k_tp' : 'md', 'num_of_hours' : 1}, 
               '10to14' : {'4k_tp' : 'md', 'num_of_hours' : 4}, 
               '14to15' : {'4k_tp' : 'md', 'num_of_hours' : 1}}
# Input Files:
counts_file = 'TrafficCounts_Mid.txt'

# Output Files: 
net_summary_file = 'network_summary.csv'
counts_output_file = 'counts_output.csv'
screenlines_file = 'screenline_volumes.csv'

uc_list = ['@svtl1', '@svtl2', '@svtl3', '@svnt1', '@svnt2', '@svnt3', '@h2tl1', '@h2tl2', '@h2tl3',
           '@h2nt1', '@h2nt2', '@h2nt3', '@h3tl1', '@h3tl2', '@h3tl3', '@h3nt1', '@h3nt2', '@h3nt3', '@lttrk', '@mveh', '@hveh', '@bveh']

class EmmeProject:
    def __init__(self, filepath):
        self.desktop = app.start_dedicated(True, "cth", filepath)
        self.m = _m.Modeller(self.desktop)
        pathlist = filepath.split("/")
        self.fullpath = filepath
        self.filename = pathlist.pop()
        self.dir = "/".join(pathlist) + "/"
        self.bank = self.m.emmebank
        self.tod = self.bank.title
        self.current_scenario = list(self.bank.scenarios())[0]
        self.data_explorer = self.desktop.data_explorer()
    
    def change_active_database(self, database_name):
        for database in self.data_explorer.databases():
            #print database.title()
            if database.title() == database_name:
                
                database.open()
                print 'changed'
                self.bank = self.m.emmebank
                self.tod = self.bank.title
                print self.tod
                self.current_scenario = list(self.bank.scenarios())[0]
    def create_extras(self, type, name, description):
        NAMESPACE = "inro.emme.data.extra_attribute.create_extra_attribute"
        create_extras = self.m.tool(NAMESPACE)
        create_extras(extra_attribute_type=type, extra_attribute_name = name, extra_attribute_description = description, overwrite=True)
    
    def link_calculator(self, **kwargs):
        spec = json_to_dictionary("link_calculation")
        for name, value in kwargs.items():
            print name
            if name == 'selections':
                spec[name]['link'] = value
            else:
                spec[name] = value
        NAMESPACE = "inro.emme.network_calculation.network_calculator"
        network_calc = self.m.tool(NAMESPACE)
        self.link_calc_result = network_calc(spec)
       
     
    def transit_line_calculator(self, **kwargs):
        spec = json_to_dictionary("transit_line_calculation")
        for name, value in kwargs.items():
            spec[name] = value
        
        NAMESPACE = "inro.emme.network_calculation.network_calculator"
        network_calc = self.m.tool(NAMESPACE)
        self.link_calc_result = network_calc(spec)
    
    def transit_segment_calculator(self, **kwargs):
        spec = json_to_dictionary("transit_segment_calculation")
        for name, value in kwargs.items():
            spec[name] = value
        
        NAMESPACE = "inro.emme.network_calculation.network_calculator"
        network_calc = self.m.tool(NAMESPACE)
        self.link_calc_result = network_calc(spec)




def json_to_dictionary(dict_name):

    #Determine the Path to the input files and load them
    skim_params_loc = os.path.abspath(os.path.join(os.getcwd(),"inputs\\skim_params"))    # Assumes the cwd is @ run_soundcast.py; always run this script from run_soundcast.py
    input_filename = os.path.join(skim_params_loc,dict_name+'.json').replace("\\","/")
    my_dictionary = json.load(open(input_filename))

    return(my_dictionary)
 
def calc_vmt_vht_delay_by_ft(EmmeProject):
    ###calculates vmt, vht, and delay for all links and returns a nested dictionary with key=metric(e.g. 'vmt') 
    #and value = dictionary where dictionary has key = facility type(e.g. 'highway') and value = sum of metric 
    #for that facility type
  
     #medium trucks
     EmmeProject.link_calculator(result = '@mveh', expression = '@metrk/1.5')
     
     #heavy trucks:
     EmmeProject.link_calculator(result = '@hveh', expression = '@hvtrk/2')
     
     #busses:
     EmmeProject.link_calculator(result = '@bveh', expression = '@trnv/2')
     ####################still need to do*****************************
     #hdw- number of buses:
     #mod_spec = network_calc_spec
     #mod_spec["result"] = "@hdw"
     #mod_spec["expression"] = 'hdw'
     #network_calc(mod_spec)
     
     #calc total vehicles, store in @tveh 
     str_expression = '@svtl1 + @svtl2 + @svtl3 + @svnt1 +  @svnt2 + @svnt3 + @h2tl1 + @h2tl2 + @h2tl3 + @h2nt1 + @h2nt2 + @h2nt3 + @h3tl1\
                       + @h3tl2 + @h3tl3 + @h3nt1 + @h3nt2 + @h3nt3 + @lttrk + @mveh + @hveh + @bveh'
     EmmeProject.link_calculator(result = '@tveh', expression = str_expression)
     #a dictionary to hold vmt/vht/delay values:
     results_dict = {}
     #dictionary to hold vmts:
     vmt_dict = {}
     #calc vmt for all links by factilty type and get sum by ft. 
     for key, value in fac_type_dict.iteritems():    
        EmmeProject.link_calculator(result = "@vmt", expression = "@tveh * length", selections = value)
        #total vmt by ft: 
        vmt_dict[key] = EmmeProject.link_calc_result['sum']
     #add to results dictionary
     results_dict['vmt'] = vmt_dict
    
     #Now do the same for VHT:
     vht_dict = {}
     for key, value in fac_type_dict.iteritems():    
        EmmeProject.link_calculator(result = "@vht", expression = "@tveh * timau / 60", selections = value)
        vht_dict[key] = EmmeProject.link_calc_result['sum']
     results_dict['vht'] = vht_dict

     #Delay:
     delay_dict = {}
     for key, value in fac_type_dict.iteritems():    
        EmmeProject.link_calculator(result = None, expression =  "@tveh*(timau-(length*60/ul2))/60", selections = value)
        delay_dict[key] = EmmeProject.link_calc_result['sum']
     
     results_dict['delay'] = delay_dict
     return results_dict
def vmt_by_user_class(EmmeProject):
    #uc_list = ['@svtl1', '@svtl2', '@svtl3', '@svnt1', '@h2tl1', '@h2tl2', '@h2tl3', '@h2nt1', '@h3tl1', '@h3tl2', '@h3tl3', '@h3nt1', '@lttrk', '@mveh', '@hveh', '@bveh']
    uc_vmt_list = []
    for item in uc_list:
        EmmeProject.link_calculator(result = None, expression = item + ' * length')
        #total vmt by ft: 
        uc_vmt_list.append(EmmeProject.link_calc_result['sum'])
    return uc_vmt_list
def get_link_counts(EmmeProject, df_counts, tod):
    #get the network for the active scenario
     network = EmmeProject.current_scenario.get_network()
     list_model_vols = []
     for item in df_counts.index:
         i = list(item)[0]
         j = list(item)[1]
         link = network.link(i, j)
         x = {}
         x['loop_INode'] = i
         x['loop_JNode'] = j
         if link <> None:
            x['vol' + tod] = link['@tveh']   
         else:
            x['vol' + tod] = None
         list_model_vols.append(x)
     print len(list_model_vols)
     df =  pd.DataFrame(list_model_vols)
     df = df.set_index(['loop_INode', 'loop_JNode'])
     return df
def get_unique_screenlines(EmmeProject):
    network = EmmeProject.current_scenario.get_network()
    unique_screenlines = []
    for link in network.links():
        if link.type <> 90 and link.type not in unique_screenlines:
            unique_screenlines.append(str(link.type))
    return unique_screenlines
def get_screenline_volumes(screenline_dict, EmmeProject):

    for screen_line in screenline_dict.iterkeys():
        EmmeProject.link_calculator(result = None, expression = "@tveh", selections = screen_line)
        screenline_dict[screen_line] = screenline_dict[screen_line] + EmmeProject.link_calc_result['sum']

def calc_transit_line_atts(EmmeProject):
    #calc boardings and transit line time
     EmmeProject.transit_line_calculator(result = '@board', expression = 'board')
     EmmeProject.transit_line_calculator(result = '@timtr', expression = 'timtr')
def get_transit_boardings_time(EmmeProject):
    network = EmmeProject.current_scenario.get_network()
    df_transit_atts = pd.DataFrame(columns=('id', EmmeProject.tod + '_boardings', EmmeProject.tod + '_boardings''_time'))
    line_list = []
    
    for transit_line in network.transit_lines():
        x = {}
        #company_code = transit_line['@ut3']
        x['id'] = transit_line.id
        x[EmmeProject.tod + '_board'] = transit_line['@board']
        x[EmmeProject.tod + '_time']= transit_line['@timtr']
        line_list.append(x)
    df = pd.DataFrame(line_list)
    df = df.set_index(['id'])
    return df
def calc_transit_link_volumes(EmmeProject):
    total_hours = transit_tod[EmmeProject.tod]['num_of_hours']
    my_expression = str(total_hours) + ' * vauteq * (60/hdw)'
    print my_expression
    EmmeProject.transit_segment_calculator(result = '@trnv', expression = my_expression, aggregation = "+")
    
          
        
def writeCSV(fileNamePath, listOfTuples):
    myWriter = csv.writer(open(fileNamePath, 'wb'))
    for l in listOfTuples:
        myWriter.writerow(l)


def main():
    ft_summary_dict = {}
    transit_summary_dict = {}
    my_project = EmmeProject(project)
    
    writer = pd.ExcelWriter('outputs/network_summary_detailed.xlsx', engine = 'xlsxwriter')#Defines the file to write to and to use xlsxwriter to do so
    #create extra attributes:
    
       
    #pandas dataframe to hold count table:
    df_counts = pd.read_csv('inputs/network_summary/' + counts_file, index_col=['loop_INode', 'loop_JNode'])
 
    counts_dict = {}
    uc_vmt_dict = {}
    #get a list of screenlines from the bank/scenario
    screenline_list = get_unique_screenlines(my_project) 
    screenline_dict = {}
    
    for item in screenline_list:
        #dict where key is screen line id and value is 0
        screenline_dict[item] = 0

    #loop through all tod banks and get network summaries
    for key, value in sound_cast_net_dict.iteritems():
        my_project.change_active_database(key)
        for name, desc in extra_attributes_dict.iteritems():
            my_project.create_extras('LINK', name, desc)
        #TRANSIT:
        if my_project.tod in transit_tod.keys():
            for name, desc in transit_extra_attributes_dict.iteritems():
                my_project.create_extras('TRANSIT_LINE', name, desc)
            calc_transit_link_volumes(my_project)
            calc_transit_line_atts(my_project)
  
            transit_summary_dict[key] = get_transit_boardings_time(my_project)
            #print transit_summary_dict
          
        net_stats = calc_vmt_vht_delay_by_ft(my_project)
        #store tod network summaries in dictionary where key is tod:
        ft_summary_dict[key] = net_stats
        #store vmt by user class in dict:
        uc_vmt_dict[key] = vmt_by_user_class(my_project)

        #counts:
        df_tod_vol = get_link_counts(my_project, df_counts, key)
        counts_dict[key] = df_tod_vol
        
        get_screenline_volumes(screenline_dict, my_project) 

   #write out transit:
    print uc_vmt_dict
    col = 0
    transit_df = pd.DataFrame()
    for tod, df in transit_summary_dict.iteritems():
       #if transit_tod[tod] == 'am':
       #    pd.concat(objs, axis=0, join='outer', join_axes=None, ignore_index=False,
       #keys=None, levels=None, names=None, verify_integrity=False)

       workbook = writer.book
       index_format = workbook.add_format({'align': 'left', 'bold': True, 'border': True})
       transit_df = pd.merge(transit_df, df, 'outer', left_index = True, right_index = True)
       #transit_df[tod + '_board'] = df[tod + '_board']
       #transit_df[tod + '_time'] = df[tod + '_time']
    transit_df = transit_df[['6to7_board', '6to7_time', '7to8_board', '7to8_time', '8to9_board', '8to9_time', '9to10_board', '9to10_time', '10to14_board', '10to14_time', '14to15_board', '14to15_time']]
    transit_df.to_excel(excel_writer = writer, sheet_name = 'Transit Summaries')
       
       #if col == 0:
       #    worksheet = writer.sheets['Transit Summaries']
       #    routes = df.index.tolist()
       #    for route_no in range(len(routes)):
       #        worksheet.write_string(route_no + 1, 0, routes[route_no], index_format)
       #    col = col + 1
       #    df.to_excel(excel_writer = writer, sheet_name = 'Transit Summaries', index = False, startcol = col)
       #    col = col + 2
       #else:
       #    df.to_excel(excel_writer = writer, sheet_name = 'Transit Summaries', index = False, startcol = col)
       #    col = col + 2


    #*******write out counts:
    for value in counts_dict.itervalues():
        df_counts = df_counts.merge(value, right_index = True, left_index = True)
        df_counts = df_counts.drop_duplicates()
    
    #write counts out to xlsx:

    df_counts.to_excel(excel_writer = writer, sheet_name = 'Counts Output')

    #*******write out network summaries
    soundcast_tods = sound_cast_net_dict.keys
    list_of_measures = ['vmt', 'vht', 'delay']
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

    writer.save()

    #checks if openpyxl is installed (or pip to install it) in order to run xlautofit.run() to autofit the columns
    import imp
    try:
        imp.find_module('openpyxl')
        found_openpyxl = True
    except ImportError:
        found_openpyxl = False
    if found_openpyxl == True:
        xlautofit.run('outputs/network_summary_detailed.xlsx')
    else:
        try:
            imp.find_module('pip')
            found_pip = True
        except ImportError:
            found_pip = False
        if found_pip == True:
            pip.main(['install','openpyxl'])
        else:
            print('Library openpyxl needed to autofit columns')
    
    #writer = csv.writer(open('outputs/' + screenlines_file, 'ab'))
    #for key, value in screenline_dict.iteritems():
    #    print key, value
    #    writer.writerow([key, value])
    #writer = None

if __name__ == "__main__":
    main()



 





               
