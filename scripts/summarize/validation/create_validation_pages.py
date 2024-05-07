import os, sys, shutil
import toml
import nbformat
from nbconvert.preprocessors import ExecutePreprocessor

config = toml.load(os.path.join(os.getcwd(), "validation_configuration.toml"))
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))


def run_ipynb(sheet_name, nb_path):
    print("create " + sheet_name + " summary")
    with open(nb_path + r"/" + sheet_name + ".ipynb") as f:
        nb = nbformat.read(f, as_version=4)
        if sys.version_info > (3, 0):
            py_version = "python3"
        else:
            py_version = "python2"
        ep = ExecutePreprocessor(timeout=1500, kernel_name=py_version)
        ep.preprocess(nb, {"metadata": {"path": nb_path + r"/"}})
        with open(nb_path + r"/" + sheet_name + ".ipynb", "wt") as f:
            nbformat.write(nb, f)
    print(sheet_name + " validation notebook created")


def main():
    for sheet_name in config["summary_list"]:
        run_ipynb(sheet_name, CURRENT_DIR)

    # render quarto book
    # TODO: automate _quarto.yml chapter list
    text = "quarto render " + CURRENT_DIR
    os.system(text)
    print("validation notebook created")

    # Move these files to output folder
    # if os.path.exists(os.path.join(os.getcwd(),config['p_output_dir'],"validation-notebook")):
    #     os.remove(os.path.join(os.getcwd(),config['p_output_dir'],"validation-notebook"))
    # os.rename((os.path.join(CURRENT_DIR,"validation-notebook"))),
    #            os.path.join(os.getcwd(),config['p_output_dir'],"validation-notebook")))


if __name__ == "__main__":
    main()
