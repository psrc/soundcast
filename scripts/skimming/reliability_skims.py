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
#os.chdir(r"D:\stefan\sc_calibration\soundcast")
import h5py
import Tkinter, tkFileDialog
import multiprocessing as mp
import subprocess
from multiprocessing import Pool
import logging
import datetime
import argparse
sys.path.append(os.path.join(os.getcwd(),"scripts"))
sys.path.append(os.path.join(os.getcwd(),"inputs"))
sys.path.append(os.getcwd())
from emme_configuration import *
from EmmeProject import *

# Time of day periods
#tods = ['5to6', '6to7', '7to8', '8to9', '9to10', '10to14', '14to15', '15to16', '16to17', '17to18', '18to20', '20to5' ]
project_list = ['Projects/' + tod + '/' + tod + '.emp' for tod in tods]

def json_to_dictionary(dict_name):

    #Determine the Path to the input files and load them

    input_filename = os.path.join('inputs/skim_params/',dict_name+'.json').replace("\\","/")
    
    my_dictionary = json.load(open(input_filename))
    
    return(my_dictionary)


def start_pool(project_list):
    #An Emme databank can only be used by one process at a time. Emme Modeler API only allows one instance of Modeler and
    #it cannot be destroyed/recreated in same script. In order to run things con-currently in the same script, must have
    #seperate projects/banks for each time period and have a pool for each project/bank.
    #Fewer pools than projects/banks will cause script to crash.

    pool = Pool(processes=parallel_instances)
    
    pool.map(run_skim,project_list[0:parallel_instances])
    
    pool.close()


def run_skim(project_name):
    #Function to calculate reliability skims

     start_time_skim = time.time()

     my_project = EmmeProject(project_name)
     attribute_name = '@reliab'

     skim_desig = 'r'

     skim_traffic = my_project.m.tool("inro.emme.traffic_assignment.path_based_traffic_analysis")

     skim_specification = json_to_dictionary("general_attribute_based_skim")

     my_user_classes = json_to_dictionary("user_classes")

     my_project.create_extra_attribute("LINK", attribute_name, 'reliability index', True)

     exp = '0.max.(timau-((length * 60 / ul2) * (1 + .72 * (1 * (volau + @bveh) / (ul1* lanes)) ^ 7.2)))'

     my_project.network_calculator("link_calculation", result = attribute_name, expression = exp, selections_by_link = "ul3=1,2")

     mod_skim = skim_specification
     for x in range (0, len(mod_skim["classes"])):

        matrix_name= my_user_classes["Highway"][x]["Name"]+skim_desig

        if my_project.bank.matrix(matrix_name):

            my_project.delete_matrix(matrix_name)

        my_project.create_matrix(matrix_name, 'reliability skim', 'FULL')

        mod_skim["classes"][x]["analysis"]["results"]["od_values"] = matrix_name

        mod_skim["path_analysis"]["link_component"] = attribute_name

     skim_traffic(mod_skim)


def main():

    for i in range (0, 12, parallel_instances):

        l = project_list[i:i+parallel_instances]

        start_pool(l)


if __name__ == "__main__":

    main()