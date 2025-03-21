import pandas as pd


def parcel_summary():
    """
    Summarize parcels for quick check of totals and means
    """

    # Load parcels_urbansim input
    df = pd.read_csv(
        r"inputs/scenario/landuse/parcels_urbansim.txt", delim_whitespace=True
    )

    # Save results in flat text file
    results_df = pd.DataFrame()

    # Calculate totals for jobs by sector, households, students, and parking spaces
    cols = [
        "empedu_p",
        "empfoo_p",
        "empgov_p",
        "empind_p",
        "empmed_p",
        "empofc_p",
        "empoth_p",
        "empret_p",
        "emprsc_p",
        "empsvc_p",
        "emptot_p",
        "hh_p",
        "stugrd_p",
        "stuhgh_p",
        "stuuni_p",
        "parkdy_p",
        "parkhr_p",
    ]
    parking_cols = ["ppricdyp", "pprichrp"]

    # If lower case, convert to upper
    if "empedu_p" not in df.columns:
        cols = [i.upper() for i in cols]
        parking_cols = [i.upper() for i in parking_cols]

    _df = df[cols]
    # Append results to results_df
    results_df["value"] = _df.sum()
    results_df["field"] = results_df.index
    results_df.reset_index(inplace=True, drop=True)
    results_df["measure"] = "sum"

    # Calculate average parking price
    _df = pd.DataFrame(df[parking_cols].mean(), columns=["value"])
    _df["measure"] = "mean"
    _df["field"] = _df.index
    _df.reset_index(inplace=True, drop=True)
    results_df = results_df.append(_df)

    _df = pd.DataFrame(df[parking_cols].max(), columns=["value"])
    _df["measure"] = "max"
    _df["field"] = _df.index
    _df.reset_index(inplace=True, drop=True)
    results_df = results_df.append(_df)

    results_df.to_csv(r"outputs/landuse/parcels_urbansim_summary.txt", index=False)


if __name__ == "__main__":
    parcel_summary()
