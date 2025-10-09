# Copyright [2014] [Puget Sound Regional Council]

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#    http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os, shutil
import pandas as pd
import numpy as np
import json
import h5py


def get_intrazonal_vol(state, emmeproject, df_vol):
    """Calculate intrazonal volumes for all modes"""

    iz_uc_list = ["sov_inc", "hov2_inc", "hov3_inc"]
    if state.input_settings.include_av:
        iz_uc_list += "av_sov_inc", "av_hov2_inc", "av_hov3_inc"
    iz_uc_list = [uc + str(1 + i) for i in range(3) for uc in iz_uc_list]
    if state.input_settings.include_tnc:
        iz_uc_list += ["tnc_inc1", "tnc_inc2", "tnc_inc3"]
    if state.input_settings.include_delivery:
        iz_uc_list += ["delivery_truck"]
    iz_uc_list += ["medium_truck", "heavy_truck"]

    for uc in iz_uc_list:
        df_vol[uc + "_" + emmeproject.tod] = (
            emmeproject.bank.matrix(uc).get_numpy_data().diagonal()
        )

    return df_vol


def calc_total_vehicles(state, project):
    """For a given time period, calculate link level volume, store as extra attribute on the link."""

    project.network_calculator(
        "link_calculation", result="@mveh", expression="@medium_truck/1.5"
    )  # medium trucks
    project.network_calculator(
        "link_calculation", result="@hveh", expression="@heavy_truck/2.0"
    )  # heavy trucks
    project.network_calculator(
        "link_calculation", result="@bveh", expression="@trnv3/2.0"
    )  # buses
    if state.input_settings.include_delivery:
        project.network_calculator(
            "link_calculation", result="@dveh", expression="@delivery_truck/1.5"
        )  # medium trucks

    # Calculate total vehicles as @tveh, depending on which modes are included
    str_base = (
        "@sov_inc1 + @sov_inc2 + @sov_inc3 + @hov2_inc1 + @hov2_inc2 + @hov2_inc3 + "
        + "@hov3_inc1 + @hov3_inc2 + @hov3_inc3 + @mveh + @hveh + @bveh "
    )
    av_str = (
        "+ @av_sov_inc1 + @av_sov_inc2 + @av_sov_inc3 + @av_hov2_inc1 + @av_hov2_inc2 + @av_hov2_inc3 + "
        + "@av_hov3_inc1 + @av_hov3_inc2 + @av_hov3_inc3 "
    )
    tnc_str = "+ @tnc_inc1 + @tnc_inc2 + @tnc_inc3 "

    str_expression = str_base
    if state.input_settings.include_av:
        str_expression += av_str
    if state.input_settings.include_tnc:
        str_expression += tnc_str
    if state.input_settings.include_delivery:
        str_expression += " + @dveh"

    project.network_calculator(
        "link_calculation", result="@tveh", expression=str_expression
    )


def freeflow_skims(state, project, dictZoneLookup):
    """Attach "freeflow" (20to5) SOV skims to daysim_outputs"""

    # Load daysim_outputs as dataframe
    daysim = h5py.File("outputs/daysim/daysim_outputs.h5", "r+")
    df = pd.DataFrame()
    for field in ["travtime", "otaz", "dtaz"]:
        df[field] = daysim["Trip"][field][:]
    df["od"] = df["otaz"].astype("str") + "-" + df["dtaz"].astype("str")

    skim_vals = h5py.File(f"{state.model_input_dir}/roster/20to5.h5", "r")["Skims"][
        "sov_inc3t"
    ][:]

    skim_df = pd.DataFrame(skim_vals)
    # Reset index and column headers to match zone ID
    skim_df.columns = [dictZoneLookup[i] for i in skim_df.columns]
    skim_df.index = [dictZoneLookup[i] for i in skim_df.index.values]

    skim_df = skim_df.stack().reset_index()
    skim_df.columns = ["otaz", "dtaz", "ff_travtime"]
    skim_df["od"] = skim_df["otaz"].astype("str") + "-" + skim_df["dtaz"].astype("str")
    skim_df.index = skim_df["od"]

    df = df.join(skim_df, on="od", lsuffix="_cong", rsuffix="_ff")

    # Write to h5, create dataset if
    if "sov_ff_time" in daysim["Trip"].keys():
        del daysim["Trip"]["sov_ff_time"]
    try:
        daysim["Trip"].create_dataset(
            "sov_ff_time", data=df["ff_travtime"].values, compression="gzip"
        )
    except:
        print("could not write freeflow skim to h5")
    daysim.close()

    # Write to TSV files
    for df_dir in ["outputs/daysim/_trip.tsv", "inputs/base_year/survey/_trip.tsv"]:
        df = pd.read_csv(df_dir, sep="\t")
        df["od"] = df["otaz"].astype("str") + "-" + df["dtaz"].astype("str")
        skim_df["sov_ff_time"] = skim_df["ff_travtime"]
        # Delete sov_ff_time if it already exists
        if "sov_ff_time" in df.columns:
            df.drop("sov_ff_time", axis=1, inplace=True)
        skim_df = skim_df.reset_index(drop=True)
        df = pd.merge(df, skim_df[["od", "sov_ff_time"]], on="od", how="left")
        df.to_csv(df_dir, sep="\t", index=False)


def export_network_attributes(network):
    """Calculate link-level results by time-of-day, append to csv"""

    _attribute_list = network.attributes("LINK")

    network_data = {k: [] for k in _attribute_list}
    i_node_list = []
    j_node_list = []
    network_data["modes"] = []
    for link in network.links():
        for colname, array in network_data.items():
            if colname != "modes":
                try:
                    network_data[colname].append(link[colname])
                except:
                    network_data[colname].append(0)
        i_node_list.append(link.i_node.id)
        j_node_list.append(link.j_node.id)
        network_data["modes"].append(link.modes)

    network_data["i_node"] = i_node_list
    network_data["j_node"] = j_node_list
    df = pd.DataFrame.from_dict(network_data)
    df["modes"] = df["modes"].apply(lambda x: "".join(list([j.id for j in x])))
    df["modes"] = df["modes"].astype("str").fillna("")
    df["ij"] = df["i_node"].astype("str") + "-" + df["j_node"].astype("str")

    df["speed"] = df["length"] / df["auto_time"] * 60
    df["congestion_index"] = df["speed"] / df["data2"]
    df["congestion_index"] = df["congestion_index"].clip(0, 1)
    df["congestion_category"] = pd.cut(
        df["congestion_index"],
        bins=[0, 0.25, 0.5, 0.7, 1],
        labels=["Severe", "Heavy", "Moderate", "Light"],
    )

    return df


def sort_df(df, sort_list, sort_column):
    """Sort a dataframe based on user-defined list of indices"""

    df[sort_column] = df[sort_column].astype("category")
    df[sort_column] = df[sort_column].cat.set_categories(sort_list)
    df = df.sort_values(sort_column)

    return df


def summarize_network(state, df, writer):
    """Calculate VMT, VHT, and Delay from link-level results"""

    # Exclude trips taken on non-designated facilities (facility_type == 0)
    # These are artificial (weave lanes to connect HOV) or for non-auto uses
    df = df[df["data3"] != 0].copy()  # data3 represents facility_type

    # calculate total link VMT and VHT
    df["VMT"] = df["@tveh"] * df["length"]
    df["VHT"] = df["@tveh"] * df["auto_time"] / 60

    # Define facility type
    df.loc[df["data3"].isin([1, 2]), "facility_type"] = "highway"
    df.loc[df["data3"].isin([3, 4, 6]), "facility_type"] = "arterial"
    df.loc[df["data3"].isin([5]), "facility_type"] = "connector"

    # Calculate delay
    # Select links from overnight time of day
    delay_df = df.loc[df["tod"] == "20to5"][["ij", "auto_time"]]
    delay_df.rename(columns={"auto_time": "freeflow_time"}, inplace=True)

    # Merge delay field back onto network link df
    df = pd.merge(df, delay_df, on="ij", how="left")

    # Calcualte hourly delay
    df["delay"] = (
        (df["auto_time"] - df["freeflow_time"]) * df["@tveh"]
    ) / 60  # sum of (volume)*(travtime diff from freeflow)

    # Add time-of-day group (AM, PM, etc.)
    for tod in df['tod'].unique():
        df.loc[df["tod"] == tod, "period"] = state.network_settings.sound_cast_net_dict[tod]

    # Totals by functional classification
    for metric in ["VMT", "VHT", "delay"]:
        _df = pd.pivot_table(
            df,
            values=metric,
            index=["tod", "period"],
            columns="facility_type",
            aggfunc="sum",
        ).reset_index()
        _df = sort_df(df=_df, sort_list=state.network_settings.tods, sort_column="tod")
        _df = _df.reset_index(drop=True)
        _df.to_excel(writer, sheet_name=metric + " by FC")
        _df.to_csv(r"outputs/network/" + metric.lower() + "_facility.csv", index=False)

    df["lane_miles"] = df["length"] * df["num_lanes"]
    lane_miles = df[df["tod"] == "7to8"]
    lane_miles = pd.pivot_table(
        lane_miles,
        values="lane_miles",
        index="@countyid",
        columns="facility_type",
        aggfunc="sum",
    ).reset_index()
    lane_miles["@countyid"] = lane_miles["@countyid"].astype(int).astype(str)
    lane_miles = lane_miles.replace({"@countyid": state.summary_settings.county_map})
    lane_miles = lane_miles[
        lane_miles["@countyid"].isin(state.summary_settings.county_map.values())
    ]
    lane_miles.rename(
        columns={
            col: col + "_lane_miles"
            for col in lane_miles.columns
            if col in ["highway", "arterial", "connector"]
        },
        inplace=True,
    )

    county_vmt = pd.pivot_table(
        df, values="VMT", index=["@countyid"], columns="facility_type", aggfunc="sum"
    ).reset_index()
    county_vmt["@countyid"] = county_vmt["@countyid"].astype(int).astype(str)
    county_vmt = county_vmt.replace({"@countyid": state.summary_settings.county_map})
    county_vmt.rename(
        columns={
            col: col + "_vmt"
            for col in county_vmt.columns
            if col in ["highway", "arterial", "connector"]
        },
        inplace=True,
    )
    lane_miles = lane_miles.merge(county_vmt, how="left", on="@countyid")
    lane_miles.to_csv(r"outputs/network/county_vmt_lane_miles.csv", index=False)
    # Totals by user classification

    # Update uc_list based on inclusion of TNC and AVs
    new_uc_list = []

    if state.input_settings.include_delivery:
        new_uc_list.append("@dveh")

    if (not state.input_settings.include_tnc) & (not state.input_settings.include_av):
        for uc in state.summary_settings.uc_list:
            if ("@tnc" not in uc) & ("@av" not in uc):
                new_uc_list.append(uc)

    if (state.input_settings.include_tnc) & (not state.input_settings.include_av):
        for uc in state.summary_settings.uc_list:
            if "@av" not in uc:
                new_uc_list.append(uc)

    if (not state.input_settings.include_tnc) & (state.input_settings.include_av):
        for uc in state.summary_settings.uc_list:
            if "@tnc" not in uc:
                new_uc_list.append(uc)

    # VMT
    _df = df.copy()
    for uc in new_uc_list:
        _df[uc] = df[uc] * df["length"]
    _df = _df[new_uc_list + ["tod"]].groupby("tod").sum().reset_index()
    _df = sort_df(df=_df, sort_list=state.network_settings.tods, sort_column="tod")
    _df.to_excel(excel_writer=writer, sheet_name="VMT by UC")
    _df.to_csv(r"outputs/network/vmt_user_class.csv", index=False)

    # VHT
    _df = df.copy()
    for uc in new_uc_list:
        _df[uc] = df[uc] * df["auto_time"] / 60
    _df = _df[new_uc_list + ["tod"]].groupby("tod").sum().reset_index()
    _df = sort_df(df=_df, sort_list=state.network_settings.tods, sort_column="tod")
    _df = _df.reset_index(drop=True)
    _df.to_excel(excel_writer=writer, sheet_name="VHT by UC")
    _df.to_csv(r"outputs/network/vht_user_class.csv", index=False)

    # Delay
    _df = df.copy()
    for uc in new_uc_list:
        _df[uc] = ((_df["auto_time"] - _df["freeflow_time"]) * _df[uc]) / 60
    _df = _df[new_uc_list + ["tod"]].groupby("tod").sum().reset_index()
    _df = sort_df(df=_df, sort_list=state.network_settings.tods, sort_column="tod")
    _df = _df.reset_index(drop=True)
    _df.to_excel(excel_writer=writer, sheet_name="Delay by UC")
    _df.to_csv(r"outputs/network/delay_user_class.csv", index=False)

    # Results by County

    df["county_name"] = (
        df["@countyid"].astype(int).astype(str).map(state.summary_settings.county_map).fillna("Outside Region")
    )
    # df["county_name"].fillna("Outside Region", inplace=True)
    _df = df.groupby("county_name")[["VMT", "VHT", "delay"]].sum().reset_index()
    _df.to_excel(excel_writer=writer, sheet_name="County Results")
    _df.to_csv(r"outputs/network/county_network.csv", index=False)

    writer.close()


def line_to_line_transfers(state, emme_project, tod):
    emme_project.create_extra_attribute("TRANSIT_LINE", "@ln2ln")
    emme_project.network_calculator(
        "transit_line_calculation", result="@ln2ln", expression="index1"
    )
    with open(
        f"{state.model_input_dir}/skim_parameters/transit/transit_traversal.json"
    ) as f:
        spec = json.load(f)
    NAMESPACE = "inro.emme.transit_assignment.extended.traversal_analysis"
    process = emme_project.m.tool(NAMESPACE)

    transit_line_list = []
    network = emme_project.current_scenario.get_network()

    for line in network.transit_lines():
        transit_line_list.append({"line": line.id, "mode": line.mode.id})
    transit_lines = pd.DataFrame(transit_line_list)
    transit_lines["lindex"] = transit_lines.index + 1
    transit_lines = transit_lines[["lindex", "line", "mode"]]

    df_list = []

    for class_name in ["trnst", "commuter_rail", "ferry", "litrat", "passenger_ferry"]:
        report = process(
            spec,
            class_name=class_name,
            output_file="outputs/transit/traversal_results.txt",
        )
        traversal_df = pd.read_csv(
            "outputs/transit/traversal_results.txt",
            skiprows=16,
            skipinitialspace=True,
            sep=" ",
            names=["from_line", "to_line", "boardings"],
        )
        traversal_df = traversal_df.merge(
            transit_lines, left_on="from_line", right_on="lindex"
        )
        traversal_df = traversal_df.rename(
            columns={"line": "from_line_id", "mode": "from_mode"}
        )
        traversal_df.drop(columns=["lindex"], inplace=True)

        traversal_df = traversal_df.merge(
            transit_lines, left_on="to_line", right_on="lindex"
        )
        traversal_df = traversal_df.rename(
            columns={"line": "to_line_id", "mode": "to_mode"}
        )
        traversal_df.drop(columns=["lindex"], inplace=True)
        df_list.append(traversal_df)
        os.remove("outputs/transit/traversal_results.txt")
    df = pd.concat(df_list.dropna(axis=1, how='all'))
    df = df.groupby(["from_line", "to_line"]).agg(
        {
            "from_line_id": "min",
            "to_line_id": "min",
            "from_mode": "min",
            "to_mode": "min",
            "boardings": "sum",
        }
    )
    df.reset_index(inplace=True)
    df["tod"] = tod
    return df


def transit_summary(emme_project, df_transit_line, df_transit_node, df_transit_segment):
    """Export transit line, segment, and mode attributes"""

    network = emme_project.current_scenario.get_network()
    tod = emme_project.tod

    # Extract Transit Line Data
    transit_line_data = []
    for line in network.transit_lines():
        transit_line_data.append(
            {
                "line_id": line.id,
                "route_code": line.data1,
                "agency_code": line.data3,
                "mode": str(line.mode),
                "description": line.description,
                "boardings": line["@board"],
                "time": line["@timtr"],
                "transit_type": line["@transittype"],
            }
        )
    _df_transit_line = pd.DataFrame(transit_line_data)
    _df_transit_line["tod"] = tod

    # Extract Transit Node Data
    transit_node_data = []
    for node in network.nodes():
        transit_node_data.append(
            {
                "node_id": int(node.id),
                "initial_boardings": node.initial_boardings,
                "final_alightings": node.final_alightings,
            }
        )

    _df_transit_node = pd.DataFrame(transit_node_data)
    _df_transit_node["tod"] = tod

    # Extract Transit Segment Data
    transit_segment_data = []
    for tseg in network.transit_segments():
        if tseg.j_node is None:
            transit_segment_data.append(
                {
                    "line_id": tseg.line.id,
                    "segment_boarding": tseg.transit_boardings,
                    "segment_volume": tseg.transit_volume,
                    "i_node": tseg.i_node.number,
                    "j_node": np.nan,
                }
            )
        else:
            transit_segment_data.append(
                {
                    "line_id": tseg.line.id,
                    "segment_boarding": tseg.transit_boardings,
                    "segment_volume": tseg.transit_volume,
                    "i_node": tseg.i_node.number,
                    "j_node": tseg.j_node.number,
                }
            )

    _df_transit_segment = pd.DataFrame(transit_segment_data)
    _df_transit_segment["tod"] = tod

    return _df_transit_line, _df_transit_node, _df_transit_segment


def main(state):
    # Delete any existing files
    for _path in [
        "outputs/transit/transit_line_results.csv",
        "outputs/transit/transit_node_results.csv",
        "outputs/transit/transit_segment_results.csv",
        "outputs/network/network_results.csv",
    ]:
        if os.path.exists(_path):
            os.remove(_path)

    # ## Access Emme project with all time-of-day banks available
    project = state.main_project
    network = project.current_scenario.get_network()
    zones = project.current_scenario.zone_numbers
    dictZoneLookup = dict((index, value) for index, value in enumerate(zones))

    # Initialize result dataframes
    df_transit_line = pd.DataFrame()
    df_transit_node = pd.DataFrame()
    df_transit_segment = pd.DataFrame()
    df_transit_transfers = pd.DataFrame()
    network_df = pd.DataFrame()
    df_iz_vol = pd.DataFrame()
    df_iz_vol["taz"] = dictZoneLookup.values()

    dir = r"outputs/transit/line_od"
    if os.path.exists(dir):
        shutil.rmtree(dir)
    os.makedirs(dir)

    transit_line_od_period_list = ["7to8"]

    # Loop through all Time-of-Day banks to get network summaries
    # Initialize extra network and transit attributes
    for tod_hour, tod_segment in state.network_settings.sound_cast_net_dict.items():
        print("processing network summary for time period: " + str(tod_hour))
        project.change_active_database(tod_hour)
        if tod_hour in state.network_settings.transit_tod.keys():
            try:
                _df_transit_transfers = line_to_line_transfers(state, project, tod_hour)
                df_transit_transfers = pd.concat(
                    [df_transit_transfers, _df_transit_transfers]
                )
            except:
                pass

        for name, description in state.network_settings.extra_attributes_dict.items():
            project.create_extra_attribute("LINK", name, description, "True")
        # Calculate transit results for time periods with transit assignment:
        if project.tod in state.network_settings.transit_tod.keys():
            for name, desc in {
                "@board": "total boardings",
                "@timtr": "transit line time",
            }.items():
                project.create_extra_attribute("TRANSIT_LINE", name, desc, "True")
                project.transit_line_calculator(result=name, expression=name[1:])
            _df_transit_line, _df_transit_node, _df_transit_segment = transit_summary(
                emme_project=project,
                df_transit_line=df_transit_line,
                df_transit_node=df_transit_node,
                df_transit_segment=df_transit_segment,
            )
            df_transit_line = pd.concat([df_transit_line, _df_transit_line])
            df_transit_node = pd.concat([df_transit_node, _df_transit_node])
            df_transit_segment = pd.concat([df_transit_segment, _df_transit_segment])

        # Add total vehicle sum for each link (@tveh)
        calc_total_vehicles(state, project)

        # Calculate intrazonal VMT
        _df_iz_vol = pd.DataFrame(
            project.bank.matrix("izdist").get_numpy_data().diagonal(),
            columns=["izdist"],
        )
        _df_iz_vol["taz"] = dictZoneLookup.values()
        _df_iz_vol = get_intrazonal_vol(state, project, _df_iz_vol)
        if "izdist" in df_iz_vol.columns:
            _df_iz_vol = _df_iz_vol.drop("izdist", axis=1)
        df_iz_vol = df_iz_vol.merge(_df_iz_vol, on="taz", how="left")

        # Export link-level results for multiple attributes
        network = project.current_scenario.get_network()
        _network_df = export_network_attributes(network)
        _network_df["tod"] = project.tod
        network_df = pd.concat([network_df, _network_df])

    output_dict = {
        "outputs/network/network_results.csv": network_df,
        "outputs/network/iz_vol.csv": df_iz_vol,
        "outputs/transit/transit_line_results.csv": df_transit_line,
        "outputs/transit/transit_node_results.csv": df_transit_node,
        "outputs/transit/transit_segment_results.csv": df_transit_segment,
    }

    # Append hourly results to file output
    for filepath, df in output_dict.items():
        df.to_csv(filepath, index=False)

    ## Write freeflow skims to Daysim trip records to calculate individual-level delay
    if state.input_settings.abm_model == "daysim":
        freeflow_skims(state, project, dictZoneLookup)

    # Export transit transfers
    df_transit_transfers.to_csv("outputs/transit/transit_transfers.csv")

    # Create basic spreadsheet summary of network
    writer = pd.ExcelWriter(
        r"outputs/network/network_summary.xlsx", engine="xlsxwriter"
    )
    summarize_network(state, network_df, writer)


if __name__ == "__main__":
    main(state)
