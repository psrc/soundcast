import numpy as np
import pandas as pd
import xlsxwriter
import time
import h5toDF

def get_total(exp_fac):
    total=pd.Series.sum(exp_fac)
    if total<1:
        total=pd.Series.count(exp_fac)
    return(total)

def weighted_average(df_in,col,weights,grouper):
    if grouper==None:
        df_in[col+'_sp']=df_in[col]*df_in[weights]
        n_out=pd.Series.sum(df_in[col+'_sp'])/pd.Series.sum(df_in[weights])
        return(n_out)
    else:
        df_in[col+'_sp']=df_in[col]*df_in[weights]
        df_out=df_in.groupby(grouper).sum()
        df_out[col+'_wa']=df_out[col+'_sp']/df_out[weights]
        return(df_out)

def recode_index(df,old_name,new_name):
    df[new_name]=df.index
    df=df.reset_index()
    del df[old_name]
    df=df.set_index(new_name)
    return df

def get_districts(file):
    zone_district=pd.DataFrame.from_csv(file,index_col=None)
    return(zone_district)

def get_differences(df,colname1,colname2,roundto):
    df['Difference']=df[colname1]-df[colname2]
    df['Percent Difference']=pd.Series.round(df['Difference']/df[colname2]*100,1)
    if type(roundto)==list:
        for i in range(len(df['Difference'])):
            df[colname1][i]=round(df[colname1][i],roundto[i])
            df[colname2][i]=round(df[colname2][i],roundto[i])
            df['Difference'][i]=round(df['Difference'][i],roundto[i])
    else:
        for i in range(len(df['Difference'])):
            df[colname1][i]=round(df[colname1][i],roundto)
            df[colname2][i]=round(df[colname2][i],roundto)
            df['Difference'][i]=round(df['Difference'][i],roundto)
    return(df)


daysimfile='R:/JOE/summarize/daysim_outputs.h5'
surveyfile='R:/JOE/summarize/survey.h5'
guidefile='R:/JOE/summarize/CatVarDict.xlsx'
name1='2010 Model Run'
name2='2006 Survey'
data1=h5toDF.convert(daysimfile,guidefile,name1)
data2=h5toDF.convert(surveyfile,guidefile,name2)
districtfile='R:/JOE/summarize/TAZ_TAD_County.csv'
zone_district=get_districts(districtfile)
location='R:/JOE/summarize/reports'


#def DayPattern(data1,data2,name1,name2,location):

merge_per_hh_1=pd.merge(data1['Person'],data1['Household'],'outer')
merge_per_hh_2=pd.merge(data2['Person'],data2['Household'],'outer')
Person_1_total=get_total(merge_per_hh_1['psexpfac'])
Person_2_total=get_total(merge_per_hh_2['psexpfac'])

#Tours per person
tpp1=pd.Series.sum(data1['Tour']['toexpfac'])/pd.Series.sum(data1['Person']['psexpfac'])
tpp2=pd.Series.sum(data2['Tour']['toexpfac'])/pd.Series.sum(data2['Person']['psexpfac'])
tpp=pd.DataFrame(index=['Tours'])
tpp[name1]=tpp1
tpp[name2]=tpp2
tpp=get_differences(tpp,name1,name2,2)

#Percent of Tours by Purpose
ptbp1=data1['Tour'].groupby('pdpurp').sum()['toexpfac']/pd.Series.sum(data1['Tour']['toexpfac'])*100
ptbp2=data2['Tour'].groupby('pdpurp').sum()['toexpfac']/pd.Series.sum(data2['Tour']['toexpfac'])*100
ptbp=pd.DataFrame()
ptbp['Percent of Tours ('+name1+')']=ptbp1
ptbp['Percent of Tours ('+name2+')']=ptbp2
ptbp=get_differences(ptbp,'Percent of Tours ('+name1+')','Percent of Tours ('+name2+')',1)
ptbp=recode_index(ptbp,'pdpurp','Tour Purpose')

#Tours per Person by Purpose
tpp1=data1['Tour'].groupby('pdpurp').sum()['toexpfac']/pd.Series.sum(data1['Person']['psexpfac'])
tpp2=data2['Tour'].groupby('pdpurp').sum()['toexpfac']/pd.Series.sum(data2['Person']['psexpfac'])
tpp=pd.DataFrame()
tpp['Tours per Person ('+name1+')']=tpp1
tpp['Tours per Person ('+name2+')']=tpp2
tpp=get_differences(tpp,'Tours per Person ('+name1+')','Tours per Person ('+name2+')',3)
tpp=recode_index(tpp,'pdpurp','Tour Purpose')

#Tours per Person by Purpose and Person Type/Number of Stops
PersonsDay1=pd.merge(data1['Person'],data1['PersonDay'],on=['hhno','pno'])
PersonsDay2=pd.merge(data2['Person'],data2['PersonDay'],on=['hhno','pno'])
tpd={}
stops={}
for purpose in pd.Series.value_counts(data1['Tour']['pdpurp']).index:
    if purpose=='Work':
        tc='wktours'
    elif purpose=='Social':
        tc='sotours'
    elif purpose=='School':
        tc='sctours'
    elif purpose=='Escort':
        tc='estours'
    elif purpose=='Personal Business':
        tc='pbtours'
    elif purpose=='Shop':
        tc='shtours'
    elif purpose=='Meal':
        tc='mltours'
    toursPersPurp1=weighted_average(PersonsDay1,tc,'psexpfac','pptyp')[tc+'_wa']
    toursPersPurp2=weighted_average(PersonsDay2,tc,'psexpfac','pptyp')[tc+'_wa']
    toursPersPurp=pd.DataFrame.from_items([(name1,toursPersPurp1),(name2,toursPersPurp2)])
    toursPersPurp=get_differences(toursPersPurp,name1,name2,2)
    tpd.update({purpose:toursPersPurp})
    person_day_hh1=pd.merge(data1['PersonDay'],data1['Household'],on=['hhno'])
    person_day_hh2=pd.merge(data2['PersonDay'],data2['Household'],on=['hhno'])
    person_day_hh1['aps']=person_day_hh1['pdexpfac']/pd.Series.sum(person_day_hh1['pdexpfac'])*100
    person_day_hh2['aps']=person_day_hh2['pdexpfac']/pd.Series.sum(person_day_hh2['pdexpfac'])*100
    ave_purp_stops1=person_day_hh1.groupby(tc).sum()['aps']
    ave_purp_stops2=person_day_hh2.groupby(tc).sum()['aps']
    purp_stops=pd.DataFrame.from_items([('% of Tours ('+name1+')',ave_purp_stops1),('% of Tours ('+name2+')',ave_purp_stops2)])
    no_stops=purp_stops.query(tc+'==0')
    has_stops=100-no_stops
    ps=pd.DataFrame()
    ps['% of Tours ('+name1+')']=[no_stops['% of Tours ('+name1+')'][0],has_stops['% of Tours ('+name1+')'][0]]
    ps['% of Tours ('+name2+')']=[no_stops['% of Tours ('+name2+')'][0],has_stops['% of Tours ('+name2+')'][0]]
    ps['index']=['0','1+']
    ps=ps.set_index('index')
    ps=get_differences(ps,'% of Tours ('+name1+')','% of Tours ('+name2+')',1)
    ps=recode_index(ps,'index',purpose+' Tours')
    stops.update({purpose:ps})

#Work-Based Subtour Generation
#Total trips per person
atp1=pd.Series.sum(data1['Trip']['trexpfac'])/pd.Series.sum(data1['Person']['psexpfac'])
atp2=pd.Series.sum(data2['Trip']['trexpfac'])/pd.Series.sum(data2['Person']['psexpfac'])
atl1=weighted_average(data1['Trip'],'travdist','trexpfac',None)
atl2=weighted_average(data2['Trip'],'travdist','trexpfac',None)
tt1[name1]=[atp1,atl1]
tt2[name2]=[atp2,atl2]
label=['Average Trips Per Person','Average Trip Length']
tt=pd.DataFrame.from_items([(name1,tt1),(name2,tt2)],index=label)

#Tours by Type by Person Type
#wrkto1=data1['Tour'].query('pdpurp=="Work"')
#wrkto2=data2['Tour'].query('pdpurp=="Work"')
#numtours1=wrkto1.groupby(['hhno','pno']).sum()
#numtours2=wrkto1.groupby(['hhno','pno']).sum()
#persontours1=pd.merge(numtours1,data1['Person'],left_index=True,right_on=['hhno','pno'])
#persontours2=pd.merge(numtours2,data2['Person'],left_index=True,right_on=['hhno','pno'])
#wtpt1=persontours1.groupby('pptyp').sum()['toexpfac']/persontours1.groupby('pptyp').sum()['psexpfac']
#wtpt2=persontours2.groupby('pptyp').sum()['toexpfac']/persontours1.groupby('pptyp').sum()['psexpfac']


def DaysimReport(data1,data2,name1,name2,location,districtfile):
    start=time.time()
    merge_per_hh_1=pd.merge(data1['Person'],data1['Household'],'outer')
    merge_per_hh_2=pd.merge(data2['Person'],data2['Household'],'outer')
    label=[]
    value1=[]
    value2=[]
    Person_1_total=get_total(merge_per_hh_1['psexpfac'])
    Person_2_total=get_total(merge_per_hh_2['psexpfac'])
    label.append('Number of People')
    value1.append(int(round(Person_1_total,-5)))
    value2.append(int(round(Person_2_total,-5)))
    Trip_1_total=get_total(data1['Trip']['trexpfac'])
    Trip_2_total=get_total(data2['Trip']['trexpfac'])
    label.append('Number of Trips')
    value1.append(int(round(Trip_1_total,-5)))
    value2.append(int(round(Trip_2_total,-5)))
    Tour_1_total=get_total(data1['Tour']['toexpfac'])
    Tour_2_total=get_total(data2['Tour']['toexpfac'])
    label.append('Number of Tours')
    value1.append(int(round(Tour_1_total,-5)))
    value2.append(int(round(Tour_2_total,-5)))
    tour_ok_1=data1['Tour'].query('tautodist>0 and tautodist<2000')
    tour_ok_2=data2['Tour'].query('tautodist>0 and tautodist<2000')
    trip_ok_1=data1['Trip'].query('travdist>0 and travdist<2000')
    trip_ok_2=data2['Trip'].query('travdist>0 and travdist<2000')

    ##Basic Summaries
    #Total Households, Persons, and Trips
    tp1=pd.Series.sum(data1['Person']['psexpfac'])
    tp2=pd.Series.sum(data2['Person']['psexpfac'])
    th1=pd.Series.sum(data1['Household']['hhexpfac'])
    th2=pd.Series.sum(data2['Household']['hhexpfac'])
    ttr1=pd.Series.sum(data1['Trip']['trexpfac'])
    ttr2=pd.Series.sum(data2['Trip']['trexpfac'])
    ahhs1=tp1/th1
    ahhs2=tp2/th2
    ntr1=ttr1/tp1
    ntr2=ttr2/tp2
    atl1=weighted_average(data1['Trip'],'travdist','trexpfac',None)
    atl2=weighted_average(data2['Trip'],'travdist','trexpfac',None)
    driver_trips1=trip_ok_1.query('dorp=="Driver"')
    driver_trips2=trip_ok_2.query('dorp=="Driver"')
    vmpp1sp=pd.Series.sum(driver_trips1['travdist']*driver_trips1['trexpfac'])
    vmpp2sp=pd.Series.sum(driver_trips2['travdist']*driver_trips2['trexpfac'])
    vmpp1=vmpp1sp/Trip_1_total
    vmpp2=vmpp2sp/Trip_2_total
    #Work Location
    wrkrs1=merge_per_hh_1.query('pwtyp=="Paid Full-Time Worker" or pwtyp=="Paid Part-Time Worker"')
    wrkrs2=merge_per_hh_1.query('pwtyp=="Paid Full-Time Worker" or pwtyp=="Paid Part-Time Worker"')
    wrkr_1_hzone=pd.merge(wrkrs1,districtfile,left_on='hhtaz',right_on='TAZ')
    wrkr_2_hzone=pd.merge(wrkrs2,districtfile,left_on='hhtaz',right_on='TAZ')
    total_workers_1=pd.Series.count(wrkrs1['id'])
    total_workers_2=pd.Series.count(wrkrs2['id'])
    workers_1=wrkr_1_hzone.query('pwpcl!=hhparcel and pwaudist>0 and pwaudist<200')
    workers_2=wrkr_2_hzone.query('pwpcl!=hhparcel and pwaudist>0 and pwaudist<200')
    workers_1['Share']=workers_1['psexpfac']/pd.Series.sum(workers_1['psexpfac'])
    workers_2['Share']=workers_2['psexpfac']/pd.Series.sum(workers_2['psexpfac'])
    workers1_avg_dist=weighted_average(workers_1,'pwaudist','psexpfac',None)
    workers2_avg_dist=weighted_average(workers_2,'pwaudist','psexpfac',None)
    #School Location
    st1=merge_per_hh_1.query('pstyp=="Full-Time Student" or pstyp=="Part-Time Student"')
    st2=merge_per_hh_2.query('pstyp=="Full-Time Student" or pstyp=="Part-Time Student"')
    st_1_hzone=pd.merge(st1,districtfile,'outer',left_on='hhtaz',right_on='TAZ')
    st_2_hzone=pd.merge(st2,districtfile,'outer',left_on='hhtaz',right_on='TAZ')
    total_students_1=pd.Series.count(st1['hhno'])
    total_students_2=pd.Series.count(st2['hhno'])
    students_1=st_1_hzone.query('pspcl!=hhparcel and psaudist>0 and psaudist<200')
    students_2=st_2_hzone.query('pspcl!=hhparcel and psaudist>0 and psaudist<200')
    students_1['Share']=students_1['psexpfac']/pd.Series.sum(students_1['psexpfac'])
    students_2['Share']=students_2['psexpfac']/pd.Series.sum(students_2['psexpfac'])
    students1_avg_dist=weighted_average(students_1,'psaudist','psexpfac',None)
    students2_avg_dist=weighted_average(students_2,'psaudist','psexpfac',None)
    #Glue DataFrame Together
    thp=pd.DataFrame(index=['Total Persons','Total Households','Average Household Size','Average Trips Per Person','Average Trip Length','Vehicle Miles per Person','Average Distance to Work (Non-Home)','Average Distance to School (Non-Home)'])
    thp[name1]=[tp1,th1,ahhs1,ntr1,atl1,vmpp1,workers1_avg_dist,students1_avg_dist]
    thp[name2]=[tp2,th2,ahhs2,ntr2,atl2,vmpp2,workers2_avg_dist,students2_avg_dist]
    thp=get_differences(thp,name1,name2,[-5,-5,1,1,1,1,1,1])

    #Transit Pass Ownership
    ttp1=pd.Series.sum(data1['Person']['ptpass']*data1['Person']['psexpfac'])
    ttp2=pd.Series.sum(data2['Person']['ptpass']*data2['Person']['psexpfac'])
    ppp1=ttp1/Person_1_total
    ppp2=ttp2/Person_2_total
    tpass=pd.DataFrame(index=['Total Passes','Passes per Person'])
    tpass[name1]=[ttp1,ppp1]
    tpass[name2]=[ttp2,ppp2]
    tpass=get_differences(tpass,name1,name2,[-4,3])

    #Auto Ownership
    ao1=data1['Household'].groupby('hhvehs').sum()['hhexpfac']/pd.Series.sum(data1['Household']['hhexpfac'])*100
    ao2=data2['Household'].groupby('hhvehs').sum()['hhexpfac']/pd.Series.sum(data1['Household']['hhexpfac'])*100
    ao=pd.DataFrame()
    ao['Percent of Households ('+name1+')']=ao1
    ao['Percent of Households ('+name2+')']=ao2
    ao=get_differences(ao,'Percent of Households ('+name1+')','Percent of Households ('+name2+')',1)
    ao=recode_index(ao,'hhvehs','Number of Vehicles in Household')

    #Boardings
    board=pd.DataFrame(index=['Boardings'])
    board['Total Observed Transit Boardings (2011)']=647127
    board['Implied Transit Boardings (Assuming 1.3 Boardings/Trip']=1.3*pd.Series.sum((data1['Trip'].query('mode=="Transit"'))['trexpfac'])
    board=get_differences(board,'Total Observed Transit Boardings (2011)','Implied Transit Boardings (Assuming 1.3 Boardings/Trip',0)

    #File Compile
    writer=pd.ExcelWriter(location+'/DaysimReport.xlsx',engine='xlsxwriter')
    thp.to_excel(excel_writer=writer,sheet_name='Basic Summaries',na_rep='NA')
    tpass.to_excel(excel_writer=writer,sheet_name='Transit Pass Ownership',na_rep='NA')
    ao.to_excel(excel_writer=writer,sheet_name='Automobile Ownership',na_rep='NA')
    board.to_excel(excel_writer=writer,sheet_name='Transit Boardings',na_rep='NA')
    workbook=writer.book
    colors=['#ed3300','#00529f']
    sheet='Basic Summaries'
    worksheet=writer.sheets[sheet]
    worksheet.set_column(0,worksheet.dim_colmax,width=35)
    worksheet.freeze_panes(0,1)
    chart=workbook.add_chart({'type':'column'})
    for col_num in range(1,3):
        chart.add_series({'name':[sheet, 0, col_num],
                            'categories':[sheet,3,0,worksheet.dim_rowmax,0],
                            'values':[sheet,3,col_num,worksheet.dim_rowmax,col_num],
                            'fill':{'color':colors[col_num-1]}})
    chart.set_legend({'position':'top'})
    chart.set_size({'x_scale':2,'y_scale':1.75})
    worksheet.insert_chart('B11',chart)
    sheet='Transit Pass Ownership'
    worksheet=writer.sheets[sheet]
    worksheet.set_column(0,worksheet.dim_colmax,width=35)
    worksheet.freeze_panes(0,1)
    chart=workbook.add_chart({'type':'column'})
    for col_num in range(1,3):
        chart.add_series({'name':[sheet, 0, col_num],
                            'categories':[sheet,1,0,1,0],
                            'values':[sheet,1,col_num,1,col_num],
                            'fill':{'color':colors[col_num-1]}})
    chart.set_legend({'position':'top'})
    chart.set_size({'x_scale':2,'y_scale':2.25})
    worksheet.insert_chart('B5',chart)
    sheet='Automobile Ownership'
    worksheet=writer.sheets[sheet]
    worksheet.set_column(0,worksheet.dim_colmax,width=35)
    worksheet.freeze_panes(0,1)
    chart=workbook.add_chart({'type':'column'})
    for col_num in range(1,3):
        chart.add_series({'name':[sheet, 0, col_num],
                            'categories':[sheet,2,0,worksheet.dim_rowmax,0],
                            'values':[sheet,2,col_num,worksheet.dim_rowmax,col_num],
                            'fill':{'color':colors[col_num-1]}})
    chart.set_title({'name':'Percentage of Households with Number of Automobiles'})
    chart.set_legend({'position':'top'})
    chart.set_size({'x_scale':2,'y_scale':2})
    worksheet.insert_chart('B9',chart)
    sheet='Transit Boardings'
    worksheet=writer.sheets[sheet]
    worksheet.set_column(0,worksheet.dim_colmax,width=35)
    worksheet.freeze_panes(0,1)
    chart=workbook.add_chart({'type':'column'})
    for col_num in range(1,3):
        chart.add_series({'name':[sheet, 0, col_num],
                            'categories':[sheet,1,0,worksheet.dim_rowmax,0],
                            'values':[sheet,1,col_num,worksheet.dim_rowmax,col_num],
                            'fill':{'color':colors[col_num-1]}})
    chart.set_legend({'position':'top'})
    chart.set_size({'x_scale':2,'y_scale':2.25})
    worksheet.insert_chart('B4',chart)
    writer.save()

    print('DaySim Report successfully compiled in '+str(round(time.time()-start,1))+' seconds')

def DestChoice(data1,data2,name1,name2,location,districtfile):
    start=time.time()
    Trip_1_total=get_total(data1['Trip']['trexpfac'])
    Trip_2_total=get_total(data2['Trip']['trexpfac'])
    Tour_1_total=get_total(data1['Tour']['toexpfac'])
    Tour_2_total=get_total(data2['Tour']['toexpfac'])
    tour_ok_1=data1['Tour'].query('tautodist>0 and tautodist<200')
    tour_ok_2=data2['Tour'].query('tautodist>0 and tautodist<200')
    trip_ok_1=data1['Trip'].query('travdist>0 and travdist<200')
    trip_ok_2=data2['Trip'].query('travdist>0 and travdist<200')

    #Average distance by tour purpose
    tourtrip1=pd.merge(tour_ok_1,trip_ok_1,on=['hhno','pno','tour','day'])
    tourtrip2=pd.merge(tour_ok_2,trip_ok_2,on=['hhno','pno','tour','day'])
    triptotal1=weighted_average(tourtrip1,'tautodist','trexpfac','pdpurp')
    triptotal2=weighted_average(tourtrip2,'tautodist','trexpfac','pdpurp')
    atl1=pd.DataFrame.from_items([('Average Tour Length ('+name1+')',pd.Series.round(triptotal1['tautodist_wa'],1))])
    #atl1=pd.DataFrame.from_items([('Average Trip Length ('+name1+')',tourtrip1.groupby('pdpurp').mean()['tautodist'])])
    atl2=pd.DataFrame.from_items([('Average Tour Length ('+name2+')',pd.Series.round(triptotal2['tautodist_wa'],1))])
    atl=pd.merge(atl1,atl2,'outer',left_index=True,right_index=True)
    atl['Difference']=pd.Series.round(atl['Average Tour Length ('+name1+')']-atl['Average Tour Length ('+name2+')'],1)
    atl['Percent Difference']=pd.Series.round((atl['Difference'])/atl['Average Tour Length ('+name2+')']*100,1)
    atl=recode_index(atl,'pdpurp','Tour Purpose')

    #Number of trips by tour purpose
    notrips1=tourtrip1.groupby(['hhno','pno','tour','day']).count()['trexpfac']
    notrips2=tourtrip2.groupby(['hhno','pno','tour','day']).count()['trexpfac']
    notrips1=notrips1.reset_index()
    notrips2=notrips2.reset_index()
    notrips1=notrips1.rename(columns={'trexpfac':'notrips'})
    notrips2=notrips2.rename(columns={'trexpfac':'notrips'})
    toursnotrips1=pd.merge(tour_ok_1,notrips1,on=['hhno','pno','tour'])
    toursnotrips2=pd.merge(tour_ok_2,notrips2,on=['hhno','pno','tour'])
    tourtotal1=weighted_average(toursnotrips1,'notrips','toexpfac','pdpurp')
    tourtotal2=weighted_average(toursnotrips2,'notrips','toexpfac','pdpurp')
    ttd=tourtotal1['notrips_wa']-tourtotal2['notrips_wa']
    ttpd=(tourtotal1['notrips_wa']-tourtotal2['notrips_wa'])/tourtotal2['notrips_wa']*100
    nttp1=pd.DataFrame.from_items([('Average Number of Trips per Tour ('+name1+')',pd.Series.round(tourtotal1['notrips_wa'],1))])
    nttp2=pd.DataFrame.from_items([('Average Number of Trips per Tour ('+name2+')',pd.Series.round(tourtotal2['notrips_wa'],1))])
    nttp=pd.merge(nttp1,nttp2,'outer',left_index=True,right_index=True)
    ttd['Difference']=pd.Series.round(ttd,1)
    ttpd['Percent Difference']=pd.Series.round(ttpd,1)
    nttp=recode_index(nttp,'pdpurp','Tour Purpose')

    #Average Distance by Trip Purpose
    atripdist1=weighted_average(data1['Trip'],'travdist','trexpfac','dpurp')
    atripdist2=weighted_average(data2['Trip'],'travdist','trexpfac','dpurp')
    atripdist=pd.DataFrame()
    atripdist['Average Distance ('+name1+')']=pd.Series.round(atripdist1['travdist_wa'],1)
    atripdist['Average Distance ('+name2+')']=pd.Series.round(atripdist2['travdist_wa'],1)
    atripdist['Difference']=atripdist['Average Distance ('+name1+')']-atripdist['Average Distance ('+name2+')']
    atripdist['Percent Difference']=pd.Series.round(atripdist['Difference']/atripdist['Average Distance ('+name2+')']*100,1)
    atripdist=recode_index(atripdist,'dpurp','Trip Purpose')

    #Average Distance by Tour Mode
    triptotalm1=weighted_average(tourtrip1,'tautodist','trexpfac','tmodetp')
    triptotalm2=weighted_average(tourtrip2,'tautodist','trexpfac','tmodetp')
    atlm1=pd.DataFrame.from_items([('Average Trip Length ('+name1+')',pd.Series.round(triptotalm1['tautodist_wa'],1))])
    atlm2=pd.DataFrame.from_items([('Average Trip Length ('+name2+')',pd.Series.round(triptotalm2['tautodist_wa'],1))])
    atlm=pd.merge(atlm1,atlm2,'outer',left_index=True,right_index=True)
    atlm['Difference']=atlm['Average Trip Length ('+name1+')']-atlm['Average Trip Length ('+name2+')']
    atlm['Percent Difference']=pd.Series.round((atlm['Difference']/atlm['Average Trip Length ('+name2+')'])*100,1)
    atlm=recode_index(atlm,'tmodetp','Tour Mode')

    #Number of Trips by Tour Mode
    tourtotalm1=weighted_average(toursnotrips1,'notrips','toexpfac','tmodetp')
    tourtotalm2=weighted_average(toursnotrips2,'notrips','toexpfac','tmodetp')
    ttdm=tourtotalm1['notrips_wa']-tourtotalm2['notrips_wa']
    ttpdm=(tourtotalm1['notrips_wa']-tourtotalm2['notrips_wa'])/tourtotalm2['notrips_wa']*100
    nttpm1=pd.DataFrame.from_items([('Average Number of Trips per Tour ('+name1+')',pd.Series.round(tourtotalm1['notrips_wa'],1))])
    nttpm2=pd.DataFrame.from_items([('Average Number of Trips per Tour ('+name2+')',pd.Series.round(tourtotalm2['notrips_wa'],1))])
    nttpm=pd.merge(nttpm1,nttpm2,'outer',left_index=True,right_index=True)
    nttpm['Difference']=pd.Series.round(ttdm,1)
    nttpm['Percent Difference']=pd.Series.round(ttpdm,1)
    nttpm=recode_index(nttpm,'tmodetp','Tour Mode')

    #Average Distance by Trip Mode
    atripdist1m=weighted_average(data1['Trip'],'travdist','trexpfac','mode')
    atripdist2m=weighted_average(data2['Trip'],'travdist','trexpfac','mode')
    atripdistm=pd.DataFrame()
    atripdistm['Average Distance ('+name1+')']=pd.Series.round(atripdist1m['travdist_wa'],1)
    atripdistm['Average Distance ('+name2+')']=pd.Series.round(atripdist2m['travdist_wa'],1)
    atripdistm['Difference']=atripdistm['Average Distance ('+name1+')']-atripdistm['Average Distance ('+name2+')']
    atripdistm['Percent Difference']=pd.Series.round(atripdistm['Difference']/atripdistm['Average Distance ('+name2+')']*100,1)
    atripdistm=recode_index(atripdistm,'mode','Trip Mode')

    ##Tours and Trips by Destination District
    #Percent of Tours by Destination District
    toursdest1=pd.merge(tour_ok_1,districtfile,'outer',left_on='tdtaz',right_on='TAZ')
    toursdest2=pd.merge(tour_ok_2,districtfile,'outer',left_on='tdtaz',right_on='TAZ')
    dist1=toursdest1.groupby('New DistrictName').sum()['toexpfac']
    dist2=toursdest2.groupby('New DistrictName').sum()['toexpfac']
    tourdestshare1=pd.Series.round(dist1/Tour_1_total*100,1)
    tourdestshare2=pd.Series.round(dist2/Tour_2_total*100,1)
    tourdest=pd.DataFrame()
    tourdest['Percent of Tours ('+name1+')']=tourdestshare1
    tourdest['Percent of Tours ('+name2+')']=tourdestshare2
    tourdest['Difference']=tourdestshare1-tourdestshare2

    #Percent of Trips by Destination District
    tripsdest1=pd.merge(trip_ok_1,districtfile,'outer',left_on='dtaz',right_on='TAZ')
    tripsdest2=pd.merge(trip_ok_2,districtfile,'outer',left_on='dtaz',right_on='TAZ')
    tdist1=tripsdest1.groupby('New DistrictName').sum()['trexpfac']
    tdist2=tripsdest2.groupby('New DistrictName').sum()['trexpfac']
    tripdestshare1=pd.Series.round(tdist1/Trip_1_total*100,1)
    tripdestshare2=pd.Series.round(tdist2/Trip_2_total*100,1)
    tripdest=pd.DataFrame()
    tripdest['Percent of Trips ('+name1+')']=tripdestshare1
    tripdest['Percent of Trips ('+name2+')']=tripdestshare2
    tripdest['Difference']=tripdestshare1-tripdestshare2

    #Compile the file
    writer=pd.ExcelWriter(location+'/DaysimDestChoiceReport.xlsx',engine='xlsxwriter')
    atl.to_excel(excel_writer=writer,sheet_name='Average Dist by Tour Purpose',na_rep='NA',)
    atlm.to_excel(excel_writer=writer,sheet_name='Average Dist by Tour Mode',na_rep='NA')
    nttp.to_excel(excel_writer=writer,sheet_name='Trips per Tour by Tour Purpose',na_rep='NA')
    nttpm.to_excel(excel_writer=writer,sheet_name='Trips per Tour by Tour Mode',na_rep='NA')
    atripdist.to_excel(excel_writer=writer,sheet_name='Average Dist by Trip Purpose',na_rep='NA')
    atripdistm.to_excel(excel_writer=writer,sheet_name='Average Dist by Trip Mode',na_rep='NA')
    tourdest.to_excel(excel_writer=writer,sheet_name='% Tours by Destination District',na_rep='NA')
    tripdest.to_excel(excel_writer=writer,sheet_name='% Trips by Destination District',na_rep='NA')
    workbook=writer.book
    colors=['#ed3300','#00529f']
    for sheet in writer.sheets:
        worksheet=writer.sheets[sheet]
        worksheet.set_column(0,worksheet.dim_colmax,width=35)
        worksheet.freeze_panes(0,1)
        chart=workbook.add_chart({'type':'column'})
        for col_num in range(1,3):
            chart.add_series({'name':[sheet, 0, col_num],
                                'categories':[sheet,2,0,worksheet.dim_rowmax,0],
                                'values':[sheet,2,col_num,worksheet.dim_rowmax,col_num],
                                'fill':{'color':colors[col_num-1]}})
        chart.set_legend({'position':'top'})
        chart.set_size({'x_scale':2,'y_scale':1.5})
        worksheet.insert_chart('B15',chart)
    writer.save()

    print('Destination Choice Report successfully compiled in '+str(round(time.time()-start,1))+' seconds')

def ModeChoice(data1,data2,name1,name2,location):
    start=time.time()
    
    #Subsection Vehicle Miles Per Person
    merge_per_hh_1=pd.merge(data1['Person'],data1['Household'],'outer')
    merge_per_hh_2=pd.merge(data2['Person'],data2['Household'],'outer')
    label=[]
    value1=[]
    value2=[]
    Person_1_total=get_total(merge_per_hh_1['psexpfac'])
    Person_2_total=get_total(merge_per_hh_2['psexpfac'])
    label.append('Number of People')
    value1.append(int(round(Person_1_total,-5)))
    value2.append(int(round(Person_2_total,-5)))
    Trip_1_total=get_total(data1['Trip']['trexpfac'])
    Trip_2_total=get_total(data2['Trip']['trexpfac'])
    label.append('Number of Trips')
    value1.append(int(round(Trip_1_total,-5)))
    value2.append(int(round(Trip_2_total,-5)))
    Tour_1_total=get_total(data1['Tour']['toexpfac'])
    Tour_2_total=get_total(data2['Tour']['toexpfac'])
    label.append('Number of Tours')
    value1.append(int(round(Tour_1_total,-5)))
    value2.append(int(round(Tour_2_total,-5)))
    tour_ok_1=data1['Tour'].query('tautodist>0 and tautodist<2000')
    tour_ok_2=data2['Tour'].query('tautodist>0 and tautodist<2000')
    trip_ok_1=data1['Trip'].query('travtime>0 and travtime<2000')
    trip_ok_2=data2['Trip'].query('travtime>0 and travtime<2000')

    vmpp=pd.DataFrame.from_items([('',label),(name1,value1),(name2,value2)])
    vmpp['Difference']=vmpp[name1]-vmpp[name2]
    vmpp['Percent Difference']=pd.Series.round(vmpp['Difference']/vmpp[name2]*100,1)
    vmpp=vmpp.set_index('')

    ##Subsection Tour Summaries

    #Mode Share
    mode1=data1['Tour'].groupby('tmodetp').sum()['toexpfac']
    mode2=data2['Tour'].groupby('tmodetp').sum()['toexpfac']
    modeshare1=pd.Series.round(mode1/Tour_1_total*100,1)
    modeshare2=pd.Series.round(mode2/Tour_2_total*100,1)
    msdf=pd.DataFrame()
    difference=modeshare1-modeshare2
    modeshare1=modeshare1.sort_index()
    msdf[name1+' Share']=modeshare1
    modeshare2=modeshare2.sort_index()
    msdf[name2+' Share']=modeshare2
    difference=difference.sort_index()
    msdf['Difference']=difference
    msdf=recode_index(msdf,'tmodetp','Mode')


    #Mode share by purpose
    tourpurpmode1=pd.DataFrame.from_items([('Purpose',data1['Tour']['pdpurp']),('Mode',data1['Tour']['tmodetp']),('Expansion Factor',data1['Tour']['toexpfac'])])
    tourpurpmode2=pd.DataFrame.from_items([('Purpose',data2['Tour']['pdpurp']),('Mode',data2['Tour']['tmodetp']),('Expansion Factor',data2['Tour']['toexpfac'])])
    tourpurp1=tourpurpmode1.groupby('Purpose').sum()['Expansion Factor']
    tourpurp2=tourpurpmode2.groupby('Purpose').sum()['Expansion Factor']
    tpm1=pd.DataFrame({name1+' Share': tourpurpmode1.groupby(['Purpose','Mode']).sum()['Expansion Factor']/tourpurp1*100},dtype='float').reset_index()
    tpm2=pd.DataFrame({name2+' Share': tourpurpmode2.groupby(['Purpose','Mode']).sum()['Expansion Factor']/tourpurp2*100},dtype='float').reset_index()
    tpm=pd.merge(tpm1,tpm2,'outer')
    tpm=tpm.sort(name2+' Share')

    nrows=pd.Series.value_counts(tpm['Purpose'])
    halfcols=pd.Series.value_counts(tpm['Mode'])
    modenames=halfcols.index
    ncols=[]
    for i in range(len(modenames)):
        ncols.append(modenames[i].encode('ascii','replace')+' ('+name1+')')
        ncols.append(modenames[i].encode('ascii','replace')+' ('+name2+')')
    mbpcdf=pd.DataFrame()
    for column in ncols:   
        filler=pd.Series()
        for purpose in nrows.index:
            filler[purpose]=float('Nan')
        mbpcdf[column]=filler

    for i in range(len(tpm['Purpose'])):
        mbpcdf[tpm['Mode'][i]+' ('+name1+')'][tpm['Purpose'][i]]=round(tpm[name1+' Share'][i],1)
        mbpcdf[tpm['Mode'][i]+' ('+name2+')'][tpm['Purpose'][i]]=round(tpm[name2+' Share'][i],1)

    #Trip Mode by Tour Mode
    tourtrip1=pd.merge(data1['Tour'],data1['Trip'],on=['hhno','pno','tour'])
    tourtrip2=pd.merge(data2['Tour'],data2['Trip'],on=['hhno','pno','tour'])
    counts1=pd.DataFrame({name1+' Count':tourtrip1.groupby(['tmodetp','mode']).sum()['trexpfac']})
    counts2=pd.DataFrame({name2+' Count':tourtrip2.groupby(['tmodetp','mode']).sum()['trexpfac']})
    tcounts=pd.merge(counts1,counts2,left_index=True,right_index=True)
    tcounts.reset_index(inplace=True)
    nrows=pd.Series.value_counts(tourtrip2['tmodetp'])
    halfcols=pd.Series.value_counts(tourtrip2['mode'])
    modenames=halfcols.index
    ncols=[]
    for i in range(len(modenames)):
        ncols.append(modenames[i].encode('ascii','replace')+' ('+name1+')')
        ncols.append(modenames[i].encode('ascii','replace')+' ('+name2+')')
    tmbtm=pd.DataFrame()
    for column in ncols:   
        filler=pd.Series()
        for tourmode in nrows.index:
            filler[tourmode]=0
        tmbtm[column]=filler
    for i in range(len(tcounts.index)):
        tmbtm[tcounts['mode'][i]+' ('+name1+')'][tcounts['tmodetp'][i]]=int(round(tcounts[name1+' Count'][i],0))
        tmbtm[tcounts['mode'][i]+' ('+name2+')'][tcounts['tmodetp'][i]]=int(round(tcounts[name2+' Count'][i],0))

    ##Trip Cross-Tabulations

    #Tours by Mode and Travel Time
    df1=data1['Tour']
    df2=data2['Tour']
    df1['atimesp']=df1['tautotime']*df1['toexpfac']
    df1['adistsp']=df1['tautodist']*df1['toexpfac']
    df1['acostsp']=df1['tautocost']*df1['toexpfac']
    df2['atimesp']=df2['tautotime']*df2['toexpfac']
    df2['adistsp']=df2['tautodist']*df2['toexpfac']
    df2['acostsp']=df2['tautocost']*df2['toexpfac']
    tgrouped1=df1.groupby('tmodetp').sum()
    tgrouped2=df2.groupby('tmodetp').sum()
    tgrouped1['matime']=tgrouped1['atimesp']/tgrouped1['toexpfac']
    tgrouped1['madist']=tgrouped1['adistsp']/tgrouped1['toexpfac']
    tgrouped1['macost']=tgrouped1['acostsp']/tgrouped1['toexpfac']
    tgrouped2['matime']=tgrouped2['atimesp']/tgrouped2['toexpfac']
    tgrouped2['madist']=tgrouped2['adistsp']/tgrouped2['toexpfac']
    tgrouped2['macost']=tgrouped2['acostsp']/tgrouped2['toexpfac']
    toursmtt1=pd.DataFrame()
    toursmtt2=pd.DataFrame()
    toursmtt1['Mean Auto Time ('+name1+')']=pd.Series.round(tgrouped1['matime'],2)
    toursmtt2['Mean Auto Time ('+name2+')']=pd.Series.round(tgrouped2['matime'],2)
    toursmtt=pd.merge(toursmtt1,toursmtt2,'outer',left_index=True,right_index=True)
    toursmtt['Mean Auto Distance ('+name1+')']=pd.Series.round(tgrouped1['madist'],2)
    toursmtt['Mean Auto Distance ('+name2+')']=pd.Series.round(tgrouped2['madist'],2)
    toursmtt['Mean Auto Cost ('+name1+')']=pd.Series.round(tgrouped1['macost'],2)
    toursmtt['Mean Auto Cost ('+name2+')']=pd.Series.round(tgrouped2['macost'],2)
    toursmtt=recode_index(toursmtt,'tmodetp','Mode')

    #Trips by Mode and Travel Time
    tripdf1=data1['Trip']
    tripdf2=data2['Trip']
    tripsmtt1=pd.DataFrame()
    tripsmtt2=pd.DataFrame()
    tripm1=tripdf1.groupby('mode').sum()['trexpfac']
    tripm2=tripdf2.groupby('mode').sum()['trexpfac']
    tms1=tripm1/Trip_1_total*100
    tms2=tripm2/Trip_2_total*100
    tripsmtt1['Total Trips ('+name1+')']=pd.Series.round(tripm1,-4)
    tripsmtt2['Total Trips ('+name2+')']=pd.Series.round(tripm2,-4)
    tripsmtt=pd.merge(tripsmtt1,tripsmtt2,'outer',left_index=True,right_index=True)
    tripsmtt['Mode Share ('+name1+')']=pd.Series.round(tms1,1)
    tripsmtt['Mode Share ('+name2+')']=pd.Series.round(tms2,1)
    tripdf1['atimesp']=tripdf1['travtime']*tripdf1['trexpfac']
    tripdf1['adistsp']=tripdf1['travdist']*tripdf1['trexpfac']
    tripdf1['acostsp']=tripdf1['travcost']*tripdf1['trexpfac']
    tripdf2['atimesp']=tripdf2['travtime']*tripdf2['trexpfac']
    tripdf2['adistsp']=tripdf2['travdist']*tripdf2['trexpfac']
    tripdf2['acostsp']=tripdf2['travcost']*tripdf2['trexpfac']
    tripgrouped1=tripdf1.groupby('mode').sum()
    tripgrouped2=tripdf2.groupby('mode').sum()
    tripgrouped1['matime']=tripgrouped1['atimesp']/tripgrouped1['trexpfac']
    tripgrouped1['madist']=tripgrouped1['adistsp']/tripgrouped1['trexpfac']
    tripgrouped1['macost']=tripgrouped1['acostsp']/tripgrouped1['trexpfac']
    tripgrouped2['matime']=tripgrouped2['atimesp']/tripgrouped2['trexpfac']
    tripgrouped2['madist']=tripgrouped2['adistsp']/tripgrouped2['trexpfac']
    tripgrouped2['macost']=tripgrouped2['acostsp']/tripgrouped2['trexpfac']
    tripsmtt['Mean Auto Time ('+name1+')']=pd.Series.round(tripgrouped1['matime'],2)
    tripsmtt['Mean Auto Time ('+name2+')']=pd.Series.round(tripgrouped2['matime'],2)
    tripsmtt['Mean Auto Distance ('+name1+')']=pd.Series.round(tripgrouped1['madist'],2)
    tripsmtt['Mean Auto Distance ('+name2+')']=pd.Series.round(tripgrouped2['madist'],2)
    tripsmtt['Mean Auto Cost ('+name1+')']=pd.Series.round(tripgrouped1['macost'],2)
    tripsmtt['Mean Auto Cost ('+name2+')']=pd.Series.round(tripgrouped2['macost'],2)
    tripsmtt=recode_index(tripsmtt,'mode','Mode')

    #Trip by purpose and travel time
    ttdf1=data1['Trip']
    ttdf2=data2['Trip']
    ttdf1['ttsp']=ttdf1['travtime']*ttdf1['trexpfac']
    ttdf2['ttsp']=ttdf2['travtime']*ttdf2['trexpfac']
    ttdf1['tdsp']=ttdf1['travdist']*ttdf1['trexpfac']
    ttdf2['tdsp']=ttdf2['travdist']*ttdf2['trexpfac']
    tt1im=ttdf1.groupby(['mode','dpurp']).sum()['trexpfac']
    tt2im=ttdf2.groupby(['mode','dpurp']).sum()['trexpfac']
    tt1=pd.DataFrame(tt1im)
    tt2=pd.DataFrame(tt1im)
    ttrips1im=ttdf1.groupby(['mode','dpurp']).sum()
    ttrips2im=ttdf2.groupby(['mode','dpurp']).sum()
    ttrips1=pd.DataFrame(ttrips1im)
    ttrips2=pd.DataFrame(ttrips2im)
    ttrips1['mtt']=pd.Series.round(ttrips1['ttsp']/ttrips1['trexpfac'],1)
    ttrips2['mtt']=pd.Series.round(ttrips2['ttsp']/ttrips2['trexpfac'],1)
    ttrips1['mtd']=pd.Series.round(ttrips1['tdsp']/ttrips1['trexpfac'],1)
    ttrips2['mtd']=pd.Series.round(ttrips2['tdsp']/ttrips2['trexpfac'],1)
    full1=pd.merge(tt1,ttrips1,'outer',left_index=True,right_index=True)
    full2=pd.merge(tt2,ttrips2,'outer',left_index=True,right_index=True)
    full1=full1.reset_index()
    full2=full2.reset_index()
    tptt1=pd.DataFrame.from_items([('Mode',full1['mode']),('Purpose',full1['dpurp']),('Total Trips ('+name1+')',full1['trexpfac_x']),('Mean Time ('+name1+')',full1['mtt']),('Mean Distance ('+name1+')',full1['mtd'])])
    tptt2=pd.DataFrame.from_items([('Mode',full2['mode']),('Purpose',full2['dpurp']),('Total Trips ('+name2+')',full2['trexpfac_x']),('Mean Time ('+name2+')',full2['mtt']),('Mean Distance ('+name2+')',full2['mtd'])])
    tptt=pd.merge(tptt1,tptt2,'outer')
    tptt=tptt.sort_index(axis=1,ascending=False)
    tptt=tptt.set_index(['Mode','Purpose'])

    #Write DataFrames to Excel File
    writer=pd.ExcelWriter(location+'/ModeChoiceReport.xlsx',engine='xlsxwriter')
    vmpp.to_excel(excel_writer=writer,sheet_name='# People, Trips, and Tours',na_rep='NA')
    msdf.to_excel(excel_writer=writer,sheet_name='Mode Share',na_rep='NA')
    mbpcdf.to_excel(excel_writer=writer,sheet_name='Mode Share by Purpose',na_rep='NA')
    tmbtm.to_excel(excel_writer=writer,sheet_name='Trip Mode by Tour Mode',na_rep='NA')
    toursmtt.to_excel(excel_writer=writer,sheet_name='Tours by Mode & Travel Time',na_rep='NA')
    tripsmtt.to_excel(excel_writer=writer,sheet_name='Trips by Mode & Travel Time',na_rep='NA')
    tptt.to_excel(excel_writer=writer,sheet_name='Trips by Purpose & Travel Time',na_rep='NA')
    workbook=writer.book
    colors=['#ed3300','#00529f']
    for sheet in writer.sheets:
        worksheet=writer.sheets[sheet]
        worksheet.set_column(0,worksheet.dim_colmax,width=35)
        worksheet.freeze_panes(0,1)
        if sheet in ['# People, Trips, and Tours','Mode Share']:
            chart=workbook.add_chart({'type':'column'})
            for col_num in range(1,3):
                if sheet=='# People, Trips, and Tours':
                    chart.add_series({'name':[sheet, 0, col_num],
                                        'categories':[sheet,1,0,worksheet.dim_rowmax,0],
                                        'values':[sheet,1,col_num,worksheet.dim_rowmax,col_num],
                                        'fill':{'color':colors[col_num-1]}})
                    chart.set_legend({'position':'top'})
                    chart.set_size({'x_scale':2,'y_scale':1.75})
                else:
                    chart.add_series({'name':[sheet, 0, col_num],
                                        'categories':[sheet,2,0,worksheet.dim_rowmax,0],
                                        'values':[sheet,2,col_num,worksheet.dim_rowmax,col_num],
                                        'fill':{'color':colors[col_num-1]}})
                    chart.set_legend({'position':'top'})
                    chart.set_size({'x_scale':2,'y_scale':1.75})
            worksheet.insert_chart('B12',chart)
        elif sheet in ['Mode Share by Purpose','Trip Mode by Tour Mode']:
            chart=workbook.add_chart({'type':'column'})
            for row_num in range(1,worksheet.dim_rowmax):
                chart.add_series({'name':[sheet,row_num,0],
                                    'categories':[sheet,0,1,0,worksheet.dim_colmax],
                                    'values':[sheet,row_num,1,row_num,worksheet.dim_colmax]})
            chart.set_legend({'position':'top'})
            chart.set_size({'x_scale':2,'y_scale':1.75})
            worksheet.insert_chart('B12',chart)
        elif sheet in ['Tours by Mode & Travel Time','Trips by Mode & Travel Time']:
            chart=workbook.add_chart({'type':'column'})
            for row_num in range(2,worksheet.dim_rowmax):
                chart.add_series({'name':[sheet,row_num,0],
                                    'categories':[sheet,0,1,0,worksheet.dim_colmax],
                                    'values':[sheet,row_num,1,row_num,worksheet.dim_colmax]})
            chart.set_legend({'position':'top'})
            chart.set_size({'x_scale':2,'y_scale':1.75})
            worksheet.insert_chart('B12',chart)
    writer.save()

    print('Mode Choice Report successfully compiled in '+str(round(time.time()-start,1))+' seconds')
    
DaysimReport(data1,data2,name1,name2,location,zone_district)
ModeChoice(data1,data2,name1,name2,location)
DestChoice(data1,data2,name1,name2,location,zone_district)