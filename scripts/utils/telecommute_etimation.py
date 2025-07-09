import pandas as pd
import re
from pathlib import Path
import numpy as np

# import pyodbc
import statsmodels.formula.api as smf

# conn_string = "DRIVER={ODBC Driver 17 for SQL Server}; SERVER=AWS-PROD-SQL\Sockeye; DATABASE=Elmer; trusted_connection=yes"
# sql_conn = pyodbc.connect(conn_string)
# df_days = pd.read_sql(sql='select * from HHSurvey.days_2017_2019', con=sql_conn)
hours_telecommuting_threshold = 2.5
survey_path = Path(
    "R:/e2projects_two/SoundCast/Inputs\dev/base_year/2018/survey/RSG_version"
)

person_day = pd.read_csv(survey_path / "_person_day.tsv", sep="\t")
person = pd.read_csv(survey_path / "_person.tsv", sep="\t")
household = pd.read_csv(survey_path / "_household.tsv", sep="\t")

parcels = pd.read_csv(
    r"R:\e2projects_two\SoundCast\Inputs\dev\landuse\2018\v3_RTP\parcels_urbansim.txt",
    sep=" ",
)

# test = df_days[['household_id', 'person_id']]
# test.merge(household, how='left', left_on='household_id', right_on='hhno')

# def create_person_id(df):
#     df['person_id'] = df['hhno'].astype(str) + '_' + df['pno'].astype(str)
#     return df


person_day["person_id"] = (
    person_day["hhno"].astype(str) + "_" + person_day["pno"].astype(str)
)
person["person_id"] = person["hhno"].astype(str) + "_" + person["pno"].astype(str)
# df_days['person_id'] = df_days['hhid'].astype(str) + '_' + df_days['pernum'].astype(str)

# df_days['telework_time_num'] = df_days['telework_time'].apply(transform_telework_time)


person_day = person_day.merge(household, how="left", left_on="hhno", right_on="hhno")
person_day = person_day.merge(
    person, how="left", left_on="person_id", right_on="person_id"
)

commuters = person_day[person_day["pwpcl"] > 0]
commuters = commuters[commuters["pwtyp"] > 0]
commuters = commuters[commuters["pwpcl"] != commuters["hhparcel"]]
commuters = commuters.merge(parcels, how="left", left_on="pwpcl", right_on="parcelid")
# commuters['wkathome']

# test = person[person['id'].isin(df_days['personid'])]
# commuters = commuters.merge(df_days, left_on=['person_id', 'day'], right_on=['person_id', 'daynum'])
commuters["wkathome"] = np.where(
    commuters["wkathome"] >= hours_telecommuting_threshold, 1, 0
)

# independent variables
commuters["part_time_worker"] = np.where(commuters["pwtyp"] == 2, 1, 0)
commuters["missing_income"] = np.where(commuters["hhincome"] == -1, 1, 0)
commuters["income_0_50"] = np.where(commuters["hhincome"] < 50000, 1, 0)
commuters["income_50plus"] = np.where(
    commuters["hhincome"] >= 50000, 1, 0
)  # not used in estimation
commuters["income_150plus"] = np.where(commuters["hhincome"] > 150000, 1, 0)


commuters["children"] = commuters["hhhsc"] + commuters["hh515"] + commuters["hhcu5"]
commuters["children_plus_nwa"] = np.where(
    (commuters["children"] > 0) & (commuters["hhoad"] > 0), 1, 0
)
commuters["no_vehicles"] = np.where(commuters["hhvehs"] < 1, 1, 0)


commuters["fraction_medical_jobs"] = commuters["empmed_p"] / commuters["emptot_p"]
commuters["fraction_other_jobs"] = commuters["empoth_p"] / commuters["emptot_p"]


commuters["fraction_industrial_jobs"] = commuters["empind_p"] / commuters["emptot_p"]
commuters["frac_industrial_inc_0_50"] = (
    commuters["fraction_industrial_jobs"] * commuters["income_0_50"]
)
commuters["frac_industrial_inc_50plus"] = (
    commuters["fraction_industrial_jobs"] * commuters["income_50plus"]
)

commuters["fraction_office_jobs"] = commuters["empofc_p"] / commuters["emptot_p"]
commuters["frac_office_inc_0_50"] = (
    commuters["fraction_office_jobs"] * commuters["income_0_50"]
)
commuters["frac_office_inc_50plus"] = (
    commuters["fraction_office_jobs"] * commuters["income_50plus"]
)

commuters["fraction_gov_jobs"] = commuters["empgov_p"] / commuters["emptot_p"]
commuters["frac_gov_inc_0_50"] = (
    commuters["fraction_gov_jobs"] * commuters["income_0_50"]
)
commuters["frac_gov_inc_50plus"] = (
    commuters["fraction_gov_jobs"] * commuters["income_50plus"]
)

commuters["fraction_retail_jobs"] = (
    commuters["empret_p"] + commuters["empfoo_p"]
) / commuters["emptot_p"]
commuters["frac_retail_inc_0_50"] = (
    commuters["fraction_retail_jobs"] * commuters["income_0_50"]
)
commuters["frac_retail_inc_50plus"] = (
    commuters["fraction_retail_jobs"] * commuters["income_50plus"]
)

commuters["log_income"] = np.where(commuters["hhincome"] < 0, 0, commuters["hhincome"])
commuters["log_income"] = np.log1p(commuters["log_income"])


# log_reg = smf.logit("wkathome ~ hhincome + ptpass + pgend + pagey", data=commuters).fit()
# log_reg = smf.logit("wkathome ~ pwautime + part_time_worker + missing_income + income_0_50 + income_150plus + children_plus_nwa + no_vehicles + fraction_medical_jobs + fraction_other_jobs + frac_industrial_inc_0_50 + frac_industrial_inc_50plus + frac_office_inc_0_50 + frac_office_inc_50plus + frac_gov_inc_0_50 + frac_gov_inc_50plus + frac_retail_inc_0_50 + frac_retail_inc_50plus", data=commuters).fit()
log_reg = smf.logit(
    "wkathome ~  pwautime + part_time_worker + missing_income + income_0_50 + income_150plus + no_vehicles + fraction_medical_jobs + fraction_other_jobs + frac_industrial_inc_0_50 + frac_industrial_inc_50plus + frac_office_inc_0_50 + frac_office_inc_50plus + frac_gov_inc_0_50 + frac_gov_inc_50plus + frac_retail_inc_0_50 + frac_retail_inc_50plus",
    data=commuters,
).fit()
# log_reg = smf.logit("wkathome ~ pwautime + part_time_worker + missing_income + log_income + no_vehicles + fraction_medical_jobs + fraction_other_jobs + frac_industrial_inc_0_50 + frac_industrial_inc_50plus + frac_office_inc_0_50 + frac_office_inc_50plus + frac_gov_inc_0_50 + frac_gov_inc_50plus + frac_retail_inc_0_50 + frac_retail_inc_50plus", data=commuters).fit()
log_reg.summary()


print("done")
