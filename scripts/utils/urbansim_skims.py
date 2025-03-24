import pandas as pd
import array as _array
import inro.emme.desktop.app as app
import inro.modeller as _m
import inro.emme.matrix as ematrix
import inro.emme.database.matrix
import inro.emme.database.emmebank as _eb
import json
import numpy as np
import time
import os, sys
import multiprocessing as mp
import subprocess
from multiprocessing import Pool
import h5py

sys.path.append(os.path.join(os.getcwd(), "scripts"))
sys.path.append(os.path.join(os.getcwd(), "scripts/trucks"))
sys.path.append(os.getcwd())
# from emme_configuration import *
from scripts.emme_project import *
import toml

emme_config = toml.load(
    os.path.join(os.getcwd(), "configuration/emme_configuration.toml")
)


def init_dir(directory):
    if os.path.exists(directory):
        shutil.rmtree(directory)
    os.mkdir(directory)


def json_to_dictionary(dict_name):
    # Determine the Path to the input files and load them
    input_filename = os.path.join(
        "inputs/model/skim_parameters/lookup", dict_name
    ).replace("\\", "/")
    my_dictionary = json.load(open(input_filename))
    return my_dictionary


def load_skims(skim_file_loc, mode_name, divide_by_100=False):
    """Loads H5 skim matrix for specified mode."""
    with h5py.File(skim_file_loc, "r") as f:
        skim_file = f["Skims"][mode_name][:]
    # Divide by 100 since decimals were removed in H5 source file through multiplication
    if divide_by_100:
        return skim_file.astype(float) / 100.0
    else:
        return skim_file


def load_skim_data(trip_purpose, np_matrix_name_input, TrueOrFalse):
    # get am and pm skim
    am_skim = load_skims(
        r"inputs/model/roster/7to8.h5",
        mode_name=np_matrix_name_input,
        divide_by_100=TrueOrFalse,
    )
    pm_skim = load_skims(
        r"inputs/model/roster/17to18.h5",
        mode_name=np_matrix_name_input,
        divide_by_100=TrueOrFalse,
    )

    # calculate the bi_dictional skim
    return (am_skim + pm_skim) * 0.5


def get_cost_time_distance_skim_data(trip_purpose):
    skim_dict = {}
    input_skim = {
        "hbw1": {
            "cost": {"svt": "sov_inc1c", "h2v": "hov2_inc1c", "h3v": "hov3_inc1c"},
            "time": {"svt": "sov_inc1t", "h2v": "hov2_inc1t", "h3v": "hov3_inc1t"},
            "distance": {"svt": "sov_inc1d", "h2v": "hov2_inc1d", "h3v": "hov3_inc1d"},
        },
        "hbw2": {
            "cost": {"svt": "sov_inc2c", "h2v": "hov2_inc2c", "h3v": "hov3_inc2c"},
            "time": {"svt": "sov_inc2t", "h2v": "hov2_inc2t", "h3v": "hov3_inc2t"},
            "distance": {"svt": "sov_inc2d", "h2v": "hov2_inc2d", "h3v": "hov3_inc2d"},
        },
        "hbw3": {
            "cost": {"svt": "sov_inc2c", "h2v": "hov2_inc2c", "h3v": "hov3_inc2c"},
            "time": {"svt": "sov_inc2t", "h2v": "hov2_inc2t", "h3v": "hov3_inc2t"},
            "distance": {"svt": "sov_inc2d", "h2v": "hov2_inc2d", "h3v": "hov3_inc2d"},
        },
        "hbw4": {
            "cost": {"svt": "sov_inc3c", "h2v": "hov2_inc3c", "h3v": "hov3_inc3c"},
            "time": {"svt": "sov_inc3t", "h2v": "hov2_inc3t", "h3v": "hov3_inc3t"},
            "distance": {"svt": "sov_inc3d", "h2v": "hov2_inc3d", "h3v": "hov3_inc3d"},
        },
        "nhb": {
            "cost": {"svt": "sov_inc1c", "h2v": "hov2_inc1c", "h3v": "hov3_inc1c"},
            "time": {"svt": "sov_inc1t", "h2v": "hov2_inc1t", "h3v": "hov3_inc1t"},
            "distance": {"svt": "sov_inc1d", "h2v": "hov2_inc1d", "h3v": "hov3_inc1d"},
        },
        "hbo": {
            "cost": {"svt": "sov_inc1c", "h2v": "hov2_inc1c", "h3v": "hov3_inc1c"},
            "time": {"svt": "sov_inc1t", "h2v": "hov2_inc1t", "h3v": "hov3_inc1t"},
            "distance": {"svt": "sov_inc1d", "h2v": "hov2_inc1d", "h3v": "hov3_inc1d"},
        },
    }
    output_skim = {
        "cost": {"svt": "dabcs", "h2v": "s2bcs", "h3v": "s3bcs"},
        "time": {"svt": "dabtm", "h2v": "s2btm", "h3v": "s3btm"},
        "distance": {"svt": "dabds", "h2v": "s2bds", "h3v": "s3bds"},
    }

    for skim_name in ["cost", "time", "distance"]:
        for sov_hov in ["svt", "h2v", "h3v"]:
            skim_dict[output_skim[skim_name][sov_hov]] = load_skim_data(
                trip_purpose, input_skim[trip_purpose][skim_name][sov_hov], True
            )

    return skim_dict


def get_walk_bike_skim_data():
    skim_dict = {}
    for skim_name in ["walkt", "biket"]:
        skim_dict[skim_name] = load_skims(
            r"inputs/model/roster/5to6.h5", mode_name=skim_name, divide_by_100=True
        )
    return skim_dict


def get_transit_skim_data():
    transit_skim_dict = {
        "ivtwa": "ivtwa",
        "iwtwa": "iwtwa",
        "ndbwa": "ndbwa",
        "xfrwa": "xfrwa",
        "auxwa": "auxwa",
        "ivtwr": "ivtwr",
        "iwtwr": "iwtwr",
        "ndbwr": "ndbwr",
        "xfrwr": "xfrwr",
        "auxwr": "auxwr",
        "farwa": "mfafarps",
        "farbx": "mfafarbx",
    }
    skim_dict = {}

    for input, output in transit_skim_dict.items():
        if input in ["farbx", "farwa"]:
            skim_dict[input] = load_skims(
                r"inputs/model/roster/6to7.h5", mode_name=output, divide_by_100=True
            )
        else:
            am_skim = load_skims(
                r"inputs/model/roster/7to8.h5", mode_name=output, divide_by_100=True
            )
            pm_skim = load_skims(
                r"inputs/model/roster/17to18.h5", mode_name=output, divide_by_100=True
            )
            skim_dict[input] = (am_skim + pm_skim) * 0.5

    return skim_dict


def get_total_transit_time(tod):
    rail_component_list = ["ivtwr", "auxwr", "iwtwr", "xfrwr"]
    bus_component_list = ["ivtwa", "auxwa", "iwtwa", "xfrwa"]
    rail_skims = {}
    bus_skims = {}
    for component in rail_component_list:
        rail_skims[component] = load_skims(
            "inputs/model/roster/" + tod + ".h5",
            mode_name=component,
            divide_by_100=True,
        )
    for component in bus_component_list:
        bus_skims[component] = load_skims(
            "inputs/model/roster/" + tod + ".h5",
            mode_name=component,
            divide_by_100=True,
        )

    rail = sum(rail_skims.values())
    bus = sum(bus_skims.values())
    bus[rail <= bus] = 0
    rail[bus < rail] = 0
    return bus + rail


def get_total_sov_trips(tod_list):
    trip_table = np.zeros((len(zones), len(zones)))
    for tod in tod_list:
        for trip_table_name in ["sov_inc1", "sov_inc2", "sov_inc3"]:
            my_bank = _eb.Emmebank("Banks/" + tod + "/emmebank")
            skim = my_bank.matrix(trip_table_name).get_numpy_data()
            trip_table = trip_table + skim
    return trip_table


def calculate_auto_cost(trip_purpose, auto_skim_dict, parking_cost_array):
    input_paramas_vot_name = {
        "hbw1": {"svt": "avot1v", "h2v": "avots2", "h3v": "avots3"},
        "hbw2": {"svt": "avot2v", "h2v": "avots2", "h3v": "avots3"},
        "hbw3": {"svt": "avot3v", "h2v": "avots2", "h3v": "avots3"},
        "hbw4": {"svt": "avot4v", "h2v": "avots2", "h3v": "avots3"},
        "nhb": {"svt": "mvotda", "h2v": "mvots2", "h3v": "mvots3"},
        "hbo": {"svt": "mvotda", "h2v": "mvots2", "h3v": "mvots3"},
    }
    output_auto_cost_name = {"svt": "dabct", "h2v": "s2bct", "h3v": "s3bct"}

    auto_cost_matrices = {}

    # *******Code below is different from 4k in that 4k uses generalized time - time / vot to get cost. Soundcat already has a cost skims, so no need to do that.*******

    # SOV
    auto_cost_matrices["dabct"] = (
        auto_skim_dict["dabds"] * parameters_dict["autoop"]
        + auto_skim_dict["dabcs"]
        + (parking_cost_array / 2)
    )

    # HOV 2 passenger
    auto_cost_matrices["s2bct"] = (
        auto_skim_dict["s2bds"] * parameters_dict["autoop"]
        + auto_skim_dict["s2bcs"]
        + (parking_cost_array / 2)
    ) / 2

    # HOV 2 passenger                                 #'+ (md"daily"/2))/2')
    auto_cost_matrices["s3bct"] = (
        auto_skim_dict["s3bds"] * parameters_dict["autoop"]
        + auto_skim_dict["s3bcs"]
        + (parking_cost_array / 2)
    ) / 3.5
    # + (md"daily"/2))/3.5')

    return auto_cost_matrices


def calculate_log_sums(trip_purpose, mode_utilities_dict):
    output_logsum_name = {
        "hbw1": "lsum1",
        "hbw2": "lsum2",
        "hbw3": "lsum3",
        "hbw4": "lsum4",
    }
    # Calculate the sum of utility: eusm
    skim = np.log(
        mode_utilities_dict["euda"]
        + mode_utilities_dict["eus2"]
        + mode_utilities_dict["eus3"]
        + mode_utilities_dict["eutw"]
        + mode_utilities_dict["eurw"]
        + mode_utilities_dict["eubk"]
        + mode_utilities_dict["euwk"]
    )

    name = output_logsum_name[trip_purpose]
    return name, skim


def test(taz):
    return zone_lookup_dict[taz]


def get_destination_parking_costs(parcel_file):
    parking_cost_array = np.zeros(len(zones))
    df = pd.read_csv(parcel_file, sep=" ")
    df = df[df.PPRICDYP > 0]
    df1 = pd.DataFrame(df.groupby("TAZ_P").mean()["PPRICDYP"])
    df1.reset_index(inplace=True)
    df1["zone_index"] = df1.TAZ_P.apply(test)
    df1 = df1.set_index("zone_index")
    parking = df1["PPRICDYP"]
    parking = parking.reindex([zone_lookup_dict[x] for x in zones])
    parking.fillna(0, inplace=True)
    return np.array(parking)


def calculate_mode_utilties(
    trip_purpose, auto_skim_dict, walk_bike_skim_dict, transit_skim_dict, auto_cost_dict
):
    """
    some submatrices restrictions:
    mode_choice.bat : %hightaz% %lowstation% %highstation% %lowpnr% %highpnr%
    %1%: 3700 - regional TAZ
    %2%: 3733 - external TAZ
    %3%: 3750 - external TAZ
    %4%: 3751 - PNR TAZ
    %5%: 4000 - PNR TAZ

    there are -e+21 values in the TAZ zone after 3751, it is because the ln(0)
    will come back fix it later
    """

    utility_matrices = {}

    # Calculate Drive Alone Utility
    utility_matrices["euda"] = np.exp(
        parameters_dict[trip_purpose]["autivt"] * auto_skim_dict["dabtm"]
        + parameters_dict[trip_purpose]["autcos"] * auto_cost_dict["dabct"]
    )
    # rows, cols includes internal, externals, exclude p&rs
    zone_start_constraint = zone_lookup_dict[3751]
    utility_matrices["euda"][zone_start_constraint:] = 0
    utility_matrices["euda"][:, zone_start_constraint:] = 0

    # Calculate Shared Ride 2 utility
    utility_matrices["eus2"] = np.exp(
        parameters_dict[trip_purpose]["asccs2"]
        + parameters_dict[trip_purpose]["autivt"] * auto_skim_dict["s2btm"]
        + parameters_dict[trip_purpose]["autcos"] * auto_cost_dict["s2bct"]
    )
    # rows, cols includes internal, externals, exclude p&rs
    zone_start_constraint = zone_lookup_dict[3751]
    utility_matrices["eus2"][zone_start_constraint:] = 0
    utility_matrices["eus2"][:, zone_start_constraint:] = 0

    # Calculate Shared Ride 3+ Utility
    utility_matrices["eus3"] = np.exp(
        parameters_dict[trip_purpose]["asccs3"]
        + parameters_dict[trip_purpose]["autivt"] * auto_skim_dict["s3btm"]
        + parameters_dict[trip_purpose]["autcos"] * auto_cost_dict["s3bct"]
    )
    # rows, cols includes internal, externals, exclude p&rs
    zone_start_constraint = zone_lookup_dict[3751]
    utility_matrices["eus3"][zone_start_constraint:] = 0
    utility_matrices["eus3"][:, zone_start_constraint:] = 0

    # Calculate Walk to Transit Utility
    utility_matrices["eutw"] = np.exp(
        parameters_dict[trip_purpose]["ascctw"]
        + parameters_dict[trip_purpose]["trwivt"] * transit_skim_dict["ivtwa"]
        + parameters_dict[trip_purpose]["trwovt"]
        * (
            transit_skim_dict["auxwa"]
            + transit_skim_dict["iwtwa"]
            + transit_skim_dict["xfrwa"]
        )
        + parameters_dict[trip_purpose]["trwcos"] * transit_skim_dict["farwa"]
    )
    # rows, cols includes internal, excludes extermal, p&rs (no walk, transit to external stations)
    zone_start_constraint = zone_lookup_dict[3733]
    utility_matrices["eutw"][zone_start_constraint:] = 0
    utility_matrices["eutw"][:, zone_start_constraint:] = 0

    # Calculate Walk to Light Rail Utility
    utility_matrices["eurw"] = np.exp(
        parameters_dict[trip_purpose]["ascctw"]
        + parameters_dict[trip_purpose]["trwivt"] * transit_skim_dict["ivtwr"]
        + parameters_dict[trip_purpose]["trwovt"]
        * (
            transit_skim_dict["auxwr"]
            + transit_skim_dict["iwtwr"]
            + transit_skim_dict["xfrwr"]
        )
        + parameters_dict[trip_purpose]["trwcos"] * transit_skim_dict["farwa"]
    )
    # rows, cols includes internal, excludes extermal, p&rs (no walk, transit to external stations)
    zone_start_constraint = zone_lookup_dict[3733]
    utility_matrices["eurw"][zone_start_constraint:] = 0
    utility_matrices["eurw"][:, zone_start_constraint:] = 0

    # keep best utility between regular transit and light rail. Give to light rail if there is a tie.
    utility_matrices["eutw"][utility_matrices["eurw"] >= utility_matrices["eutw"]] = 0
    utility_matrices["eurw"][utility_matrices["eutw"] > utility_matrices["eurw"]] = 0

    # Calculate Walk Utility
    utility_matrices["euwk"] = np.exp(
        parameters_dict[trip_purpose]["asccwk"]
        + parameters_dict[trip_purpose]["walktm"] * walk_bike_skim_dict["walkt"]
    )
    # rows, cols includes internal, excludes extermal, p&rs (no walk, transit to external stations)
    zone_start_constraint = zone_lookup_dict[3733]
    utility_matrices["euwk"][zone_start_constraint:] = 0
    utility_matrices["euwk"][:, zone_start_constraint:] = 0

    # Calculate Bike Utility
    utility_matrices["eubk"] = np.exp(
        parameters_dict[trip_purpose]["asccbk"]
        + parameters_dict[trip_purpose]["biketm"] * walk_bike_skim_dict["biket"]
    )
    # rows, cols includes internal, excludes extermal, p&rs (no walk, transit to most external stations)
    zone_start_constraint = zone_lookup_dict[3733]
    utility_matrices["eubk"][zone_start_constraint:] = 0
    utility_matrices["eubk"][:, zone_start_constraint:] = 0

    return utility_matrices


# Validate, test the results
def test_results():
    shda = my_project.bank.matrix("mf68").get_numpy_data()
    shs2 = my_project.bank.matrix("mf69").get_numpy_data()
    shs3 = my_project.bank.matrix("mf70").get_numpy_data()
    shtw = my_project.bank.matrix("mf71").get_numpy_data()
    shtd = my_project.bank.matrix("mf72").get_numpy_data()
    shbk = my_project.bank.matrix("mf73").get_numpy_data()
    shwk = my_project.bank.matrix("mf74").get_numpy_data()

    sum = shda + shs2 + shs3 + shtw + shtd + shbk + shwk
    error = 0
    for i in range(0, 3868):
        for j in range(0, 3868):
            if sum[i][j] > 0.1 and sum[i][j] < 0.9:
                # every value should be very close to 1, so that means nothing would print out at this step.
                error += 1


def mode_choice_to_h5(trip_purpose, mode_shares_dict):
    output_mode_share_name = {
        "hbw1": [
            "eusm",
            "w1shda",
            "w1shs2",
            "w1shs3",
            "w1shtw",
            "w1shrw",
            "w1shtd",
            "w1shbk",
            "w1shwk",
        ],
        "hbw2": [
            "eusm",
            "w2shda",
            "w2shs2",
            "w2shs3",
            "w2shtw",
            "w2shrw",
            "w2shtd",
            "w2shbk",
            "w2shwk",
        ],
        "hbw3": [
            "eusm",
            "w3shda",
            "w3shs2",
            "w3shs3",
            "w3shtw",
            "w3shrw",
            "w3shtd",
            "w3shbk",
            "w3shwk",
        ],
        "hbw4": [
            "eusm",
            "w4shda",
            "w4shs2",
            "w4shs3",
            "w4shtw",
            "w4shrw",
            "w4shtd",
            "w4shbk",
            "w4shwk",
        ],
        "nhb": [
            "eusm",
            "nhshda",
            "nhshs2",
            "nhshs3",
            "nhshtw",
            "nhshrw",
            "nhshbk",
            "nhshwk",
        ],
        "hbo": [
            "eusm",
            "nwshda",
            "nwshs2",
            "nwshs3",
            "nwshtw",
            "nwshrw",
            "nwshbk",
            "nwshwk",
        ],
    }

    my_store = h5py.File(
        emme_config["urbansim_skims_dir"] + "/" + trip_purpose + "_ratio.h5", "w"
    )
    grp = my_store.create_group(trip_purpose)
    for mode in output_mode_share_name[trip_purpose]:
        grp.create_dataset(mode, data=mode_shares_dict[mode])
        print(mode)
    my_store.close()


def urbansim_skims_to_h5(h5_name, skim_dict):
    my_store = h5py.File(emme_config["urbansim_skims_dir"] + "/" + h5_name + ".h5", "w")
    grp = my_store.create_group("results")
    for name, skim in skim_dict.items():
        skim = skim[0:max_internal_zone, 0:max_internal_zone]
        grp.create_dataset(name, data=skim.astype("float32"), compression="gzip")
        print(skim)

    my_store.close()


def main():
    trip_purpose_list = ["hbw1", "hbw2", "hbw3", "hbw4"]

    urbansim_skim_dict = {}

    # am_single_vehicle_to_work_travel_time
    urbansim_skim_dict["aau1tm"] = load_skims(
        "inputs/model/roster/7to8.h5", mode_name="sov_inc1t", divide_by_100=True
    )

    # am_single_vehicle_to_work_toll
    urbansim_skim_dict["aau1tl"] = load_skims(
        "inputs/model/roster/7to8.h5", mode_name="sov_inc1c", divide_by_100=False
    )

    # single_vehicle_to_work_travel_distance
    urbansim_skim_dict["aau1ds"] = load_skims(
        "inputs/model/roster/7to8.h5", mode_name="sov_inc1d", divide_by_100=True
    )

    # am_walk_time_in_minutes
    urbansim_skim_dict["awlktm"] = load_skims(
        "inputs/model/roster/5to6.h5", mode_name="walkt", divide_by_100=True
    )

    # am_pk_period_drive_alone_vehicle_trips
    urbansim_skim_dict["avehda"] = get_total_sov_trips(["6to7", "7to8", "8to9"])

    # am_total_transit_time_walk
    urbansim_skim_dict["atrtwa"] = get_total_transit_time("7to8")

    # single_vehicle_to_work_travel_cost
    urbansim_skim_dict["aau1cs"] = load_skims(
        "inputs/model/roster/7to8.h5", mode_name="sov_inc2g", divide_by_100=False
    )

    for trip_purpose in trip_purpose_list:
        print(trip_purpose)

        auto_skim_dict = get_cost_time_distance_skim_data(trip_purpose)
        print("get auto skim done")

        walk_bike_skim_dict = get_walk_bike_skim_data()
        print("get walk bike skim done")

        transit_skim_dict = get_transit_skim_data()
        print("transit skim done")

        parking_costs = get_destination_parking_costs(parcels_file_name)

        auto_cost_dict = calculate_auto_cost(
            trip_purpose, auto_skim_dict, parking_costs
        )

        mode_utilities_dict = calculate_mode_utilties(
            trip_purpose,
            auto_skim_dict,
            walk_bike_skim_dict,
            transit_skim_dict,
            auto_cost_dict,
        )
        print("calculate mode utilities done")

        name, skim = calculate_log_sums(trip_purpose, mode_utilities_dict)
        urbansim_skim_dict[name] = skim
        print("calculate log sums done")

        # mode_choice_to_h5(trip_purpose, mode_shares_dict)
        # print trip_purpose, 'is done'
    urbansim_skims_to_h5(config["model_year"] + "-travelmodel", urbansim_skim_dict)


my_project = EmmeProject(r"projects/Supplementals/Supplementals.emp")
zones = my_project.current_scenario.zone_numbers
max_internal_zone = 3700
# Create a dictionary lookup where key is the taz id and value is it's numpy index.
zone_lookup_dict = dict((value, index) for index, value in enumerate(zones))
# origin_destination_dict = json_to_dictionary(r'supplemental_matrices_dict.txt')
parameters_dict = json_to_dictionary("urbansim_skims_parameters.json")
ensembles_path = r"inputs/scenario/supplemental/generation/ensembles/ensembles_list.csv"
parcels_file_name = "inputs/scenario/landuse/parcels_urbansim.txt"

if not os.path.exists(emme_config["urbansim_skims_dir"]):
    os.makedirs(emme_config["urbansim_skims_dir"])

if __name__ == "__main__":
    main()
