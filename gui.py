# GUI for Soundcast
# Run as | python gui.py | or use .exe
#
# To build .exe, run | pyinstaller.exe --onefile --icon=myicon.ico gui.py
# Result is stored in dist folder

import os, sys, subprocess
from Tkinter import *
import Tkinter, Tkconstants, tkFileDialog
from input_configuration import distance_rate_dict, hot_rate_dict
from emme_configuration import base_year

class MainApplication():
    def __init__(self, master):
        self.master = master
        master.title("Soundcast")
        master.geometry('1050x900')

        # Store form responses to write to input_configuration.py
        var_dict = {}
        # Pre-defined model year list
        model_years = ['2014', '2025', '2040', '2050']

        ##############################
        # Title
        ##############################
        self.label = Label(master, text="soundcast", font=("Arial Bold", 32))
        self.label.pack()
        self.label = Label(master, text="PSRC's Regional Travel Model", font=("Arial", 12))
        self.label.pack()

        ##############################
        # Set Base Input Directory
        ##############################
        self.base_dir_button = Button(master, 
            text='Base Input Directory', 
            command=lambda: self.askdir('base_inputs', self.base_feedb))
        self.base_dir_button.pack(pady=(30,0))
        self.base_feedb = Label(master, text="<Select Base Input Directory>")
        self.base_feedb.pack(pady=(0,5))

        ##############################
        # Set Scenario Input Directory
        ##############################
        # self.dir_button = Button(master, text='Scenario Input Directory', command=self.askdir)

        self.base_dir_button = Button(master, 
            text='Scenario Input Directory', 
            command=lambda: self.askdir('scenario_inputs', self.feedb))
        self.base_dir_button.pack(pady=(30,0))
        self.feedb = Label(master, text="<Select Scenario Input Directory>")
        self.feedb.pack(pady=(0,30))

        ##############################
        # Set Model Year
        ##############################
        self.year = Label(master, text="Scenario Model Year")
        self.year.pack()
        var_dict['model_year'] = Tkinter.StringVar()
        # Selecting model year will automatically update pricing
        # Future years should include tolling and HOT by default, base year will not
        # Users can toggle this in the "Pricing" section
        self.entry = OptionMenu(master, var_dict['model_year'], *model_years, 
            command=lambda x: self.get_model_year(var_dict['model_year'],
                                                 chklist, var_dict, pricing_dict))
        self.entry.pack(pady=(0,30))


        ##############################
        # Toggle Setup Steps
        ##############################
        cf1 = CollapsibleFrame(root, text ="Intial Setup", interior_padx=6)
        cf1.pack(side=LEFT, fill=X, expand=1, anchor=N)
        item_list = ['Run Accessibility Calculations','Setup Emme Project Folders',
                     'Setup Emmebank Folders','Copy Scenario Inputs','Import Networks',]

        for var in item_list:
            var_dict[var] = Tkinter.IntVar(value=1)
            chk = Tkinter.Checkbutton(cf1.interior, text=var, variable=var_dict[var])
            chk.pack(padx=5, pady=3, anchor="w")
        cf1.update_width()

        ##############################
        # Toggle Model Processes
        ##############################
        cf2 = CollapsibleFrame(root, text ="Model Procedures", interior_padx=6)
        cf2.pack(side=LEFT, fill=X, expand=1, anchor=N)
        item_list = ['Start with Freeflow Assignment and Skims','Run Assignment and Skimming', 
                    'Run Truck Model', 'Run Supplemental Trips', 'Run Daysim Choice Models',
                    'Generate Summaries']

        for var in item_list:
            var_dict[var] = Tkinter.IntVar(value=1)
            chk = Tkinter.Checkbutton(cf2.interior, text=var, variable=var_dict[var])
            chk.pack(padx=5, pady=3, anchor="w")
        cf2.update_width()

        ##############################
        # Toggle Modes (AV, TNC)
        ##############################
        cf3 = CollapsibleFrame(root, text ="Modes", interior_padx=6)
        cf3.pack(side=LEFT, fill=X, expand=1, anchor=N)
        item_list = ['Include AV Modes','Include TNCs','TNCs are AV']

        for var in item_list:
            var_dict[var] = Tkinter.IntVar(value=0)
            chk = Tkinter.Checkbutton(cf3.interior, text=var, variable=var_dict[var])
            chk.pack(padx=5, pady=3, anchor="w")
        cf3.update_width()

        ##############################
        # Toggle Tolling
        ##############################
        cf4 = CollapsibleFrame(root, text ="Pricing", interior_padx=6)
        cf4.pack(side=LEFT, fill=X, expand=1, anchor=N)

        # Per-Mile Pricing
        var_permile = 'Apply Per-Mile Distance Pricing'
        var_dict[var_permile] = Tkinter.IntVar(value=0)    # Initialize chkbtn variable in off state
        # Create checkbutton that toggles value fields on/off, and is responsive to change in model yr
        per_mile_chk = Tkinter.Checkbutton(cf4.interior, 
            text=var_permile, 
            variable=var_dict[var_permile], 
            command=lambda : self.toggle_pricing_fields(var_permile, var_dict, tod_pricing_var_dict))
        per_mile_chk.pack()

        # Define Time of Day Pricing Fields
        tod_pricing_var_dict = {}
        for tod in tod_list:
            Label(cf4.interior, text=tod).pack()
            tod_pricing_var_dict[tod] = Entry(cf4.interior)
            tod_pricing_var_dict[tod].pack()
            tod_pricing_var_dict[tod].insert(0, distance_rate_dict[tod])
            tod_pricing_var_dict[tod].config(state='disabled')

        # HOT Pricing
        var_hot = 'Include HOT Lane Tolls'
        var_dict[var_hot] = Tkinter.IntVar(value=0)    # Initialize as off
        hot_chk = Tkinter.Checkbutton(cf4.interior, text=var_hot, variable=var_dict[var_hot],
            command=lambda : self.toggle_pricing_fields(var_hot, var_dict, tod_hot_var_dict))
        hot_chk.pack()

        # Define HOT Variable Pricing
        global tod_hot_var_dict
        tod_hot_var_dict = {}
        for tod in tod_list:
            Label(cf4.interior, text=tod).pack()
            tod_hot_var_dict[tod] = Entry(cf4.interior)
            tod_hot_var_dict[tod].pack()
            tod_hot_var_dict[tod].insert(0, hot_rate_dict[tod])
            tod_hot_var_dict[tod].config(state='disabled')

        chklist = {'Apply Per-Mile Distance Pricing': per_mile_chk,
                    'Include HOT Lane Tolls': hot_chk}

        pricing_dict = {
            'var_permile' : var_permile,
            'tod_pricing_var_dict': tod_pricing_var_dict,
            'var_hot': var_hot,
            'tod_hot_var_dict': tod_hot_var_dict
        }
  
        ##############################
        # Start and Quit
        ##############################
        Button(root, text='Quit', command=root.quit).pack(side=BOTTOM, padx=10, pady=(0,20))
        b1 = Button(root, 
            text='Run Soundcast', 
            command=lambda : self.run_soundcast(var_dict, tod_pricing_var_dict, tod_hot_var_dict))
        b1.pack(side=BOTTOM, padx=20, pady=20)

    def toggle_pricing_fields(self, var, var_dict, target_dict):
        """ Enable/disable pricing fields based on checkbutton state. """
        state = 'normal'
        if var_dict[var].get() == 0:
            state = 'disabled'
           
        for tod in tod_list:
            target_dict[tod].config(state=state)

    def get_model_year(self, year_var, chklist, var_dict, pricing_dict):
        """ Update pricing fields based on model year """

        year = year_var.get()
        for name, var in chklist.iteritems():
            if str(year) != '2014':
                var.select()
            else:
                var.deselect()

        self.toggle_pricing_fields(pricing_dict['var_permile'], 
            var_dict, 
            pricing_dict['tod_pricing_var_dict'])
        self.toggle_pricing_fields(pricing_dict['var_hot'], 
            var_dict, 
            pricing_dict['tod_hot_var_dict'])

    def askdir(self, var, label):
        """Generate dialog box for input dir and write selection to input_configuration.py """
        
        f = tkFileDialog.askdirectory(title='Select Directory', initialdir='R:/soundcast/inputs/lodes')
        
        label.config(text=f)
        update_input_config(var, f)

    def run_soundcast(self, var_dict, tod_pricing_var_dict, tod_hot_var_dict):
        """
        Update input_configuration.py and start run_soundcast.py
        """

        # Update input_configuration.py
        for var_label in var_dict.keys():
            # Get variable from the label
            var_name = config_dict[var_label]
            if var_label not in ['model_year']:    # for boolean fields first
                var_value = str(bool(var_dict[var_label].get()))
                update_input_config(var_name, var_value, bool=True)
            else:
                var_value = str(var_dict[var_name].get())
                update_input_config(var_name, var_value)

        # Update toll and HOT rates by time of day
        distance_rate_dict = {}
        hot_rate_dict = {}
        for tod in tod_list:
            distance_rate_dict[tod] = float(tod_pricing_var_dict[tod].get())
            hot_rate_dict[tod] = float(tod_hot_var_dict[tod].get())

        update_input_config(var_name='distance_rate_dict',var_value=str(distance_rate_dict),bool=True)
        update_input_config(var_name='hot_rate_dict',var_value=str(hot_rate_dict),bool=True)

        # Activate virtual environment and start model run
        subprocess.call('activate model & python run_soundcast.py', shell=True)

class CollapsibleFrame(Frame):
    """
    Collapsable Frame class to build individual input framse
    """
    def __init__(self, master, text=None, borderwidth=2, width=0, height=16, interior_padx=0, interior_pady=8, background=None, caption_separation=4, caption_font=None, caption_builder=None, icon_x=5):
        Frame.__init__(self, master)
        if background is None:
            background = self.cget("background")

        self.configure(background=background)

        self._is_opened = False

        self._interior_padx = interior_padx
        self._interior_pady = interior_pady

        self._iconOpen = PhotoImage(data="R0lGODlhEAAQAKIAAP///9TQyICAgEBAQAAAAAAAAAAAAAAAACwAAAAAEAAQAAADNhi63BMgyinFAy0HC3Xj2EJoIEOM32WeaSeeqFK+say+2azUi+5ttx/QJeQIjshkcsBsOp/MBAA7")
        self._iconClose = PhotoImage(data="R0lGODlhEAAQAKIAAP///9TQyICAgEBAQAAAAAAAAAAAAAAAACwAAAAAEAAQAAADMxi63BMgyinFAy0HC3XjmLeA4ngpRKoSZoeuDLmo38mwtVvKu93rIo5gSCwWB8ikcolMAAA7")
        
        height_of_icon = max(self._iconOpen.height(), self._iconClose.height())
        width_of_icon = max(self._iconOpen.width(), self._iconClose.width())
        
        containerFrame_pady = (height_of_icon//2) +1

        self._height = height
        self._width = width

        self._containerFrame = Frame(self, borderwidth=borderwidth, width=width, height=height, relief=RIDGE, background=background)
        self._containerFrame.pack(expand=True, fill=X, pady=(containerFrame_pady,0))
        
        self.interior = Frame(self._containerFrame, background=background)

        self._collapseButton = Label(self, borderwidth=0, image=self._iconOpen, relief=RAISED)
        self._collapseButton.place(in_= self._containerFrame, x=icon_x, y=-(height_of_icon//2), anchor=N+W, bordermode="ignore")
        self._collapseButton.bind("<Button-1>", lambda event: self.toggle())

        if caption_builder is None:
            self._captionLabel = Label(self, anchor=W, borderwidth=1, text=text)
            if caption_font is not None:
                self._captionLabel.configure(font=caption_font)
        else:
            self._captionLabel = caption_builder(self)
            
            if not isinstance(self._captionLabel, Widget):
                raise Exception("'caption_builder' doesn't return a tkinter widget")

        self.after(0, lambda: self._place_caption(caption_separation, icon_x, width_of_icon))

    def update_width(self, width=None):
        self.after(0, lambda width=width:self._update_width(width))

    def _place_caption(self, caption_separation, icon_x, width_of_icon):
        self.update()
        x = caption_separation + icon_x + width_of_icon
        y = -(self._captionLabel.winfo_reqheight()//2)

        self._captionLabel.place(in_= self._containerFrame, x=x, y=y, anchor=N+W, bordermode="ignore")

    def _update_width(self, width):
        self.update()
        if width is None:
            width=self.interior.winfo_reqwidth()

        if isinstance(self._interior_pady, (list, tuple)):
            width += self._interior_pady[0] + self._interior_pady[1]
        else:
            width += 2*self._interior_pady
            
        width = max(self._width, width)

        self._containerFrame.configure(width=width)
        
    def open(self):
        self._collapseButton.configure(image=self._iconClose)
        
        self._containerFrame.configure(height=self.interior.winfo_reqheight())
        self.interior.pack(expand=True, fill=X, padx=self._interior_padx, pady =self._interior_pady)

        self._is_opened = True

    def close(self):
        self.interior.pack_forget()
        self._containerFrame.configure(height=self._height)
        self._collapseButton.configure(image=self._iconOpen)

        self._is_opened = False
    
    def toggle(self):
        if self._is_opened:
            self.close()
        else:
            self.open()

##############################
# Global variables and lookup fields
##############################

tod_list = ['am','md','pm','ev','ni']

# Dictionary to relate config variables to descriptive name
config_dict = {
    'Run Accessibility Calculations': 'run_accessibility_calcs',
    'Setup Emme Project Folders': 'run_setup_emme_project_folders',
    'Setup Emmebank Folders': 'run_setup_emme_bank_folders',
    'Copy Scenario Inputs': 'run_copy_scenario_inputs',
    'Import Networks': 'run_import_networks',
    'Start with Freeflow Assignment and Skims': 'run_skims_and_paths_free_flow',
    'Run Assignment and Skimming': 'run_skims_and_paths',
    'Run Truck Model': 'run_truck_model',
    'Run Supplemental Trips': 'run_supplemental_trips',
    'Run Daysim Choice Models': 'run_daysim',
    'Generate Summaries': 'run_summaries',
    'Include AV Modes': 'include_av',
    'Include TNCs': 'include_tnc',
    'TNCs are AV': 'tnc_av',
    'Apply Per-Mile Distance Pricing': 'add_distance_pricing',
    'Include HOT Lane Tolls':'add_hot_lane_tolls',
    'model_year': 'model_year'
}

config_path = 'input_configuration.py'
new_file_path = 'input_configuration_tmp.py'

def update_input_config(var_name, var_value, bool=False):
    """ Update input_configuration.py with user inputs """

    with open(config_path) as template_file, open(new_file_path, 'w') as newfile:
        for line in template_file:
            if var_name in line:
                var = line.split(" = ")[0]
                if bool:
                    # Do not add quotes when adding boolean values True/False
                    line = var + " = " + var_value + "\n"
                else:
                    # Add quotes to ensure strings are read as python vars
                    line = var + " = " + "'" + var_value + "'\n"
                newfile.write(line)
            else:
                newfile.write(line)

    try:
        os.remove(config_path)
        os.rename(new_file_path, config_path)
    except OSError as e:  ## if failed, report it back to the user ##
        print("Error: %s - %s." % (e.filename, e.strerror))

##############################
# Main Program
##############################
if __name__ == "__main__":
    
    root = Tk()
    my_gui = MainApplication(root)
    root.mainloop()