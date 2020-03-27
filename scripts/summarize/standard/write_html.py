import os
import nbformat
from nbconvert.preprocessors import ExecutePreprocessor

def main():

    # Create HTML sheets from jupyter notebooks
    for sheet in ['topsheet','metrics','validation','validation_census','validation_tour']:
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