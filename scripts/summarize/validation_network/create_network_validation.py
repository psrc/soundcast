from pathlib import Path
import toml
import os, sys

sys.path.append(os.path.join(os.getcwd(), 'scripts', 'summarize'))

from create_quarto_notebook import *

config = toml.load(os.path.join(os.getcwd(), "configuration/validation_configuration.toml"))


def main():

    # create network validation notebook
    create_quarto_notebook(notebook_name = "network-validation-notebook",
                           summary_list = config["network_summary_list"],
                           scripts_dir = "scripts/summarize/validation_network",
                           output_folder = config["p_output_dir"])
    


if __name__ == "__main__":
    main()
