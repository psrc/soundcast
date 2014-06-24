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
from multiprocessing import Pool
import pandas as pd
sys.path.append(os.path.join(os.getcwd(),"inputs"))
from input_configuration import *


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
    for tod, df in transit_summary_dict.iteritems():
       #if transit_tod[tod] == 'am':
       #    pd.concat(objs, axis=0, join='outer', join_axes=None, ignore_index=False,
       #keys=None, levels=None, names=None, verify_integrity=False)

       with open('outputs/' + tod + '_transit.csv', 'wb') as f:
                  df.to_csv(f)

    #*******write out counts:
    for value in counts_dict.itervalues():
        df_counts = df_counts.merge(value, right_index = True, left_index = True)
        df_counts = df_counts.drop_duplicates()
    
    #write counts out to csv:
    with open('outputs/' + counts_output_file, 'wb') as f:
        df_counts.to_csv(f)
    f.close


    #*******write out network summaries
    #will rewrite using pandas
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
    
    #write out the rows and columns
    for key, value in ft_summary_dict.iteritems():
        #tod
        row_list.append(key)
        #4k time period:
        row_list.append(sound_cast_net_dict[key])
        for measure in list_of_measures:
            for factype in list_of_FTs:
                #print measure, factype
                row_list.append(value[measure][factype])
        list_of_rows.append(row_list)
        row_list = []
    
    writeCSV('outputs/' + net_summary_file, list_of_rows)

    #*******write out screenlines
    with open('outputs/' + screenlines_file, 'wb') as f:
        writer = csv.writer(f)
        for key, value in screenline_dict.iteritems():
           #print key, value
           writer.writerow([key, value])
    f.close

    
    

    a = 0
    with open('outputs/' + 'uc_vmt.csv', 'wb') as f:
        writer = csv.writer(f)
        #write header:
        for tod, uv_vmt_list in uc_vmt_dict.iteritems():
            if a == 0:
                #header
                writer.writerow(uc_list)
                uv_vmt_list.append(tod)
                writer.writerow(uv_vmt_list)
            else: 
                uv_vmt_list.append(tod)
                writer.writerow(uv_vmt_list)
            a = a + 1
    f.close
    
    
    #writer = csv.writer(open('outputs/' + screenlines_file, 'ab'))
    #for key, value in screenline_dict.iteritems():
    #    print key, value
    #    writer.writerow([key, value])
    #writer = None

if __name__ == "__main__":
    main()



 





               
