import array as _array
import time
import inro.emme.desktop.app as app
import inro.modeller as _m
import inro.emme.matrix as ematrix
import inro.emme.database.matrix
import inro.emme.database.emmebank as _eb
import pandas as pd
import numpy as np
import h5py
import openmatrix as omx
import json
import os

from pathlib import Path
import yaml

# Record script start time
script_start_time = time.time()
print(f"=== ASIM PARK AND RIDE SCRIPT START ===")
print(f"Start time: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(script_start_time))}")
print("=" * 50)

matrix_dict = {
    "DRV_TRN_WLK_DTIM": "auto_pnr_time_access",
    "WLK_TRN_DRV_DTIM": "auto_pnr_time_egress",
    "DRV_TRN_WLK_DDIST": "auto_pnr_distance_access",
    "WLK_TRN_DRV_DDIST": "auto_pnr_distance_egress",
    "DRV_TRN_WLK_WAUX": "pnr_aux_time_access",
    "WLK_TRN_DRV_WAUX": "pnr_aux_time_egress",
    "DRV_TRN_WLK_IWAIT": "pnr_initial_wait_access",
    "WLK_TRN_DRV_IWAIT": "pnr_initial_wait_egress",
    "DRV_TRN_WLK_WAIT": "pnr_total_wait_access",
    "WLK_TRN_DRV_WAIT": "pnr_total_wait_egress",
    "DRV_TRN_WLK_TOTIVT": "pnr_aivt_access",
    "WLK_TRN_DRV_TOTIVT": "pnr_aivt_egress",
    "DRV_TRN_WLK_BOARDS": "pnr_boardings_access",
    "WLK_TRN_DRV_BOARDS": "pnr_boardings_egress",
}

pnr_access_class_name = "pnr_access"
pnr_egress_class_name = "pnr_egress"
ferry_class_name = "asim_ferry"
all_transit_class_name = "all_transit"


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


def change_max_matrices_emmebank(my_project, number_of_matriecs):
    NAMESPACE = "inro.emme.data.database.change_database_dimensions"
    change_db_dim = my_project.m.tool(NAMESPACE)
    # emmebank = _m.Modeller().emmebank
    new_dimensions = my_project.bank.dimensions
    if new_dimensions["full_matrices"] != number_of_matriecs:
        new_dimensions["full_matrices"] = number_of_matriecs
        change_db_dim(emmebank_dimensions=new_dimensions, keep_backup=False)


def park_and_ride_assignment(my_project, sc_tod, spec_dir, results_dict, asim_tod):

    # my_project.change_active_database(sc_tod)

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
            except:
                pass
            my_project.create_matrix(matrix_name + "_" + type, "", "FULL")
            print(matrix_name)


def all_transit_assignment(
    my_project, transit_spec_dir, class_name, matrix_list, results_dict, asim_tod
):
    spec = json.load(open(transit_spec_dir / "all_transit_assignment.json"))
    spec["demand"] = "WLK_TRN_WLK_DEMAND"
    spec["od_results"]["total_impedance"] = "WLK_TRN_WLK_TIMP"
    transit_assignment(spec, my_project, class_name)
    # Skims:
    skim = my_project.m.tool("inro.emme.transit_assignment.extended.matrix_results")
    skim(
        json.load(open(transit_spec_dir / "all_transit_skim_spec.json")),
        class_name=class_name,
    )
    # Export
    # for name in matrix_list:
    #     print(name)
    #     try:
    #         matrix_value = emmeMatrix_to_numpyMatrix(name, my_project.bank, "uint16", 1)
    #         results_dict[name + "__" + asim_tod] = matrix_value
    #         # h5file.create_dataset(name+'__'+asim_tod, data=matrix_value.astype('uint16'),compression='gzip')
    #         # f[name+'__'+asim_tod] = matrix_value
    #     except:
    #         print(name)

    # return results_dict


def two_leg_trip(my_project, spec_dir):
    _m = inro.modeller
    NAMESPACE = "inro.emme.choice_model.two_leg_trip_chain"
    # two_leg_trip = _m.Modeller().tool(NAMESPACE)
    two_leg_trip = my_project.m.tool(NAMESPACE)
    # trip_demand = my_project.bank.matrix("pnr_demand_access")
    # mf16 = my_project.bank.matrix("DRV_TRN_WLK_A_DEMAND")
    # md4 = my_project.bank.matrix("DRV_TRANSIT_WLK_LOT_USAGE")
    # mf17 = my_project.bank.matrix("DRV_TRN_WLK_T_DEMAND")
    # leg1_pk_spec =json.load(open(spec_dir/'first_leg.json'))
    # stop_k_spec =json.load(open(spec_dir/'stop_location_util.json'))
    # leg2_kq_spec =json.load(open(spec_dir/'second_leg.json'))
    # zone_spec =json.load(open(spec_dir/'constraint.json'))
    # pq_avg_results = json.load(open(spec_dir/'average_results.json'))

    # DRV_TRN_WLK ()
    two_leg_trip(
        tour_demand=my_project.bank.matrix("pnr_demand_access"),   # THIS IS WHERE DEMAND GOES IN
        # tour_demand=my_project.bank.matrix("pnr_demand"),
        leg1_pk_utility_spec=json.load(open(spec_dir / "access/first_leg.json")),
        stop_k_utility_spec=json.load(
            open(spec_dir / "access/stop_location_util.json")
        ),
        leg2_kq_utility_spec=json.load(open(spec_dir / "second_leg.json")),
        leg1_demand=my_project.bank.matrix("DRV_TRN_WLK_A_DEMAND"),
        stop_usage=my_project.bank.matrix("DRV_TRN_WLK_LOT_USAGE"),
        leg2_demand=my_project.bank.matrix("DRV_TRN_WLK_T_DEMAND"),
        stop_capacity=my_project.bank.matrix("PARK_AND_RIDE_CAPACITIY"),
        max_iterations=20,
        constraint=json.load(open(spec_dir / "access/constraint.json")),
        pq_avg_results=json.load(open(spec_dir / "access/average_results.json")),
        log_worksheets=True,
        scenario=my_project.current_scenario,
    )

    # WLK_TRN_DRV (EGRESS)
    two_leg_trip(
        tour_demand=my_project.bank.matrix("pnr_demand_egress"),   # THIS IS WHERE DEMAND GOES IN
        # tour_demand=my_project.bank.matrix("pnr_demand"),
        leg1_pk_utility_spec=json.load(open(spec_dir / "egress/first_leg.json")),
        stop_k_utility_spec=json.load(
            open(spec_dir / "egress/stop_location_util.json")
        ),
        leg2_kq_utility_spec=json.load(open(spec_dir / "second_leg.json")),
        leg1_demand=my_project.bank.matrix("WLK_TRN_DRV_A_DEMAND"),
        stop_usage=my_project.bank.matrix("WLK_TRN_DRV_LOT_USAGE"),
        leg2_demand=my_project.bank.matrix("WLK_TRN_DRV_T_DEMAND"),
        stop_capacity=my_project.bank.matrix("PARK_AND_RIDE_CAPACITIY"),
        max_iterations=20,
        constraint=json.load(open(spec_dir / "egress/constraint.json")),
        pq_avg_results=json.load(open(spec_dir / "egress/average_results.json")),
        log_worksheets=True,
        scenario=my_project.current_scenario,
    )


def create_transit_matrices(my_project, asim_tod, matrix_dict):

    for type, matrix_list in matrix_dict.items():
        for matrix_name in matrix_list:
            # Delete matrix if it already exists
            try:
                my_project.delete_matrix(my_project.bank.matrix(matrix_name).id)
                print("-----")
                print(matrix_name)
            except:
                pass
            my_project.create_matrix(matrix_name, "", type)
            print(matrix_name)


def transit_assignment(spec, my_project, class_name):
    # Extended transit assignment
    assign_transit = my_project.m.tool(
        "inro.emme.transit_assignment.extended_transit_assignment"
    )
    assign_transit(spec, class_name=class_name)


def run_park_and_ride(
    state,
    my_project,
    spec_dir,
    time_period_lookup,
    # project_path: Path
):
    results_dict = {}
    pnr_spec_dir = spec_dir / "park_and_ride"
    ferry_spec_dir = spec_dir / "ferry"
    all_transit_dir = spec_dir / "all_transit"
    emme_spec_dir = spec_dir / "emme"
    # matrix_list = ["WLK_TRN_WLK_DEMAND", "WLK_TRN_WLK_WAUX", "WLK_TRN_WLK_TWAIT", "WLK_TRN_WLK_IVT"]
    matrix_list = {
        "FULL": [
            "WLK_TRN_WLK_DEMAND",
            "WLK_TRN_WLK_WAUX",
            "DRV_TRN_WLK_DDIST",
            "DRV_TRN_WLK_DTIM",
            "DRV_TRN_WLK_WAUX",
            "DRV_TRN_WLK_TOTIVT",
            "DRV_TRN_WLK_WAIT",
            "DRV_TRN_WLK_IWAIT",
            "DRV_TRN_WLK_BOARDS",
            "WLK_TRN_DRV_DDIST",
            "WLK_TRN_DRV_DTIM",
            "WLK_TRN_DRV_WAUX",
            "WLK_TRN_DRV_TOTIVT",
            "WLK_TRN_DRV_WAIT",
            "WLK_TRN_DRV_IWAIT",
            "WLK_TRN_DRV_BOARDS",
            "WLK_TRN_WLK_TWAIT",
            "WLK_TRN_WLK_IWAIT",
            "WLK_TRN_WLK_IVT",
            "WLK_TRN_WLK_TIMP",
            "WLK_TRN_WLK_BOARDS",
            "DRV_TRN_WLK_T_DEMAND",
            "DRV_TRN_WLK_A_DEMAND",
            "WLK_TRN_DRV_T_DEMAND",
            "WLK_TRN_DRV_A_DEMAND",
            # "pnr_demand_access",
            # "pnr_demand_egress",
        ],
        "DESTINATION": [
            "DRV_TRN_WLK_LOT_USAGE",
            "WLK_TRN_DRV_LOT_USAGE",
            "PARK_AND_RIDE_UTIL",
            "PARK_AND_RIDE_CAPACITY",
        ],
    }
    # increase number of matrices if needed:

    # open park and ride capacities file (currently daysim)
    # and change to emme fomrat

    # this should be done with the network_importer
    df = pd.DataFrame(my_project.current_scenario.zone_numbers, columns=["index"])
    pnr_capacities = pd.read_csv(
        "inputs/scenario/networks/p_r_nodes.csv"
    )
    pnr_capacities = pnr_capacities.rename(columns={"Capacity": "value"})
    df = df.merge(pnr_capacities, how="left", left_on="index", right_on="ZoneID")
    df["value"] = df["value"].fillna(0)
    df = df[["index", "value"]]
    df.to_csv("inputs/scenario/networks/p_r_capacities.csv", index=False)

    # for sc_tod, asim_tod in time_period_lookup.items():
    #     print(asim_tod)
    #     print(sc_tod)
        # my_project.change_active_database(sc_tod)
        # change_max_matrices_emmebank(my_project, 170)
        # create zone partition to hold park and ride zones
    my_project.initialize_zone_partition("ga")

    # my_project

    # use matrix calculator to save park and rides to partition
    # matrix_calc_spec = json.load(open(emme_spec_dir / "matrix_calc_spec.json"))
    my_project.matrix_calculator(
        # matrix_calc_spec,
        result="ga",
        expression="1",
        constraint_by_zone_origins="1-3700",
    )
    my_project.matrix_calculator(
        # matrix_calc_spec,
        result="ga",
        expression="2",
        constraint_by_zone_origins="3751-4000",
    )
    # park_and_ride_skims(my_project, sc_tod, pnr_spec_dir, results_dict, asim_tod)

    create_transit_matrices(my_project, my_project.tod, matrix_list)
    my_project.import_matrix_from_csv(
        "inputs/scenario/networks/p_r_capacities.csv",
        "PARK_AND_RIDE_CAPACITY"
    )
    # ferry_assignment(my_project, ferry_spec_dir, ferry_class_name)
    # need to run all tranist to get transit impedances for park and ride lot choice
    all_transit_assignment(
        my_project,
        all_transit_dir,
        all_transit_class_name,
        matrix_list,
        results_dict,
        my_project.tod,
    )
    two_leg_trip(my_project, pnr_spec_dir)
    # park_and_ride_assignment(my_project, sc_tod, pnr_spec_dir, results_dict, asim_tod)

    # f = omx.open_file(skims_file_path, "w")
    # for skim_matrix in results_dict.keys():
    #     print(skim_matrix)
    #     #statsDict= {attr:getattr(skim_matrix,attr)() for attr in ['min', 'max','mean','std']}
    #     f[skim_matrix] = results_dict[skim_matrix]

    # f.close()

    # Record script end time and display execution duration
    script_end_time = time.time()
    execution_duration = script_end_time - script_start_time
    print("=" * 50)
    print("=== ASIM PARK AND RIDE SCRIPT COMPLETED ===")
    print(f"End time: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(script_end_time))}")
    print(f"Total execution time: {execution_duration:.4f} seconds")
    print(f"Total execution time: {execution_duration/60:.2f} minutes")
    print("=" * 50)