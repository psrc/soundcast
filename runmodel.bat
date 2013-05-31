:: Run PSRC "Nameless" AB Model
:: -----------------------------------------------

set LARGE_INPUTS=c:\users\billy\desktop\ab_inputs

:: -----------------------------------------------

set RUNPY="C:\Program Files (x86)\INRO\Emme\Emme 4\Emme-4.0.6\Python26\python.exe"

%RUNPY% initial-setup.py
%RUNPY% skimbuilding/build-skims.py

