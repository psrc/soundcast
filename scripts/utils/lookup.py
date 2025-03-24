# Take median age
age_map = {
    1: 2,
    2: 8,
    3: 14,
    4: 17,
    5: 21,
    6: 30,
    7: 40,
    8: 50,
    9: 60,
    10: 70,
    11: 80,
    12: 85,
}

gender_map = {
    1: 1,  # male: male
    2: 2,  # female: female
    3: 9,  # another: missing
    4: 9,  # prefer not to answer: missing
}

pstyp_map = {1: 0, 2: 1, 3: 2}

hownrent_map = {1: 1, 2: 2, 3: 3, 4: 3, 4: 3}

mode_dict = {
    "Walk": 1,
    "Bike": 2,
    "SOV": 3,
    "HOV2": 4,
    "HOV3+": 5,
    "Transit": 6,
    "School_Bus": 8,
    "TNC": 9,  # Note that 9 was other in older Daysim records
    "Other": 10,
}

commute_mode_dict = {
    1: 3,  # SOV
    2: 4,  # HOV (2 or 3)
    3: 4,  # HOV (2 or 3)
    4: 3,  # Motorcycle, assume drive alone
    5: 5,  # vanpool, assume HOV3+
    6: 2,  # bike
    7: 1,  # walk
    8: 6,  # bus -> transit
    9: 10,  # private bus -> other
    10: 10,  # paratransit -> other
    11: 6,  # commuter rail
    12: 6,  # urban rail
    13: 6,  # streetcar
    14: 6,  # ferry
    15: 10,  # taxi -> other
    16: 9,  # TNC
    17: 10,  # plane -> other
    97: 10,  # other
}

day_map = {"Monday": 1, "Tuesday": 2, "Wednesday": 3, "Thursday": 4}

purpose_map = {
    1: 0,  # home
    6: 2,  # school
    9: 3,  # escort
    10: 1,  # work
    11: 1,  # work-related
    14: 1,  # work-related
    30: 5,  # grocery -> shop
    32: 5,  # other shopping -> shop
    33: 4,  # personal business
    34: 4,  # medical is combined with personal business (4)
    50: 6,  # restaurant -> meal
    51: 7,  # recreational is combined with social (7)
    52: 7,  # socail
    53: 7,  # recreational is combined with social (7)
    54: 7,  # religious/community/volunteer -> social
    56: 7,  # family activity -> social
    60: 10,  # change mode
    61: 4,  # personal business
    62: 7,  # other social
    97: -1,  # other, should we exclude these or assume a purpose?
}

dorp_map = {1: 1, 2: 2, 3: 9}

# Household

hownrent_map = {
    1: 1,  # Own: own
    2: 2,  # Rent: rent
    3: 3,  # provided by job/military: other
    4: 3,  # other: other
    5: 3,
}  # prefer not to answer: other

hhrestype_map = {
    1: 1,  # SFH: SFH
    2: 2,  # Townhouse (attached house): duplex/triplex/rowhouse
    3: 2,  # Building with 3 or fewer apartments/condos: duplex/triplex/rowhouse
    4: 3,  # Building with 4 or more apartments/condos: apartment/condo
    5: 4,  # Mobile home/trailer: Mobile home/trailer
    6: 5,  # Dorm or institutional housing: Dorm room/rented room
    7: 6,  # other: other
}

# Use the midpoint of the ranges provided since DaySim uses actual values
income_map = {
    1: 5000,
    2: 17500,
    3: 30000,
    4: 42500,
    5: 62500,
    6: 87500,
    7: 125000,
    8: 175000,
    9: 225000,
    10: 250000,
    11: -1,
}
