import sys
from scripts.skimming.SkimsAndPaths import *
from scripts.EmmeProject import *

def mummify(project_name):
	'''Remove all matrix file types from Emme project.'''
	
	my_project = EmmeProject(project_name)
	
	delete_matrices(my_project, "FULL")
	delete_matrices(my_project, "ORIGIN")
	delete_matrices(my_project, "DESTINATION")

def start_pool(project_list):
	'''Run parallel instances of Emme to process multiple times of day.'''
	pool = Pool(processes=parallel_instances)
	pool.map(mummify,project_list[0:parallel_instances])

	pool.close()

def main():
	'''Shrink Soundcast output files for all times of day.'''

	for i in range (0, 12, parallel_instances):
	    l = project_list[i:i+parallel_instances]
	    start_pool(l)

if __name__ == '__main__':
	main()