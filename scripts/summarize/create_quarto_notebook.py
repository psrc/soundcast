import os, sys, shutil, time
from pathlib import Path
import nbformat
from nbconvert.preprocessors import ExecutePreprocessor


def run_ipynb(sheet_name, nb_path):
    start_time = time.time()
    print("creating " + sheet_name + " page")
    with open(Path(nb_path) / (sheet_name + ".ipynb")) as f:
        nb = nbformat.read(f, as_version=4)
        if sys.version_info > (3, 0):
            py_version = "python3"
        else:
            py_version = "python2"
        ep = ExecutePreprocessor(timeout=1500, kernel_name=py_version)
        ep.preprocess(nb, {"metadata": {"path": Path(nb_path)}})
        with open(Path(nb_path) / (sheet_name + ".ipynb"), "wt") as f:
            nbformat.write(nb, f)
    end_time = time.time()
    print("Time taken to create " + sheet_name + " page: " + str(end_time - start_time) + " seconds")


def create_quarto_notebook(notebook_name, summary_list, scripts_dir, output_folder):
    # Try to remove existing data first
    output_dir = Path.cwd() / output_folder / notebook_name
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)

    for sheet_name in summary_list:
        run_ipynb(sheet_name, scripts_dir + "/summary_scripts")

    # render quarto book
    # TODO: automate _quarto.yml chapter list
    text = "quarto render " + scripts_dir
    os.system(text)
    print(notebook_name + " created")

    # Move these files to output folder
    if not os.path.exists(Path.cwd() / output_folder):
        os.makedirs(Path.cwd() / output_folder)
    shutil.move(Path.cwd() / scripts_dir / notebook_name, output_dir)
