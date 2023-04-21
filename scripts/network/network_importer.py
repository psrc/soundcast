import pandas as pd
import os, sys
import re 
import multiprocessing as mp
import subprocess
import json
from multiprocessing import Pool, pool
sys.path.append(os.path.join(os.getcwd(),"inputs"))
sys.path.append(os.path.join(os.getcwd(),"scripts"))
sys.path.append(os.getcwd())
# from emme_configuration import *
# from input_configuration import *
from EmmeProject import *
import toml
config = toml.load(os.path.join(os.getcwd(), 'configuration/input_configuration.toml'))
network_config = toml.load(os.path.join(os.getcwd(), 'configuration/network_configuration.toml'))
emme_config = toml.load(os.path.join(os.getcwd(), 'configuration/emme_configuration.toml'))

def json_to_dictionary(dict_name):

    #Determine the Path to the input files and load them
    input_filename = os.path.join('inputs/model/skim_parameters/',dict_name+'.json').replace("\\","/")
    my_dictionary = json.load(open(input_filename))

    return(my_dictionary)
          
def multiwordReplace(text, replace_dict):
    rc = re.compile(r"[A-Za-z_]\w*")
    def translate(match):
        word = match.group(0)
        return replace_dict.get(word, word)
    return rc.sub(translate, text)

def update_headways(emmeProject, headways_df):
    network = emmeProject.current_scenario.get_network()
    for transit_line in network.transit_lines():
        row = headways_df.loc[(headways_df.id == int(transit_line.id))]
        if int(row['hdw_' + emmeProject.tod]) > 0:
            transit_line.headway = int(row['hdw_' + emmeProject.tod])
        else:
            network.delete_transit_line(transit_line.id)
    emmeProject.current_scenario.publish_network(network)

def distance_pricing(distance_rate, emmeProject):
   toll_atts = ["@toll1", "@toll2", "@toll3", "@trkc1", "@trkc2", "@trkc3"]
   network = emmeProject.current_scenario.get_network()
   for link in network.links():
        if link.data3 > 0:
            if config['add_distance_pricing']:
                for att in toll_atts:
                    link[att] = link[att] + (link.length * distance_rate)
   emmeProject.current_scenario.publish_network(network)

def arterial_delay(emmeProject, factor):
    network = emmeProject.current_scenario.get_network()
    #if '@rdly' in network.attributes('LINK'):
    #    emmeProject.delete_extra_attribute('@rdly')
    emmeProject.create_extra_attribute('LINK', '@rdly', 'arterial delay', True)
    network = emmeProject.current_scenario.get_network()
    attribute_dict = {'arterial_flag' : 'LINK', 
                      'lane_3to5' : 'LINK', 
                      'lanecap_3to5' : 'LINK', 
                      'oneway_arterial_flag' : 'LINK', 
                      'red' : 'LINK', 
                      'rdly' : 'LINK',  
                      'number_arts_entering_int' : 'NODE', 
                      'sum_arts_lane_3to5_entering_int' : 'NODE',
                      'sum_arts_lanecap_3to5_entering_int' : 'NODE', 
                      'number_oneway_arts_entering_int' : 'NODE', 
                      'cycle' : 'NODE'}

    for name, type in attribute_dict.items():
        network.create_attribute(type, name)
    
    for link in network.links():
        ftype = link.data3
        lanes = link.num_lanes
        lanecap = link.data1


    # 1) Set temporary link attributes

        # Temp Link Attribute [arterial_flag] = 1 for arterials (ftype=3,4 or 6)
        if ftype == 3 or ftype == 4 or ftype == 6: 
            link.arterial_flag = 1
        else: 
            link.arterial_flag = 0

        # Temp Link Attribute [lane_3to5] = (minimum of 5 or lanes+2 (range 3-5) wherever arterial_flag=1)
        if link.arterial_flag == 1: 
            link.lane_3to5 = min(5, (lanes+2))
        else:
            link.lane_3to5 = 0

        # Temp Link Attribute [lanecap_3to5] = (minimum of 5*lanecap or (lanes+2)*lanecap wherever arterial_flag=1)
        if link.arterial_flag == 1:
            link.lanecap_3to5 = min((5*lanecap),((lanes+2)*lanecap))
        else:
            link.lanecap_3to5 = 0 

        # Temp Link Attribute [oneway_arterial_flag] = 1 for oneway arterials (ftype=4)
        if ftype == 4: 
            link.oneway_arterial_flag = 1
        else:
            link.oneway_arterial_flag = 0


    # 2) Aggregate link attributes to temporary node attributes

    for node in network.nodes():

        node.number_arts_entering_int = 0    
        node.sum_arts_lane_3to5_entering_int = 0
        node.sum_arts_lanecap_3to5_entering_int = 0
        node.number_oneway_arts_entering_int = 0
            
        for link in node.incoming_links():

            # Temp Node Attribute [number_arts_entering_int] = number of arterial links (arterial_flag = 1) entering the intersection (node --> j-node of link)
            node.number_arts_entering_int = node.number_arts_entering_int + link.arterial_flag
                
            # Temp Node Attribute [sum_arts_lane_3to5_entering_int] = sum of lane_3to5 for arterials (arterial_flag = 1) entering the intersection (node --> j-node of link) 
            node.sum_arts_lane_3to5_entering_int = node.sum_arts_lane_3to5_entering_int + link.lane_3to5
        
            # Temp Node Attribute [sum_arts_lanecap_3to5_entering_int] = sum of lanecap_3to5 for arterials (arterial_flag = 1) entering the intersection (node --> j-node of link)
            node.sum_arts_lanecap_3to5_entering_int = node.sum_arts_lanecap_3to5_entering_int + link.lanecap_3to5
        
            # Temp Node Attribute [number_oneway_arts_entering_int] = number of oneway arterial links (ftype=4) entering the intersection (node --> j-node of link)
            node.number_oneway_arts_entering_int = node.number_oneway_arts_entering_int + link.oneway_arterial_flag
        
 
    # 3) Calculate intersection cycle time (permanent node attribute - [cycle] in minutes at all nodes)

    for node in network.nodes():

        node.cycle = 0.0

        for link in node.incoming_links():

            # Permanent Node Attribute [cycle] = signal cycle duration in minutes where number_arts_entering_int > 2 or number_oneway_arts_entering_int > 1
            if (node.number_arts_entering_int > 2) or (node.number_oneway_arts_entering_int > 1):
                node.cycle = 1.0 + (node.sum_arts_lane_3to5_entering_int / 8.0) * (node.number_arts_entering_int / 4.0)
            else:
                node.cycle = 0.0
              

    # 4) Calculate red time (permanent link attribute - [red] in minutes at j-node of every arterial link

    for node in network.nodes():

        for link in node.incoming_links():

            link.red = 0.0

            if node.sum_arts_lanecap_3to5_entering_int > 0.0 and link.data3 != 0 and link.data3 != 5:
                link.red = 1.2 * node.cycle * (1 - (node.number_arts_entering_int * link.lanecap_3to5) / (2 * node.sum_arts_lanecap_3to5_entering_int))
            else:
                link.red = 0.0

            # Use this to match 4K macro results.  Revise in the future to consider freeway and expressway links that end at signalized intersections.
            if link.data3 == 1 or link.data3 == 2:
                link.red = 0.0
        

    # 5) Calculate intersection delay factor (permanent link attribute - [rdly] in minutes for every arterial link
            # restrict to arterials for now - not ul3=0 or 5

    for node in network.nodes():

        for link in node.incoming_links():

            link.rdly = 0.0

            if node.cycle:
                link.rdly = min(1,max(0.2,(link.red * link.red) / (2 * node.cycle)))

    # 6) Factor rdly by 0.5
    
            link.rdly = link.rdly * factor
            link['@rdly'] = link.rdly
            
            #print link.i_node, link.j_node, link.rdly, link.data3
            
    for name, type in attribute_dict.items():
            network.delete_attribute(type, name)
    emmeProject.current_scenario.publish_network(network)

def run_importer(project_name):
    my_project = EmmeProject(project_name)
    headway_df = pd.read_csv('inputs/scenario/networks/headways.csv')
    tod_index = pd.Series(range(1,len(tod_networks)+1),index=tod_networks)
    for key, value in network_config['sound_cast_net_dict'].items():
        my_project.change_active_database(key)
        for scenario in list(my_project.bank.scenarios()):
            my_project.bank.delete_scenario(scenario)
        #create scenario
        my_project.bank.create_scenario(1002)
        my_project.change_scenario()
        my_project.delete_links()
        my_project.delete_nodes()
      
        my_project.process_modes('inputs/scenario/networks/modes.txt')
        
        my_project.process_base_network('inputs/scenario/networks/roadway/' + value + '_roadway.in')
        
        my_project.process_shape('inputs/scenario/networks/shape/' + value + '_shape.in')
        my_project.process_turn('inputs/scenario/networks/turns/' + value + '_turns.in')
        if my_project.tod in network_config['transit_tod_list']:
            my_project.process_vehicles('inputs/scenario/networks/vehicles.txt')
            my_project.process_transit('inputs/scenario/networks/transit/' + value + '_transit.in')
            for att in network_config['transit_line_extra_attributes']:
                my_project.create_extra_attribute('TRANSIT_LINE', att)
            my_project.import_extra_attributes('inputs/scenario/networks/extra_attributes/' + value + '_link_attributes.in/extra_transit_lines_'+ str(tod_index[value]) +'.txt', False)
            update_headways(my_project, headway_df)

        print(value)
        for att in network_config['link_extra_attributes']:
            my_project.create_extra_attribute('LINK', att)
        for att in network_config['node_extra_attributes']:
            my_project.create_extra_attribute('NODE', att)
        my_project.import_extra_attributes('inputs/scenario/networks/extra_attributes/' + value + '_link_attributes.in/extra_links_'+ str(tod_index[value]) +'.txt')
        my_project.import_extra_attributes('inputs/scenario/networks/extra_attributes/' + value + '_link_attributes.in/extra_nodes_'+ str(tod_index[value]) +'.txt')

        arterial_delay(my_project, rdly_factor)
        if config['add_distance_pricing']:
            distance_pricing(config['distance_rate_dict'][value], my_project)
       
def main():

    run_importer(network_config['network_summary_project'])
    
    print('networks imported')

if __name__ == "__main__":
    main()






