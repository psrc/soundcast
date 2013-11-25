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

project = 'D:/soundcast/soundcat/Projects/LoadTripTables/LoadTripTables.emp'
ft_dict = {'highway' : 'ul3 = 1 or ul3 = 2', 'arterial' : 'ul3 = 3 or ul3 = 4 or ul3 = 6', 'connectors' : 'ul3 = 5'}
sound_cast_net_dict = {'5to6' : 'ni', '6to7' : 'am', '7to8' : 'am', '8to9' : 'am', '9to10' : 'md', '10to14' : 'md', '14to15' : 'md', '15to16' : 'pm', '16to17' : 'pm', '17to18' : 'pm', '18to20' : 'ev', '20to5' : 'ni'}


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
    def network_counts_by_element(self, element):
        network = self.current_scenario.get_network()
        d = network.element_totals
        count = d[element]
        return count
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
def json_to_dictionary(dict_name):

    #Determine the Path to the input files and load them
    input_filename = os.path.join('D:/soundcast/soundcat/inputs/skim_params/',dict_name+'.txt').replace("\\","/")
    my_dictionary = json.load(open(input_filename))

    return(my_dictionary)
 
def calc_vmt_by_ft(modeler):
     create_extras = modeler.tool("inro.emme.data.extra_attribute.create_extra_attribute")
     network_calc = modeler.tool("inro.emme.network_calculation.network_calculator")
     delete_extras = modeler.tool("inro.emme.data.extra_attribute.delete_extra_attribute")
     
     #create an extra attribute to hold total vehicles by link
     t1 = create_extras(extra_attribute_type="LINK",extra_attribute_name="@tveh",extra_attribute_description="total vehicles",overwrite=True)
     t2 = create_extras(extra_attribute_type="LINK",extra_attribute_name="@mveh",extra_attribute_description="med truck vehicles",overwrite=True)
     t3 = create_extras(extra_attribute_type="LINK",extra_attribute_name="@hveh",extra_attribute_description="heavy truck vehicles",overwrite=True)
     # Create the temporary attributes to hold summary calcs
     t4 = create_extras(extra_attribute_type="LINK",extra_attribute_name="@vmt",extra_attribute_description="temp link calc 1",overwrite=True)
     t5 = create_extras(extra_attribute_type="LINK",extra_attribute_name="@vht",extra_attribute_description="temp link calc 1",overwrite=True)
     t6 = create_extras(extra_attribute_type="LINK",extra_attribute_name="@hdw",extra_attribute_description="temp link calc 1",overwrite=True)
     #convert auto vehicle equivlents to truck vehicles:
     #medium trucks:
     network_calc_spec = json_to_dictionary("link_calculation")
     mod_spec = network_calc_spec
     mod_spec["result"] = "@mveh"
     mod_spec["expression"] = '@metrk/1.5'
     network_calc(mod_spec)
    
     #heavy trucks:
     mod_spec = network_calc_spec
     mod_spec["result"] = "@hveh"
     mod_spec["expression"] = '@hvtrk/2'        
     network_calc(mod_spec)
     
     #hdw- number of buses:
     #mod_spec = network_calc_spec
     #mod_spec["result"] = "@hdw"
     #mod_spec["expression"] = 'hdw'
     #network_calc(mod_spec)
     
     #create a string epression using existing attributes for all vehicle types/modes. Same as 
     #str_expression =""
     #matrix_dict = json_to_dictionary("user_classes")
     
     #for x in range (0, len(matrix_dict["Highway"])):
     #   extra_attribute_name= "@"+matrix_dict["Highway"][x]["Name"]
     #   str_expression = str_expression + extra_attribute_name + " + "
     #remove the last plus sign
     #str_expression = str_expression[:-2]
     #print 
     str_expression = '@svtl1 + @svtl2 + @svtl3 + @svnt1 + @h2tl1 + @h2tl2 + @h2tl3 + @h2nt1 + @h3tl1 + @h3tl2 + @h3tl3 + @h3nt1 + @lttrk + @mveh + @hveh'
     #str_expression = '@svtl1 + @svtl2 + @svtl3 + @svnt1 + @h2tl1 + @h2tl2 + @h2tl3 + @h2nt1 + @h3tl1 + @h3tl2 + @h3tl3 + @h3nt1'
     #network_calc_spec = json_to_dictionary("link_calculation")
     mod_spec = network_calc_spec
     mod_spec["result"] = "@tveh"
     mod_spec["expression"] = str_expression
     #mod_spec["selections"]["link"] = None
     network_calc(mod_spec)
     sum = 0
     results_dict = {}
     vmt_dict = {}
     for key, value in ft_dict.iteritems():    
        mod_spec = network_calc_spec
        mod_spec["result"] = "@vmt"
        mod_spec["selections"]["link"] = value
        mod_spec["expression"] = "@tveh * length"
        x = network_calc(mod_spec)
        vmt_dict[key] = x['sum']
     print vmt_dict
     #print sum(vmt_dict.values())
     results_dict['vmt'] = vmt_dict
     print sum
     vht_dict = {}
     for key, value in ft_dict.iteritems():    
        mod_spec = network_calc_spec
        mod_spec["result"] = "@vht"
        mod_spec["selections"]["link"] = value
        mod_spec["expression"] = "@tveh * timau / 60"
        x = network_calc(mod_spec)
        vht_dict[key] = x['sum']
     results_dict['vht'] = vht_dict

     delay_dict = {}
     for key, value in ft_dict.iteritems():    
        mod_spec = network_calc_spec
        mod_spec["result"] = None
        mod_spec["selections"]["link"] = value
        mod_spec["expression"] = "@tveh*(timau-(length*60/ul2))/60"
        x = network_calc(mod_spec)
        delay_dict[key] = x['sum']
     print vmt_dict
     #print sum(vmt_dict.values())
     results_dict['delay'] = delay_dict
     return results_dict

    



def aggregate_totals(aggregate_dict, soundcast_network_summary, sum_stat):
    #get a unique list of the aggregation names (e.g. 'am, 'md', 'pm', 'ev', 'ni' if aggregating results to 4k time periods).
    aggregate_periods = list(set(aggregate_dict.values()))
    #create a dictionary to hold 4k time periods and vmt values
    aggregate_results_dict = {}
    for tp in aggregate_periods:
        #populate a dict with aggregation names and 0 values
        aggregate_results_dict[tp] = 0

    for key, value in soundcast_network_summary.iteritems():
        #get the aggregation name by passing in soundcat tod:
        tp = aggregate_dict[key]
        #sum the tod measure (e.g. vmt or vht) using sum_stat as a key and associate with aggregation name, eg. 'am' 
        aggregate_results_dict[tp] =  aggregate_results_dict[tp] + sum(value[sum_stat].values())
    
    return aggregate_results_dict 

def daily_totals_by_ft(soundcast_network_summary, sum_stat):
    daily_totals_dict = {}
    fac_types = list(ft_dict.keys())
    for fac_type in fac_types:
        daily_totals_dict[fac_type] = 0
    for network_measure_dict in soundcast_network_summary.values():
        for fac_type, ft_total in network_measure_dict[sum_stat].iteritems():
         
            daily_totals_dict[fac_type] = daily_totals_dict[fac_type] + ft_total
    return daily_totals_dict

def writeCSV(fileNamePath, listOfTuples):
    myWriter = csv.writer(open(fileNamePath, 'ab'))
    for l in listOfTuples:
        myWriter.writerow(l)


ft_summary_dict = {}
my_project = EmmeProject(project)
for key, value in sound_cast_net_dict.iteritems():
        my_project.change_active_database(key)
        test = calc_vmt_by_ft(my_project.m)
        ft_summary_dict[key] = test
#d = ft_summary_dict['7to8']['vmt']
#print sum(d.values())



vmt_by_4k_time_period = aggregate_totals(sound_cast_net_dict, ft_summary_dict, 'vmt')
vht_by_4k_time_period = aggregate_totals(sound_cast_net_dict, ft_summary_dict, 'vht')
vmt_by_ft_daily_totals = daily_totals_by_ft(ft_summary_dict, 'vmt')
vht_by_ft_daily_totals = daily_totals_by_ft(ft_summary_dict, 'vht')

soundcast_tods = sound_cast_net_dict.keys
list_of_measures = ['vmt', 'vht', 'delay']
list_of_FTs = ft_dict.keys()
row_list = []
list_of_rows = []

header = ['tod', 'TP_4k']
for measure in list_of_measures:
    for factype in list_of_FTs:
        header.append(factype + '_' + measure)
list_of_rows.append(header)
for key, value in ft_summary_dict.iteritems():
    #tod
    row_list.append(key)
    #4k time period:
    row_list.append(sound_cast_net_dict[key])
    for measure in list_of_measures:
        for factype in list_of_FTs:
            print measure, factype
            row_list.append(value[measure][factype])
    list_of_rows.append(row_list)
    row_list = []
#print list_of_rows
writeCSV("C:\\outTest.csv", list_of_rows)

#vmt_by_4k_time_period = {}
#time_periods_4k = list(set(sound_cast_net_dict.values()))
#create a dictionary to hold 4k time periods and vmt values
#for tp in time_periods_4k:
#    vmt_by_4k_time_period[tp] = 0

#for key, value in ft_summary_dict.iteritems():
#    print key, value
    #get the 4k time of day:
#    tp = sound_cast_net_dict[key]
 #   vmt_by_4k_time_period[tp] = vmt_by_4k_time_period[tp] + sum(value['vmt'].values())






               
