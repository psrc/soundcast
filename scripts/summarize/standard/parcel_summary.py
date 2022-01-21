import pandas as pd

def parcel_summary():
	"""
	Summarize parcels for quick check of totals and means
	"""

	# Load parcels_urbansim input
	df = pd.read_csv(r'inputs/scenario/landuse/parcels_urbansim.txt', delim_whitespace=True)

	# Save results in flat text file
	results_df = pd.DataFrame()

	# Calculate totals for jobs by sector, households, students, and parking spaces
	cols = [u'empedu_p', u'empfoo_p', u'empgov_p', u'empind_p', u'empmed_p', 
			u'empofc_p', u'empoth_p', u'empret_p', u'emprsc_p', u'empsvc_p', 
        	u'emptot_p', u'hh_p','stugrd_p', u'stuhgh_p', u'stuuni_p',
        	u'parkdy_p', u'parkhr_p']
	parking_cols = ['ppricdyp','pprichrp']

    # If lower case, convert to upper
	if 'empedu_p' not in df.columns:
		cols = [i.upper() for i in cols]
		parking_cols = [i.upper() for i in parking_cols]

	_df = df[cols]
	# Append results to results_df
	results_df['value'] = _df.sum()
	results_df['field'] = results_df.index
	results_df.reset_index(inplace=True, drop=True)
	results_df['measure'] = 'sum'

	# Calculate average parking price
	_df = pd.DataFrame(df[parking_cols].mean(),
                  columns=['value'])
	_df['measure'] = 'mean'
	_df['field'] = _df.index
	_df.reset_index(inplace=True, drop=True)
	results_df = results_df.append(_df)

	_df = pd.DataFrame(df[parking_cols].max(),
	                  columns=['value'])
	_df['measure'] = 'max'
	_df['field'] = _df.index
	_df.reset_index(inplace=True, drop=True)
	results_df = results_df.append(_df)

	results_df.to_csv(r'outputs/landuse/parcels_urbansim_summary.txt', index=False)

if __name__ == '__main__':
	parcel_summary()