import pandas as pd

xls = pd.ExcelFile('1340 - Costeo Pampa.xlsx')
sheets = ['1 MANO DE OBRA', 'Equipos', '3 SUMINISTRO DE INSUMOS', '4 SUBCONTRATACIONES']
for s in sheets:
    if s in xls.sheet_names:
        df = pd.read_excel('1340 - Costeo Pampa.xlsx', sheet_name=s)
        print('---', s, '---')
        print(df.columns.tolist())
        print(df.head(3).to_string())
