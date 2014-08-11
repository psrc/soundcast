import numpy as np
import pandas as pd
import h5py
import xlrd
import time
import json

def zero_out_negative_expansion_factors(data, name):
    zotimestart = time.time()
    hh_exp_fac = pd.Series.value_counts(data['Household']['hhexpfac'])
    ps_exp_fac = pd.Series.value_counts(data['Person']['psexpfac'])
    hd_exp_fac = pd.Series.value_counts(data['HouseholdDay']['hdexpfac'])
    pd_exp_fac = pd.Series.value_counts(data['PersonDay']['pdexpfac'])
    tr_exp_fac = pd.Series.value_counts(data['Trip']['trexpfac'])
    to_exp_fac = pd.Series.value_counts(data['Tour']['toexpfac'])
    negatives = []
    negatives.append(hh_exp_fac.where(hh_exp_fac.index<0).index)
    negatives.append(ps_exp_fac.where(ps_exp_fac.index<0).index)
    negatives.append(hd_exp_fac.where(hd_exp_fac.index<0).index)
    negatives.append(pd_exp_fac.where(pd_exp_fac.index<0).index)
    negatives.append(tr_exp_fac.where(tr_exp_fac.index<0).index)
    negatives.append(to_exp_fac.where(to_exp_fac.index<0).index)
    zeromap = {}
    for i in range(len(negatives)):
        for value in negatives[i]:
            if value not in zeromap and value < 0:
                zeromap.update({value: 0})
            elif value not in zeromap and value >= 0:
                zeromap.update({value: value})
    data['Household']['hhexpfac']=data['Household']['hhexpfac'].map(zeromap)
    data['Person']['psexpfac']=data['Person']['psexpfac'].map(zeromap)
    data['HouseholdDay']['hdexpfac']=data['HouseholdDay']['hdexpfac'].map(zeromap)
    data['PersonDay']['pdexpfac']=data['PersonDay']['pdexpfac'].map(zeromap)
    data['Trip']['trexpfac']=data['Trip']['trexpfac'].map(zeromap)
    data['Tour']['toexpfac']=data['Tour']['toexpfac'].map(zeromap)
    print('Negative expansion factors set to zero for '+name+' data in '+str(round(time.time()-zostart,1))+' seconds')
    return(data)

#Imports the variable guide Excel file
def get_guide(guide_file):
    guide=xlrd.open_workbook(guide_file,on_demand=True)
    fileguides={}
    j=0
    for i in guide.sheet_names():
        if guide.sheet_names()[j][len(guide.sheet_names()[j])-1]==' ':
            fileguides.update({guide.sheet_names()[j][0:len(guide.sheet_names()[j])-1].encode('ascii','replace'):guide.sheet_by_name(guide.sheet_names()[j])})
            j=j+1
        else:
            fileguides.update({guide.sheet_names()[j][0:].encode('ascii','replace'):guide.sheet_by_name(guide.sheet_names()[j])})
            j=j+1
    print('Guide import complete')
    return(fileguides)

#Converts the guide into a dictionary of "subdictionaries" (I don't know if that's a word) to convert integers to categorical variables
def guide_to_dict(guide):    
    time_start=time.time()
    catdict={} #Main dictionary
    for file in guide:
        vnames=guide[file].row(0)
        for var in range((len((guide[file].row(0)))+1)/2):
            vardict={} #Subdictionary for specific variable
            for value in range(1,len(guide[file].col(2*var))):
                if(str(guide[file].cell(value,2*var))[7:len(str(guide[file].cell(value,2*var)))-2])=='':
                    pass
                else:
                    #If a cell has an entry, this updates the subdictionary with the cell (an integer), and the cell next to it (the meaning of the integer)
                    vardict.update({int(str(guide[file].cell(value,2*var))[7:len(str(guide[file].cell(value,2*var)))-2]): str(guide[file].cell(value,2*var+1))[7:len(str(guide[file].cell(value,2*var+1)))-1]})
            if 0 in vardict:
                pass
            else:
                vardict.update({0:'Error'}) #If 0 is not a possible entry for the variable and 0 is an actual entry, this converts the entry to 'Error'
            vardict.update({-1:'Error'}) #Some entries for categorical variables are -1, so this converts those to 'Error'
            catdict.update({str(vnames[2*var])[7:len(str(vnames[2*var]))-1]: vardict})
    print('Guide converted to dictionary in '+str(round(time.time()-time_start,1))+' seconds')
    return(catdict)

def convert(filename,guidefile,name):
    has_negative_expansion_factors = False
    L=len(guidefile)
    if guidefile[L-4:L]=='json':
        print('---Begin '+name+' conversion---')
        ts=time.time()
        input=h5py.File(filename,'r+')
        with open(guidefile,'rb') as fp:
            categorical_dict=json.load(fp)
        output={}
        for f in input: #loop through the files
            fs=time.time()
            df=pd.DataFrame()
            for v in input[f]:
                if type(input[f][v][0]) is np.void: #If entries are in the form '(number,)', this loop converts them to number
                    inarray=np.asarray(input[f][v])
                    outarray=[]
                    for i in range(len(inarray)):
                        s=str(inarray[i])
                        s=s.replace('(','')
                        s=s.replace(',)','')
                        outarray.append(float(s))
                    df[v]=outarray
                else:
                    df[v]=np.asarray(input[f][v])
                if v in categorical_dict:
                    local_dict=categorical_dict[v]                             
                    df[v]=df[v].map(local_dict)
                else:
                    if v in ['psexpfac','pdexpfac','hhexpfac','hdexpfac','toexpfac','trexpfac']:
                        if pd.Series.min(df[v])<0:
                            print('WARNING: Negative Expansion Factor Present!')
                    if v in ['taudist','travdist']:
                        if pd.Series.min(df[v])<0:
                            print('WARNING: Negative Travel Distance Present!')
                    if v in ['tautotime','travtime']:
                        if pd.Series.min(df[v])<0:
                            print('WARNING: Negative Travel Time Present!')                                             
            output.update({f:df})
            print(f+' File import/recode complete in '+str(round(time.time()-fs,1))+' seconds')
        print('---'+name+' import/recode complete in '+str(round(time.time()-ts,1))+' seconds---')
        return(output)
    elif guidefile[L-4:L]=='xlsx':
        print('---Begin '+name+' conversion---')
        ts=time.time()
        input=h5py.File(filename,'r+')
        guides=get_guide(guidefile)
        categorical_dict=guide_to_dict(guides)
        output={}
        for f in input: #loop through the files
            fs=time.time()
            df=pd.DataFrame()
            for v in input[f]:
                if type(input[f][v][0]) is np.void: #If entries are in the form '(number,)', this loop converts them to number
                    inarray=np.asarray(input[f][v])
                    outarray=[]
                    for i in range(len(inarray)):
                        s=str(inarray[i])
                        s=s.replace('(','')
                        s=s.replace(',)','')
                        outarray.append(float(s))
                    df[v]=outarray
                else:
                    df[v]=np.asarray(input[f][v])
                if v in categorical_dict:
                    local_dict=categorical_dict[v]                             
                    df[v]=df[v].map(local_dict)
                else:
                    if v in ['psexpfac','pdexpfac','hhexpfac','hdexpfac','toexpfac','trexpfac']:
                        if pd.Series.min(df[v])<0:
                            has_negative_expansion_factors = True
                            print('WARNING: Negative Expansion Factor Present!')
                    if v in ['taudist','travdist']:
                        if pd.Series.min(df[v])<0:
                            print('WARNING: Negative Travel Distance Present!')
                    if v in ['tautotime','travtime']:
                        if pd.Series.min(df[v])<0:
                            print('WARNING: Negative Travel Time Present!')                                             
            output.update({f:df})
            print(f+' File import/recode complete in '+str(round(time.time()-fs,1))+' seconds')
        if has_negative_expansion_factors == True:
            output = zero_out_negative_expansion_factors(output, name)
        print('---'+name+' import/recode complete in '+str(round(time.time()-ts,1))+' seconds---')
        return(output)
    else:
        raise ValueError('Guide file type '+guidefile[L-4:L]+' not supported.')