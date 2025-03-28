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

import pandas as pd
import inro.emme.database.emmebank as _emmebank


def summarize_transit_detail(state):
    """Sumarize various transit measures."""

    df_transit_line = pd.read_csv(r"outputs/transit/transit_line_results.csv")
    df_transit_node = pd.read_csv(r"outputs/transit/transit_node_results.csv")
    df_transit_segment = pd.read_csv(r"outputs/transit/transit_segment_results.csv")

    df_transit_line["agency_code"] = df_transit_line["agency_code"].astype("int")
    df_transit_line["route_code"] = df_transit_line["route_code"].astype("int")

    # Daily Boardings by Agency
    df_transit_line["agency_name"] = df_transit_line["agency_code"].map(
        {int(k): v for k, v in state.summary_settings.agency_lookup.items()}
    )
    df_daily = (
        df_transit_line.groupby("agency_name")
        .sum()[["boardings"]]
        .reset_index()
        .sort_values("boardings", ascending=False)
    )
    df_daily.to_csv("outputs/transit/daily_boardings_by_agency.csv", index=False)

    # Boardings by Time of Day and Agency
    df_tod_agency = df_transit_line.pivot_table(
        columns="tod", index="agency_name", values="boardings", aggfunc="sum"
    )
    df_tod_agency = df_tod_agency[state.network_settings.transit_tod_list]
    df_tod_agency = df_tod_agency.sort_values("7to8", ascending=False).reset_index()
    df_tod_agency.to_csv("outputs/transit/boardings_by_tod_agency.csv", index=False)

    # Daily Boardings by Stop
    df_transit_segment = pd.read_csv(r"outputs\transit\transit_segment_results.csv")
    df_transit_node = pd.read_csv(r"outputs\transit\transit_node_results.csv")
    df_transit_segment = df_transit_segment.groupby("i_node").sum().reset_index()
    df_transit_node = df_transit_node.groupby("node_id").sum().reset_index()
    df = pd.merge(
        df_transit_node, df_transit_segment, left_on="node_id", right_on="i_node"
    )
    df.rename(columns={"segment_boarding": "total_boardings"}, inplace=True)
    df["transfers"] = df["total_boardings"] - df["initial_boardings"]
    df.to_csv("outputs/transit/boardings_by_stop.csv")


def jobs_transit():
    buf = pd.read_csv(r"outputs/landuse/buffered_parcels.txt", sep=" ")

    # distance to any transit stop
    df = buf[
        [
            "parcelid",
            "dist_lbus",
            "dist_crt",
            "dist_fry",
            "dist_lrt",
            "hh_p",
            "stugrd_p",
            "stuhgh_p",
            "stuuni_p",
            "empedu_p",
            "empfoo_p",
            "empgov_p",
            "empind_p",
            "empmed_p",
            "empofc_p",
            "empret_p",
            "empsvc_p",
            "empoth_p",
            "emptot_p",
        ]
    ]
    df.index = df["parcelid"]

    # Use minimum distance to any transit stop
    newdf = pd.DataFrame(
        df[["dist_lbus", "dist_crt", "dist_fry", "dist_lrt"]].min(axis=1)
    )
    newdf = newdf.reset_index()
    df = df.reset_index(drop=True)
    newdf.rename(columns={0: "nearest_transit"}, inplace=True)
    df = pd.merge(df, newdf[["parcelid", "nearest_transit"]], on="parcelid")

    # only sum for parcels closer than quarter mile to stop
    quarter_mile_jobs = pd.DataFrame(df[df["nearest_transit"] <= 0.25].sum())
    quarter_mile_jobs.rename(columns={0: "quarter_mile_transit"}, inplace=True)
    all_jobs = pd.DataFrame(df.sum())
    all_jobs.rename(columns={0: "total"}, inplace=True)

    df = pd.merge(all_jobs, quarter_mile_jobs, left_index=True, right_index=True)
    df.drop(
        [
            "parcelid",
            "dist_lbus",
            "dist_crt",
            "dist_fry",
            "dist_lrt",
            "nearest_transit",
        ],
        inplace=True,
    )

    return df


def daily_transit_trips():
    # Use daily bank

    bank = _emmebank.Emmebank(r"Banks/Daily/emmebank")

    # Export total daily transit trips by mode
    df = pd.DataFrame()
    for mode in ["commuter_rail", "litrat", "ferry", "passenger_ferry", "trnst"]:
        df.loc[mode, "total_trips"] = bank.matrix(mode).get_numpy_data().sum()
    df.to_csv(r"outputs\transit\total_transit_trips.csv")


def main(state):
    daily_transit_trips()

    # Produce transit summaries
    summarize_transit_detail(state)

    # Export number of jobs near transit stops
    jobs_transit().to_csv("outputs/transit/transit_access.csv")


if __name__ == "__main__":
    main()
