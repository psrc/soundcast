# Read in Configuration Hard Code for now
output_name = 'TransFu2010'

pollutant_file = 'scripts/summarize/inputs/benefit_cost/pollutant_rates.csv'
injury_file ='scripts/summarize/inputs/benefit_cost/injury_rates.csv'

#truck_file =somewhere

HOUSEHOLD_VOT = 25
TRUCK_VOT = 50
MINS_HR= 60
CENTS_DOLLAR = 100

LOW_INC_MAX = 25000
MAX_INC = 10000000000

HRS_PARKED_AVG = 2
PAID_UNPAID_PARK_RATIO = 0.5
FOUR_PLUS_CAR_AVG = 4.3
ANNUALIZATION = 300
ANNUAL_OWNERSHIP_COST = 6290

# Passenger car equivalent factors
HV_TRUCK_FACTOR = 2
MED_TRUCK_FACTOR = 1.5

# The emissions and safety rates are per 1 million VMT
EMISSIONS_FACTOR = 1000000
SAFETY_FACTOR = 1000000
# Cost per ton of emissions
CO2_COST = 55.34
CO_COST = 380
NO_COST = 9800
VOC_COST = 7800
PM_COST = 6500
# Collision Costs
PROPERTYD_COST = 2600
INJURY_COST = 75500
FATALITY_COST = 2500000
# Noise Costs per VMT
CAR_NOISE_COST = 0.0012
TRUCK_NOISE_COST = 0.015

#Write the tables every report_row_gap number of rows apart
REPORT_ROW_GAP = 20

# Calibration Summary Configuration
h5_results_file = 'outputs/daysim_outputs.h5'
h5_results_name = 'DaysimOutputs'
h5_comparison_file = 'scripts/summarize/inputs/calibration/survey.h5'
h5_comparison_name = 'Survey'
guidefile = 'scripts/summarize/inputs/calibration/CatVarDict.xlsx'
districtfile = 'scripts/summarize/inputs/calibration/TAZ_TAD_County.csv'
report_output_location = 'outputs'
bc_outputs_file = 'outputs/BenefitCost.xlsx'