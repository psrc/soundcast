import os, sys, shutil
import toml
import nbformat
from nbconvert.preprocessors import ExecutePreprocessor

config = toml.load(os.path.join(os.getcwd(), "configuration", "validation_configuration.toml"))

def run_ipynb(sheet_name, nb_path):
    print("creating " + sheet_name + " summary")
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

    # Try to remove existing data first
    output_dir = os.path.join(os.getcwd(),config['p_output_dir'],'validation-notebook')
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)

    for sheet_name in config["summary_list"]:
        run_ipynb(sheet_name, os.path.join(r'scripts/summarize/validation/validation_scripts'))

    # render quarto book
    # TODO: automate _quarto.yml chapter list
    text = "quarto render " + os.path.join(r'scripts/summarize/validation')
    os.system(text)
    print("validation notebook created")

    # Move these files to output folder
    if not os.path.exists(os.path.join(os.getcwd(),config['p_output_dir'])):
        os.makedirs(os.path.join(os.getcwd(),config['p_output_dir']))
    shutil.move((os.path.join(r'scripts/summarize/validation',"validation-notebook")),
               output_dir)


if __name__ == "__main__":
    main()
