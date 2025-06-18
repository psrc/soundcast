import os, sys, shutil, time
from pathlib import Path
import toml
import nbformat
from nbconvert.preprocessors import ExecutePreprocessor

config = toml.load(Path.cwd() / "configuration/validation_configuration.toml")


def run_ipynb(sheet_name, nb_path):
    start_time = time.time()
    print("creating " + sheet_name + " summary")
    with open(Path(nb_path) / (sheet_name + ".ipynb")) as f:
        nb = nbformat.read(f, as_version=4)
        if sys.version_info > (3, 0):
            py_version = "python3"
        else:
            py_version = "python2"
        ep = ExecutePreprocessor(timeout=1500, kernel_name=py_version)
        ep.preprocess(nb, {"metadata": {"path": nb_path + r"/"}})
        with open(Path(nb_path) / (sheet_name + ".ipynb"), "wt") as f:
            nbformat.write(nb, f)
    end_time = time.time()
    print("Time taken to create " + sheet_name + " summary: " + str(end_time - start_time) + " seconds")


def main():
    # Try to remove existing data first
    output_dir = Path.cwd() / config["p_output_dir"] / "validation-notebook"
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)

    for sheet_name in config["summary_list"]:
        run_ipynb(
            sheet_name, "scripts/summarize/validation/validation_scripts"
        )

    # render quarto book
    ## validation notebook
    text = "quarto render scripts/summarize/validation"
    os.system(text)
    print("validation notebook created")

    # Move these files to output folder
    if not os.path.exists(Path.cwd() / config["p_output_dir"]):
        os.makedirs(Path.cwd() / config["p_output_dir"])
    shutil.move(
        Path.cwd() / "scripts/summarize/validation/validation-notebook",
        output_dir
    )

    ## separate notebook for telecommute analysis
    if "../telecommute_analysis/telecommute_analysis" in config["summary_list"]:
        # Try to remove existing data first
        telecommute_analysis_output_dir = Path.cwd() / config["p_output_dir"] / "telecommute-analysis-notebook"
        if os.path.exists(telecommute_analysis_output_dir):
            shutil.rmtree(telecommute_analysis_output_dir)

        text = "quarto render scripts/summarize/validation/telecommute_analysis"
        os.system(text)
        print("telecommute analysis notebook created")

        # Move these files to output folder
        if not os.path.exists(Path.cwd() / config["p_output_dir"]):
            os.makedirs(Path.cwd() / config["p_output_dir"])
        shutil.move(
            Path.cwd() / "scripts/summarize/validation/telecommute-analysis-notebook",
            telecommute_analysis_output_dir,
        )


if __name__ == "__main__":
    main()
