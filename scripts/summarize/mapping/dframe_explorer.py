# This script is adopted from 

from bottle import route, response, run, hook, static_file
from urbansim.utils import yamlio
import simplejson
import numpy as np
import pandas as pd
import os
from jinja2 import Environment

@hook('after_request')
def enable_cors():
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = \
        'Origin, Accept, Content-Type, X-Requested-With, X-CSRF-Token'

DFRAMES = {}
CONFIG = None


def get_schema():
    global DFRAMES
    return {name: list(DFRAMES[name].columns) for name in DFRAMES}


@route('/map_query/<table>/<compare>/<filter>/<groupby>/<field:path>/<agg>', method="GET")
def map_query(table, compare, filter, groupby, field, agg):
    global DFRAMES

    filter = ".query('%s')" % filter if filter != "empty" else ""

    df_main = DFRAMES['main']
    df_alt = DFRAMES['alternative']

    if compare=='Main vs. Alternative':
        print 'Showing base-alternative comparison'
        if field not in df_main.columns:
            print "Col not found, trying eval:", field
            df_main["eval"] = df_main.eval(field)
            field = "eval"

        cmd_base = "df_main%s.groupby('%s')['%s'].%s" % \
              (filter, groupby, field, agg)
        print cmd_base

        if field not in df_alt.columns:
            print "Col not found, trying eval:", field
            df_alt["eval"] = df_alt.eval(field)
            field = "eval"

        cmd_alt = "df_alt%s.groupby('%s')['%s'].%s" % \
              (filter, groupby, field, agg)

        base_results = eval(cmd_base)
        base_results[base_results == np.inf] = np.nan
        
        alt_results = eval(cmd_alt)
        alt_results[alt_results == np.inf] = np.nan

        # Percent change versus base, should be flexible in future
        results = (alt_results-base_results)/base_results
    else:
        print 'Showing primary results'
        if field not in df_main.columns:
            df_main["eval"] = df_main.eval(field)
            field = "eval"

        cmd_base = "df_main%s.groupby('%s')['%s'].%s" % \
              (filter, groupby, field, agg)
        results = eval(cmd_base)

    results = yamlio.series_to_yaml_safe(results.dropna())
    results = {int(k): results[k] for k in results}
    return results


@route('/map_query/<table>/<compare>/<filter>/<groupby>/<field>/<agg>', method="OPTIONS")
def ans_options(compare=False, table=None, filter=None, groupby=None, field=None, agg=None):
    return {}


@route('/')
def index():
    global CONFIG
    dir = os.path.dirname(__file__)
    index = open(os.path.join(dir, 'dframe_explorer.html')).read()
    # index = open('dframe_explorer.html').read()
    return Environment().from_string(index).render(CONFIG)

# # Original code
# @route('/data/<filename>')
# def data_static(filename):
#     return static_file(filename, root='./data')

# New code
@route('/inputs/<filename>')
def data_static(filename):
    return static_file(filename, root='./inputs')

def start(views,
          center=[37.7792, -122.2191],
          zoom=11,
          shape_json='inputs/taz2010.geojson',
          geom_name='ZONE_ID',  # from JSON file
          join_name='zone_id',  # from data frames
          precision=8,
          port=8765,
          host='0.0.0.0',
          testing=False):
    """
    Start the web service which serves the Pandas queries and generates the
    HTML for the map.  You will need to open a web browser and navigate to
    http://localhost:8765 (or the specified port)

    Parameters
    ----------
    views : Python dictionary
        This is the data that will be displayed in the maps.  Keys are strings
        (table names) and values are dataframes.  Each data frame should have a
        column with the name specified as join_name below
    center : a Python list with two floats
        The initial latitude and longitude of the center of the map
    zoom : int
        The initial zoom level of the map
    shape_json : str
        The path to the geojson file which contains that shapes that will be
        displayed
    geom_name : str
        The field name from the JSON file which contains the id of the geometry
    join_name : str
        The column name from the dataframes passed as views (must be in each
        view) which joins to geom_name in the shapes
    precision : int
        The precision of values to show in the legend on the map
    port : int
        The port for the web service to respond on
    host : str
        The hostname to run the web service from
    testing : bool
        Whether to print extra debug information

    Returns
    -------
    Does not return - takes over control of the thread and responds to
    queries from a web browser
    """

    global DFRAMES, CONFIG
    DFRAMES = {str(k): views[k] for k in views}

    config = {
        'center': str(center),
        'zoom': zoom,
        'shape_json': shape_json,
        'geom_name': geom_name,
        'join_name': join_name,
        'precision': precision,
        'port': port,
        'host': host
    }

    for k in views:
        if join_name not in views[k].columns:
            raise Exception("Join name must be present on all dataframes - "
                            "'%s' not present on '%s'" % (join_name, k))

    config['schema'] = simplejson.dumps(get_schema())

    CONFIG = config

    if testing:
        return

    run(host=host, port=port, debug=True)
