import os, sys, shutil
from pathlib import Path
import toml
import nbformat
from nbconvert.preprocessors import ExecutePreprocessor

config = toml.load(Path.cwd() / "configuration/summary_configuration.toml")


def run_ipynb(sheet_name, nb_path):
    print("creating " + sheet_name + " summary")
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
    print(sheet_name + " summary notebook created")


def main():
    # Try to remove existing data first
    output_dir = Path.cwd() / config["p_output_dir"] / "RTP-summary-notebook"
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)

    # Ensure output directory for CSV outputs exists
    if not os.path.exists(Path.cwd() / "outputs" / "RTP"):
        os.makedirs(Path.cwd() / "outputs" / "RTP")
    for dir_name in ['person','mode_share','access']:
        if not os.path.exists(Path.cwd() / "outputs" / "RTP"/ dir_name):
            os.makedirs(Path.cwd() / "outputs" / "RTP" / dir_name)

    for sheet_name in config["RTP_summary_list"]:
        run_ipynb(sheet_name, "scripts/summarize/RTP_summary/RTP_summary_scripts")

    # render quarto book
    # TODO: automate _quarto.yml chapter list
    text = "quarto render scripts/summarize/RTP_summary"
    os.system(text)
    print("RTP summary notebook created")

    # Move these files to output folder
    if not os.path.exists(Path.cwd() / config["p_output_dir"]):
        os.makedirs(Path.cwd() / config["p_output_dir"])
    shutil.move(Path.cwd() / "scripts/summarize/RTP_summary/RTP-summary-notebook", output_dir)


if __name__ == "__main__":
    main()
