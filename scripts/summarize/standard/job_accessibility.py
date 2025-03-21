import os, sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(CURRENT_DIR))
sys.path.append(os.path.join(os.getcwd(), "inputs"))
sys.path.append(os.path.join(os.getcwd(), "scripts"))
sys.path.append(os.getcwd())
import collections
import h5py
import re
import time
import pandas as pd
import numpy as np
import pandana as pdna
import inro.emme.database.emmebank as _eb
from pyproj import Proj, transform

# from input_configuration import base_year
import toml

config = toml.load(os.path.join(os.getcwd(), "configuration/input_configuration.toml"))


def assign_nodes_to_dataset(dataset, network, column_name, x_name, y_name):
    """Adds an attribute node_ids to the given dataset."""
    dataset[column_name] = network.get_node_ids(
        dataset[x_name].values, dataset[y_name].values
    )


def process_net_attribute(network, attr, fun, distances):
    # print "Processing %s" % attr
    newdf = None
    for dist_index, dist in distances.items():
        res_name = "%s_%s" % (
            re.sub("_?p$", "", attr),
            dist_index,
        )  # remove '_p' if present
        # print res_name
        res_name_list.append(res_name)
        aggr = network.aggregate(dist, type=fun, decay="flat", name=attr)
        if newdf is None:
            newdf = pd.DataFrame({res_name: aggr, "node_ids": aggr.index.values})
        else:
            newdf[res_name] = aggr
    return newdf


def get_weighted_jobs(household_data, new_column_name):
    for res_name in res_name_list:
        weighted_res_name = new_column_name + res_name
        household_data[weighted_res_name] = (
            household_data[res_name] * household_data["hh_p"]
        )
        # print weighted_res_name
    return household_data


def get_average_jobs(household_data, geo_boundry, new_columns_name):
    data = (
        household_data[
            [geo_boundry, "hh_p"]
            + res_name_list
            + ["HHweighted_" + i for i in res_name_list]
        ]
        .groupby([geo_boundry])
        .sum()
    )
    data.reset_index(inplace=True)
    for res_name in res_name_list:
        weighted_res_name = "HHweighted_" + res_name
        averaged_res_name = new_columns_name + res_name
        data[averaged_res_name] = data[weighted_res_name] / data["hh_p"]
    return data


def get_average_jobs_transit(transit_data, geo_attr, parcel_attributes_list):
    """Calculate the weighted average number of jobs available across a geography."""

    for attr in parcel_attributes_list:
        # print 'process attribute: ', attr

        # Calculated weight values
        weighted_attr = "HHweighted_" + attr
        transit_data[weighted_attr] = transit_data["hh_p"] * transit_data[attr]

    # Group results by geographic defintion
    transit_data_groupby = (
        transit_data[
            [geo_attr, "hh_p"]
            + parcel_attributes_list
            + ["HHweighted_" + i for i in parcel_attributes_list]
        ]
        .groupby([geo_attr])
        .sum()
    )
    # Make sure geography has at least 1 household so we can compute a weighted average
    transit_data_groupby["hh_p"] = transit_data_groupby["hh_p"].replace(0, 1)
    transit_data_groupby.reset_index(inplace=True)
    for attr in parcel_attributes_list:
        weighted_attr = "HHweighted_" + attr
        averaged_attr = "HHaveraged_" + attr
        transit_data_groupby[averaged_attr] = (
            transit_data_groupby[weighted_attr] / transit_data_groupby["hh_p"]
        )
    return transit_data_groupby


def get_transit_information(bank):
    """Extract transit travel times from skim matrices, between all zones"""

    # Bus and rail travel times are the sum of access, wait time, and in-vehicle times; Bus and rail have separate paths
    bus_time = (
        bank.matrix("auxwa").get_numpy_data()
        + bank.matrix("twtwa").get_numpy_data()
        + bank.matrix("ivtwa").get_numpy_data()
    )
    rail_time = (
        bank.matrix("auxwr").get_numpy_data()
        + bank.matrix("twtwr").get_numpy_data()
        + bank.matrix("ivtwr").get_numpy_data()
    )
    ferry_time = (
        bank.matrix("auxwf").get_numpy_data()
        + bank.matrix("twtwf").get_numpy_data()
        + bank.matrix("ivtwf").get_numpy_data()
    )
    p_ferry_time = (
        bank.matrix("auxwp").get_numpy_data()
        + bank.matrix("twtwp").get_numpy_data()
        + bank.matrix("ivtwp").get_numpy_data()
    )
    commuter_rail_time = (
        bank.matrix("auxwc").get_numpy_data()
        + bank.matrix("twtwc").get_numpy_data()
        + bank.matrix("ivtwc").get_numpy_data()
    )
    # Take the shortest transit time between bus or rail
    # transit_time = np.minimum(bus_time, rail_time)
    transit_time = np.minimum.reduce(
        [bus_time, rail_time, ferry_time, p_ferry_time, commuter_rail_time]
    )
    transit_time = transit_time[0:3700, 0:3700]
    transit_time_df = pd.DataFrame(transit_time)
    transit_time_df["from"] = transit_time_df.index
    transit_time_df = pd.melt(
        transit_time_df,
        id_vars="from",
        value_vars=list(transit_time_df.columns[0:3700]),
        var_name="to",
        value_name="travel_time",
    )

    # Join with parcel data; add 1 to get zone ID because emme matrices are indexed starting with 0
    transit_time_df["to"] = transit_time_df["to"] + 1
    transit_time_df["from"] = transit_time_df["from"] + 1

    return transit_time_df


# def process_transit_attribute(transit_time_data, time_max,  attr_list, origin_df, dest_df):

#    # Select OD pairs with travel time under time_max threshold
#    transit = transit_time_data[transit_time_data.travel_time <= time_max]
#    # Remove intrazonal transit trips; assuming access will not be via transit within zones
#    transit = transit[transit['from'] != transit['to']]

#    # Calculate total jobs at destination TAZs
#    dest_transit = transit.merge(dest_df, left_on='to', right_on='TAZ_P', how = 'left')
#    dest_transit = pd.DataFrame(dest_transit.groupby(dest_transit['from'])[attr_list].sum())
#    dest_transit.reset_index(inplace=True)

#    origin_dest = origin_df.merge(dest_transit, left_on='TAZ_P', right_on='from', how='left')
#    # groupby destination information by origin geo id
#    origin_dest_emp = pd.DataFrame(origin_dest.groupby('PARCELID')[attr_list+['HH_P']].sum())
#    origin_dest_emp.reset_index(inplace=True)

#    return origin_dest_emp


def bike_walk_jobs_access(links, nodes, parcel_df, parcel_geog, distances, geo_list):
    """Calculate weighted average numbers of jobs available to a parcel by mode, within a max distance."""

    parcel_attributes = {"sum": ["emptot_p"]}

    # assign impedance
    imp = pd.DataFrame(links.Shape_Length)
    imp = imp.rename(columns={"Shape_Length": "distance"})

    links = links[links['to_node_id'].isin(nodes.index) & links['from_node_id'].isin(nodes.index)]

    # create pandana network
    net = pdna.network.Network(
        nodes.x, nodes.y, links.from_node_id, links.to_node_id, imp
    )

    for dist in distances:
        # print dist
        net.precompute(dist)

    # assign network nodes to parcels, for buffer variables
    assign_nodes_to_dataset(parcel_df, net, "node_ids", "xcoord_p", "ycoord_p")
    x, y = parcel_df.xcoord_p, parcel_df.ycoord_p
    parcel_df["node_ids"] = net.get_node_ids(x, y)

    # start processing attributes
    newdf = None
    for fun, attrs in parcel_attributes.items():
        for attr in attrs:
            net.set(parcel_df.node_ids, variable=parcel_df[attr], name=attr)
            res = process_net_attribute(net, attr, fun, distances)
            if newdf is None:
                newdf = res
            else:
                newdf = pd.merge(newdf, res, on="node_ids", copy=False)

    # parcel level jobs - weighted
    new_parcel_df = pd.merge(
        newdf, parcel_df[["node_ids", "hh_p"] + geo_list], on="node_ids", copy=False
    )

    # Append results to initally empty df
    df = pd.DataFrame()

    for geo in geo_list:
        # print 'processing', geo
        new_parcel_df = get_weighted_jobs(new_parcel_df, "HHweighted_")
        # flag the minority tracts
        new_parcel_df_groupby = get_average_jobs(new_parcel_df, geo, "HHaveraged_")

        _df = new_parcel_df_groupby[
            [geo] + ["HHaveraged_emptot_1", "HHaveraged_emptot_3"]
        ].copy()
        _df.columns = ["geography_value", "jobs_1_mile_walk", "jobs_3_mile_bike"]
        _df["geography_group"] = geo
        df = pd.concat([df, _df])

    # df = pd.melt(df, 'Geography', var_name='Data Item')
    # df['Grouping'] = 'Total'
    # df.rename(columns={'value':'Value'},inplace=True)

    return df


def get_parcel_data_max_travel_time(
    travel_time_df,
    max_time,
    origin_df,
    dest_df,
    parcel_attributes_list,
    include_intrazonal=True,
):
    travel_time_df = travel_time_df[travel_time_df.travel_time <= max_time]
    # Remove intrazonal transit trips; assuming access will not be via transit within zones
    if not include_intrazonal:
        travel_time_df = travel_time_df[travel_time_df["from"] != travel_time_df["to"]]
    # Calculate total jobs at destination TAZs
    reachable_destinations = travel_time_df.merge(
        dest_df, left_on="to", right_on="taz_p", how="left"
    )
    reachable_destinations = reachable_destinations.groupby(
        reachable_destinations["from"]
    )[parcel_attributes_list].sum()

    reachable_destinations.reset_index(inplace=True)

    origin_dest = origin_df.merge(
        reachable_destinations, left_on="taz_p", right_on="from", how="left"
    )

    # groupby destination information by origin geo id
    origin_dest_emp = pd.DataFrame(
        origin_dest.groupby("parcelid")[parcel_attributes_list + ["hh_p"]].sum()
    )

    origin_dest_emp.reset_index(inplace=True)
    return origin_dest_emp

    # get the origin geography level household info
    # transit_hh_emp = origin_dest_emp.merge(parcel_geog[geo_list+['ParcelID']], left_on='PARCELID', right_on='ParcelID', how='left')


def main():
    output_dir = r"outputs/access"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Define time buffer for transit - caclulate available jobs at this travel time or less
    # time_max = 45

    geo_list = [
        "CountyName",
        "region",
        "GrowthCenterName",
        "rg_proposed",
        "Census2020Tract",
        "rgc_binary",
    ]
    equity_geogs = ["youth", "elderly", "english", "racial", "poverty", "disability"]
    for equity_geog in equity_geogs:
        for geog_type in ["_geog_vs_reg_total", "_geog_vs_50_percent"]:
            geo_list.append(equity_geog + geog_type)

    parcel_attributes_list = ["emptot_p"]

    global res_name_list
    res_name_list = []

    distances = {  # miles to feet;
        # 1: 2640, # 0.5 mile
        1: 5280,  # 1 mile
        3: 15840,  # 3 miles
    }

    parcel_df = pd.read_csv(r"outputs/landuse/parcels_urbansim.txt", sep="\s+")
    # parcel_df['region'] = 1
    nodes = pd.read_csv(r"inputs/base_year/all_streets_nodes.csv")
    nodes.set_index("node_id", inplace=True)  # required for newer version of pandana
    links = pd.read_csv(r"inputs/base_year/all_streets_links.csv", index_col=None)

    # Load geography lookups and join to parcel data
    parcel_geog = pd.read_sql_table(
        "parcel_" + config["base_year"] + "_geography",
        "sqlite:///inputs/db/" + config["db_name"],
    )
    parcel_geog["region"] = 1

    # Create a field that identifies whether parcel is inside or outside of an RGC
    parcel_geog["rgc_binary"] = 0
    parcel_geog.loc[parcel_geog["GrowthCenterName"] != "Not in RGC", "rgc_binary"] = 1

    parcel_df = pd.merge(
        parcel_df, parcel_geog, left_on="parcelid", right_on="ParcelID", how="left"
    )

    # Join race from the synthetic population
    myh5 = h5py.File(r"inputs\scenario\landuse\hh_and_persons.h5", "r")

    hh_df = pd.DataFrame()
    for col in myh5["Household"].keys():
        hh_df[col] = myh5["Household"][col][:]
    person_df = pd.DataFrame()
    for col in myh5["Person"].keys():
        person_df[col] = myh5["Person"][col][:]

    #######################################################
    # Access to Jobs by Walking and Biking (via all-streets network)
    #######################################################

    df = bike_walk_jobs_access(
        links, nodes, parcel_df, parcel_geog, distances, geo_list
    )
    df.to_csv(os.path.join(output_dir, "walk_bike_jobs_access.csv"))

    #######################################################
    # Access to Jobs by Transit (via TAZ-based skims)
    #######################################################

    # Parcel variables that should be summarized; only total jobs are considered currently but jobs by sector could be included
    parcel_attributes_list = ["emptot_p"]

    # Work with only necessary cols
    origin_df = parcel_df[["parcelid", "taz_p", "hh_p"]]

    # Aggregate destinations by TAZ since we are used taz-level skims
    dest_df = pd.DataFrame(parcel_df.groupby(["taz_p"])[parcel_attributes_list].sum())
    dest_df.reset_index(inplace=True)
    dest_df["taz_p"] = dest_df["taz_p"].astype("object")

    # extract transit travel time from emme matrices from AM time period
    bank = _eb.Emmebank(os.path.join(os.getcwd(), r"Banks/7to8/emmebank"))
    transit_time_df = get_transit_information(bank)

    # Set threshold travel time
    transit_time_max = 45
    auto_time_max = 30

    origin_dest_emp = get_parcel_data_max_travel_time(
        transit_time_df,
        transit_time_max,
        origin_df,
        dest_df,
        parcel_attributes_list,
        include_intrazonal=False,
    )
    transit_hh_emp = origin_dest_emp.merge(
        parcel_geog[geo_list + ["ParcelID"]],
        left_on="parcelid",
        right_on="ParcelID",
        how="left",
    )

    # Append results to initally empty df
    df = pd.DataFrame()
    for geo in geo_list:
        average_jobs_df = get_average_jobs_transit(
            transit_hh_emp, geo, parcel_attributes_list
        )

        _df = average_jobs_df[[geo] + ["HHaveraged_emptot_p"]].copy()
        _df.loc[:, "geography_group"] = geo
        _df.columns = ["geography", "value", "geography_group"]
        df = pd.concat([df, _df])

    # Add summaries by race from synthetic population
    if "prace" in person_df.columns:
        avg_race_df = person_df[["hhno", "pno", "prace"]].merge(
            hh_df[["hhno", "hhparcel"]], on="hhno", how="left"
        )
        avg_race_df = avg_race_df.merge(
            origin_dest_emp, left_on="hhparcel", right_on="parcelid", how="left"
        )
        # Write person records with individual jobs access
        avg_race_df.to_csv(os.path.join(output_dir, "transit_jobs_access_person.csv"))
        avg_race_df = avg_race_df.groupby("prace").mean()[["emptot_p"]]
        avg_race_df = avg_race_df.reset_index()
        avg_race_df.rename(
            columns={"prace": "geography", "emptot_p": "value"}, inplace=True
        )
        avg_race_df["geography_group"] = "race"
        df = pd.concat([df, avg_race_df])

    df.to_csv(os.path.join(output_dir, "transit_jobs_access.csv"))

    #######################################################
    # Access to Jobs by Auto (via TAZ-based skims)
    #######################################################

    # Calculate auto time access
    auto_time = bank.matrix("sov_inc2t").get_numpy_data()

    auto_time = auto_time[0:3700, 0:3700]
    auto_time_df = pd.DataFrame(auto_time)
    auto_time_df["from"] = auto_time_df.index
    auto_time_df = pd.melt(
        auto_time_df,
        id_vars="from",
        value_vars=list(auto_time_df.columns[0:3700]),
        var_name="to",
        value_name="travel_time",
    )

    # Join with parcel data; add 1 to get zone ID because emme matrices are indexed starting with 0
    auto_time_df["to"] = auto_time_df["to"] + 1
    auto_time_df["from"] = auto_time_df["from"] + 1

    origin_dest_emp = get_parcel_data_max_travel_time(
        auto_time_df,
        auto_time_max,
        origin_df,
        dest_df,
        parcel_attributes_list,
        include_intrazonal=False,
    )
    auto_hh_emp = origin_dest_emp.merge(
        parcel_geog[geo_list + ["ParcelID"]],
        left_on="parcelid",
        right_on="ParcelID",
        how="left",
    )

    # Append results to initally empty df
    df = pd.DataFrame()
    for geo in geo_list:
        average_jobs_df = get_average_jobs_transit(
            auto_hh_emp, geo, parcel_attributes_list
        )

        _df = average_jobs_df[[geo] + ["HHaveraged_emptot_p"]].copy()
        _df.loc[:, "geography_group"] = geo
        _df.columns = ["geography", "value", "geography_group"]
        df = pd.concat([df, _df])

    if "prace" in person_df.columns:
        avg_race_df = person_df[["hhno", "pno", "prace"]].merge(
            hh_df[["hhno", "hhparcel"]], on="hhno", how="left"
        )
        avg_race_df = avg_race_df.merge(
            origin_dest_emp, left_on="hhparcel", right_on="parcelid", how="left"
        )
        avg_race_df.to_csv(os.path.join(output_dir, "auto_jobs_access_person.csv"))
        avg_race_df = avg_race_df.groupby("prace").mean()[["emptot_p"]]
        avg_race_df = avg_race_df.reset_index()
        avg_race_df.rename(
            columns={"prace": "geography", "emptot_p": "value"}, inplace=True
        )
        avg_race_df["geography_group"] = "race"
        df = pd.concat([df, avg_race_df])
    df.to_csv(os.path.join(output_dir, "auto_jobs_access.csv"))


if __name__ == "__main__":
    main()
