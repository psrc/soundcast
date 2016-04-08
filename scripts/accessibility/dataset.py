import pandas as pd
#import assumptions
import urbansim_default_utils
import urbansim.sim.simulation as sim

import warnings
warnings.filterwarnings('ignore', category=pd.io.pytables.PerformanceWarning)


@sim.table('parcels', cache=True)
def parcels(store):
    df = store['parcels']
    return df

@sim.table('buildings', cache=True)
def buildings(store):
    df = store['buildings']
    return df

@sim.table('households', cache=True)
def households(store):
    df = store['households']
    return df

@sim.table('jobs', cache=True)
def jobs(store):
    df = store['jobs']
    return df

@sim.table('persons', cache=True)
def persons(store):
    df = store['persons']
    return df

@sim.table('zones', cache=True)
def zones(store):
    df = store['zones']
    return df

@sim.table('fazes', cache=True)
def fazes(store):
    df = store['fazes']
    return df

@sim.table('tractcity', cache=True)
def tractcity(store):
    df = store['tractcity']
    return df

sim.broadcast('parcels', 'buildings', cast_index=True, onto_on='parcel_id')
sim.broadcast('buildings', 'households', cast_index=True, onto_on='building_id')
sim.broadcast('buildings', 'jobs', cast_index=True, onto_on='building_id')
sim.broadcast('zones', 'parcels', cast_index=True, onto_on='zone_id')
sim.broadcast('households', 'persons', cast_index=True, onto_on='household_id')
sim.broadcast('jobs', 'households', cast_index=True, onto_on='job_id')
sim.broadcast('fazes', 'zones', cast_index=True, onto_on='faz_id')
sim.broadcast('tractcity', 'parcels', cast_index=True, onto_on='tractcity_id')