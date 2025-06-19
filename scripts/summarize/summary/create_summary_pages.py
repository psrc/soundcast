import toml
import os, sys

sys.path.append(os.path.join(os.getcwd(), 'scripts', 'summarize'))

from create_quarto_notebook import *

config = toml.load(os.path.join(os.getcwd(), "configuration/summary_configuration.toml"))

def main():

    # create summary notebook
    create_quarto_notebook(notebook_name = "run-comparison-notebook",
                           summary_list = config["summary_list"],
                           scripts_dir = "scripts/summarize/summary",
                           output_folder = config["p_output_dir"])    


if __name__ == "__main__":
    main()
