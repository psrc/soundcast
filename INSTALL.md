Installing SoundCast
====================

- Complete documentation is always at http://soundcast.readthedocs.io

Requirements:
--------------

Hardware:

- 8 CPUs
- 32 GB RAM
- 120 GB disk space **per model run**

Software:

- Windows 7+, 64-bit only
- Python 2.7 and pip (tested only with Anaconda Python - strongly recommended)
- Emme 4.2.3+


Basic setup instructions:
-------------------------

1. Install 64-bit Anaconda Python 2.7 from http://www.continuum.io/downloads

2. Find your Python install folder in File Explorer:
   - Go to Anaconda2\Lib\site-packages
   - Delete the folder 'ply'
   - (This is for Emme Python compatibility)

3. Install Emme 4.2.3+
   - NO to Emme Python as the System Python
   - Make sure you can open Emme Desktop and that your license is validated

4. Run Emme Desktop:
   - Go to Tools - App Options - Modeller.
   - Change Python Path to point to your Anaconda install folder, and click "Install Modeller Package".
   - Close Emme.

5. Clone SoundCast or grab latest zipfile with either:
   - git clone http://github.com/psrc/soundcast.git
   - or download and unzip: https://github.com/psrc/soundcast/archive/master.zip

6. Open a Command Terminal (CMD DOS box):
   - cd into the SoundCast folder
   - Run 'install.bat' to install all software dependencies
   - Check output for errors.

You're ready to run SoundCast.
