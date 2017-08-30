import pandas as pd

agg_logsum_file = r'outputs\daysim\aggregate_logsums.1.dat'

logsums = pd.read_csv(agg_logsum_file, sep = '\t', skiprows=1, header=None)

auto_list = ['child', 'nocars', 'lsonecradult', 'onepluscarsperadult']
inc_list = ['low', 'med',  'high']
transit_list = ['lsqtmil', 'qtmitohalfmi', 'morehfmi']



logsums_columns = ['TAZ']

# the file has some junk in the columns after 29 so we can't use it
logsums.drop(logsums.columns[[29,30,31,32,33,34]], axis =1, inplace=True)

for auto in auto_list:
    for inc in inc_list:
        for transit in transit_list:
            if len(logsums_columns)<29:
              logsums_columns.append(auto + '_'+ inc + '_'+ transit)

logsums.columns = logsums_columns

# Use this logsum as the one:
#lsonecradult_med_qtmitohalfmi

accessibility_file = r'outputs\daysim\accessibility.csv'
accessibility = logsums.filter(['TAZ', 'lsonecradult_med_qtmitohalfmi'], axis=1)
accessibility.columns = ['TAZ', 'Accessibility']
accessibility.to_csv(accessibility_file, index = False)

