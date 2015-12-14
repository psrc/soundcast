*Where do I find Soundcast and how do I set it up?*

# Initial Setup

All Soundcast scripts are stored within a public [GitHub repository](https://github.com/psrc/soundcast). If you're familiar with Git technology, you can [clone](http://git-scm.com/docs/git-clone) the repository on your modeling machine. 

Alternatively, you can download all the code as a ZIP file. 

![Download GitHub ZIP](http://oi60.tinypic.com/dxmo2u.jpg)

# Python Packages and Paths
It's recommended to [install the Anaconda Python package](https://repo.continuum.io/archive) to run Soundcast. This package should include all necessary libraries to run the model. When installing, make sure the installer adds the Anaconda install to the system path (or add it yourself after installing). It's important that this install is the one referenced whenever the "python" program is invoked from a command. Many machines might include another Python install; it's okay to leave other versions installed, but you'll want to update the path variable to point only to the Anaconda version. In order to avoid conflicts with Emme's Python install, *download package version 2.2.0.* [Click here to directly download Anaconda 2.2.0 for 64-bit Windows](2.2.0 https://repo.continuum.io/arcive/Anaconda-2.2.0-Windows-x86_64.exe). Additionally, you may want to install Anaconda for current users only (not for all users). Sometimes installing Python for all users will conflict with administrative rights, so it's best to install and use it as a local user. 

After installing Anaconda, you must change Emme's settings to use the Anaconda installation by default. Otherwise, scripts that interact with Emme will use another install without the necessary libraries. To change the Python version used by Emme, select Tools (from the main taskbar) and click 'Application Options'. Under the Modeller tab is a field "Python path", which by default probably looks like:

	%<$EmmePath>%/Python27

![Emme Python version settings](http://oi57.tinypic.com/2466ecp.jpg)

Replace this path with the full path to the Anaconda Python executable (python.exe). Depending on where Anaconda was installed, it may be something like:

	C:\Anaconda

# Troubleshooting Python Install
Emme's Python libraries can conflict with the Anaconda install used to run Python. As of Emme release 4.2.3, there are two known conflicts with the Anaconda libraries. Two libraries "ply" and "pyqt" from Anaconda clash with Emme. INRO's solution is to remove these two libraries from the Anaconda install and rely on the Emme libraries. This works for Anaconda 2.2.0 and prior releases, but does not work for the latest versions. For now, the recommended approach is to use Anaconda 2.2.0 and remove ply and pyqt libraries. This can be done from the command prompt with "conda uninstall ply" and "condat uninstall pyqt". When these libraries are removed from Anaconda, Emme will look to its local install of these packages, which should have no conflicts.

# Install Additional Python Libraries
Although the Anaconda Python package include many libraries, there are some specialized libraries required for Soundcast that are not included. Fortunately, these can easily be added from the command prompt. The required additional libraries are:

	- pysal (used to read geodatabase files from ArcGIS)
	- pandas_highcharts (for visualization of results in iPython notebooks)

These can be added either by typing "pip install [library name]" or "conda install [library name]". If the model run crashes because of a missing library, it should be easy to quickly add the library and restart the model from the point of failure.

# Install 7-zip
Soundcast inputs are very large and are stored as compressed files to save space. Scripts rely on the 7-zip tool to open and expand these files, and the program *must be added to the system path*. Before running Soundcast, ensure that 7-zip is installed. If not, it can be [freely obtained here](http://www.7-zip.org/). Once installed, copy the location of the 7-zip.exe and add it to the system's path environment variable. To do this, open the Environment Variables window under Control Panel and edit the "path" system variable (the second scroll window from the top).

Soundcast should now be ready to run.