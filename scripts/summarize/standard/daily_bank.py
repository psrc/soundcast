import inro.emme.database.emmebank as _emmebank
import os
from input_configuration import *
import json
import shutil
from distutils import dir_util


#create a new bank for daily volume:
#sound_cast_net_dict = {'5to6' : 'ni', '6to7' : 'am', '7to8' : 'am', '8to9' : 'am', 
                       #'9to10' : 'md', '10to14' : 'md', '14to15' : 'md', 
                       #'15to16' : 'pm', '16to17' : 'pm', '17to18' : 'pm', 
                       #'18to20' : 'ev', '20to5' : 'ni'}

#tods = ['6to7', '5to6', '7to8', '8to9', '9to10', '10to14', '14to15', '15to16', '16to17', '17to18', '18to20', '20to5']
keep_atts = ['@type']
def json_to_dictionary(dict_name):

    #Determine the Path to the input files and load them
    skim_params_loc = os.path.abspath(os.path.join(os.getcwd(),"inputs\\skim_params")) 
    input_filename = os.path.join(skim_params_loc,dict_name+'.json').replace("\\","/")
    my_dictionary = json.load(open(input_filename))

    return(my_dictionary)

def text_to_dictionary(dict_name):

    input_filename = os.path.join('inputs/skim_params/',dict_name+'.json').replace("\\","/")
    my_file=open(input_filename)
    my_dictionary = {}

    for line in my_file:
        k, v = line.split(':')
        my_dictionary[eval(k)] = v.strip()

    return(my_dictionary)


def create_emmebank(dir_name):
    
    #tod_dict = text_to_dictionary('time_of_day')
    emmebank_dimensions_dict = json_to_dictionary('emme_bank_dimensions')
    
    path = os.path.join('Banks', dir_name)
    if os.path.exists(path):
        shutil.rmtree(path)
    
    os.makedirs(path)
    path = os.path.join(path, 'emmebank')
    emmebank = _emmebank.create(path, emmebank_dimensions_dict)
    emmebank.title = dir_name
    scenario = emmebank.create_scenario(1002)
    network = scenario.get_network()
    #need to have at least one mode defined in scenario. Real modes are imported in network_importer.py
    network.create_mode('AUTO', 'a')
    scenario.publish_network(network)
    emmebank.dispose()

def copy_emmebank(from_dir, to_dir):
    if os.path.exists(to_dir):
        shutil.rmtree(to_dir)
    os.makedirs(to_dir)
    dir_util.copy_tree(from_dir, to_dir)

def merge_networks(master_network, merge_network):
    for node in merge_network.nodes():
        if not master_network.node(node.id):
            new_node = master_network.create_regular_node(node.id)
            new_node.x = node.x
            new_node.y = node.y
      
    for link in merge_network.links():
        if not master_network.link(link.i_node, link.j_node):
            master_network.create_link(link.i_node, link.j_node, link.modes)

    return master_network
       
#Use a copy of an existing bank for the daily bank
copy_emmebank('Banks/7to8', 'Banks/Daily')

daily_emmebank =_emmebank.Emmebank(r'Banks\Daily\emmebank')
# Set the emmebank title
daily_emmebank.title = 'daily'
daily_scenario = daily_emmebank.scenario(1002)
daily_network = daily_scenario.get_network()

matrix_dict = text_to_dictionary('demand_matrix_dictionary')
uniqueMatrices = set(matrix_dict.values())

################## delete all matrices #################

for matrix in daily_emmebank.matrices():
    daily_emmebank.delete_matrix(matrix.id)
   
################ create new matrices in daily emmebank for trip tables only ##############

for unique_name in uniqueMatrices:
    daily_matrix = daily_emmebank.create_matrix(daily_emmebank.available_matrix_identifier('FULL')) #'FULL' means the full-type of trip table
    daily_matrix.name = unique_name

daily_matrix_dict = {}
for matrix in daily_emmebank.matrices():
    daily_arr = matrix.get_numpy_data()
    daily_matrix_dict[matrix.name] = daily_arr
    print matrix.name

time_period_list = []


for tod, time_period in sound_cast_net_dict.iteritems():
    path = os.path.join('Banks', tod, 'emmebank')
    print path
    bank = _emmebank.Emmebank(path)
    scenario = bank.scenario(1002)
    network = scenario.get_network()
    # Trip  table stuff:
    for matrix in bank.matrices():
        if matrix.name in daily_matrix_dict:
            hourly_arr = matrix.get_numpy_data()
            daily_matrix_dict[matrix.name] = daily_matrix_dict[matrix.name] + hourly_arr
  

    # Network stuff:
    if len(time_period_list) == 0:
        daily_network = network
        time_period_list.append(time_period)
    elif time_period not in time_period_list:
        time_period_list.append(time_period) #this line was repeated below
        daily_network = merge_networks(daily_network, network)
        time_period_list.append(time_period) #this line was repeated above
daily_scenario.publish_network(daily_network)

# Write daily trip tables:
for matrix in daily_emmebank.matrices():
    matrix.set_numpy_data(daily_matrix_dict[matrix.name])


for extra_attribute in daily_scenario.extra_attributes():
    print extra_attribute
    if extra_attribute not in keep_atts:
        daily_scenario.delete_extra_attribute(extra_attribute)
daily_volume_attr = daily_scenario.create_extra_attribute('LINK', '@tveh')
daily_network = daily_scenario.get_network()

for tod, time_period in sound_cast_net_dict.iteritems():
    path = os.path.join('Banks', tod, 'emmebank')
    print path
    bank = _emmebank.Emmebank(path)
    scenario = bank.scenario(1002)
    network = scenario.get_network()
    if daily_scenario.extra_attribute('@v' + tod[:4]):
        daily_scenario.delete_extra_attribute('@v' + tod[:4])
    attr = daily_scenario.create_extra_attribute('LINK', '@v' + tod[:4])
    values = scenario.get_attribute_values('LINK', ['@tveh'])
    daily_scenario.set_attribute_values('LINK', [attr], values)
    #daily_scenario.publish_network(daily_network)
    #daily_network = daily_scenario.get_network()

daily_network = daily_scenario.get_network()
attr_list = ['@tv' + x for x in tods]

for link in daily_network.links():
    for item in tods:
        link['@tveh'] = link['@tveh'] + link['@v' + item[:4]]
daily_scenario.publish_network(daily_network)

######################## Validate results ##########################

zone1 = 100
zone2 = 100

print 'from zone', zone1, 'to zone', zone2
for matrix1 in daily_emmebank.matrices():
    NAME = matrix1.name
    print NAME
    print 'daily:' , matrix1.get_numpy_data()[zone1][zone2]
    a = 0
    for tod, time_period in sound_cast_net_dict.iteritems():
        path = os.path.join('banks', tod, 'emmebank')
        bank = _emmebank.Emmebank(path)
        for matrix2 in bank.matrices():
            if matrix2.name == NAME:
                my_arr = matrix2.get_numpy_data()
                a += my_arr[zone1][zone2]
    print 'hourly total:', a


print 'done'


            




  
