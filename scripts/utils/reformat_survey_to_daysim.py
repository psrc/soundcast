import os, sys
import numpy as np
import pandas as pd


# Set current working directory to script location
# working_dir = r'C:\Users\bnichols\travel-studies\2017\daysim_conversions'
# os.chdir(working_dir)

# Import local module variables
from lookup import *

# Set input paths
hh_file_dir = r"J:\Projects\Surveys\HHTravel\Survey2019\Data\PSRC_2019_HTS_Deliverable_022020\Weighted_Data_022020\1_household.csv"
person_file_dir = r"J:\Projects\Surveys\HHTravel\Survey2019\Data\PSRC_2019_HTS_Deliverable_022020\Weighted_Data_022020\2_person.csv"
trip_file_dir = r"J:\Projects\Surveys\HHTravel\Survey2019\Data\PSRC_2019_HTS_Deliverable_022020\Weighted_Data_022020\5_trip.csv"

# FIXME - which columns to use?:
hh_wt_col = "hh_wt_combined"


# trip_file_dir = r'R:\e2projects_two\SoundCastDocuments\2017Estimation\trip_from_db.csv'
# purp_lookup_dir = r'R:\e2projects_two\SoundCastDocuments\2017Estimation\purp_lookup.csv'

# Output directory
# output_dir = r'C:\Users\bnichols\travel-studies\2017\daysim_conversions'
output_dir = r"R:\e2projects_two\SoundCastDocuments\2017Estimation"


# Flexible column names, given that these may change in future surveys
hhno = "hhid"
hownrent = "rent_own"
hrestype = "res_type"
hhincome = "hhincome_detailed"
hhtaz = "final_home_taz2010"
hhexpfac = "hh_wt_revised"
hhwkrs = "numworkers"
hhvehs = "vehicle_count"
pno = "pernum"


def process_person_file(person_file_dir):
    """Create Daysim-formatted person file from Survey Excel file."""

    # FIXME: use final version from Elmer

    person = pd.read_csv(person_file_dir, encoding="latin-1")

    # Full time worker
    person.loc[person["employment"] == 1, "pptyp"] = 1

    # Part-time worker
    person.loc[person["employment"] == 2, "pptyp"] = 2

    # Non-working adult age 65+
    person.loc[
        (person["employment"] != 1) & (person["age"].isin([10, 11, 12])), "pptyp"
    ] = 3

    # High school student age 16+
    person.loc[
        (person["age"] >= 4) & (person["schooltype"].isin([3, 4, 5])), "pptyp"
    ] = 6

    # university student (full-time)
    person.loc[
        (person["schooltype"].isin([6, 7])) & (person["student"] == 3), "pptyp"
    ] = 5

    # Child age 5-15
    person.loc[person["schooltype"].isin([2, 3]), "pptyp"] = 7

    # child under 5
    person.loc[person["schooltype"].isin([1]), "pptyp"] = 8

    # Non-working adult age 65 should accoutn for all others
    person.loc[person["pptyp"].isnull(), "pptyp"] = 4

    # Person worker type
    person.loc[person["employment"].isin([1]), "pwtyp"] = 1
    person.loc[person["employment"].isin([2]), "pwtyp"] = 2
    person.loc[person["employment"].isin([3, 4, 5, 6, 7]), "pwtyp"] = 0
    person["pwtyp"].fillna(0, inplace=True)
    person["pwtyp"] = person["pwtyp"].astype("int")

    # Transit pass availability
    person["ptpass"] = 0
    person.loc[
        (person["tran_pass_12"].isin([1, 2])) | (person["benefits_3"].isin([2, 3])),
        "ptpass",
    ] = 1

    # Paid parking at work (any level of subsidy counts as 'paid')
    person["ppaidprk"] = 0
    person.loc[person["workpass"].isin([3, 4]), "ppaidprk"] = 1

    # Map other variables from lookup tables
    person["age"] = person["age"].astype("int")
    person["pagey"] = person["age"].map(age_map)
    person["pgend"] = person["gender"].map(gender_map)
    person["pstyp"] = person["student"].map(pstyp_map)
    person["pstyp"].fillna(0, inplace=True)
    person["hhno"] = person["hhid"]
    person["pno"] = person["pernum"]
    person["psexpfac"] = person["hh_wt_combined"]
    person["pwtaz"] = -1
    person["pstaz"] = -1
    person["pwpcl"] = -1
    person["pspcl"] = -1

    daysim_cols = [
        "hhno",
        "pno",
        "pptyp",
        "pagey",
        "pgend",
        "pwtyp",
        "pwpcl",
        "pwtaz",
        "pwautime",
        "pwaudist",
        "pstyp",
        "pspcl",
        "pstaz",
        "psautime",
        "psaudist",
        "puwmode",
        "puwarrp",
        "puwdepp",
        "ptpass",
        "ppaidprk",
        "pdiary",
        "pproxy",
        "psexpfac",
    ]

    # Add empty columns to fill in later with skims
    for col in daysim_cols:
        if col not in person.columns:
            person[col] = -1

    person = person[daysim_cols]

    return person


def total_persons_to_hh(
    hh,
    person,
    daysim_field,
    filter_field,
    filter_field_list,
    hhid_col="hhno",
    wt_col="hhexpfac",
):
    """Use person field to calculate total number of person in a household for a given field
    e.g., total number of full-time workers"""

    df = person[person[filter_field].isin(filter_field_list)]
    df = df.groupby(hhid_col).count().reset_index()[[wt_col, hhid_col]]
    df.rename(columns={wt_col: daysim_field}, inplace=True)

    # Join to households
    hh = pd.merge(hh, df, how="left", on=hhid_col)
    hh[daysim_field].fillna(0, inplace=True)

    return hh


def process_household_file(hh_file_dir, person):
    hh = pd.read_csv(hh_file_dir, encoding="latin-1")
    hh["hhno"] = hh["hhid"]
    hh["hhexpfac"] = hh[hh_wt_col]

    # Workers hhwkrs
    hh = total_persons_to_hh(
        hh,
        person,
        daysim_field="hhwkrs",
        filter_field="pwtyp",
        filter_field_list=[1, 2],
        hhid_col="hhno",
        wt_col="psexpfac",
    )

    # Full-time workers
    hh = total_persons_to_hh(
        hh,
        person,
        daysim_field="hhftw",
        filter_field="pwtyp",
        filter_field_list=[1],
        hhid_col="hhno",
        wt_col="psexpfac",
    )

    ## Part-time workers
    hh = total_persons_to_hh(
        hh,
        person,
        daysim_field="hhptw",
        filter_field="pwtyp",
        filter_field_list=[2],
        hhid_col="hhno",
        wt_col="psexpfac",
    )

    ## Retirees
    hh = total_persons_to_hh(
        hh,
        person,
        daysim_field="hhret",
        filter_field="pptyp",
        filter_field_list=[3],
        hhid_col="hhno",
        wt_col="psexpfac",
    )

    ## Other Adults
    hh = total_persons_to_hh(
        hh,
        person,
        daysim_field="hhoad",
        filter_field="pptyp",
        filter_field_list=[4],
        hhid_col="hhno",
        wt_col="psexpfac",
    )

    # University Students
    hh = total_persons_to_hh(
        hh,
        person,
        daysim_field="hhuni",
        filter_field="pptyp",
        filter_field_list=[5],
        hhid_col="hhno",
        wt_col="psexpfac",
    )

    # High school students
    hh = total_persons_to_hh(
        hh,
        person,
        daysim_field="hhhsc",
        filter_field="pptyp",
        filter_field_list=[6],
        hhid_col="hhno",
        wt_col="psexpfac",
    )

    # k12 age 5-15
    hh = total_persons_to_hh(
        hh,
        person,
        daysim_field="hh515",
        filter_field="pptyp",
        filter_field_list=[7],
        hhid_col="hhno",
        wt_col="psexpfac",
    )

    ## age under 5
    hh = total_persons_to_hh(
        hh,
        person,
        daysim_field="hhcu5",
        filter_field="pptyp",
        filter_field_list=[8],
        hhid_col="hhno",
        wt_col="psexpfac",
    )

    hh["hownrent"] = hh[hownrent].map(hownrent_map)
    hh["hrestype"] = hh[hrestype].map(hhrestype_map)
    hh["hhincome"] = hh[hhincome].map(income_map)
    hh["hhtaz"] = hh[hhtaz]
    hh["hhwkrs"] = hh[hhwkrs]
    hh["hhno"] = hh[hhno]
    hh["hhvehs"] = hh[hhvehs]

    daysim_fields = [
        "hhno",
        "hhsize",
        "hhvehs",
        "hhwkrs",
        "hhftw",
        "hhptw",
        "hhret",
        "hhoad",
        "hhuni",
        "hhhsc",
        "hh515",
        "hhcu5",
        "hhincome",
        "hownrent",
        "hrestype",
        "hhtaz",
        "hhexpfac",
    ]

    hh = hh[daysim_fields]

    return hh


def process_trip_file(trip_file_dir, person):
    """Convert trip records to Daysim format."""

    trip = pd.read_csv(trip_file_dir, encoding="latin-1")
    # trip = pd.read_excel(trip_file_dir, sheetname='5-Trip', skiprows=1)

    # FIXME
    # This is all whack right now,
    trip["trexpfac"] = trip["trip_weight_revised"]
    # Filter out trips that have weight of zero or null
    trip = trip[-trip["trexpfac"].isnull()]
    trip = trip[trip["trexpfac"] > 0]

    trip["hhno"] = trip["hhid"]
    trip["pno"] = trip["pernum"]
    trip["day"] = trip["daynum"].astype(int)
    trip["tsvid"] = trip["recid"]

    # Select only weekday trips (Should we also include Friday?)
    trip = trip[
        trip["dayofweek"].isin([1, 2, 3, 4])
    ]  # This is messed up in the current version of survey
    # use nwkdays > 0 instead
    # trip = trip[trip['nwkdays'] > 0]

    # FIXME
    # Filter out people that have some missing information, like trip purpose
    # Don't just filter out trips for some applications?

    # FIXME: this field is whack
    trip["day"] = trip["dayofweek"]

    trip["opurp"] = trip["o_purpose"].map(purpose_map)
    trip["dpurp"] = trip["d_purpose"].map(purpose_map)

    trip["dorp"] = trip["driver"].map(dorp_map)
    # Dorp of N/A is e in daysim, fillna with this value
    trip["dorp"] = trip["dorp"].fillna(3)

    # FIXME: add the trip parcels and TAZs
    trip["otaz"] = -1
    trip["dtaz"] = -1
    trip["opcl"] = -1
    trip["dpcl"] = -1
    # origin and destination TAZs
    # trip['otaz'] = trip['o_taz2010']
    # trip['dtaz'] = trip['d_taz2010']
    # trip['otaz'] = trip['otaz'].fillna(-1)
    # trip['dtaz'] = trip['dtaz'].fillna(-1)

    ##############################
    # Start and end time
    ##############################
    # Filter out rows with None
    trip = trip[-trip["depart_time_mam"].isnull()]
    trip = trip[-trip["arrival_time_mam"].isnull()]
    trip["arrtm"] = trip["arrival_time_mam"] + (
        60 * 3
    )  # data is originally in minutes after 3, convert to minutes after midnight
    trip["deptm"] = trip["depart_time_mam"] + (
        60 * 3
    )  # data is originally in minutes after 3, convert to minutes after midnight
    # if arrtm/deptm > 24*60, subtract that value to normalize to a single day
    # for some reason values can extend to a full day later
    for colname in ["arrtm", "deptm"]:
        for i in range(2, int(np.ceil(trip[colname] / (24 * 60)).max()) + 1):
            filter = (trip[colname] > (24 * 60)) & (trip[colname] < (24 * 60) * i)
            trip.loc[filter, colname] = trip.loc[filter, colname] - 24 * 60 * (i - 1)

    # Minutes
    # for db_col_name, daysim_col_name in {'arrival_time_mam': 'arrtm', 'depart_time_mam': 'deptm'}.items():

    #    # Filter rows without valid depart and start times
    #    trip = trip[-trip[db_col_name].isnull()]

    #    trip[daysim_col_name] =

    # Get minutes from time stamp, as values to right of :
    # minutes = trip[db_col_name].apply(lambda row: str(row).split(' ')[-1].split(':')[1])
    # minutes = minutes.apply(lambda row: row.split('.')[0]).astype('int') # Trim any decimal places and takes whole numbers

    ## Get hours from time stamp
    # hours = trip[db_col_name].apply(lambda row: str(row).split(' ')[-1].split(':')[0]).astype('int')

    ## In minutes after midnight****
    ###########
    ## NOTE: Check that daysim uses MAM and not minutes after 3 A
    ###########
    # trip[daysim_col_name] = hours*60 + minutes

    ##############################
    # Mode
    ##############################
    trip["mode"] = "Other"

    # Get HOV2/HOV3 based on total number of travelers
    auto_mode_list = [3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 16, 17, 18, 21, 22, 33, 34]
    trip.loc[
        (trip["travelers_total"] == 1) & (trip["mode_1"].isin(auto_mode_list)), "mode"
    ] = "SOV"
    trip.loc[
        (trip["travelers_total"] == 2) & (trip["mode_1"].isin(auto_mode_list)), "mode"
    ] = "HOV2"
    trip.loc[
        (trip["travelers_total"] > 2) & (trip["mode_1"].isin(auto_mode_list)), "mode"
    ] = "HOV3+"
    # transit etc
    trip.loc[trip["mode_1"].isin([23, 32, 41, 42, 52]), "mode"] = "Transit"
    trip.loc[trip["mode_1"].isin([1]), "mode"] = "Walk"
    trip.loc[trip["mode_1"].isin([2]), "mode"] = "Bike"
    trip.loc[trip["mode_1"].isin([24]), "mode"] = "School_Bus"
    trip.loc[
        trip["mode_1"].isin([37]), "mode"
    ] = "TNC"  # Should this also include traditonal Taxi?
    trip["mode"] = trip["mode"].map(mode_dict)

    ##############################
    # Origin and Destination Types
    ##############################

    # Assume "other" by default
    trip.loc[:, "oadtyp"] = 4
    trip.loc[:, "dadtyp"] = 4

    # Trips with origin/destination purpose of "Home" (0) have a origin/destination address type of "Home" (1)
    trip.loc[trip["opurp"] == 0, "oadtyp"] = 1
    trip.loc[trip["dpurp"] == 0, "dadtyp"] = 1

    # Trips to/from work are considered "usual workplace" only if dpcl == workplace parcel
    #### FIX ME: do not have PARCELS, only using TAZ
    # must join person records to get usual work and school location
    trip = trip.merge(
        person[["hhno", "pno", "pwtaz", "pstaz"]], on=["hhno", "pno"], how="left"
    )

    # If trip is to/from TAZ of usual workplace and trip purpose is work
    trip.loc[(trip["opurp"] == 0) & (trip["otaz"] == trip["pwtaz"]), "oadtyp"] = 2
    trip.loc[(trip["dpurp"] == 0) & (trip["dtaz"] == trip["pwtaz"]), "dadtyp"] = 2

    # usual school
    trip.loc[(trip["opurp"] == 0) & (trip["otaz"] == trip["pstaz"]), "oadtyp"] = 3
    trip.loc[(trip["dpurp"] == 0) & (trip["dtaz"] == trip["pstaz"]), "dadtyp"] = 3

    # Change mode
    trip.loc[trip["opurp"] == 10, "oadtyp"] = 6
    trip.loc[trip["dpurp"] == 10, "dadtyp"] = 6

    ##############################
    # Set Skim Values
    ##############################

    trip["travcost"] = -1
    trip["travtime"] = -1
    trip["travdist"] = -1

    # Add pathtype by analyzing transit submode
    # FIXME: Note that this field doesn't exist for some trips, should really be analyzed by grouping on the trip day or tour
    trip["pathtype"] = 1
    for index, row in trip.iterrows():
        if len(
            [
                i
                for i in list(row[["mode_1", "mode_2", "mode_3", "mode_4"]].values)
                if i in [23, 32, 41, 42, 52]
            ]
        ):
            # ferry or water taxi
            if 32 in row[["mode_1", "mode_2", "mode_3", "mode_4"]].values:
                trip.loc[index, "pathtype"] = 7
            # commuter rail
            elif 41 in row[["mode_1", "mode_2", "mode_3", "mode_4"]].values:
                trip.loc[index, "pathtype"] = 6
            # 'Urban rail (e.g., Link light rail, monorail)'
            elif [42 or 52] in row[["mode_1", "mode_2", "mode_3", "mode_4"]].values:
                trip.loc[index, "pathtype"] = 4
            else:
                trip.loc[index, "pathtype"] = 3

            # FIXME
            # Note that we also need to include KnR and TNC

    trip_cols = [
        "hhno",
        "pno",
        "tsvid",
        "day",
        "mode",
        "opurp",
        "dpurp",
        "deptm",
        "otaz",
        "dtaz",
        "opcl",
        "dpcl",
        "oadtyp",
        "dadtyp",
        "arrtm",
        "trexpfac",
        "travcost",
        "travtime",
        "travdist",
        "pathtype",
        "mode_acc",
        "mode_egr",
    ]  # only include access mode temporarily

    trip = trip[-trip["mode"].isnull()]
    trip = trip[-trip["opurp"].isnull()]
    trip = trip[-trip["dpurp"].isnull()]
    trip = trip[-trip["otaz"].isnull()]
    trip = trip[-trip["dtaz"].isnull()]

    # Write to file
    trip = trip[trip_cols]

    return trip


def build_tour_file(trip, person):
    """Generate tours from Daysim-formatted trip records."""

    trip["personid"] = trip["hhno"].astype("int") + trip["pno"].astype("int")
    person["personid"] = person["hhno"].astype("int") + person["pno"].astype("int")

    tour_dict = {}
    mylist = []
    bad_trips = []
    tour_id = 0

    for personid in trip["personid"].value_counts().index.values:
        # for personid in [17100762]:

        person_df = trip.loc[trip["personid"] == personid]
        # Loop through each day
        for day in person_df["day"].unique():
            df = person_df.loc[person_df["day"] == day]

            # First o and last d of person's travel day should be home; if not, skip this trip set
            if (df.groupby("personid").first()["opurp"].values[0] != 0) or df.groupby(
                "personid"
            ).last()["dpurp"].values[0] != 0:
                bad_trips.append(df["personid"].iloc[0])
                continue

            # identify home-based tours
            home_tours_start = df[df["opurp"] == 0]
            home_tours_end = df[df["dpurp"] == 0]

            # skip person if they have a different number of tour starts/ends at home
            if len(home_tours_start) != len(home_tours_end):
                bad_trips.append(df["personid"].iloc[0])
                continue

            # Loop through each set of home-based tours
            for local_tour_index in range(len(home_tours_start)):
                tour_dict[tour_id] = {}

                # start row for this set
                start_row_id = home_tours_start.index[local_tour_index]
                #         print start_row
                end_row_id = home_tours_end.index[local_tour_index]
                #         print '-----'
                # iterate between the start row id and the end row id to build the tour

                # Select slice of trips that correspond to a trip set
                _df = df.loc[start_row_id:end_row_id]

                #################################
                # Skip this trip set under certain conditions
                #################################

                if len(_df) == 0:
                    continue

                # Trips with negative purposes
                if (_df["opurp"] < 0).any() or (_df["dpurp"] < 0).any():
                    print("negative person :(" + str(_df["personid"].iloc[0]))
                    bad_trips.append(df["personid"].iloc[0])
                    continue

                # Trips with same opurp and dpurp that is home
                if len(_df[(_df["opurp"] == _df["dpurp"]) & (_df["opurp"] == 0)]) > 0:
                    bad_trips.append(df["personid"].iloc[0])
                    continue

                #         # Trips that have different purposes in sequence
                #         if len (df[df.shift(-1)['opurp']!=df['dpurp']]) > 0:
                #             bad_trips.append(df['personid'].iloc[0])
                #             continue

                # First row contains origin information
                tour_dict[tour_id]["tlvorig"] = _df.iloc[0]["deptm"]
                tour_dict[tour_id]["tardest"] = _df.iloc[0]["arrtm"]
                tour_dict[tour_id]["totaz"] = _df.iloc[0]["otaz"]
                tour_dict[tour_id]["topcl"] = _df.iloc[0]["opcl"]
                tour_dict[tour_id]["toadtyp"] = _df.iloc[0]["oadtyp"]
                # NEED PARCEL DATA ON TRIP RECORDS!!!

                # Last row contains arrival time at destination
                #### FIX ME: this should be the departure
                tour_dict[tour_id]["tlvdest"] = _df.iloc[-1]["deptm"]
                tour_dict[tour_id]["tarorig"] = _df.iloc[-1]["arrtm"]

                # Household and person info
                tour_dict[tour_id]["hhno"] = _df.iloc[0]["hhno"]
                tour_dict[tour_id]["pno"] = _df.iloc[0]["pno"]
                tour_dict[tour_id]["day"] = day

                # Identify primary purpose and figure out the tour halves
                #   ****ASSUMING primary tour is the activity that takes the longest amount of time

                # Determine if this is part of the first half tour or second half tour
                # calculate duration, as difference between arrival at a place and start of next trip
                _df["duration"] = (
                    _df.shift(-1).iloc[:-1]["deptm"] - _df.iloc[:-1]["arrtm"]
                )

                # FIXME: what is this for, delete?
                if len(_df) > 3:
                    mylist.append(_df["personid"].iloc[0])

                # For tour groups with only 2 trips, the halves are simply the first and second trips
                if len(_df) == 2:
                    tour_dict[tour_id]["pdpurp"] = _df.iloc[0]["dpurp"]
                    tour_dict[tour_id]["tripsh1"] = 1
                    tour_dict[tour_id]["tripsh2"] = 1
                    tour_dict[tour_id]["tdadtyp"] = _df.iloc[0]["dadtyp"]
                    tour_dict[tour_id]["odadtyp"] = _df.iloc[0]["oadtyp"]
                    tour_dict[tour_id]["tpathtp"] = _df.iloc[0]["pathtype"]

                    # Set tour half and tseg within half tour for trips
                    # for tour with only two records, there will always be two halves with tseg = 1 for both
                    trip.loc[trip["tsvid"] == _df.iloc[0]["tsvid"], "half"] = 1
                    trip.loc[trip["tsvid"] == _df.iloc[-1]["tsvid"], "half"] = 2
                    trip.loc[trip["tsvid"].isin(_df["tsvid"]), "tseg"] = 1

                # For tour groups with > 2 trips, calculate primary purpose and halves
                else:
                    # Assuming that the primary purpose is the purpose for the trip to place with longest duration
                    # Exclude trips with only change-mode (10) to find primary purpose
                    print("------------------")
                    print(personid)
                    primary_purp_index = _df[_df["dpurp"] != 10]["duration"].idxmax()

                    tour_dict[tour_id]["pdpurp"] = _df.loc[primary_purp_index]["dpurp"]

                    # Get the tour DTAZ as the DTAZ of the primary trip destination; also dest address type
                    tour_dict[tour_id]["tdtaz"] = _df.loc[primary_purp_index]["dtaz"]
                    tour_dict[tour_id]["tdpcl"] = _df.loc[primary_purp_index]["dpcl"]
                    tour_dict[tour_id]["tdadtyp"] = _df.loc[primary_purp_index][
                        "dadtyp"
                    ]

                    # Pathtype is defined by a heirarchy, where highest number is chosen first
                    # Ferry > Commuter rail > Light Rail > Bus > Auto Network
                    # Note that tour pathtype is different from trip path type (?)
                    tour_dict[tour_id]["tpathtp"] = _df.loc[_df["mode"].idxmax()][
                        "pathtype"
                    ]

                    # Get number of trips in each half tour
                    tour_dict[tour_id]["tripsh1"] = len(_df.loc[0:primary_purp_index])
                    tour_dict[tour_id]["tripsh2"] = len(
                        _df.loc[primary_purp_index + 1 :]
                    )

                    # Set tour halves on trip records
                    trip.loc[
                        trip["tsvid"].isin(_df.loc[0:primary_purp_index].tsvid), "half"
                    ] = 1
                    trip.loc[
                        trip["tsvid"].isin(_df.loc[primary_purp_index + 1 :].tsvid),
                        "half",
                    ] = 2

                    # set trip segment within half tours
                    trip.loc[
                        trip["tsvid"].isin(_df.loc[0:primary_purp_index].tsvid), "tseg"
                    ] = range(1, len(_df.loc[0:primary_purp_index]) + 1)
                    trip.loc[
                        trip["tsvid"].isin(_df.loc[primary_purp_index + 1 :].tsvid),
                        "tseg",
                    ] = range(1, len(_df.loc[primary_purp_index + 1 :]) + 1)

                # Extract main mode type

                # Heirarchy order for tour mode, per DaySim docs: https://www.psrc.org/sites/default/files/2015psrc-modechoiceautomodels.pdf
                # Drive to Transit > Walk to Transit > School Bus > HOV3+ > HOV2 > SOV > Bike > Walk

                # Get a list of transit modes and identify primary mode
                # Primary mode is the first one from a heirarchy list found in the tour
                mode_list = _df["mode"].value_counts().index.astype("int").values
                mode_heirarchy = [6, 8, 5, 4, 3, 2, 1]
                for mode in mode_heirarchy:
                    if mode in mode_list:
                        # If transit, check whether access mode is walk to transit or drive to transit
                        if mode == 6:
                            # Try to use the access mode field values to get access mode
                            if len(_df[-_df["mode_acc"].isnull()]) > 0:
                                if len(
                                    [i for i in _df["mode_acc"].values if i in [1, 2]]
                                ):
                                    tour_dict[tour_id][
                                        "tmodetp"
                                    ] = 6  # walk (or bike) to transit
                                    print("mode_acc walk")
                                else:
                                    print("mode_acc drive")
                                    tour_dict[tour_id]["tmodetp"] = 7  # park and ride
                                break
                            else:
                                # otherwise, use a simpler check; if auto is used on any of the other trips, assume drive to transit, else assign walk to transit
                                if len([i for i in mode_list if i in [3, 4, 5]]) > 0:
                                    tour_dict[tour_id]["tmodetp"] = 7  # park and ride
                                else:
                                    tour_dict[tour_id][
                                        "tmodetp"
                                    ] = 6  # walk (or bike) to transit
                                break

                        # For non-transit modes, add first mode from the heirarchical list
                        tour_dict[tour_id]["tmodetp"] = mode
                        break

                # FIXME: add in park and ride trips
                # These will be change mode trips to transit where the first mode is drive

                # Identify work-based subtours
                # Subtours require:
                # - at least 2 trips in addition to initial and final trips
                # - primary tour purpose of work
                # - origin work purpose with a return destination purpose of work

                if (len(_df) >= 4) & (tour_dict[tour_id]["pdpurp"] == 1):
                    #                 my_df = _df.copy()
                    #                 # Considered a subtour if the middle trips start and end from work
                    #                 subtour_ends = len(_df[(_df['opurp'] == 1) & (_df['dpurp'] != 0)]) + len(_df[(_df['opurp'] != 0) & (_df['dpurp'] == 1)])
                    #                 subtours = subtour_ends/2

                    # Subtours must start from work (opurp==1) and not go to home or work #### FIXME, maybe revise that assumption
                    # since some trips of 1 can be work-related and may actually be a work tour
                    subtour_index_start_values = _df[
                        (_df["opurp"] == 1) & (-_df["dpurp"].isin([0, 1]))
                    ].index.values
                    local_index = 0
                    subtours = 0
                    for i in subtour_index_start_values:
                        #                 print(i)
                        # Loop through next rows until a return trip to work is found
                        # unless it hits the next subtour_index_start_value

                        while local_index < len(subtour_index_start_values):
                            try:
                                # if (_df.loc[i+1]['dpurp'] == 1) & ((_df.loc[i+1]['opurp'] != 0) or (_df.loc[i+1]['opurp'] != 1)):
                                if _df.loc[i + 1]["dpurp"] == 1:
                                    # Found the end of the subtours
                                    subtours += 1
                                    # keep searching for additional subtours
                            #                         print(local_index)
                            except:
                                local_index += 1
                                print(local_index)
                                continue

                            local_index += 1
                else:
                    subtours = 0
                tour_dict[tour_id]["subtrs"] = subtours

                # tour_dict['tour'] = int(tour_id)

                # add tour ID to the trip records
                trip.loc[trip["tsvid"].isin(_df["tsvid"].values), "tour"] = (
                    local_tour_index + 1
                )
                tour_dict[tour_id]["tour"] = local_tour_index + 1

                tour_id += 1

    tour = pd.DataFrame.from_dict(tour_dict, orient="index")
    # tour['tour'] = range(1,len(tour)+1)

    for col in [
        "jtindex",
        "parent",
        "tautotime",
        "tautocost",
        "tautodist",
        "phtindx1",
        "phtindx2",
        "fhtindx1",
        "fhtindx2",
    ]:
        tour[col] = -1

    # Assign weight toexpfac as hhexpfac (getting it from psexpfac, which is the same as hhexpfac)
    # FIXME: confirm this with Mark B
    tour["personid"] = tour["hhno"].astype("int") + tour["pno"].astype("int")
    tour = tour.merge(person[["personid", "psexpfac"]], on="personid", how="left")
    tour.rename(columns={"psexpfac": "toexpfac"}, inplace=True)

    return tour, trip


def process_household_day(tour, hh):
    household_day = pd.DataFrame()

    household_day["hhno"] = tour["hhno"].unique()

    # There should be a single trip reported for each household
    household_day["day"] = 1

    # Set number of joint tours to 0 for this version of Daysim
    for col in ["jttours", "phtours", "fhtours"]:
        household_day[col] = 0

    #

    return household_day


def person_day(tour, person):
    pday = pd.DataFrame()
    for person_rec in person["personid"].unique():
        # get this person's tours
        _tour = tour[tour["personid"] == person_rec]

        # Loop through each day
        for day in _tour["day"].unique():
            # from survey data

            # _pday_survey = pday_survey[(pday_survey['personid'] == person_rec) & (pday_survey['dayofweek'] == day)]

            day_tour = _tour[_tour["day"] == day]

            prec_id = str(person_rec) + str(day)
            pday.loc[prec_id, "hhno"] = day_tour["hhno"].iloc[0]
            pday.loc[prec_id, "pno"] = day_tour["pno"].iloc[0]
            pday.loc[prec_id, "day"] = day

            # Begin/End at home-
            # need to get from first and last trips of tour days
            pday.loc[prec_id, "beghom"] = 0
            pday.loc[prec_id, "endhom"] = 0
            _trip = trip[(trip["personid"] == person_rec) & (trip["day"] == day)]
            if _trip.iloc[0]["opurp"] == 0:
                pday.loc[prec_id, "beghom"] = 1
            if _trip.iloc[-1]["dpurp"] == 0:
                pday.loc[prec_id, "endhom"] = 1

            # Number of tours by purpose
            purp_dict = {
                "uw": 1,  # tours to usual workplace
                "sc": 2,
                "es": 3,
                "pb": 4,
                "sh": 5,
                "ml": 6,
                "so": 7,
                "re": 8,
                "me": 9,
            }
            for purp_name, purp_val in purp_dict.items():
                # Number of tours
                pday.loc[prec_id, purp_name + "tours"] = len(
                    day_tour[day_tour["pdpurp"] == purp_val]
                )

                # Number of stops
                day_tour_purp = day_tour[day_tour["pdpurp"] == purp_val]
                if len(day_tour_purp) > 0:
                    nstops = day_tour_purp[["tripsh1", "tripsh2"]].sum().sum() - 2
                else:
                    nstops = 0
                pday.loc[prec_id, purp_name + "stops"] = nstops

            # Minutes worked at home
            # pday.loc[prec_id,'wkathome'] = _pday_survey['telework_time'].values[0]

    return pday


def main():
    person = process_person_file(person_file_dir)
    hh = process_household_file(hh_file_dir, person)
    trip = process_trip_file(trip_file_dir, person)
    # df_name = 'person'
    # person = read_csv = pd.read_csv(os.path.join(output_dir,df_name+'17.csv'))
    # df_name = 'trip'
    # trip = read_csv = pd.read_csv(os.path.join(output_dir,df_name+'17.csv'))

    # household

    # Create tour file and update the trip file with tour info
    tour, trip = build_tour_file(trip, person)

    # person day and household day records

    # household day
    # all other values set to 0; hdexpfac looks like it is simply the household weights
    # FIXME: CONFIRM THIS WITH MARK B
    household_day = process_household_day(tour, hh)

    # person day
    person_day = person_day(tour, person)

    # Write files
    for df_name, df in {
        "person": person,
        "trip": trip,
        "tour": tour,
        "household": hh,
        "hhday": household_day,
        "pday": person_day,
    }.items():
        df.to_csv(os.path.join(output_dir, df_name + "17.csv"), index=False)


if __name__ == "__main__":
    main()
