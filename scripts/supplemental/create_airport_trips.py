import pandas as pd
import numpy as np
import os,sys
import h5py
from sqlalchemy import create_engine
sys.path.append(os.path.join(os.getcwd(),"scripts"))
sys.path.append(os.getcwd())
from emme_configuration import *
from EmmeProject import *

def load_skims(skim_file_loc, table, divide_by_100=False):
    ''' Load H5 skim matrix for specified mode table and time period.
        Allow format conversion from scaled integer to float.'''
    
    with h5py.File(skim_file_loc, "r") as f:
        skim_file = f['Skims'][table][:]

    if divide_by_100:
        return skim_file.astype(float)/100.0
    else:
        return skim_file

def load_skim_data():
    """Load cost, time, and distance skim data required for mode choice models. """
    skim_dict = {}

    # Skim for cost, time, and distance for all auto modes
    for skim_type in ['cost', 'time', 'distance']:
        skim_dict[skim_type] = {}
        for mode in ['sov', 'hov2', 'hov3']:
            # For auto skims, use the average of AM and PM peak periods
            skim_name = mode+'_inc2'+skim_type[0]
            am_skim = load_skims(r'inputs\model\roster\7to8.h5', 
                    table=skim_name, divide_by_100=True)
            pm_skim = load_skims(r'inputs\model\roster\17to18.h5', 
                    table=skim_name, divide_by_100=True)
            skim_dict[skim_type][mode] = (am_skim + pm_skim) * .5

        # Get walk time skims
        if skim_type == 'time':
            for mode in ['walk', 'bike']:
                skim_dict['time'][mode] = load_skims(r'inputs\model\roster\5to6.h5', table=mode+'t', divide_by_100=True)

    # Skim for transit
    skim_list = ['ivtw','iwtw','ndbw','xfrw','auxw']
    fare_list = ['mfafarps']
    submode_list = ['a','r','c','p','f']
    skim_dict['transit'] = {}

    for skim in skim_list:
        for submode in submode_list:
            skim_name = skim+submode
            am_skim = load_skims(r'inputs\model\roster\7to8.h5', table=skim_name, 
                             divide_by_100=True) 
            pm_skim = load_skims(r'inputs\model\roster\17to18.h5', table=skim_name, 
                             divide_by_100=True)
            skim_dict['transit'][skim_name] = (am_skim + pm_skim) *.5
    for skim in fare_list:
        skim_dict['transit'][skim] = load_skims(r'inputs\model\roster\6to7.h5', table=skim, divide_by_100=True)

    return skim_dict

def calculate_auto_cost(trip_purpose, skim_dict, parking_cost_array, parameters_df):

    auto_cost_dict = {}

    # Auto operating cost is assumed same across auto modes (SOV, HOV2, HOV3+)
    auto_op_cost = parameters_df[(parameters_df['purpose'] == trip_purpose) & (parameters_df['variable'] == 'autoop')]['value'].values[0]

    occupancy_factor = {'sov': 1,
                        'hov2': 2,
                        'hov3': 3.5}

    for mode in ['sov','hov2','hov3']:
        auto_cost_dict[mode] = skim_dict['distance'][mode]*auto_op_cost + (skim_dict['cost'][mode])/occupancy_factor[mode]
                                                                  
    return auto_cost_dict

def calculate_mode_shares(trip_purpose, mode_utilities_dict):

    output_dict = {}

    # Calculate the sum of utility across all modes
    output_dict['util_sum'] = 0
    for mode in mode_utilities_dict.keys():
        output_dict['util_sum'] += mode_utilities_dict[mode]

    for mode in mode_utilities_dict.keys():
        output_dict[mode] = mode_utilities_dict[mode]/output_dict['util_sum']
        output_dict[mode][np.isnan(output_dict[mode])] = 0    # Set nan values equal to 0
    
    return output_dict


def destination_parking_costs(df, zone_lookup_dict):
    """Calculate average daily parking price per zone."""

    np_array = np.zeros(len(zone_lookup_dict))
    df = df[df.PPRICDYP > 0]
    df = df.groupby('TAZ_P').mean()[['PPRICDYP']].reset_index()
    df['zone_index'] = df.TAZ_P.apply(lambda x: zone_lookup_dict[x])
    np_array[df.zone_index] = df['PPRICDYP']

    return np_array

def get_param(df, variable):
    """Return model parameter from df. """

    return df.loc[df['variable'] == variable, 'value'].values[0]

def clip_matrix(matrix, min_index, max_index):
    """ Fill matrix with zero values outside of prescribed bounds """

    trimmed_matrix = np.zeros_like(matrix)
    trimmed_matrix[min_index:max_index] = matrix[min_index:max_index]
                               
    return trimmed_matrix

def calculate_mode_utilties(trip_purpose, skim_dict, auto_cost_dict, params_df, zone_lookup_dict):

    utility_matrices = {}
    
    # Filter parameters for given trip purpose
    params_df = params_df[params_df['purpose'] == trip_purpose]

    asc_dict = {'sov': 0,    # SOV is the reference mode so ASC=0
                'hov2': 'asccs2',
                'hov3': 'asccs3',
                'transit': 'ascctw',
                'walk': 'asccwk',
                'bike': 'asccbk'}

    submode_dict = {'a': 'trnst',
                    'r': 'litrat',
                    'c': 'commuter_rail',
                    'f': 'ferry',
                    'p': 'passenger_ferry'}

    # Calcualte utility for all modes
    
    for mode in ['sov','hov2','hov3','walk','bike']:

        if mode != 'sov':
            asc = get_param(params_df, asc_dict[mode])
        else:
            asc = 0
        #utility_matrices[mode] = calculate_utility(mode, asc, skim_dict, auto_cost_dict)
        if mode not in ['walk','bike']:
            util = np.exp(asc + get_param(params_df, 'autivt') * skim_dict['time'][mode] +\
            get_param(params_df, 'autcos') * auto_cost_dict[mode])
        else:
            util = np.exp(asc + get_param(params_df, mode+'tm') * skim_dict['time'][mode])
        utility_matrices[mode] = clip_matrix(util, 0, zone_lookup_dict[LOW_PNR])

    # Calculate Walk to Transit Utility for all submodes
    # Keep only the best
    
    for submode, matrix_name in submode_dict.items():
        utility_matrices[matrix_name] = np.exp(get_param(params_df, 'ascctw') + \
        get_param(params_df, 'trwivt') * skim_dict['transit']['ivtw'+submode] + \
        get_param(params_df, 'trwovt') * (skim_dict['transit']['auxwa'] + \
        skim_dict['transit']['iwtw'+submode] + \
        skim_dict['transit']['xfrw'+submode]) + \
        get_param(params_df, 'trwcos') * skim_dict['transit']['mfafarps'])


    for submode1 in submode_dict.values():
        for submode2 in submode_dict.values():
            if submode2 != submode1:
                utility_matrices[submode2][utility_matrices[submode1] >= utility_matrices[submode2]] = 0
                utility_matrices[submode1][utility_matrices[submode2] == utility_matrices[submode1]] = 0


    return utility_matrices
        
def mode_choice_to_h5(trip_purpose, mode_shares_dict, output_dir):

    my_store = h5py.File(output_dir + '/mode_shares.h5', "w")
    grp = my_store.create_group(trip_purpose)
    for mode in mode_shares_dict.keys():
        grp.create_dataset(mode, data = mode_shares_dict[mode])
        print(mode)
    my_store.close()

def build_df(h5file, h5table, cols):
    ''' Convert H5 into dataframe '''
    data = {}
    for col in cols:
        data[col] = [i for i in h5file[h5table][col][:]]

    return pd.DataFrame(data)

def calculate_trips(daysim, parcel, control_total):
    """Calculate total daily trips to Sea-Tac based on houeshold size and employment. 
       Trips to the airport are estimated using the following formula, based on surveys 
       from New Jersey and North Carolina, and as applied in Minneapolis 
       (via research by Fehr and Peers and Stantec):
        - Airport Trip Ends HBO (production zone) = 0.02112 * population
-       - Airport Trip Ends WBO (production zone) = 0.01486 * employment

       A control total is applied to these rates that represent observed trips to Sea-Tac and forecasted trips.
    """

    airport_trip_rate_pop = 0.02112
    airport_trip_rate_emp = 0.01486
    # Zonal Population
    cols = ['hhno','hhsize','hhtaz','hhexpfac']
    daysim_df = build_df(h5file=daysim, h5table='Household', cols=cols)
    taz_df = pd.DataFrame(daysim_df.groupby('hhtaz').sum()['hhsize']).reset_index()
    taz_df.rename(columns={'hhtaz': 'TAZ'}, inplace=True)
    # Multiply zonal population by the trip rate
    taz_df['airport_trips_pop'] = taz_df['hhsize']*airport_trip_rate_pop

    # Zonal Employment (total minus education jobs)
    parcel['emptot_minus_edu'] = parcel['EMPTOT_P'] - parcel['EMPEDU_P']
    parcel['airport_trips_emp'] = parcel['emptot_minus_edu']*airport_trip_rate_emp
    parcel_df = parcel.groupby('TAZ_P').sum()[['airport_trips_emp']].reset_index()
    parcel_df.rename(columns={'TAZ_P': 'TAZ'}, inplace=True)
    
    trips = parcel_df.merge(taz_df, on='TAZ')
    trips['airport_trips'] = trips['airport_trips_pop'] + trips['airport_trips_emp']

    # Adjust estimated trips by applying observed control total
    adj_factor = control_total/trips['airport_trips'].sum()
    trips['adj_trips'] = trips['airport_trips']*adj_factor
    trips = trips[['TAZ', 'adj_trips']]
    trips['SeaTac_Taz'] = SEATAC

    return trips


def create_demand_matrix(airport_trips, dict_zone_lookup):
       
    ## Create empty matrix to store results
    demand_matrix = np.zeros((len(dict_zone_lookup), len(dict_zone_lookup)), np.float16) 
    
    ##convert to matrix
    #for index, row in airport_trips.iterrows():
    #    demand = row['adj_trips']
    #    origin = dict_zone_lookup[row.TAZ]
    #    destination = SEATAC     # Standard zone defined in emme_configuration.py
    #    demand_matrix[origin, destination] = demand
    #    #
    #return demand_matrix

    #demand_matrix = np.zeros((org_zones, dest_zones), np.float16) #IndexError: index 3868 is out of bounds for axis 0 with size 3868
    
    #convert to matrix
    for rec in airport_trips.iterrows():
        demand = rec[1].adj_trips
        origin = dict_zone_lookup[rec[1].TAZ]
        destination = dict_zone_lookup[rec[1].SeaTac_Taz]
        demand_matrix[origin, destination] = demand

    return demand_matrix

def split_trips_into_modes(total_trips, mode_shares_dict):
    """Apply trips to modes using shares for HBO purpose"""

    table_dict = {}
    for mode in mode_shares_dict.keys():
        if mode != 'util_sum':
            mode_share = mode_shares_dict[mode][:]
            trips_by_mode = total_trips * mode_share
            # Convert person trips to vehicle trips
            if mode == 'hov2':
                trips_by_mode  = trips_by_mode/2.0
            if mode == 'hov3':
                trips_by_mode = trips_by_mode/3.5    # Assume HOV3+ occupancy of 3.5

            table_dict[mode] = trips_by_mode 

    return table_dict

def split_tod_internal(total_trips_by_mode, tod_factors_df):
    """Split trips into time of a day: apply time of the day factors to internal trips"""

    matrix_dict = {}
    #for tod, dict in test.iteritems():
    for tod in tod_factors_df.time_of_day.unique():
        #open work externals:
        tod_dict = {}
        tod_df = tod_factors_df[tod_factors_df['time_of_day'] == tod]

        ixxi_work_store = h5py.File('outputs/supplemental/external_work_' + tod + '.h5', 'r')

        # Time of day distributions to use foreach mode
        tod_dict = {'sov': 'sov',
                    'hov2': 'hov',
                    'hov3': 'hov',
                    'walk': 'sov',
                    'bike': 'sov',
                    'trnst': 'trnst',
                    'litrat': 'litrat',
                    'commuter_rail': 'commuter_rail',
                    'ferry': 'ferry',
                    'passenger_ferry': 'passenger_ferry'}

        for mode, tod_type in tod_dict.items():
            if mode in ['sov','hov2','hov3']:
                tod_dict[mode] = np.array(total_trips_by_mode[mode])*tod_df[tod_df['mode'] == tod_type]['value'].values[0] + np.array(ixxi_work_store[mode])
            else:
                tod_dict[mode] = np.array(total_trips_by_mode[mode]) * tod_df[tod_df['mode'] == 'transit']['value'].values[0] 

        ixxi_work_store.close()
        matrix_dict[tod] = tod_dict

    return matrix_dict

# Output trips
def output_trips(path, matrix_dict):
    for tod in matrix_dict.keys():
        print("Exporting supplemental trips for time period: " + str(tod))
        my_store = h5py.File(path + str(tod) + '.h5', "w")
        for mode, value in matrix_dict[tod].items():
            if mode in ['sov','hov2','hov3']:
                mode = mode + '_inc2'
            my_store.create_dataset(str(mode), data=value, compression='gzip')
        my_store.close()

def summarize(mode_shares_dict, airport_trips_by_mode, total_trips_by_mode, airport_matrix_dict,  output_dir):
    df_shares = pd.DataFrame()
    df_airport = pd.DataFrame(index=list(mode_shares_dict.keys()))
    df_total= pd.DataFrame(index=list(mode_shares_dict.keys()))
    for mode in mode_shares_dict.keys():
        if mode != 'util_sum':
            df_shares[mode]= mode_shares_dict[mode].mean(axis=0)
            df_airport.loc[mode,'total'] = airport_trips_by_mode[mode].sum().sum()
            df_total.loc[mode,'total'] = total_trips_by_mode[mode].sum().sum()
    df_shares.to_csv(os.path.join(output_dir,'avg_mode_shares_origins.csv'))
    # Total trips by mode adjusted for average vehicle occupancy (HOV2/2, HOV3/3.5)
    df_airport.to_csv(os.path.join(output_dir,'airport_veh_trips.csv'))  
    # Total trips by mode, including externals
    df_total.to_csv(os.path.join(output_dir,'airport_veh_trips_with_externals.csv'))  
    
    # Total Airport Trips by mode and time of day (internal and external zones)
    df = pd.DataFrame()
    for tod in airport_matrix_dict.keys():
        _df = pd.DataFrame(index=list(airport_matrix_dict[tod].keys()))
        _df['tod'] = tod
        for mode in airport_matrix_dict[tod].keys():
            total = airport_matrix_dict[tod][mode].sum().sum()
            _df.loc[mode,'total'] = total
        df = df.append(_df)
    df.to_csv(os.path.join(output_dir,'airport_veh_trips_by_tod.csv'))

def main():

    output_dir = r'outputs/supplemental/'

    my_project = EmmeProject(r'projects/Supplementals/Supplementals.emp')
    zones = my_project.current_scenario.zone_numbers
    zonesDim = len(my_project.current_scenario.zone_numbers)

    parcel = pd.read_csv('inputs/scenario/landuse/parcels_urbansim.txt', delim_whitespace=True)

    #Create a dictionary lookup where key is the taz id and value is it's numpy index. 
    zone_lookup_dict = dict((value,index) for index,value in enumerate(zones))

    conn = create_engine('sqlite:///inputs/db/soundcast_inputs.db')
    parameters_df = pd.read_sql('SELECT * FROM mode_choice_parameters', con=conn)
    #FIXME:  Document source of TOD factors; consider calculating these from last iteration of soundcast via daysim outputs?
    tod_factors_df = pd.read_sql('SELECT * FROM time_of_day_factors', con=conn)

    # Calculate mode shares for Home-Based Other purposes 
    # Work trips from externals are grown from observed data
    trip_purpose = 'hbo'

    skim_dict = load_skim_data()
    # Calculate average TAZ parking costs for utility calculations
    parking_costs = destination_parking_costs(parcel, zone_lookup_dict)

    # Calculate auto costs from parking, operating, and cost skims
    auto_cost_dict = calculate_auto_cost(trip_purpose, skim_dict, parking_costs, parameters_df)
    mode_utilities_dict = calculate_mode_utilties(trip_purpose, skim_dict, auto_cost_dict, parameters_df, zone_lookup_dict)
    mode_shares_dict = calculate_mode_shares(trip_purpose, mode_utilities_dict)
    mode_choice_to_h5(trip_purpose, mode_shares_dict, output_dir)

    # Create airport trip tables
    daysim = h5py.File('inputs/scenario/landuse/hh_and_persons.h5','r+')

    # Calculate total trips by TAZ to Seattle-Tacoma International Airport from internal zones
    airport_control_total = pd.read_sql('SELECT * FROM seatac WHERE year=='+str(model_year), con=conn)['enplanements'].values[0]
    airport_trips = calculate_trips(daysim, parcel, airport_control_total)
    demand_matrix = np.zeros((len(zone_lookup_dict), len(zone_lookup_dict)), np.float64)
    origin_index = [zone_lookup_dict[i] for i in airport_trips['TAZ'].values]
    destination_index = zone_lookup_dict[SEATAC]
    demand_matrix[origin_index,destination_index] = airport_trips['adj_trips'].values
    # Account for both directions of travel (from/to airport) by transposing the productions matrix
    trips_to_airport = demand_matrix/2
    trips_from_airport = trips_to_airport.transpose()
    airport_trips = trips_to_airport + trips_from_airport

    # Split trips by TAZ into separate modes based on shares computed above for internal zones
    airport_trips_by_mode = split_trips_into_modes(airport_trips, mode_shares_dict)

    # Add airport trips to external trip table for auto modes:
    ixxi_non_work_store = h5py.File('outputs/supplemental/external_non_work.h5', 'r')
    external_modes = ['sov', 'hov2', 'hov3']
    ext_trip_table_dict = {}
    ext_tod_dict = {}
    # get non-work external trips
    for mode in external_modes:
        ext_trip_table_dict[mode] = np.nan_to_num(np.array(ixxi_non_work_store[mode]))

    # Add external non-work trips to airport trips
    # Export as income class 
    total_trips_by_mode = airport_trips_by_mode.copy()
    total_trips_by_mode['sov'] = airport_trips_by_mode['sov'] + ext_trip_table_dict['sov']
    total_trips_by_mode['hov2'] = airport_trips_by_mode['hov2'] + ext_trip_table_dict['hov2']
    total_trips_by_mode['hov3'] = airport_trips_by_mode['hov3'] + ext_trip_table_dict['hov3']

    # Apply time of day factors
    airport_matrix_dict = split_tod_internal(total_trips_by_mode, tod_factors_df)

    summarize(mode_shares_dict, airport_trips_by_mode, total_trips_by_mode, airport_matrix_dict, output_dir)

    # Output final trip tables, by time of the day and trip mode. 
    output_trips(output_dir, airport_matrix_dict)


if __name__ == "__main__":
    main()