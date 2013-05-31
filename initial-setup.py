# Run PSRC "Nameless" AB Model
# --------------------------------
import os, subprocess, shutil

input_dir = os.environ['LARGE_INPUTS']

# Copy large input files from network
print "Copy large files..."
input_files = [ 'hhs_and_persons.hdf5',
		'seed_trips.hdf5',
		'psrc_node_node_distances_binary.dat',
		'psrc_parcel_decay_2006.dat',
		'Projects.7z',
		]

for f in input_files:
	path = os.path.join(input_dir,f)
	shutil.copy(path,'.')


# Unzip bare databanks
print "Expanding Emme Project..."
subprocess.call(['c:\\program files\\7-zip\\7z.exe','x','-y','Projects.7z'])


