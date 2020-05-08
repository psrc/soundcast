import os
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
        ep = ExecutePreprocessor(timeout=600, kernel_name='python2')
        ep.preprocess(nb, {'metadata': {'path': 'scripts/summarize/notebooks/'}})
        with open('scripts/summarize/notebooks/'+sheet+'.ipynb', 'wt') as f:
            nbformat.write(nb, f)
        os.system("jupyter nbconvert --to HTML scripts/summarize/notebooks/"+sheet+".ipynb")
        # Move these files to output
        if os.path.exists(r"outputs/"+sheet+".html"):
            os.remove(r"outputs/"+sheet+".html")
        os.rename(r"scripts/summarize/notebooks/"+sheet+".html", r"outputs/"+sheet+".html")
	


if __name__ == '__main__':
    main()