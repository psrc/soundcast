import os
import pandas as pd
import geopandas as gpd
import os.path
import sqlalchemy
import pyodbc
import pandas as pd
import geopandas as gpd
from shapely import wkt

# from standard_summary_configuration import county_map

import toml

sum_config = toml.load(
    os.path.join(os.getcwd(), "configuration/summary_configuration.toml")
)

# Load city boundaries from Elmer


def read_from_sde(
    connection_string, feature_class_name, version, crs="epsg:2285", is_table=False
):
    """
    Returns the specified feature class as a geodataframe from ElmerGeo.

    Parameters
    ----------
    connection_string : SQL connection string that is read by geopandas
                        read_sql function

    feature_class_name: the name of the featureclass in PSRC's ElmerGeo
                        Geodatabase

    cs: cordinate system
    """

    engine = sqlalchemy.create_engine(connection_string)
    con = engine.connect()
    # con.execute("sde.set_current_version {0}".format(version))
    if is_table:
        gdf = pd.read_sql("select * from %s" % (feature_class_name), con=con)
        con.close()

    else:
        df = pd.read_sql(
            "select *, Shape.STAsText() as geometry from %s" % (feature_class_name),
            con=con,
        )
        con.close()

        df["geometry"] = df["geometry"].apply(wkt.loads)
        gdf = gpd.GeoDataFrame(df, geometry="geometry")
        gdf.crs = crs
        cols = [
            col
            for col in gdf.columns
            if col not in ["Shape", "GDB_GEOMATTR_DATA", "SDE_STATE_ID"]
        ]
        gdf = gdf[cols]

    return gdf


def load_network_summary(filepath):
    """Load network-level results using a standard procedure."""
    df = pd.read_csv(filepath)

    # Congested network components by time of day
    df.columns

    # Get freeflow from 20to5 period

    # Exclude trips taken on non-designated facilities (facility_type == 0)
    # These are artificial (weave lanes to connect HOV) or for non-auto uses
    df = df[df["data3"] != 0]  # data3 represents facility_type

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
    df["total_delay"] = (
        (df["auto_time"] - df["freeflow_time"]) * df["@tveh"]
    ) / 60  # sum of (volume)*(travtime diff from freeflow)

    df["county"] = df["@countyid"].map(
        {33: "King", 35: "Kitsap", 53: "Pierce", 61: "Snohomish"}
    )

    return df


def intersect_geog(my_gdf_shp, gdf_network):
    # Intersect geography this with the network shapefile
    gdf_intersect = gpd.overlay(
        gdf_network, my_gdf_shp, how="intersection", keep_geom_type=False
    )

    # # Will need to relaculate the lengths since some were split across the regional geographies
    gdf_intersect["new_length"] = gdf_intersect.geometry.length / 5280.0

    # ### IMPORTANT
    # # filter out the polygon results and only keep lines
    gdf_intersect = gdf_intersect[
        gdf_intersect.geometry.type.isin(["MultiLineString", "LineString"])
    ]

    return gdf_intersect


def summarize_network(df, gdf, geography):
    # Select links from network summary dataframe that are within the gdf_shp
    # The dataframe contains link-level model outputs
    df = df_network[df_network["ij"].isin(gdf["id"])]

    # Replace length with length from _gdf_shp to ensure roads stop at city boundaries
    # Drop "length field from _gdf_shp, which is length in miles;
    # use new_length field, which is calculated length of intersected links in feet
    df.drop("length", axis=1, inplace=True)
    df = df.merge(gdf, how="left", left_on="ij", right_on="id")
    # _df.drop('length', axis=1, inplace=True)
    df.rename(
        columns={"new_length": "length", "length": "original_length"}, inplace=True
    )

    # Calculate VMT, VHT, and Delay
    df = df[df["data3"] != 0]  # data3 represents facility_type

    # calculate total link VMT and VHT
    df["VMT"] = df["@tveh"] * df["length"]
    df["VHT"] = df["@tveh"] * df["auto_time"] / 60

    # Calcualte hourly delay
    df["delay"] = (
        (df["auto_time"] - df["freeflow_time"]) * df["@tveh"]
    ) / 60  # sum of (volume)*(travtime diff from freeflow)
    df = df.groupby(geography).sum()[["VMT", "VHT", "delay"]]

    df = df.reset_index()
    df.rename(columns={geography: "geography"}, inplace=True)

    return df


# Set output directory; results will be stored in a folder by model year
output_dir = "outputs/network/network_geography_summary"

# Create outputs directory if needed
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

# Load the network
crs = "EPSG:2285"
gdf_network = gpd.read_file(r"inputs\scenario\networks\shapefiles\AM\AM_edges.shp")
gdf_network.crs = crs

# Load  county geographies from ElmerGeo
connection_string = "mssql+pyodbc://AWS-PROD-SQL\Sockeye/ElmerGeo?driver=SQL Server?Trusted_Connection=yes"

# We already have County ID
# Need RGC and Regional Geographies
version = "'DBO.Default'"
gdf_shp_rg = read_from_sde(
    connection_string,
    "regional_geographies_preferred_alternative",
    version,
    crs=crs,
    is_table=False,
)
gdf_shp_rgc = read_from_sde(
    connection_string, "urban_centers", version, crs=crs, is_table=False
)

# Perform intersect to get the network within each city in a list
df_network = load_network_summary(r"outputs\network\network_results.csv")

# Intersect network with geographies
# Regional Geographies
gdf_shp_rg_intersect = intersect_geog(gdf_shp_rg, gdf_network)
df_rg = summarize_network(df_network, gdf_shp_rg_intersect, "rg_propose_pa")
df_rg["aggregation"] = "regional_geography"

# Regional Growth Center
gdf_shp_rgc.drop("id", axis=1, inplace=True)
gdf_shp_rgc_intersect = intersect_geog(gdf_shp_rgc, gdf_network)
df_rgc = summarize_network(df_network, gdf_shp_rgc_intersect, "name")
df_rgc["aggregation"] = "regional_growth_center"

# County
df_county = (
    df_network.groupby("@countyid").sum()[["VMT", "VHT", "total_delay"]].reset_index()
)
df_county["geography"] = df_county["@countyid"].map(sum_config["county_map"])
df_county = df_county[~df_county["geography"].isnull()]
df_county.drop("@countyid", axis=1, inplace=True)
df_county.rename(columns={"total_delay": "delay"}, inplace=True)
df_county["aggregation"] = "county"

results_df = pd.concat([df_rg, df_rgc, df_county])
results_df.to_csv(r"outputs/network/network_results_geog.csv")
