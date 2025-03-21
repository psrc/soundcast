import numpy as np
import pandas as pd
import time
import h5toDF
import xlautofit
import math
import xlrd
import os, sys

sys.path.append(os.path.join(os.getcwd(), "scripts"))
sys.path.append(os.getcwd())


def get_total(exp_fac):
    total = exp_fac.sum()
    if total < 1:
        total = exp_fac.count()
    return total


def weighted_average(df_in, col, weights, grouper):
    if grouper == None:
        df_in[col + "_sp"] = df_in[col].multiply(df_in[weights])
        n_out = df_in[col + "_sp"].sum() / df_in[weights].sum()
        return n_out
    else:
        df_in[col + "_sp"] = df_in[col].multiply(df_in[weights])
        df_out = df_in.groupby(grouper).sum()
        df_out[col + "_wa"] = df_out[col + "_sp"].divide(df_out[weights])
        return df_out


def recode_index(
    df, old_name, new_name
):  # Changes the index label from something like "pdpurp" to "Primary Destination Purpose"
    df[new_name] = df.index
    df = df.reset_index()
    del df[old_name]
    df = df.set_index(new_name)
    return df


def get_districts(file):
    zone_district = pd.DataFrame.from_csv(file, index_col=None)
    return zone_district


def to_percent(number):  # Might be used later
    number = "{:.2%}".format(number)
    return number


def get_differences(
    df, colname1, colname2, roundto
):  # Computes the difference and percent difference for two specified columns in a data frame
    df["Difference"] = df[colname1] - df[colname2]
    df["% Difference"] = (df["Difference"] / df[colname2] * 100).round(2)
    if type(roundto) == list:
        for i in range(len(df["Difference"])):
            df[colname1][i] = round(df[colname1][i], roundto[i])
            df[colname2][i] = round(df[colname2][i], roundto[i])
            df["Difference"][i] = round(df["Difference"][i], roundto[i])
    else:
        for i in range(len(df["Difference"])):
            df[colname1][i] = round(df[colname1][i], roundto)
            df[colname2][i] = round(df[colname2][i], roundto)
            df["Difference"][i] = round(df["Difference"][i], roundto)
    return df


def share_compare(df, colname1, colname2):
    df[colname1] = df[colname1].apply(to_percent)
    df[colname2] = df[colname2].apply(to_percent)
    df["Difference"] = df["Difference"].apply(to_percent)


def hhmm_to_min(
    input,
):  # Function that converts time in an hhmm format to a minutes since the day started format
    minmap = {}
    for i in range(0, 24):
        for j in range(0, 60):
            minmap.update({i * 100 + j: i * 60 + j})
    if input["Trip"]["deptm"].max() >= 1440:
        input["Trip"]["deptm"] = input["Trip"]["deptm"].map(minmap)
    if input["Trip"]["arrtm"].max() >= 1440:
        input["Trip"]["arrtm"] = input["Trip"]["arrtm"].map(minmap)
    if input["Trip"]["endacttm"].max() >= 1440:
        input["Trip"]["endacttm"] = input["Trip"]["endacttm"].map(minmap)
    if input["Tour"]["tlvorig"].max() >= 1440:
        input["Tour"]["tlvorig"] = input["Tour"]["tlvorig"].map(minmap)
    if input["Tour"]["tardest"].max() >= 1440:
        input["Tour"]["tardest"] = input["Tour"]["tardest"].map(minmap)
    if input["Tour"]["tlvdest"].max() >= 1440:
        input["Tour"]["tlvdest"] = input["Tour"]["tlvdest"].map(minmap)
    if input["Tour"]["tarorig"].max() >= 1440:
        input["Tour"]["tarorig"] = input["Tour"]["tarorig"].map(minmap)
    return input


def min_to_hour(
    input, base
):  # Converts minutes since a certain time of the day to hour of the day
    timemap = {}
    for i in range(0, 24):
        if i + base < 24:
            for j in range(0, 60):
                if i + base < 9:
                    timemap.update(
                        {i * 60 + j: "0" + str(i + base) + " - 0" + str(i + base + 1)}
                    )
                elif i + base == 9:
                    timemap.update(
                        {i * 60 + j: "0" + str(i + base) + " - " + str(i + base + 1)}
                    )
                else:
                    timemap.update(
                        {i * 60 + j: str(i + base) + " - " + str(i + base + 1)}
                    )
        else:
            for j in range(0, 60):
                if i + base - 24 < 9:
                    timemap.update(
                        {
                            i * 60
                            + j: "0"
                            + str(i + base - 24)
                            + " - 0"
                            + str(i + base - 23)
                        }
                    )
                elif i + base - 24 == 9:
                    timemap.update(
                        {
                            i * 60
                            + j: "0"
                            + str(i + base - 24)
                            + " - "
                            + str(i + base - 23)
                        }
                    )
                else:
                    timemap.update(
                        {i * 60 + j: str(i + base - 24) + " - " + str(i + base - 23)}
                    )
    output = input.map(timemap)
    return output


def Thousands_Comma_Insertifier_9000(number):
    number_string = str(number)
    try:
        decimal_position = number_string.index(".")
        integer_part = number_string[:decimal_position]
        decimal_part = number_string[decimal_position:]
    except ValueError:
        decimal_position = False
        integer_part = number_string
        decimal_part = ""
    integer_length = len(integer_part)
    num_commas = (integer_length - 1) / 3
    if integer_length % 3 != 0:
        digits_before_comma = integer_length % 3 - 1
    else:
        digits_before_comma = 2
    integer_list = [integer_part[: (digits_before_comma + 1)]]
    for i in range(num_commas):
        integer_list.append(
            integer_part[
                3 * i + digits_before_comma + 1 : 3 * i + digits_before_comma + 4
            ]
        )
    out_integer = ",".join(integer_list)
    out_number = out_integer + decimal_part
    return out_number


def add_percent_sign(input):
    output = str(input) + " %"
    return output


# datafile = 'D:/soundcat/soundcat/outputs/daysim_outputs.h5'
# datafile = 'R:/JOE/summarize/daysim_outputs.h5'
datafile = "Q:/soundcast/outputs/daysim_outputs.h5"
guidefile = "Q:/soundcast/scripts/summarize/inputs/CatVarDict.xlsx"
districtfile = "Q:/soundcast/scripts/summarize/inputs/TAZ_TAD_County.csv"
urbcen = "Q:/soundcast/scripts/summarize/inputs/parcels_in_urbcens.csv"
data = h5toDF.convert(datafile, guidefile, "Results")
zone_district = get_districts(districtfile)
parcels_regional_centers = pd.DataFrame.from_csv(urbcen)
HHPer = pd.merge(
    data["Household"][["hhno", "hhparcel"]],
    data["Person"][["pwpcl", "hhno", "psexpfac", "pno"]],
    on="hhno",
)
hh_center = pd.merge(
    HHPer[["hhno", "pno", "hhparcel", "psexpfac"]],
    parcels_regional_centers,
    "outer",
    left_on="hhparcel",
    right_index=True,
)
hh_center = hh_center.dropna(subset=["NAME"])

center_populations = hh_center[["NAME", "psexpfac"]].groupby("NAME").sum()["psexpfac"]
total_population = pd.Series(data=hh_center["psexpfac"].sum(), index=["Total"])
center_populations = center_populations.append(total_population)

work_center = pd.merge(
    HHPer[["hhno", "pwpcl"]],
    parcels_regional_centers,
    "outer",
    left_on="pwpcl",
    right_index=True,
)
work_center = work_center.dropna(subset=["NAME"])

center_list = (
    parcels_regional_centers["NAME"].value_counts().sort_index().index.tolist()
)
center_list.append("Total")
modes = data["Trip"]["mode"].value_counts().index

mode_split = pd.DataFrame(index=center_list, columns=modes)
work_mode_split = pd.DataFrame(index=center_list, columns=modes)
work_dest_mode_split = pd.DataFrame(index=center_list, columns=modes)
miles_traveled = pd.DataFrame(
    index=center_list, columns=["VMT", "PMT", "VMT per Person", "PMT per Person"]
)
arrival_mode_split = pd.DataFrame(index=center_list, columns=modes)
departure_mode_split = pd.DataFrame(index=center_list, columns=modes)

times = min_to_hour(data["Trip"]["arrtm"], 3).value_counts().sort_index().index

hournames = ["Midnight - 1 AM"]
for i in range(1, 11):
    hournames.append(str(i) + " - " + str(i + 1) + " AM")
hournames = hournames + ["11 AM - Noon", "Noon - 1 PM"]
for i in range(1, 11):
    hournames.append(str(i) + " - " + str(i + 1) + " PM")
hournames.append("11 PM - Midnight")

trips_by_time = {}

for time_range in times:
    time_df = pd.DataFrame(
        index=center_list, columns=["Arrivals", "Departures", "Change"]
    )
    trips_by_time.update({time_range: time_df})

regional_center_data = {}

for center in center_list:
    timerstart = time.time()
    regional_summaries = {}
    if center is not "Total":
        trip_hh_center = pd.merge(
            data["Trip"][
                ["dpurp", "mode", "hhno", "trexpfac", "travdist", "dorp", "pno"]
            ],
            hh_center,
            on=["hhno", "pno"],
        ).query('NAME == "' + str(center) + '"')
    else:
        trip_hh_center = pd.merge(
            data["Trip"][
                ["dpurp", "mode", "hhno", "trexpfac", "travdist", "dorp", "pno"]
            ],
            hh_center,
            on=["hhno", "pno"],
        )
    total_trips_center = trip_hh_center["trexpfac"].sum()
    mode_share = (
        trip_hh_center[["mode", "trexpfac"]].groupby("mode").sum()["trexpfac"]
        / total_trips_center
    ).round(3)
    regional_summaries.update({"Mode Split": mode_share})

    for mode in mode_share.index:
        mode_split[mode][center] = regional_summaries["Mode Split"][mode]

    work_trips_center = trip_hh_center[["dpurp", "trexpfac", "mode"]].query(
        'dpurp == "Work"'
    )
    total_work_trips_center = work_trips_center["trexpfac"].sum()
    work_trips_mode_share = (
        work_trips_center[["mode", "trexpfac"]].groupby("mode").sum()["trexpfac"]
        / total_work_trips_center
    ).round(3)
    regional_summaries.update({"Work Mode Split": work_trips_mode_share})

    regional_center_data.update({center: regional_summaries})

    for mode in work_trips_mode_share.index:
        work_mode_split[mode][center] = regional_summaries["Work Mode Split"][mode]

    if center is not "Total":
        trip_work_center = pd.merge(
            data["Trip"][["dpurp", "mode", "hhno", "trexpfac"]], work_center, on="hhno"
        ).query('NAME == "' + str(center) + '" and dpurp == "Work"')
    else:
        trip_work_center = pd.merge(
            data["Trip"][["dpurp", "mode", "hhno", "trexpfac"]], work_center, on="hhno"
        )
    total_trips_center = trip_work_center["trexpfac"].sum()
    work_dest_mode_share = (
        trip_work_center[["mode", "trexpfac"]].groupby("mode").sum()["trexpfac"]
        / total_trips_center
    ).round(3)
    regional_summaries.update({"Work Destination Mode Split": work_dest_mode_share})

    for mode in work_dest_mode_share.index:
        work_dest_mode_split[mode][center] = regional_summaries[
            "Work Destination Mode Split"
        ][mode]

    driver_trips_center = trip_hh_center[["dorp", "travdist", "trexpfac"]].query(
        'dorp == "Driver"'
    )
    vmt = (
        driver_trips_center["travdist"].multiply(driver_trips_center["trexpfac"])
    ).sum()
    try:
        vmt_per_person = vmt / center_populations[center]
    except ZeroDivisionError:
        vmt_per_person = float("nan")
    pmt = (trip_hh_center["travdist"].multiply(trip_hh_center["trexpfac"])).sum()
    try:
        pmt_per_person = pmt / center_populations[center]
    except ZeroDivisionError:
        pmt_per_person = float("nan")

    regional_summaries.update(
        {
            "VMT": vmt,
            "PMT": pmt,
            "VMT per Person": vmt_per_person,
            "PMT per Person": pmt_per_person,
        }
    )

    if miles_traveled["VMT"][center] == 0:
        miles_traveled["VMT"][center] = float("nan")
    else:
        miles_traveled["VMT"][center] = regional_summaries["VMT"]
    if miles_traveled["PMT"][center] == 0:
        miles_traveled["PMT"][center] = float("nan")
    else:
        miles_traveled["PMT"][center] = regional_summaries["PMT"]
    miles_traveled["VMT per Person"][center] = regional_summaries["VMT per Person"]
    miles_traveled["PMT per Person"][center] = regional_summaries["PMT per Person"]

    if center is not "Total":
        center_parcels = parcels_regional_centers.query(
            'NAME == "' + str(center) + '"'
        ).reset_index()
    else:
        center_parcels = parcels_regional_centers.reset_index()
    pcl_list = center_parcels["hhparcel"].value_counts().index

    arrivals = data["Trip"][["opcl", "dpcl", "arrtm", "mode", "trexpfac"]].query(
        "dpcl in @pcl_list and opcl not in @pcl_list"
    )
    arrivals["arr_hr"] = min_to_hour(arrivals["arrtm"], 3)
    arrivals_by_time = (
        arrivals[["arr_hr", "trexpfac"]].groupby("arr_hr").sum()["trexpfac"].round(0)
    )

    total_arrivals = arrivals["trexpfac"].sum()
    try:
        a_mode_split = (
            arrivals[["mode", "trexpfac"]].groupby("mode").sum()["trexpfac"]
            / total_arrivals
        )
    except ZeroDivisionError:
        pass
    for mode in a_mode_split.index:
        arrival_mode_split[mode][center] = a_mode_split[mode].round(3)

    departures = data["Trip"][["opcl", "dpcl", "deptm", "mode", "trexpfac"]].query(
        "opcl in @pcl_list and dpcl not in @pcl_list"
    )
    departures["dep_hr"] = min_to_hour(departures["deptm"], 3)
    departures_by_time = (
        departures[["dep_hr", "trexpfac"]].groupby("dep_hr").sum()["trexpfac"].round(0)
    )

    total_departures = departures["trexpfac"].sum()
    try:
        d_mode_split = (
            departures[["mode", "trexpfac"]].groupby("mode").sum()["trexpfac"]
            / total_departures
        )
    except ZeroDivisionError:
        pass
    for mode in a_mode_split.index:
        departure_mode_split[mode][center] = d_mode_split[mode].round(3)

    for time_range in times:
        trips_by_time[time_range]["Arrivals"][center] = arrivals_by_time[time_range]
        trips_by_time[time_range]["Departures"][center] = departures_by_time[time_range]
        trips_by_time[time_range]["Change"][center] = (
            arrivals_by_time[time_range] - departures_by_time[time_range]
        )

    print(center + ": " + str(round(time.time() - timerstart, 1)) + " seconds")


miles_traveled["VMT/PMT Ratio"] = np.nan
for center in center_list:
    try:
        miles_traveled["VMT/PMT Ratio"][center] = (
            miles_traveled["VMT"][center] / miles_traveled["PMT"][center]
        )
    except ZeroDivisionError:
        continue
miles_traveled = miles_traveled.convert_objects(convert_numeric=True)
for column in miles_traveled.columns:
    if column == "VMT" or column == "PMT":
        miles_traveled[column] = (
            miles_traveled[column]
            .round(0)
            .apply(int)
            .apply(Thousands_Comma_Insertifier_9000)
        )
    else:
        miles_traveled[column] = miles_traveled[column].round(3)


def add_pie_charts(writer, sheet_name):
    colordict = {
        "SOV": "#C00000",
        "HOV2": "#C06000",
        "HOV3+": "#C00060",
        "Walk": "#008000",
        "Bike": "#0040C0",
        "Transit": "#757575",
        "School Bus": "#FFD800",
    }
    workbook = writer.book
    worksheet = writer.sheets[sheet_name]
    book = xlrd.open_workbook(writer.path)
    sheet = book.sheet_by_name(sheet_name)
    for i in range(worksheet.dim_rowmax):
        chart = workbook.add_chart({"type": "pie"})
        chart.add_series(
            {
                "name": [sheet_name, i + 1, 0],
                "categories": [sheet_name, 0, 1, 0, 7],
                "values": [sheet_name, i + 1, 1, i + 1, 7],
                "data_labels": {"value": True, "leader_lines": True},
                "points": [
                    {"fill": {"color": colordict[sheet.cell(0, 1).value]}},
                    {"fill": {"color": colordict[sheet.cell(0, 2).value]}},
                    {"fill": {"color": colordict[sheet.cell(0, 3).value]}},
                    {"fill": {"color": colordict[sheet.cell(0, 4).value]}},
                    {"fill": {"color": colordict[sheet.cell(0, 5).value]}},
                    {"fill": {"color": colordict[sheet.cell(0, 6).value]}},
                    {"fill": {"color": colordict[sheet.cell(0, 7).value]}},
                ],
            }
        )
        chart.set_size({"width": 64 * 6, "height": 280})
        if i % 2 == 0:
            worksheet.insert_chart(1, 8 + 6 * (i / 2), chart)
        else:
            worksheet.insert_chart(15, 8 + 6 * (i / 2), chart)


writer = pd.ExcelWriter(
    "Q:/soundcast/outputs/Regional_Centers.xlsx", engine="xlsxwriter"
)
mode_split.to_excel(excel_writer=writer, sheet_name="Mode Split", na_rep="-")
work_mode_split.to_excel(
    excel_writer=writer, sheet_name="Work Trip Mode Split", na_rep="-"
)
work_dest_mode_split.to_excel(
    excel_writer=writer, sheet_name="Work Destination Mode Split", na_rep="-"
)
miles_traveled.to_excel(excel_writer=writer, sheet_name="VMT and PMT", na_rep="-")
for i in range(len(times)):
    if i == 0:
        trips_by_time[times[i]].to_excel(
            excel_writer=writer,
            sheet_name="Arrivals and Departures by Hour",
            na_rep="-",
            startrow=1,
        )
    else:
        trips_by_time[times[i]].to_excel(
            excel_writer=writer,
            sheet_name="Arrivals and Departures by Hour",
            na_rep="-",
            startrow=1,
            startcol=4 * i + 1,
            index=False,
        )
    sheet = "Arrivals and Departures by Hour"
    worksheet = writer.sheets[sheet]
    if i != len(times):
        worksheet.write(0, 4 * i, " ")
arrival_mode_split.to_excel(
    excel_writer=writer, sheet_name="Arrival Mode Split", na_rep="-"
)
departure_mode_split.to_excel(
    excel_writer=writer, sheet_name="Departure Mode Split", na_rep="-"
)
writer.save()

colwidths = xlautofit.even_widths_single_index(
    "Q:/soundcast/outputs/Regional_Centers.xlsx"
)

writer = pd.ExcelWriter(
    "Q:/soundcast/outputs/Regional_Centers.xlsx", engine="xlsxwriter"
)
mode_split.to_excel(excel_writer=writer, sheet_name="Mode Split", na_rep="-")
work_mode_split.to_excel(
    excel_writer=writer, sheet_name="Work Trip Mode Split", na_rep="-"
)
work_dest_mode_split.to_excel(
    excel_writer=writer, sheet_name="Work Destination Mode Split", na_rep="-"
)
miles_traveled.to_excel(excel_writer=writer, sheet_name="VMT and PMT", na_rep="-")
workbook = writer.book
header_format = workbook.add_format({"bold": "True", "align": "center", "border": 1})
top_5_format = workbook.add_format({"font_color": "#006060", "bold": "True"})
bot_5_format = workbook.add_format({"font_color": "#600060", "bold": "True"})
for i in range(len(times)):
    if i == 0:
        trips_by_time[times[i]].to_excel(
            excel_writer=writer,
            sheet_name="Arrivals and Departures by Hour",
            na_rep="-",
            startrow=1,
        )
    else:
        trips_by_time[times[i]].to_excel(
            excel_writer=writer,
            sheet_name="Arrivals and Departures by Hour",
            na_rep="-",
            startrow=1,
            startcol=4 * i + 1,
            index=False,
        )
    sheet = "Arrivals and Departures by Hour"
    worksheet = writer.sheets[sheet]
    worksheet.merge_range(0, 4 * i + 1, 0, 4 * i + 3, hournames[i], header_format)
arrival_mode_split.to_excel(
    excel_writer=writer, sheet_name="Arrival Mode Split", na_rep="-"
)
departure_mode_split.to_excel(
    excel_writer=writer, sheet_name="Departure Mode Split", na_rep="-"
)
for sheet in writer.sheets:
    worksheet = writer.sheets[sheet]
    for colnum in range(worksheet.dim_colmax + 1):
        worksheet.set_column(colnum, colnum, width=colwidths[sheet][colnum])
        worksheet.conditional_format(
            1, colnum, 27, colnum, {"type": "top", "value": "5", "format": top_5_format}
        )
        worksheet.conditional_format(
            1,
            colnum,
            27,
            colnum,
            {"type": "bottom", "value": "5", "format": bot_5_format},
        )
    if sheet == "Work Destination Mode Split":
        worksheet.write(0, 0, "Workplace Center", header_format)
    elif sheet == "Arrivals and Departures by Hour":
        worksheet.write(1, 0, "Center", header_format)
        worksheet.freeze_panes(0, 1)
    else:
        worksheet.write(0, 0, "Household Center", header_format)
    if sheet != "VMT and PMT" and sheet != "Arrivals and Departures by Hour":
        add_pie_charts(writer, sheet)
writer.save()
