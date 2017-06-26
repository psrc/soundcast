import pandas as pd
import inro.emme.desktop.app as app
import inro.modeller as _m
import inro.emme.matrix as ematrix
import inro.emme.database.matrix
import inro.emme.database.emmebank as _eb
import os, sys
import re 
import multiprocessing as mp
import subprocess
import json
from multiprocessing import Pool, pool
sys.path.append(os.path.join(os.getcwd(),"inputs"))
sys.path.append(os.path.join(os.getcwd(),"scripts"))
from emme_configuration import *
from input_configuration import *
from EmmeProject import *

#class EmmeProject:
#    def __init__(self, filepath):
#        self.desktop = app.start_dedicated(True, "cth", filepath)
#        self.m = _m.Modeller(self.desktop)
#        pathlist = filepath.split("/")
#        self.fullpath = filepath
#        self.filename = pathlist.pop()
#        self.dir = "/".join(pathlist) + "/"
#        self.bank = self.m.emmebank
#        self.tod = self.bank.title
#        self.current_scenario = list(self.bank.scenarios())[0]
#        self.data_explorer = self.desktop.data_explorer()
#    def network_counts_by_element(self, element):
#        network = self.current_scenario.get_network()
#        d = network.element_totals
#        count = d[element]
#        return count
#    def change_active_database(self, database_name):
#        for database in self.data_explorer.databases():
#            #print database.title()
#            if database.title() == database_name:
                
#                database.open()
#                print 'changed'
#                self.bank = self.m.emmebank
#                self.tod = self.bank.title
#                print self.tod
#                self.current_scenario = list(self.bank.scenarios())[0]
#    def process_modes(self, mode_file):
#        NAMESPACE = "inro.emme.data.network.mode.mode_transaction"
#        process_modes = self.m.tool(NAMESPACE)
#        process_modes(transaction_file = mode_file,
#              revert_on_error = True,
#              scenario = self.current_scenario)
                
#    def create_scenario(self, scenario_number, scenario_title = 'test'):
#        NAMESPACE = "inro.emme.data.scenario.create_scenario"
#        create_scenario = self.m.tool(NAMESPACE)
#        create_scenario(scenario_id=scenario_number,
#                        scenario_title= scenario_title)
#    def network_calculator(self, type, **kwargs):
#        spec = json_to_dictionary(type)
#        for name, value in kwargs.items():
#            if name == 'selections_by_link':
#                spec['selections']['link'] = value
#            else:
#                spec[name] = value
#        NAMESPACE = "inro.emme.network_calculation.network_calculator"
#        network_calc = self.m.tool(NAMESPACE)
#        self.network_calc_result = network_calc(spec)

   
#    def delete_links(self):
#        if self.network_counts_by_element('links') > 0:
#            NAMESPACE = "inro.emme.data.network.base.delete_links"
#            delete_links = self.m.tool(NAMESPACE)
#            #delete_links(selection="@dist=9", condition="cascade")
#            delete_links(condition="cascade")

#    def delete_nodes(self):
#        if self.network_counts_by_element('regular_nodes') > 0:
#            NAMESPACE = "inro.emme.data.network.base.delete_nodes"
#            delete_nodes = self.m.tool(NAMESPACE)
#            delete_nodes(condition="cascade")
#    def process_vehicles(self,vehicle_file):
#          NAMESPACE = "inro.emme.data.network.transit.vehicle_transaction"
#          process = self.m.tool(NAMESPACE)
#          process(transaction_file = vehicle_file,
#            revert_on_error = True,
#            scenario = self.current_scenario)

#    def process_base_network(self, basenet_file):
#        NAMESPACE = "inro.emme.data.network.base.base_network_transaction"
#        process = self.m.tool(NAMESPACE)
#        process(transaction_file = basenet_file,
#              revert_on_error = True,
#              scenario = self.current_scenario)
#    def process_turn(self, turn_file):
#        NAMESPACE = "inro.emme.data.network.turn.turn_transaction"
#        process = self.m.tool(NAMESPACE)
#        process(transaction_file = turn_file,
#            revert_on_error = False,
#            scenario = self.current_scenario)

#    def process_transit(self, transit_file):
#        NAMESPACE = "inro.emme.data.network.transit.transit_line_transaction"
#        process = self.m.tool(NAMESPACE)
#        process(transaction_file = transit_file,
#            revert_on_error = True,
#            scenario = self.current_scenario)
#    def process_shape(self, linkshape_file):
#        NAMESPACE = "inro.emme.data.network.base.link_shape_transaction"
#        process = self.m.tool(NAMESPACE)
#        process(transaction_file = linkshape_file,
#            revert_on_error = True,
#            scenario = self.current_scenario)
#    def change_scenario(self):

#        self.current_scenario = list(self.bank.scenarios())[0]


    
def json_to_dictionary(dict_name):

    #Determine the Path to the input files and load them
    input_filename = os.path.join('inputs/skim_params/',dict_name+'.json').replace("\\","/")
    my_dictionary = json.load(open(input_filename))

    return(my_dictionary)


          
def import_tolls(emmeProject):
    #create extra attributes:
    create_extras = emmeProject.m.tool("inro.emme.data.extra_attribute.create_extra_attribute")
    t23 = create_extras(extra_attribute_type="LINK",extra_attribute_name="@toll1",extra_attribute_description="SOV Tolls",overwrite=True)
    t24 = create_extras(extra_attribute_type="LINK",extra_attribute_name="@toll2",extra_attribute_description="HOV 2 Tolls",overwrite=True)
    t25 = create_extras(extra_attribute_type="LINK",extra_attribute_name="@toll3",extra_attribute_description="HOV 3+ Tolls",overwrite=True)
    t26 = create_extras(extra_attribute_type="LINK",extra_attribute_name="@trkc1",extra_attribute_description="Light Truck Tolls",overwrite=True)
    t27 = create_extras(extra_attribute_type="LINK",extra_attribute_name="@trkc2",extra_attribute_description="Medium Truck Tolls",overwrite=True)
    t28 = create_extras(extra_attribute_type="LINK",extra_attribute_name="@trkc3",extra_attribute_description="Heavy Truck Tolls",overwrite=True)
    t28 = create_extras(extra_attribute_type="LINK",extra_attribute_name="@brfer",extra_attribute_description="Bridge & Ferrry Flag",overwrite=True)
    t28 = create_extras(extra_attribute_type="LINK",extra_attribute_name="@rdly",extra_attribute_description="Intersection Delay",overwrite=True)
 
    
    import_attributes = emmeProject.m.tool("inro.emme.data.network.import_attribute_values")

    tod_4k = sound_cast_net_dict[emmeProject.tod]

    attr_file= ['inputs/tolls/' + tod_4k + '_roadway_tolls.in', 'inputs/tolls/ferry_vehicle_fares.in', 'inputs/networks/rdly/' + tod_4k + '_rdly.txt']

    # set tolls
    #for file in attr_file:
    import_attributes(attr_file[0], scenario = emmeProject.current_scenario,
              column_labels={0: "inode",
                             1: "jnode",
                             2: "@toll1",
                             3: "@toll2",
                             4: "@toll3",
                             5: "@trkc1",
                             6: "@trkc2",
                             7: "@trkc3"},
              revert_on_error=True)

    import_attributes(attr_file[1], scenario = emmeProject.current_scenario,
              column_labels={0: "inode",
                             1: "jnode",
                             2: "@toll1",
                             3: "@toll2",
                             4: "@toll3",
                             5: "@trkc1",
                             6: "@trkc2",
                             7: "@trkc3"},
              revert_on_error=True)

    
    #@rdly:
    import_attributes(attr_file[2], scenario = emmeProject.current_scenario,
             revert_on_error=False)
    
    #We are using 1/4 rdly now. Input values are factored by half so we need to half again.  
    emmeProject.network_calculator("link_calculation", result = "@rdly", expression = "@rdly * .50")


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

def distance_pricing(rate, emmeProject):
   toll_atts = ["@toll1", "@toll2", "@toll3", "@trkc1", "@trkc2", "@trkc3"]
   network = emmeProject.current_scenario.get_network()
   for link in network.links():
        if link.data3 > 0:
            for att in toll_atts:
                link[att] = link[att] + (link.length * rate)
            
    
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

    for name, type in attribute_dict.iteritems():
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

            if node.sum_arts_lanecap_3to5_entering_int > 0.0 and link.data3 <> 0 and link.data3 <> 5:
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
            
    for name, type in attribute_dict.iteritems():
            network.delete_attribute(type, name)
    emmeProject.current_scenario.publish_network(network)

def run_importer(project_name):
    my_project = EmmeProject(project_name)
    headway_df = pd.DataFrame.from_csv('inputs/networks/' + headway_file)
    for key, value in sound_cast_net_dict.iteritems():
        my_project.change_active_database(key)
        for scenario in list(my_project.bank.scenarios()):
            my_project.bank.delete_scenario(scenario)
        #create scenario
        my_project.bank.create_scenario(1002)
        my_project.change_scenario()
        my_project.delete_links()
        my_project.delete_nodes()
      
        my_project.process_modes('inputs/networks/' + mode_file)
        
        my_project.process_base_network('inputs/networks/' + value + base_net_name)
        my_project.process_turn('inputs/networks/' + value + turns_name)
        if my_project.tod in load_transit_tod:
           my_project.process_vehicles('inputs/networks/' + transit_vehicle_file)
           my_project.process_transit('inputs/networks/' + value + transit_name)
           update_headways(my_project, headway_df)
        #import tolls
        import_tolls(my_project)
        arterial_delay(my_project, rdly_factor)
        if add_distance_pricing:
            distance_pricing(distance_rate_dict[value], my_project)
        
        

def main():
    print network_summary_project
    run_importer(network_summary_project)
    
    returncode = subprocess.call([sys.executable,'scripts/network/daysim_zone_inputs.py'])
    if returncode != 0:
        sys.exit(1)
    
    print 'done'

if __name__ == "__main__":
    main()






