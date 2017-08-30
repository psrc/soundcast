import argparse
import tables
import re
import json
import itertools
import numpy as np
import pandas as pd
import collections



def read_zz_components(config):
    """Returns a generator that returns a dictionary of each zone-to-zone
    benefit component.

    """

    # Grumble, grumble, Python 2.6 and stupid nested context managers
    # Too lazy to wrap this with 'with' until Py27
    base = tables.open_file(config["baseline"]["filepath"])
    alt = tables.open_file(config["alternative"]["filepath"])

    # Benefits by Period:
    for per in config["timeperiods"]["periods"]:
        period = per["period"]
        code = per["code"]
        trperiod = per["trperiod"]
        trcode = per["trcode"]
        assignper = per["assignper"]
        fareper = per["fareper"]
        distper = per["distper"]
        walkper = per["walkper"]
        bikeper = per["bikeper"]


        for zzben in config["benefits-by-period"]:
            cp = zzben["costpath"]
            vp = zzben["volumepath"]

            # Substitute various time period placeholders
            cp = cp.replace("${PER}",period)
            cp = cp.replace("${CODE}",code)
            cp = cp.replace("${TRPER}",trperiod)
            cp = cp.replace("${TRCODE}",trcode)
            cp = cp.replace("${ASSIGNPER}",assignper)
            cp = cp.replace("${FAREPER}",fareper)
            cp = cp.replace("${DISTPER}",distper)
            cp = cp.replace("${WALKPER}",walkper)
            cp = cp.replace("${BIKEPER}",bikeper)

            vp = vp.replace("${PER}",period)
            vp = vp.replace("${CODE}",code)
            vp = vp.replace("${TRPER}",trperiod)
            vp = vp.replace("${TRCODE}",trcode)
            vp = vp.replace("${ASSIGNPER}",assignper)
            vp = vp.replace("${FAREPER}",fareper)
            vp = vp.replace("${DISTPER}",distper)
            vp = vp.replace("${WALKPER}",walkper)
            vp = vp.replace("${BIKEPER}",bikeper)

            zzben["basecost"] = base.get_node(cp).read()
            zzben["basevol"] = base.get_node(vp).read()
            zzben["altcost"] = alt.get_node(cp).read()
            zzben["altvol"] = alt.get_node(vp).read()
            zzben["timeperiod"] = period

            if "description" not in zzben.keys():
                zzben["description"] = "%s %s" % (zzben["timeperiod"],
                                                  zzben["userclass"])
            else:
                pass

            yield zzben

    base.close()
    alt.close()


def calc_zz_benefit(zzben, config):
    """Calculate consumer surplus benefits based on costs and volumes of
    two scenarios. Takes a benefit component dictionary containing
    cost and volume arrays of both scenarios, as returned by
    read_zz_components(). Returns the calculated benefit as an array.

    """
    max_zone = config["max_zone_id"]
    
    bc = zzben["basecost"]
    bc = bc[0:max_zone, 0:max_zone]

    bv = zzben["basevol"]
    bv = bv[0:max_zone, 0:max_zone]
    
    ac = zzben["altcost"]
    ac = ac[0:max_zone, 0:max_zone]

    av = zzben["altvol"]
    av = av[0:max_zone, 0:max_zone]

    # this can happen if there is no transit service between an od pair
    if (bc>1000000).any() or (ac>1000000).any():
        print "There is no transit service between an o-d pair, you may want to check your network."

    bc[bc>1000000] = 0
    ac[ac>1000000] = 0
    rawben = (bc - ac) * ((bv + av) / 2)


    return rawben



def calc_zz_benefits(zzbens, config):
    """Returns a generator that returns a dictionary containing the
    calculated raw benefit for each benefit component.

    """
    for zzben in zzbens:
        rawben = calc_zz_benefit(zzben, config)
        zzben["rawben"] = rawben
        yield zzben

def calc_zz_dollar_benefits(zzbens, config):
    """Returns a generator that returns a dictionary containing calculated
    benefit (in dollars) for each benefit component. Takes a list of
    zone-to-zone benefit dictionaries and a dictionary containing the
    appropriate unit conversions.

    """

    for zzben in zzbens:
        dollarben = to_dollars(zzben, config)
        zzben["dollarben"] = dollarben
        yield zzben

def to_dollars(ben, config):
    """Converts raw benefits of a given unit type to dollars. Takes a
    benefit dictionary containing the raw benefit, and returns a
    dictionary with the dollar benefits array calculated. Should work
    for all benefit types.

    """

    userclass = ben["userclass"]
    timeperiod = ben["timeperiod"]
    benarray = ben["rawben"]

    try:
        units = ben["costunits"]
    except:
        units = "minutes"
    #print 'raw benefits '
    #print benarray[1:5, 1:5]
    if units == "minutes":
        conv = config["vot"][userclass][timeperiod] / 60.0
    elif units == "cents":
        conv = 0.01
    elif units == "dollars":
        conv = 1.0 # could simply return, but this is more an example
    elif units == "distance":
         conv = config['operating cost'][userclass]
    else:
        raise ValueError(units + " is not a valid unit type")

    converted_ben_array = benarray*conv

    return converted_ben_array


def all_dollar_benefits(config):
    zzdollars = calc_zz_dollar_benefits(calc_zz_benefits(read_zz_components(config), config), config)
    allbens = itertools.chain(zzdollars)

    return(allbens)


def write_benefits(outputpath, benefits, benefittype="dollarben"):
    benefit_dict = {}
    first_ben = True

    for benefit in benefits:
                print 'calculating benefit for'
                print benefit['userclass']
                print benefit['timeperiod']
                bgroup = str(benefit['reportgroup'])
                barray = benefit[benefittype]
                base_trips = benefit['basevol']
                scen_trips = benefit['altvol']
                #hard codes
                base_trips =base_trips[0:3700, 0:3700]
                scen_trips =scen_trips[0:3700, 0:3700]
                trips = (base_trips+scen_trips)/2

                orig_ben_array = np.sum(barray, axis =1)
                dest_ben_array = np.sum(barray, axis =0)
                avg_ben = (orig_ben_array + dest_ben_array)/2

                orig_trip_array = np.sum(trips, axis =1)
                dest_trip_array = np.sum(trips, axis =0)
                avg_trip = (orig_trip_array + dest_trip_array)/2

                if bgroup in benefit_dict.keys():
                   benefit_dict[bgroup] += avg_ben
                   benefit_dict[bgroup+'_trip']+= avg_trip

                else:
                   benefit_dict[bgroup] = avg_ben
                   benefit_dict[bgroup+'_trip'] = avg_trip

    ben_df = pd.DataFrame(benefit_dict)
    ben_df.to_csv(outputpath)


if __name__ == '__main__':

    with open('scripts/summarize/benefit_cost/benefit_configuration.json') as config_file:
      config = json.load(config_file)

    bens = all_dollar_benefits(config)

    write_benefits(config["outputpath"], bens)