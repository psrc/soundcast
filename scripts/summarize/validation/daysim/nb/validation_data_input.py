import pandas as pd
# from shapely import wkt
from sqlalchemy import create_engine, text
import urllib
import pyodbc


def load_elmer_table(table_name, sql=None):
    conn_string = "DRIVER={ODBC Driver 17 for SQL Server}; SERVER=SQLserver; DATABASE=Elmer; trusted_connection=yes"
    sql_conn = pyodbc.connect(conn_string)
    params = urllib.parse.quote_plus(conn_string)
    engine = create_engine("mssql+pyodbc:///?odbc_connect=%s" % params)

    if sql is None:
        sql = "SELECT * FROM " + table_name

    # df = pd.DataFrame(engine.connect().execute(text(sql)))
    with engine.begin() as connection:
        result = connection.execute(text(sql))
        df = pd.DataFrame(result.fetchall())
        df.columns = result.keys()

    return df
