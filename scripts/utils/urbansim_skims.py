import os
import numpy as np
import pandas as pd
import inro.emme.database.matrix
import inro.emme.database.emmebank as _eb
import json
import h5py
# from scripts.emme_project import *


def json_to_dictionary(state, dict_name):
    # Determine the Path to the input files and load them
    input_filename = os.path.join(
        f"inputs/model/{state.input_settings.abm_model}/skim_parameters/lookup", dict_name
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


def load_skim_data(state, trip_purpose, np_matrix_name_input, TrueOrFalse):
    # get am and pm skim
    am_skim = load_skims(
        f"inputs/model/{state.input_settings.abm_model}/roster/7to8.h5",
        mode_name=np_matrix_name_input,
        divide_by_100=TrueOrFalse,
    )
    pm_skim = load_skims(
        f"inputs/model/{state.input_settings.abm_model}/roster/17to18.h5",
        mode_name=np_matrix_name_input,
        divide_by_100=TrueOrFalse,
    )

    # calculate the bi_dictional skim
    return (am_skim + pm_skim) * 0.5


def get_cost_time_distance_skim_data(state, trip_purpose):
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
                state, trip_purpose, input_skim[trip_purpose][skim_name][sov_hov], True
            )

    return skim_dict


def get_walk_bike_skim_data(state):
    skim_dict = {}
    for skim_name in ["walkt", "biket"]:
        skim_dict[skim_name] = load_skims(
            f"inputs/model/{state.input_settings.abm_model}/roster/5to6.h5", mode_name=skim_name, divide_by_100=True
        )
    return skim_dict


def get_transit_skim_data(state):
    transit_skim_dict = {
        "ivtwa": "ivtwa",
        "iwtwa": "iwtwa",
        "ndbwa": "ndbwa",
        "xfrwa": "xfrwa",
        "auxwa": "auxwa",
        "farwa": "mfafarps",
        "farbx": "mfafarbx",
    }
    skim_dict = {}

    for input, output in transit_skim_dict.items():
        if input in ["farbx", "farwa"]:
            skim_dict[input] = load_skims(
                f"inputs/model/{state.input_settings.abm_model}/roster/6to7.h5", mode_name=output, divide_by_100=True
            )
        else:
            am_skim = load_skims(
                f"inputs/model/{state.input_settings.abm_model}/roster/7to8.h5", mode_name=output, divide_by_100=True
            )
            pm_skim = load_skims(
                f"inputs/model/{state.input_settings.abm_model}/roster/17to18.h5", mode_name=output, divide_by_100=True
            )
            skim_dict[input] = (am_skim + pm_skim) * 0.5

    return skim_dict


def get_total_transit_time(tod, state):
    #rail_component_list = ["ivtwr", "auxwr", "iwtwr", "xfrwr"]
    bus_component_list = ["ivtwa", "auxwa", "iwtwa", "xfrwa"]
    #rail_skims = {}
    bus_skims = {}
    # for component in rail_component_list:
    #     rail_skims[component] = load_skims(
    #         f"inputs/model/{state.input_settings.abm_model}/roster/{tod}.h5",
    #         mode_name=component,
    #         divide_by_100=True,
    #     )
    for component in bus_component_list:
        bus_skims[component] = load_skims(
            f"inputs/model/{state.input_settings.abm_model}/roster/{tod}.h5",
            mode_name=component,
            divide_by_100=True,
        )

    #rail = sum(rail_skims.values())
    bus = sum(bus_skims.values())
    #bus[rail <= bus] = 0
    #rail[bus < rail] = 0
    return bus 


def get_total_sov_trips(tod_list, zones):
    trip_table = np.zeros((len(zones), len(zones)))
    for tod in tod_list:
        for trip_table_name in ["sov_inc1", "sov_inc2", "sov_inc3"]:
            my_bank = _eb.Emmebank("Banks/" + tod + "/emmebank")
            skim = my_bank.matrix(trip_table_name).get_numpy_data()
            trip_table = trip_table + skim
    return trip_table


def calculate_auto_cost(trip_purpose, auto_skim_dict, parking_cost_array, parameters_dict):
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
        + mode_utilities_dict["eubk"]
        + mode_utilities_dict["euwk"]
    )

    name = output_logsum_name[trip_purpose]
    return name, skim


def get_destination_parking_costs(parcel_file, zones, zone_lookup_dict):
    parking_cost_array = np.zeros(len(zones))
    df = pd.read_csv(parcel_file, sep=" ")
    df = df[df.ppricdyp > 0]
    df1 = pd.DataFrame(df.groupby("taz_p").mean()["ppricdyp"])
    df1.reset_index(inplace=True)
    # Get zone index for each TAZ from zone_lookup_dict
    df_zone = pd.DataFrame(zone_lookup_dict.items(), columns=["taz_p", "zone_index"])
    df1 = df1.merge(df_zone, on='taz_p')

    df1 = df1.set_index("zone_index")
    parking = df1["ppricdyp"]
    parking = parking.reindex([zone_lookup_dict[x] for x in zones])
    parking.fillna(0, inplace=True)

    return np.array(parking)


def calculate_mode_utilties(
    trip_purpose, auto_skim_dict, walk_bike_skim_dict, transit_skim_dict, auto_cost_dict,
    parameters_dict, zone_lookup_dict
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
    # utility_matrices["eurw"] = np.exp(
    #     parameters_dict[trip_purpose]["ascctw"]
    #     + parameters_dict[trip_purpose]["trwivt"] * transit_skim_dict["ivtwr"]
    #     + parameters_dict[trip_purpose]["trwovt"]
    #     * (
    #         transit_skim_dict["auxwr"]
    #         + transit_skim_dict["iwtwr"]
    #         + transit_skim_dict["xfrwr"]
    #     )
    #     + parameters_dict[trip_purpose]["trwcos"] * transit_skim_dict["farwa"]
    # )
    # rows, cols includes internal, excludes extermal, p&rs (no walk, transit to external stations)
    zone_start_constraint = zone_lookup_dict[3733]
    #utility_matrices["eurw"][zone_start_constraint:] = 0
    #utility_matrices["eurw"][:, zone_start_constraint:] = 0

    # keep best utility between regular transit and light rail. Give to light rail if there is a tie.
    #utility_matrices["eutw"][utility_matrices["eurw"] >= utility_matrices["eutw"]] = 0
    #utility_matrices["eurw"][utility_matrices["eutw"] > utility_matrices["eurw"]] = 0

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


def urbansim_skims_to_h5(state, h5_name, skim_dict):
    my_store = h5py.File(f"{state.emme_settings.urbansim_skims_dir}/{h5_name}.h5", "w")
    grp = my_store.create_group("results")
    for name, skim in skim_dict.items():
        skim = skim[0:3700, 0:3700]
        grp.create_dataset(name, data=skim.astype("float32"), compression="gzip")
        print(skim)

    my_store.close()


def main(state):

    zones = state.main_project.current_scenario.zone_numbers
    zone_lookup_dict = dict((value, index) for index, value in enumerate(zones))
    parameters_dict = json_to_dictionary(state, "urbansim_skims_parameters.json")

    if not os.path.exists(state.emme_settings.urbansim_skims_dir):
        os.makedirs(state.emme_settings.urbansim_skims_dir)
    trip_purpose_list = ["hbw1", "hbw2", "hbw3", "hbw4"]

    urbansim_skim_dict = {}

    # am_single_vehicle_to_work_travel_time
    urbansim_skim_dict["aau1tm"] = load_skims(
        f"inputs/model/{state.input_settings.abm_model}/roster/7to8.h5", mode_name="sov_inc1t", divide_by_100=True
    )

    # am_single_vehicle_to_work_toll
    urbansim_skim_dict["aau1tl"] = load_skims(
        f"inputs/model/{state.input_settings.abm_model}/roster/7to8.h5", mode_name="sov_inc1c", divide_by_100=False
    )

    # single_vehicle_to_work_travel_distance
    urbansim_skim_dict["aau1ds"] = load_skims(
        f"inputs/model/{state.input_settings.abm_model}/roster/7to8.h5", mode_name="sov_inc1d", divide_by_100=True
    )

    # am_walk_time_in_minutes
    urbansim_skim_dict["awlktm"] = load_skims(
        f"inputs/model/{state.input_settings.abm_model}/roster/5to6.h5", mode_name="walkt", divide_by_100=True
    )

    # am_pk_period_drive_alone_vehicle_trips
    urbansim_skim_dict["avehda"] = get_total_sov_trips(["6to7", "7to8", "8to9"], zones)

    # am_total_transit_time_walk
    urbansim_skim_dict["atrtwa"] = get_total_transit_time("7to8", state)

    # single_vehicle_to_work_travel_cost
    urbansim_skim_dict["aau1cs"] = load_skims(
        f"inputs/model/{state.input_settings.abm_model}/roster/7to8.h5", mode_name="sov_inc2g", divide_by_100=False
    )

    for trip_purpose in trip_purpose_list:
        print(trip_purpose)

        auto_skim_dict = get_cost_time_distance_skim_data(state, trip_purpose)
        print("get auto skim done")

        walk_bike_skim_dict = get_walk_bike_skim_data(state)
        print("get walk bike skim done")

        transit_skim_dict = get_transit_skim_data(state)
        print("transit skim done")

        parking_costs = get_destination_parking_costs("outputs/landuse/parcels_urbansim.txt",
                                                      zones, zone_lookup_dict)

        auto_cost_dict = calculate_auto_cost(
            trip_purpose, auto_skim_dict, parking_costs, parameters_dict
        )

        mode_utilities_dict = calculate_mode_utilties(
            trip_purpose,
            auto_skim_dict,
            walk_bike_skim_dict,
            transit_skim_dict,
            auto_cost_dict,
            parameters_dict,
            zone_lookup_dict
        )
        print("calculate mode utilities done")

        name, skim = calculate_log_sums(trip_purpose, mode_utilities_dict)
        urbansim_skim_dict[name] = skim
        print("calculate log sums done")

        # mode_choice_to_h5(trip_purpose, mode_shares_dict)
        # print trip_purpose, 'is done'
    urbansim_skims_to_h5(state, state.input_settings.model_year + "-travelmodel", urbansim_skim_dict)