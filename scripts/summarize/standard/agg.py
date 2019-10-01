import pandas as pd
import os, shutil
import math

def main():

	# Load the expression file
	expr_df = pd.read_csv(os.path.join(os.getcwd(),r'inputs/model/summaries/agg_expressions.csv'))

	# Create output folder for flattened output
	agg_output_dir = os.path.join(os.getcwd(),'outputs/agg')
	if os.path.exists(agg_output_dir):
		shutil.rmtree(agg_output_dir)
	os.makedirs(agg_output_dir)

	# Expression log
	expr_log_path = r'outputs/agg/expr_log.csv'
	if os.path.exists(expr_log_path):
		os.remove(expr_log_path)

	# Load daysim outputs
	trip = pd.read_csv(os.path.join(os.getcwd(),r'outputs/daysim/_trip.tsv'), sep='\t')
	tour = pd.read_csv(os.path.join(os.getcwd(),r'outputs/daysim/_tour.tsv'), sep='\t')
	person = pd.read_csv(os.path.join(os.getcwd(),r'outputs/daysim/_person.tsv'), sep='\t')
	household = pd.read_csv(os.path.join(os.getcwd(),r'outputs/daysim/_household.tsv'), sep='\t')
	person_day = pd.read_csv(os.path.join(os.getcwd(),r'outputs/daysim/_person_day.tsv'), sep='\t')
	household_day = pd.read_csv(os.path.join(os.getcwd(),r'outputs/daysim/_household_day.tsv'), sep='\t')

	# Add variable labels
	labels_df = pd.read_csv(os.path.join(os.getcwd(),'inputs/model/lookup/variable_labels.csv'))
	daysim_dict = {'Trip': trip,
				  'Household': household,
				  'Tour': tour,
				  'HouseholdDay': household_day,
				  'PersonDay': person_day}

	# Add departure time hour to trips and tours
	trip['deptm_hr'] = trip['deptm'].apply(lambda row: int(math.floor(row/60)))
	trip['arrtm_hr'] = trip['arrtm'].apply(lambda row: int(math.floor(row/60)))
		
	# tour start hour
	tour['tlvorg_hr'] = tour['tlvorig'].apply(lambda row: int(math.floor(row/60)))
	tour['tardest_hr'] = tour['tardest'].apply(lambda row: int(math.floor(row/60)))
	tour['tlvdest_hr'] = tour['tlvdest'].apply(lambda row: int(math.floor(row/60)))
	tour['tarorig_hr'] = tour['tarorig'].apply(lambda row: int(math.floor(row/60)))

	for tablename, table in daysim_dict.iteritems():
		df = labels_df[labels_df['table'] == tablename]
		for field in df['field'].unique():
			newdf = df[df['field'] == field]
			local_series = pd.Series(newdf['text'].values, index=newdf['value'])
			table[field] = table[field].map(local_series)

	expr_log_df = pd.DataFrame()

	for index, row in expr_df.iterrows():

		# Reduce dataframe to minumum relevant columns, for aggregation and value fields; notation follows pandas pivot table definitions
		agg_fields_cols = [i.strip() for i in row['agg_fields'].split(',')]
		values_cols = [i.strip() for i in row['values'].split(',')]
		col_list = "[" + str(agg_fields_cols + values_cols) + "]"
		# Pass expression string to eval method
		expr = row['table'] + col_list + ".groupby(" + str(agg_fields_cols) + ")." + row['aggfunc'] + "()[" + str(values_cols) + "]"

		# Create log of expressions executed for error checking
		expr_log_df[row['target']] = expr
		with open(expr_log_path, 'a') as f:
			expr_log_df.to_csv(f, header=False)

		# Write results to target output    
		df = pd.eval(expr)
		df.to_csv(os.path.join(os.getcwd(),r'outputs\agg',str(row['target'])+'.csv'))
		
if __name__ == '__main__':
	main()