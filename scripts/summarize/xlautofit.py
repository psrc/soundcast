import xlrd

def run(file): #This function "autofits" all of the columns in the workbook. However, it removes all charts and images
    print('WARNING: Running xlautofit.run() removes charts, images, and styles')
    import openpyxl
    wd={}
    colnums=[]
    book=xlrd.open_workbook(file,on_demand=True)
    sheetnames=book.sheet_names()
    for sheet in sheetnames:
        ws=book.sheet_by_name(sheet)
        colwidths=[]
        cols=ws.ncols
        for colnum in range(cols):
            widths=[]
            for rownum in range(len(ws.col(colnum))):
                widths.append(len(str(ws.cell(rownum,colnum)))-7)
            colwidths.append(0.96*max(widths))
        wd.update({sheet:colwidths})
        colnums.append(cols)
    wbook=openpyxl.load_workbook(file)
    for sheetnum in range(len(wbook.get_sheet_names())):
        wsheet=wbook.get_sheet_by_name(wbook.get_sheet_names()[sheetnum])
        for colnum in range(colnums[sheetnum]):
            wsheet.column_dimensions[openpyxl.cell.get_column_letter(colnum+1)].width=wd[sheetnames[sheetnum]][colnum]
    wbook.save(file)

def getwidths(file): #This function returns a dictionary where the keys are the sheet names and the values are lists of the necessary column widths for the sheet
    wd={}
    book=xlrd.open_workbook(file,on_demand=True)
    sheetnames=book.sheet_names()
    for sheet in sheetnames:
        ws=book.sheet_by_name(sheet)
        colwidths=[]
        cols=ws.ncols
        for colnum in range(cols):
            widths=[]
            for rownum in range(len(ws.col(colnum))):
                widths.append(len(str(ws.cell(rownum,colnum)))-7)
            colwidths.append(0.96*max(widths))
        wd.update({sheet:colwidths})
    return(wd)