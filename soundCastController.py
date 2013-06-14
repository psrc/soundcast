import subprocess
import sys 

# (leaving this in for now in case we decide we want a real base_path later)
base_path = '.'

returncode = subprocess.call([sys.executable, base_path+'/EmmeDaysimIntegration/src/EmmeDaysimIntegration.py', '-use_seed_trips'])
if returncode != 0:
	sys.exit(1)

print '### Finished skimbuilding ###'

daysim_runner = subprocess.Popen(base_path+'/Daysim/Daysim.exe', cwd=base_path+'/Daysim')
daysim_runner.wait()

print '### Finished running Daysim ###'

subprocess.call([sys.executable, base_path+'/EmmeDaysimIntegration/src/EmmeDaysimIntegration.py'])
print '### Finished running assignments ###'

print '### OH HAPPY DAY!  ALL DONE. (go get a cookie.) ###'

