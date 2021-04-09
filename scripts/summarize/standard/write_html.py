import os, sys, shutil
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(CURRENT_DIR))
sys.path.append(os.path.join(os.getcwd(),"inputs"))
sys.path.append(os.path.join(os.getcwd(),"scripts"))
sys.path.append(os.getcwd())
import nbformat
from nbconvert.preprocessors import ExecutePreprocessor
from input_configuration import model_year, base_year

def main():

    nb_list = ['topsheet','metrics','validation_census','validation_daysim','validation_tour','work']
    if str(model_year)==str(base_year):
        nb_list += ['validation']

    # Create HTML sheets from jupyter notebooks
    for sheet in nb_list:
        with open("scripts/summarize/notebooks/"+sheet+".ipynb") as f:
                nb = nbformat.read(f, as_version=4)
        if (sys.version_info > (3, 0)):
            py_version = 'python3'
        else:
            py_version = 'python2'
        ep = ExecutePreprocessor(timeout=600, kernel_name=py_version)
        ep.preprocess(nb, {'metadata': {'path': 'scripts/summarize/notebooks/'}})
        with open('scripts/summarize/notebooks/'+sheet+'.ipynb', 'wt') as f:
            nbformat.write(nb, f)
        if (sys.version_info > (3, 0)):
            os.system("jupyter nbconvert --to HTML --TemplateExporter.exclude_input=True scripts/summarize/notebooks/"+sheet+".ipynb")
        else:
            os.system("jupyter nbconvert --to HTML scripts/summarize/notebooks/"+sheet+".ipynb")
        # Move these files to output
        if os.path.exists(r"outputs/"+sheet+".html"):
            os.remove(r"outputs/"+sheet+".html")
        os.rename(r"scripts/summarize/notebooks/"+sheet+".html", r"outputs/"+sheet+".html")
	


if __name__ == '__main__':
    main()