import pandas as pd
import numpy as np
import os, sys
import h5py
sys.path.append(os.path.join(os.getcwd(),"scripts"))
from EmmeProject import *
from input_configuration import *
from emme_configuration import *

extra_attributes_dict = {'@tveh' : 'total vehicles', 
                         '@mveh' : 'medium trucks', 
                         '@hveh' : 'heavy trucks', 
                         '@vmt' : 'vmt',\
                         '@vht' : 'vht', 
                         '@trnv' : 'buses in auto equivalents',
                         '@ovol' : 'observed volume', 
                         '@bveh' : 'number of buses'}

def get_link_attribute(attr, network):
    ''' Return dataframe of link attribute and link ID'''
    link_dict = {}
    for i in network.links():
        link_dict[i.id] = i[attr]
    df = pd.DataFrame({'link_id': link_dict.keys(), attr: link_dict.values()})
    return df

def calc_total_vehicles(my_project):
     '''For a given time period, calculate link level volume, store as extra attribute on the link'''
    
     #medium trucks
     my_project.network_calculator("link_calculation", result = '@mveh', expression = '@metrk/1.5')
     
     #heavy trucks:
     my_project.network_calculator("link_calculation", result = '@hveh', expression = '@hvtrk/2.0')
     
     #busses:
     my_project.network_calculator("link_calculation", result = '@bveh', expression = '@trnv3/2.0')
     
     #calc total vehicles, store in @tveh 
     str_expression = '@svtl1 + @svtl2 + @svtl3 + @svnt1 +  @svnt2 + @svnt3 + @h2tl1 + @h2tl2 + @h2tl3 + @h2nt1 + @h2nt2 + @h2nt3 + @h3tl1\
                                + @h3tl2 + @h3tl3 + @h3nt1 + @h3nt2 + @h3nt3 + @lttrk + @mveh + @hveh + @bveh'
     my_project.network_calculator("link_calculation", result = '@tveh', expression = str_expression)


def get_aadt_trucks(my_project):
    '''Calculate link level daily total truck passenger equivalents for medium and heavy, store in a DataFrame'''
    
    link_list = []

    for key, value in sound_cast_net_dict.iteritems():
        my_project.change_active_database(key)
        
        # Create extra attributes to store link volume data
        for name, desc in extra_attributes_dict.iteritems():
            my_project.create_extra_attribute('LINK', name, desc, 'True')
        
        ## Calculate total vehicles for each link
        calc_total_vehicles(my_project)
        
        # Loop through each link, store length and truck pce
        network = my_project.current_scenario.get_network()
        for link in network.links():
            link_list.append({'link_id' : link.id, '@mveh' : link['@mveh'], '@hveh' : link['@hveh'], 'length' : link.length})
            
    df = pd.DataFrame(link_list, columns = link_list[0].keys())       
    
    grouped = df.groupby(['link_id'])
    
    df = grouped.agg({'@mveh':sum, '@hveh':sum, 'length':min})
    
    df.reset_index(level=0, inplace=True)
    
    return df
    
        

def main():
   print 'running truck_summary'
   truck_counts = pd.read_excel('scripts/summarize/inputs/network_summary/truck_counts_2014.xlsx')
   filepath = r'projects/' + master_project + r'/' + master_project + '.emp'
   my_project = EmmeProject(filepath)
   truck_volumes =get_aadt_trucks(my_project)
   truck_compare = pd.merge(truck_counts, truck_volumes, left_on = 'ij_id', right_on = 'link_id')
   truck_compare['med_hvy_tot'] = truck_compare['@mveh']+truck_compare['@hveh']
   truck_compare['model-count'] = truck_compare['med_hvy_tot']- truck_compare['Observed']
   truck_compare['percentdiff'] = truck_compare['model-count']/truck_compare['Observed']
   writer = pd.ExcelWriter('outputs/trucks_vol_summary.xlsx')
   truck_compare.to_excel(writer, 'Sheet1')

if __name__ == "__main__":
	main()