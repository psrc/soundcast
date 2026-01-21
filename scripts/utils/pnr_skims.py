# This script performs a mixed mode assignment to produce park and ride skims
# These skims are primarly used for development of Activitysim and supplementary to
# Soundcast's park and ride modeling.
# This script was generated to provide individual skim components from an origin to a destination
# For example, auto time to access the nearest park and ride station along with all other standard
# transit components like wait time, in-vehicle time, etc.
# Emme's mixed mode assignment will select the optimal park and ride location and transit route.
# The result is a measure of skim components directly between an origin and destination, which
# is not directly available from existing Soundcast park and ride procedures.

import array as _array
import time
import inro.emme.desktop.app as app
import inro.modeller as _m
import inro.emme.matrix as ematrix
import inro.emme.database.matrix
import inro.emme.database.emmebank as _eb
import json
import numpy as np
import time
import os, sys
import h5py
import shutil
import multiprocessing as mp
import subprocess
from multiprocessing import Pool
import logging
import datetime
import argparse
import traceback

sys.path.append(os.path.join(os.getcwd(), "scripts"))
sys.path.append(os.path.join(os.getcwd(), "inputs"))
sys.path.append(os.getcwd())
# from emme_configuration import *
from scripts.emme_project import *
# from data_wrangling import text_to_dictionary, json_to_dictionary
from pathlib import Path

# Script should be run from project root
# os.chdir(r'C:\Workspace\sc_park_and_ride\soundcast')

# Run this script for 5 time periods
tod_dict = {"AM": "7to8", "MD": "10to14", "PM": "16to17", "EV": "18to20", "NI": "20to5"}

# Lookup between matrix names used here and activitysim names
matrix_dict = {
    "DRV_LOC_WLK_DTIM": "auto_pnr_time_access",
    "WLK_LOC_DRV_DTIM": "auto_pnr_time_egress",
    "DRV_WLK_DDIST": "auto_pnr_distance_access",
    "DRV_WLK_DDIST": "auto_pnr_distance_egress",
    "DRV_LOC_WLK_WAUX": "pnr_aux_time_access",
    "WLK_LOC_DRV_WAUX": "pnr_aux_time_egress",
    "DRV_LOC_WLK_IWAIT": "pnr_initial_wait_access",
    "WLK_LOC_DRV_IWAIT": "pnr_initial_wait_egress",
    "DRV_LOC_WLK_WAIT": "pnr_total_wait_access",
    "WLK_LOC_DRV_WAIT": "pnr_total_wait_egress",
    "DRV_LOC_WLK_TOTIVT": "pnr_aivt_access",
    "WLK_LOC_DRV_TOTIVT": "pnr_aivt_egress",
    "DRV_LOC_WLK_BOARDS": "pnr_boardings_access",
    "WLK_LOC_DRV_BOARDS": "pnr_boardings_egress",
}


def emmeMatrix_to_numpyMatrix(
    matrix_name, emmebank, np_data_type, multiplier, max_value=None
):
    matrix_id = emmebank.matrix(matrix_name).id
    emme_matrix = emmebank.matrix(matrix_id)
    matrix_data = emme_matrix.get_data()
    np_matrix = np.matrix(matrix_data.raw_data)
    np_matrix = np_matrix * multiplier

    if np_data_type == "uint16":
        max_value = np.iinfo(np_data_type).max
        np_matrix = np.where(np_matrix > max_value, max_value, np_matrix)

    if np_data_type != "float32":
        np_matrix = np.where(
            np_matrix > np.iinfo(np_data_type).max,
            np.iinfo(np_data_type).max,
            np_matrix,
        )

    return np_matrix


def assignment(spec, my_project, class_name):
    # Extended transit assignment
    assign_transit = my_project.m.tool(
        "inro.emme.transit_assignment.extended_transit_assignment"
    )
    assign_transit(spec, class_name=class_name)

    return None


def skim(spec1, spec2, my_project, class_name):
    skim_pnr = my_project.m.tool("inro.emme.transit_assignment.extended.matrix_results")

    # Skim for time in transit from park and ride lot to destination station
    # submodes bcfpr
    # loop through each submode and write out a skim file for each (?)
    # my_project.create_matrimx ('auto_access_time_all_test', 'new test', 'FULL')
    skim_pnr(spec1, class_name=class_name)

    # Skim for walk access to destination
    skim_pnr(spec2, class_name=class_name)

    return None


def process(my_project, sc_tod, asim_tod, h5file):

    # FIXME - read from config
    pnr_spec_dir = Path(
        "R:/e2projects_two/activitysim/assignment_skims_inputs/park_and_ride"
    )
    ferry_spec_dir = Path("R:/e2projects_two/activitysim/assignment_skims_inputs/ferry")

    pnr_access_class_name = "pnr_access"
    pnr_egress_class_name = "pnr_egress"

    my_project.change_active_database(sc_tod)

    matrix_list = [
        "pnr_demand",
        "auto_pnr_distance",
        "auto_pnr_time",
        "pnr_aivt",
        "pnr_boardings",
        "pnr_aux_time",
        "pnr_initial_wait",
        "pnr_total_wait",
    ]

    for type in ["access", "egress"]:
        for matrix_name in matrix_list:
            # Delete matrix if it already exists
            try:
                my_project.delete_matrix(
                    my_project.bank.matrix(matrix_name + "_" + type).id
                )
                print("-----")
                print(matrix_name)
            except Exception:
                pass
            my_project.create_matrix(matrix_name + "_" + type, "", "FULL")
            print(matrix_name)

    ## Create extra attribute for auxiliary walk demand modes x and w with an all designation
    my_project.create_extra_attribute(
        "LINK", "@volax_w_all", description="aux w pnr all", overwrite=True
    )
    my_project.create_extra_attribute(
        "LINK", "@volax_x_all", description="aux x pnr all", overwrite=True
    )
    my_project.create_extra_attribute(
        "LINK", "@volax_w_pnr", description="aux x pnr", overwrite=True
    )
    my_project.create_extra_attribute(
        "LINK", "@volax_x_pnr", description="aux x pnr", overwrite=True
    )
    my_project.create_extra_attribute(
        "LINK", "@volax_y_pnr", description="aux x pnr", overwrite=True
    )
    my_project.create_extra_attribute(
        "LINK", "@volax_z_pnr", description="aux (x pnr", overwrite=True
    )

    ##############################
    # Process auto access portion (trips TO Park and Rides)

    spec = json.load(open(pnr_spec_dir / "pnr_assignment_spec.json"))
    assignment(spec, my_project, pnr_access_class_name)

    spec1 = json.load(open(pnr_spec_dir / "pnr_skim_1.json"))
    spec2 = json.load(open(pnr_spec_dir / "pnr_skim_2.json"))
    skim(spec1, spec2, my_project, pnr_access_class_name)

    ##############################
    # Process auto egress portion (trips FROM Park and Rides)
    spec = json.load(open(ferry_spec_dir / "pnr_assignment_spec_egress.json"))
    assignment(spec, my_project, pnr_egress_class_name)

    spec1 = json.load(open(pnr_spec_dir / "pnr_skim_1_egress.json"))
    spec2 = json.load(open(pnr_spec_dir / "pnr_skim_2_egress.json"))
    skim(spec1, spec2, my_project, pnr_egress_class_name)

    for asim_name, matrix_name in matrix_dict.items():
        try:
            matrix_value = emmeMatrix_to_numpyMatrix(
                matrix_name, my_project.bank, "uint16", 100
            )
            h5file["Skims"].create_dataset(
                asim_name + "__" + asim_tod,
                data=matrix_value.astype("uint16"),
                compression="gzip",
            )
        except:
            print(matrix_name)

    # Transfer Time
    # Total wait time minus initial wait time gives transfer time
    # DRV_LOC_WLK_XWAIT: pnr_total_wait_access-pnr_initial_wait_access
    # WLK_LOC_DRV_XWAIT:pnr_total_wait_egress-pnr_initial_wait_egress

    pnr_total_wait_access = emmeMatrix_to_numpyMatrix(
        "pnr_total_wait_access", my_project.bank, "uint16", 100
    )
    pnr_initial_wait_access = emmeMatrix_to_numpyMatrix(
        "pnr_initial_wait_access", my_project.bank, "uint16", 100
    )
    pnr_transfer_wait_access = pnr_total_wait_access - pnr_initial_wait_access
    h5file["Skims"].create_dataset(
        "DRV_LOC_WLK_XWAIT__" + asim_tod,
        data=pnr_transfer_wait_access.astype("uint16"),
        compression="gzip",
    )

    pnr_total_wait_egress = emmeMatrix_to_numpyMatrix(
        "pnr_total_wait_egress", my_project.bank, "uint16", 100
    )
    pnr_initial_wait_egress = emmeMatrix_to_numpyMatrix(
        "pnr_initial_wait_egress", my_project.bank, "uint16", 100
    )
    pnr_transfer_wait_egress = pnr_total_wait_egress - pnr_initial_wait_egress
    h5file["Skims"].create_dataset(
        "WLK_LOC_DRV_XWAIT__" + asim_tod,
        data=pnr_transfer_wait_access.astype("uint16"),
        compression="gzip",
    )

    del my_project
    return None

def main(state):
    ################################################
    # Write skims to file in activitysim format
    h5file = h5py.File("pnr_skims.h5", "w")
    h5file.create_group("Skims")

    # my_project = EmmeProject(
    #     "C:\Workspace\sc_new_daysim\soundcast\projects\LoadTripTables/LoadTripTables.emp"
    # )



    # for asim_tod, sc_tod in tod_dict.items():
    for sc_tod, asim_tod in state.network_settings.sound_cast_net_dict.items():
        print(asim_tod)
        print(sc_tod)

        # my_project = state.main_project
        my_project = EmmeProject("projects/5to9/5to9.emp", state.model_input_dir)

        process(my_project, sc_tod, asim_tod, h5file)

    h5file.close()


if __name__ == "__main__":
    main()
