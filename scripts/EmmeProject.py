#Copyright [2014] [Puget Sound Regional Council]

#Licensed under the Apache License, Version 2.0 (the "License");
#you may not use this file except in compliance with the License.
#You may obtain a copy of the License at

#    http://www.apache.org/licenses/LICENSE-2.0

#Unless required by applicable law or agreed to in writing, software
#distributed under the License is distributed on an "AS IS" BASIS,
#WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#See the License for the specific language governing permissions and
#limitations under the License.

import inro.emme.desktop.app as app
import inro.modeller as _m
import inro.emme.matrix as ematrix
import inro.emme.database.matrix
import inro.emme.database.emmebank as _eb
import os, sys
import re 
import multiprocessing as mp
import subprocess
import pandas as pd
import json
from multiprocessing import Pool, pool
sys.path.append(os.path.join(os.getcwd(),"inputs"))
from input_configuration import *
from EmmeProject import *


class EmmeProject:
    def __init__(self, filepath):
        self.desktop = app.start_dedicated(True, "cth", filepath)
        self.m = _m.Modeller(self.desktop)
        #delete locki:
        self.m.emmebank.dispose()
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
                self.bank = self.m.emmebank
                self.tod = self.bank.title
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

    def delete_matrix(self, matrix):
        NAMESPACE = "inro.emme.data.matrix.delete_matrix"
        process = self.m.tool(NAMESPACE)
        process(matrix, self.bank)

    def delete_matrices(self, matrix_type):
        NAMESPACE = "inro.emme.data.matrix.delete_matrix"
        process = self.m.tool(NAMESPACE)
        for matrix in self.bank.matrices():
            if matrix_type == "ALL":
                process(matrix, self.bank)
            elif matrix.type == matrix_type:
                process(matrix, self.bank)

    def create_matrix (self, matrix_name, matrix_description, matrix_type):
        NAMESPACE = "inro.emme.data.matrix.create_matrix"
        process = self.m.tool(NAMESPACE)
        print self.current_scenario
        process (matrix_id= self.bank.available_matrix_identifier(matrix_type),
                          matrix_name= matrix_name,
                          matrix_description= matrix_description,
                          default_value=0,
                          overwrite=True,
                          scenario=self.current_scenario)

    def matrix_calculator(self, **kwargs):
        spec = json_to_dictionary('matrix_calc_spec')
        for name, value in kwargs.items():
            if name == 'aggregation_origins':
                spec['aggregation']['origins'] = value
            elif name == 'aggregation_destinations':
                spec['aggregation']['destinations'] = value
            elif name == 'constraint_by_value':
                spec['constraint']['by_value'] = value
            elif name == 'constraint_by_zone_origins':
                spec['constraint']['by_zone']['origins'] = value
            elif name == 'constraint_by_zone_destinations':
                spec['constraint']['by_zone']['destinations'] = value
            else:
                spec[name] = value
        #print spec
        NAMESPACE = "inro.emme.matrix_calculation.matrix_calculator"
        process = self.m.tool(NAMESPACE)
        report = process(spec) 
        return report

    def matrix_transaction(self, transactionFile):
        NAMESPACE=("inro.emme.data.matrix.matrix_transaction")
        process = self.m.tool(NAMESPACE)
        process(transaction_file = transactionFile,
                       throw_on_error = True,
                       scenario = self.current_scenario)

    def initialize_zone_partition(self, partition_name):
        NAMESPACE=("inro.emme.data.zone_partition.init_partition")
        process = self.m.tool(NAMESPACE)
        process(partition=partition_name)
        
    

    def process_zone_partition(self, transactionFile):
        NAMESPACE=("inro.emme.data.zone_partition.partition_transaction")
        process = self.m.tool(NAMESPACE)
        process(transaction_file = transactionFile,
                       throw_on_error = True,
                       scenario = self.current_scenario)

    def create_extra_attribute(self, type, name, description, overwrite):
        NAMESPACE=("inro.emme.data.extra_attribute.create_extra_attribute")
        process = self.m.tool(NAMESPACE)
        process(extra_attribute_type=type,
                      extra_attribute_name= name,
                      extra_attribute_description= description,
                      overwrite=overwrite)

    def delete_extra_attribute(self, name):
        NAMESPACE=("inro.emme.data.extra_attribute.delete_extra_attribute")
        process = self.m.tool(NAMESPACE)
        process(name)

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

    def process_function_file(self, file_name):
        NAMESPACE=("inro.emme.data.function.function_transaction" )
        process = self.m.tool(NAMESPACE)
        process(file_name ,throw_on_error = True)

    def matrix_balancing(self, **kwargs):
        spec = json_to_dictionary('matrix_balancing_spec')
        for name, value in kwargs.items():
            if name == 'results_od_balanced_values':
                spec['results']['od_balanced_values'] = value
            elif name == 'constraint_by_value':
                spec['constraint']['by_value'] = value
            elif name == 'constraint_by_zone_origins':
                spec['constraint']['by_zone']['origins'] = value
            elif name == 'constraint_by_zone_destinations':
                spec['constraint']['by_zone']['destinations'] = value
            else:
                spec[name] = value
        NAMESPACE = "inro.emme.matrix_calculation.matrix_balancing"
        compute_matrix = self.m.tool(NAMESPACE)
        report = compute_matrix(spec) 

    def import_matrices(self, matrix_name):
        NAMESPACE = "inro.emme.data.matrix.matrix_transaction"
        process = self.m.tool(NAMESPACE)
        process(transaction_file = matrix_name,
            throw_on_error = False,
            scenario = self.current_scenario)

    def transit_line_calculator(self, **kwargs):
        spec = json_to_dictionary("transit_line_calculation")
        for name, value in kwargs.items():
            spec[name] = value
        
        NAMESPACE = "inro.emme.network_calculation.network_calculator"
        network_calc = self.m.tool(NAMESPACE)
        self.transit_line_calc_result = network_calc(spec)

    def transit_segment_calculator(self, **kwargs):
        spec = json_to_dictionary("transit_segment_calculation")
        for name, value in kwargs.items():
            spec[name] = value
        
        NAMESPACE = "inro.emme.network_calculation.network_calculator"
        network_calc = self.m.tool(NAMESPACE)
        self.transit_segment_calc_result = network_calc(spec)


def json_to_dictionary(dict_name):

    #Determine the Path to the input files and load them
    input_filename = os.path.join('inputs/skim_params/',dict_name+'.json').replace("\\","/")
    my_dictionary = json.load(open(input_filename))

    return(my_dictionary)


