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
from EmmeProject import *
from pathlib import Path
import yaml


# file = Path().joinpath(configuration.args.configs_dir, "config.yaml")
# config = yaml.safe_load(open(file))


def get_trn_sub_component_skim(condition, my_project, sub_component_name):
    bus = emmeMatrix_to_numpyMatrix(
        sub_component_name + "a", my_project.bank, "float32"
    )

    rail = emmeMatrix_to_numpyMatrix(
        sub_component_name + "r", my_project.bank, "float32"
    )

    ferry = emmeMatrix_to_numpyMatrix(
        sub_component_name + "f", my_project.bank, "float32"
    )

    p_ferry = emmeMatrix_to_numpyMatrix(
        sub_component_name + "f", my_project.bank, "float32"
    )

    commuter_rail = emmeMatrix_to_numpyMatrix(
        sub_component_name + "c", my_project.bank, "float32"
    )

    condition[1] = np.where(condition[0] == True, False, condition[1])
    condition[2] = np.where((condition[0] + condition[1]), False, condition[2])
    condition[3] = np.where(
        (condition[0] + condition[1] + condition[2]), False, condition[3]
    )
    condition[4] = np.where(
        (condition[0] + condition[1] + condition[2] + condition[3]), False, condition[4]
    )

    skim = (
        np.where([condition[0]], bus, 0)
        + np.where([condition[1]], rail, 0)
        + np.where([condition[2]], ferry, 0)
        + np.where([condition[2]], p_ferry, 0)
        + np.where([condition[2]], commuter_rail, 0)
    )
    skim = skim.reshape([matrix_size, matrix_size])
    return skim


def emmeMatrix_to_numpyMatrix(
    matrix_name, emmebank, np_data_type, multiplier=1, max_value=None
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


def bike_and_walk_skims(emme_project, tod, results_dict):
    results_dict["TIMEBIKE"] = emmeMatrix_to_numpyMatrix(
        "biket", emme_project.bank, "float32"
    )

    results_dict["TIMEWALK"] = emmeMatrix_to_numpyMatrix(
        "walkt", emme_project.bank, "float32"
    )

    # Assuming 10 mph bike speed
    results_dict["DISTBIKE"] = emmeMatrix_to_numpyMatrix(
        "walkt", emme_project.bank, "float32"
    ) * (10.0 / 60.0)

    # Assuming 3 mph bike speed
    results_dict["DISTWALK"] = emmeMatrix_to_numpyMatrix(
        "walkt", emme_project.bank, "float32"
    ) * (3.0 / 60.0)

    
    return results_dict


def transit_fare_skims(emme_project, results_dict, time_period):

    # Using AM fares for all time periods for now
    # FIXME Set up park and ride procedure to skim for fares
    results_dict["WLK_TRN_DRV_FAR__" + time_period] = emmeMatrix_to_numpyMatrix(
        "mfafarbx", emme_project.bank, "float32"
    )
    results_dict["DRV_TRN_WLK_FAR__" + time_period] = emmeMatrix_to_numpyMatrix(
        "mfafarbx", emme_project.bank, "float32"
    )
    for mtc_mode in ["COM", "FRY", "HVY", "LOC", "LR"]:
        # Fare
        results_dict[
            "WLK_" + mtc_mode + "_WLK_FAR__" + time_period
        ] = emmeMatrix_to_numpyMatrix("mfafarbx", emme_project.bank, "float32")
    return results_dict


def distance_skims(emme_project, results_dict, time_period, vot_dict):
    # Vehicle matrices
    #### DISTANCE ####

    results_dict["DIST"] = emmeMatrix_to_numpyMatrix(
        "sov_inc2d", emme_project.bank, "float32"
    )
    results_dict["medium_truckd"] = emmeMatrix_to_numpyMatrix(
        "medium_truckd", emme_project.bank, "float32"
    )
    results_dict["heavy_truckd"] = emmeMatrix_to_numpyMatrix(
        "heavy_truckd", emme_project.bank, "float32"
    )

    for k, v in vot_dict.items():
        results_dict[f"SOV_DIST_{k}__" + time_period] = emmeMatrix_to_numpyMatrix(
        f"sov_{v}d", emme_project.bank, "float32"
    )

        results_dict[f"HOV2_DIST_{k}__" + time_period] = emmeMatrix_to_numpyMatrix(
        f"hov2_{v}d", emme_project.bank, "float32"
    )

        results_dict[f"HOV3_DIST_{k}__" + time_period] = emmeMatrix_to_numpyMatrix(
        f"hov3_{v}d", emme_project.bank, "float32"
    )

        results_dict[f"SOV_DIST_{k}__" + time_period] = emmeMatrix_to_numpyMatrix(
        f"sov_{v}d", emme_project.bank, "float32"
    )

        results_dict[f"HOV2_DIST_{k}__" + time_period] = emmeMatrix_to_numpyMatrix(
        f"hov2_{v}d", emme_project.bank, "float32"
    )

        results_dict[f"HOV3_DIST_{k}__" + time_period] = emmeMatrix_to_numpyMatrix(
        f"hov3_{v}d", emme_project.bank, "float32"
    )

        results_dict[f"SOVTOLL_DIST_{k}__" + time_period] = emmeMatrix_to_numpyMatrix(
        f"sov_{v}d", emme_project.bank, "float32"
    )

        results_dict[f"HOV2TOLL_DIST_{k}__" + time_period] = emmeMatrix_to_numpyMatrix(
        f"hov2_{v}d", emme_project.bank, "float32"
    )

        results_dict[f"HOV3TOLL_DIST_{k}__" + time_period] = emmeMatrix_to_numpyMatrix(
        f"hov3_{v}d", emme_project.bank, "float32"
    )

        results_dict[f"SOVTOLL_DIST_{k}__" + time_period] = emmeMatrix_to_numpyMatrix(
        f"sov_{v}d", emme_project.bank, "float32"
    )

        results_dict[f"HOV2TOLL_DIST_{k}__" + time_period] = emmeMatrix_to_numpyMatrix(
        f"hov2_{v}d", emme_project.bank, "float32"
    )

        results_dict[f"HOV3TOLL_DIST_{k}__" + time_period] = emmeMatrix_to_numpyMatrix(
        f"hov3_{v}d", emme_project.bank, "float32"
    )

    return results_dict

def bridge_skims(results_dict, tod):
    matrix_size = len(results_dict[list(results_dict.keys())[0]])
    zero_array = np.zeros((matrix_size, matrix_size))
    # BTOLL is bridge toll
    # Set this to 0 and only use the value toll (?)

    results_dict["SOV_BTOLL__" + tod] = zero_array
    results_dict["HOV2_BTOLL__" + tod] = zero_array
    results_dict["HOV3_BTOLL__" + tod] = zero_array
    results_dict["SOVTOLL_BTOLL__" + tod] = zero_array
    results_dict["HOV2TOLL_BTOLL__" + tod] = zero_array
    results_dict["HOV3TOLL_BTOLL__" + tod] = zero_array

    return results_dict


def time_cost_skims(emme_project, results_dict, tod, vot_dict):

    for k, v in vot_dict.items():

    # Auto Time
        results_dict[f"SOV_TIME_{k}__" + tod] = emmeMatrix_to_numpyMatrix(
        f"sov_{v}t", emme_project.bank, "float32"
    )

        results_dict[f"HOV2_TIME_{k}__" + tod] = emmeMatrix_to_numpyMatrix(
        f"hov2_{v}t", emme_project.bank, "float32"
    )

        results_dict[f"HOV3_TIME_{k}__" + tod] = emmeMatrix_to_numpyMatrix(
        f"hov3_{v}t", emme_project.bank, "float32"
    )

        results_dict[f"SOVTOLL_TIME_{k}__" + tod] = emmeMatrix_to_numpyMatrix(
        f"sov_{v}t", emme_project.bank, "float32"
    )

        results_dict[f"HOV2TOLL_TIME_{k}__" + tod] = emmeMatrix_to_numpyMatrix(
        f"hov2_{v}t", emme_project.bank, "float32"
    )

        results_dict[f"HOV3TOLL_TIME_{k}__" + tod] = emmeMatrix_to_numpyMatrix(
        f"hov3_{v}t", emme_project.bank, "float32"
    )

        results_dict[f"SOVTOLL_VTOLL_{k}__" + tod] = emmeMatrix_to_numpyMatrix(
        f"sov_{v}c", emme_project.bank, "float32"
    )

        results_dict[f"HOV2TOLL_VTOLL_{k}__" + tod] = emmeMatrix_to_numpyMatrix(
        f"hov2_{v}c", emme_project.bank, "float32"
    )

        results_dict[f"HOV3TOLL_VTOLL_{k}__" + tod] = emmeMatrix_to_numpyMatrix(
        f"hov3_{v}c", emme_project.bank, "float32"
    )
    
    return results_dict

def park_and_ride_skims(emme_project, results_dict, tod):

    for dir in ['DRV_TRN_WLK_', 'WLK_TRN_DRV_']:
        for component in ['WAUX', 'DDIST', 'DTIM', 'TOTIVT', 'WAIT', 'IWAIT', "BOARDS"]:
            matrix_name = dir + component 
            skim_name = matrix_name + '__' + tod
            skim = emmeMatrix_to_numpyMatrix(matrix_name, emme_project.bank, "float32")
            listOfCoordinates= list(zip(skim[0], skim[1]))
            max_value = np.nanmax(skim[skim != np.inf])
            skim = np.nan_to_num(skim, copy=True, posinf=max_value)
            assert np.isnan(np.min(skim)) == False
            assert True not in np.isinf(skim)
            results_dict[skim_name] = skim
        results_dict[dir + "XWAIT__" + tod] =  results_dict[dir + "WAIT__" + tod] - results_dict[dir + "IWAIT__" + tod]
    
        return results_dict

def transit_skims(emme_project, results_dict, tod):
    submode_dict = {"COM": "c", "LR": "r", "LOC": "a", "FRY": "f"}

    for mtc_mode, psrc_mode in submode_dict.items():
        print(mtc_mode)
        # if mtc_mode == 'LOC':
        # Walk Access Time
        results_dict[
            "WLK_" + mtc_mode + "_WLK_WAUX__" + tod
        ] = emmeMatrix_to_numpyMatrix(
            "auxw" + psrc_mode, emme_project.bank, "float32"
        )

        # Initial Wait Time
        results_dict[
            "WLK_" + mtc_mode + "_WLK_IWAIT__" + tod
        ] = emmeMatrix_to_numpyMatrix(
            "iwtw" + psrc_mode, emme_project.bank, "float32"
        )

        # Total Wait Time
        results_dict[
            "WLK_" + mtc_mode + "_WLK_WAIT__" + tod
        ] = emmeMatrix_to_numpyMatrix(
            "twtw" + psrc_mode, emme_project.bank, "float32"
        )

        # In vehicle time for Walk access/egress
        results_dict[
            "WLK_" + mtc_mode + "_WLK_TOTIVT__" + tod
        ] = emmeMatrix_to_numpyMatrix(
            "ivtw" + psrc_mode, emme_project.bank, "float32"
        )

        if not mtc_mode == "LOC":
            results_dict[
                "WLK_" + mtc_mode + "_WLK_KEYIVT__" + tod
            ] = emmeMatrix_to_numpyMatrix(
                "ivtw" + psrc_mode + psrc_mode, emme_project.bank, "float32"
            )

            if mtc_mode == "LRF":
                results_dict[
                    "WLK_" + mtc_mode + "_WLK_FERRYIVT__" + tod
                ] = emmeMatrix_to_numpyMatrix(
                    "ivtw" + psrc_mode + psrc_mode,
                    emme_project.bank.bank,
                    "float32",
                )

            # Transfer Time
        results_dict[
            "WLK_" + mtc_mode + "_WLK_XWAIT__" + tod
        ] = emmeMatrix_to_numpyMatrix(
            "xfrw" + psrc_mode, emme_project.bank, "float32"
        )

        # Boardings
        results_dict[
            "WLK_" + mtc_mode + "_WLK_BOARDS__" + tod
        ] = emmeMatrix_to_numpyMatrix(
            "ndbw" + psrc_mode, emme_project.bank, "float32"
        )

    return results_dict

def all_transit_skims(emme_project, results_dict, tod):

    # emme_project.change_active_database(hour)
    results_dict["WLK_TRN_WLK_WAUX__" + tod] = emmeMatrix_to_numpyMatrix("auxwa", emme_project.bank, "float32")
    results_dict["WLK_TRN_WLK_TWAIT__" + tod] = emmeMatrix_to_numpyMatrix("twtwa", emme_project.bank, "float32")
    results_dict["WLK_TRN_WLK_IWAIT__" + tod] = emmeMatrix_to_numpyMatrix("iwtwa", emme_project.bank, "float32")
    results_dict["WLK_TRN_WLK_IVT__" + tod] = emmeMatrix_to_numpyMatrix("ivtwa", emme_project.bank, "float32")
    results_dict["WLK_TRN_WLK_XWAIT__" + tod] =  emmeMatrix_to_numpyMatrix("xfrwa", emme_project.bank, "float32")
    results_dict["WLK_TRN_WLK_TOTIVT__" + tod] =  emmeMatrix_to_numpyMatrix("ivtwa", emme_project.bank, "float32")
    results_dict["WLK_TRN_WLK_BOARDS__" + tod] =  emmeMatrix_to_numpyMatrix("ivtwa", emme_project.bank, "float32")
    
    return results_dict

def create_skims(my_project, skim_file_path, time_period):
    results_dict = {}
    vot_dict = {"L" : "inc1", "M" : "inc2", "H" : "inc3"}

    results_dict = bike_and_walk_skims(my_project, "5to6", results_dict)
    results_dict = transit_fare_skims(
        my_project, "6to7", results_dict, time_period
    )
    results_dict = distance_skims(my_project, "7to8", results_dict, time_period, vot_dict)
    results_dict = bridge_skims(results_dict, time_period)
    results_dict = time_cost_skims(my_project, results_dict, time_period, vot_dict)
    results_dict = transit_skims(my_project, results_dict, time_period)
    results_dict = park_and_ride_skims(my_project, results_dict, time_period)
    results_dict = all_transit_skims(my_project, results_dict, time_period)
    f = omx.open_file(skim_file_path, "w")
    for skim_matrix in results_dict.keys():
        print(skim_matrix)
        # statsDict= {attr:getattr(skim_matrix,attr)() for attr in ['min', 'max','mean','std']}
        f[skim_matrix] = results_dict[skim_matrix]

    f.close()