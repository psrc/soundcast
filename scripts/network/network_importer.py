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
from emme_configuration import *
from input_configuration import *

#project = 'Projects/LoadTripTables/LoadTripTables.emp'
#tod_networks = ['am', 'md', 'pm', 'ev', 'ni']
#sound_cast_net_dict = {'5to6' : 'ni', '6to7' : 'am', '7to8' : 'am', '8to9' : 'am', 
#                       '9to10' : 'md', '10to14' : 'md', '14to15' : 'md', 
#                       '15to16' : 'pm', '16to17' : 'pm', '17to18' : 'pm', 
#                       '18to20' : 'ev', '20to5' : 'ni'}
#load_transit_tod = ['6to7', '7to8', '8to9', '9to10', '10to14', '14to15']

#mode_file = 'modes.txt'
#transit_vehicle_file = 'vehicles.txt' 
#base_net_name = '_roadway.in'
#turns_name = '_turns.in'
#transit_name = '_transit.in'
#shape_name = '_link_shape_1002.txt'
#no_toll_modes = ['s', 'h', 'i', 'j']

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
    def process_modes(self, mode_file):
        NAMESPACE = "inro.emme.data.network.mode.mode_transaction"
        process_modes = self.m.tool(NAMESPACE)
        process_modes(transaction_file = mode_file,
              revert_on_error = True,
              scenario = self.current_scenario)
                
    def create_scenario(self, scenario_number, scenario_title = 'test'):
        NAMESPACE = "inro.emme.data.scenario.create_scenario"
        create_scenario = self.m.tool(NAMESPACE)
        create_scenario(scenario_id=scenario_number,
                        scenario_title= scenario_title)
    def network_calculator(self, type, **kwargs):
        spec = json_to_dictionary(type)
        for name, value in kwargs.items():
            if name == 'selections_by_link':
                spec['selections']['link'] = value
            else:
                spec[name] = value
        NAMESPACE = "inro.emme.network_calculation.network_calculator"
        network_calc = self.m.tool(NAMESPACE)
        self.network_calc_result = network_calc(spec)

   
    def delete_links(self):
        if self.network_counts_by_element('links') > 0:
            NAMESPACE = "inro.emme.data.network.base.delete_links"
            delete_links = self.m.tool(NAMESPACE)
            #delete_links(selection="@dist=9", condition="cascade")
            delete_links(condition="cascade")

    def delete_nodes(self):
        if self.network_counts_by_element('regular_nodes') > 0:
            NAMESPACE = "inro.emme.data.network.base.delete_nodes"
            delete_nodes = self.m.tool(NAMESPACE)
            delete_nodes(condition="cascade")
    def process_vehicles(self,vehicle_file):
          NAMESPACE = "inro.emme.data.network.transit.vehicle_transaction"
          process = self.m.tool(NAMESPACE)
          process(transaction_file = vehicle_file,
            revert_on_error = True,
            scenario = self.current_scenario)

    def process_base_network(self, basenet_file):
        NAMESPACE = "inro.emme.data.network.base.base_network_transaction"
        process = self.m.tool(NAMESPACE)
        process(transaction_file = basenet_file,
              revert_on_error = True,
              scenario = self.current_scenario)
    def process_turn(self, turn_file):
        NAMESPACE = "inro.emme.data.network.turn.turn_transaction"
        process = self.m.tool(NAMESPACE)
        process(transaction_file = turn_file,
            revert_on_error = False,
            scenario = self.current_scenario)

    def process_transit(self, transit_file):
        NAMESPACE = "inro.emme.data.network.transit.transit_line_transaction"
        process = self.m.tool(NAMESPACE)
        process(transaction_file = transit_file,
            revert_on_error = True,
            scenario = self.current_scenario)
    def process_shape(self, linkshape_file):
        NAMESPACE = "inro.emme.data.network.base.link_shape_transaction"
        process = self.m.tool(NAMESPACE)
        process(transaction_file = linkshape_file,
            revert_on_error = True,
            scenario = self.current_scenario)
    def change_scenario(self):

        self.current_scenario = list(self.bank.scenarios())[0]


    
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
             revert_on_error=True)
    
    #We are using the same rdly has 4k. No need to factor. 
    #emmeProject.network_calculator("link_calculation", result = "@rdly", expression = "@rdly * .50")

# set bridge/ferry flags

    #bridge_ferry_flag__file = function_file = 'inputs/tolls/bridge_ferry_flags.in'
    #import_attributes(bridge_ferry_flag__file, scenario = emmeProject.current_scenario,
    #          column_labels={0: "inode",
    #                         1: "jnode",
    #                         2: "@brfer"},
    #          revert_on_error=True)

    
    # change modes on tolled network, but exclude some bridges/ferries
    if create_no_toll_network:
        network = emmeProject.current_scenario.get_network()
        for link in network.links():
            if link['@toll1'] > 0 and link['@brfer'] == 0:
                for i in no_toll_modes:
                    link.modes -= set([network.mode(i)])
        emmeProject.current_scenario.publish_network(network)

def multiwordReplace(text, replace_dict):
    rc = re.compile(r"[A-Za-z_]\w*")
    def translate(match):
        word = match.group(0)
        return replace_dict.get(word, word)
    return rc.sub(translate, text)

def run_importer(project_name):
    my_project = EmmeProject(project_name)
    for key, value in sound_cast_net_dict.iteritems():
        my_project.change_active_database(key)
        for scenario in list(my_project.bank.scenarios()):
            my_project.bank.delete_scenario(scenario)
        #create scenario
        my_project.bank.create_scenario(1002)
        my_project.change_scenario()
        #print key
        my_project.delete_links()
        my_project.delete_nodes()
      
        my_project.process_modes('inputs/networks/' + mode_file)
        
        my_project.process_base_network('inputs/networks/' + value + base_net_name)
       # my_project.process_base_network('inputs/networks/fixes/ferries/' + value + base_net_name)

        my_project.process_turn('inputs/networks/' + value + turns_name)
    #my_project.process_shape('/inputs/network' + tod_network + shape_name)

        if my_project.tod in load_transit_tod:
           my_project.process_vehicles('inputs/networks/' + transit_vehicle_file)
           my_project.process_transit('inputs/networks/' + value + transit_name)

        #import tolls
        import_tolls(my_project)
        

def main():
    print network_summary_project
    run_importer(network_summary_project)
    
    returncode = subprocess.call([sys.executable,'scripts/network/daysim_zone_inputs.py'])
    if returncode != 0:
        sys.exit(1)
    
    print 'done'

if __name__ == "__main__":
    main()






