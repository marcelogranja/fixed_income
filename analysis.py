# -*- coding: utf-8 -*-
"""
Created on Wed May 18 23:02:58 2016

@author: marcelo

hypothesis data sources:
http://www.bcb.gov.br/pec/GCI/PORT/readout/readout.asp
https://www.itau.com.br/itaubba-pt/analises-economicas/projecoes/longo-prazo-dezembro-de-2016
http://www.economiaemdia.com.br/vgn-ext-templating/v/index.jsp?vgnextoid=065098037f782310VgnVCM100000882810acRCRD

"""

import datetime
import sqlite3
import pandas as pd
#import matplotlib.pyplot as plt


CURRENT_YEAR = datetime.datetime.now().year

# hypothesis regarding inflation and interest rates obtained \
# from boletim focus and historical worst case scenario

h_focus = {
2016:(6.5, 14.16),
2017:(4.9, 11.63),
2018:(4.2, 8.7),
2019:(4.0, 7.7),
2020:(4.0, 7.7),
2021:(4.0, 7.7),  
2022:(4.0, 7.7)
}

h_worst = {
2016:6.5,
2017:5.5,
2018:6.,
2019:6.,
2020:6.,
2021:6.,
2022:6.
}


# copies selic into worst case scenario
for year in h_worst.keys():
    if type(h_worst[year]) == type(1.):
        h_worst[year] = ( h_worst[year], h_focus[year][1] )
        

# creates mixed scenario
h_mix = {}
for year in h_worst.keys():
    ipca = (h_worst[year][0] + h_focus[year][0]) / 2
    selic = (h_worst[year][1] + h_focus[year][1]) / 2
    h_mix[year] = (ipca, selic)


#TODO: IGPM projection
def calc_interest(x, year):
    ''' returns interest yearly multiplier '''
    ipca, selic = h[year]

    if x['indice'] == 'IPCA' or x['indice'] == 'IGPM':
        return ( 1. + x['taxa'] / 100 )  * ipca
    elif x['indice'] == 'PRE':
        return 1. + x['taxa'] / 100
    elif x['indice'] == 'CDI':
        return 1. + (x['taxa'] / 100 * selic) / 100


def calc_tax(x, acc_bruto):
    ''' calculates income tax by considering gross multipliers, e.g. for 5yo bond, 
    a 60% gross profit, ie, 1.60, is returned as 1.51'''
    
    if x['tipo'] in ['LCA', 'LCI']:
        irpf = 1.00
    elif x['vencimento'] < 180:
        irpf = 1. - 0.225
    elif x['vencimento'] < 360:
        irpf = 1. - 0.200
    elif x['vencimento'] < 720:
        irpf = 1. - 0.175
    else:
        irpf = 1. - 0.150
    return 1. + (acc_bruto - 1. ) * irpf


def calc_return(x):

    # computes remaining period during current year
    base_date = datetime.date(CURRENT_YEAR, 01, 01)
    today_date = datetime.date.today()
    first_year_residual = 1. - 1. * (today_date - base_date).days / 365
    
    main_period = int(x['prazo'] - first_year_residual)
    
    # computes remaining period during last year
    last_year_residual = x['prazo'] - main_period - first_year_residual
    
    #vector of multipliers across the years, eg. yearly inflation multiplier = 1.065
    interest_yearly = []
    inflation_yearly = []
    
    # calcs for the remaining of the current year
    interest_yearly.append( calc_interest(x, CURRENT_YEAR)  ** first_year_residual )
    inflation_yearly.append( h[CURRENT_YEAR][0]  ** first_year_residual )
    
    # calcs for year that are in the middle
    for year in range(CURRENT_YEAR + 1, CURRENT_YEAR + 1 + main_period ):
        interest_yearly.append( calc_interest(x, year) )
        inflation_yearly.append( h[year][0] )
    
    # calcs for the final year
    final_year = CURRENT_YEAR + 1 + main_period
    interest_yearly.append( calc_interest(x, final_year)  ** last_year_residual )
    inflation_yearly.append( h[final_year][0]  ** last_year_residual )
    
    # calcs total money groth and the maximum initial investment to be covered by FGC
    interest_acc = reduce( (lambda x, y: x*y), interest_yearly )
    fgc_limit  = 250. / interest_acc
    
    # removes taxes
    juros_after_tax = calc_tax(x, interest_acc)
    
    # compesates for inflation
    inflation_acc = reduce( (lambda x, y: x*y), inflation_yearly )
    real_interest = juros_after_tax / inflation_acc
    
    #calcs CAGR
    cagr = 100. * (real_interest ** (1. / x['prazo']) - 1 )

    return [cagr, fgc_limit]



def calc_color(x):
    ''' Auxiliary functions to help plot data'''
    
    if x['indice'] == 'IPCA' or x['indice'] == 'IGPM':
        return 'g'
    elif x['indice'] == 'PRE':
        return 'r'
    elif x['indice'] == 'CDI':
        return 'y'


def calc_shape(x):
    ''' Auxiliary functions to help plot data'''
    
    if x['corretora'] in ['RICO', 'Ativa', 'Easynvest', 'XP', 'Orama']:
        return u'y'
    else:
        return u'n'



h = h_mix   #CHOOSE HYPOTHESIS SET <<<<<<<<<<<<<<<<<<<<<<<<<<

# project long term
for year in range(2016, 2080):
    last_year = h.keys()[-1]
    if year not in h.keys():
        h[year] = h[last_year]
    
#   converts data to yearly multipliers,eg. selic at 1.065    
    ipca = h[year][0]
    h[year] = ( 1. + ipca/100, selic )


con = sqlite3.connect('data.db')
date = str(datetime.datetime.now().date())
df = pd.read_sql_query('SELECT * FROM data WHERE data = "%s";' % date, con)

# securing and transforming dataframe

df['prazo'] = 1. * df['vencimento'] / 365
df['fgc'] = map( (lambda x: x.lower() in ['cdb','lc','lca','lci'] ), df['tipo'].tolist() )
df['cagr'], df['limite_fgc'] = zip( *df.apply(calc_return, axis=1) )
df['prazo'] = 1. * df['prazo'].round(decimals=0) #must be done after calc CAGR
df['cor'] = df.apply(calc_color, axis=1)
df['shape'] = df.apply(calc_shape, axis=1)



# filtering dataframe with sensable investment options 
df_filtered = df.query('fgc == True & minimo < 20000' )

df_filtered.plot.scatter(x='prazo', y='cagr', c=df['cor'], \
    s=100*pd.np.log10(df['minimo']+1), ylim=(4, 7.5))

print df_filtered.sort_values('cagr').tail(40)
print 'LEMBRAR DE VERIFICAR SE ESTA NA LISTA DE ASSOCIADOS DA FGC!!'

print df_filtered[['corretora','prazo','indice','cagr','nome']].sort_values('cagr').tail(40)

# computes best option for different time windows and indexes

# gets max CAGR by category
max_cagr_idxs = df_filtered[['cagr','indice','prazo']].groupby(['indice','prazo']).idxmax()
max_cagr_idxs = map( (lambda x: x[0]), max_cagr_idxs.values)

max_per_category = df_filtered.iloc[max_cagr_idxs]\
[['prazo','indice','fgc','cagr','minimo','limite_fgc','corretora','nome',]]\
.groupby(['prazo','indice']).head()
# if any IndexError occurs just go remove the filter on the dataframe

print max_per_category.sort_values(['prazo','indice'])
print 'LEMBRAR DE VERIFICAR SE ESTA NA LISTA DE ASSOCIADOS DA FGC!!'


# cor by corretora and shape by indice!


#x = df['prazo'].tolist()
#y = df['cagr'].tolist()
#c = df['cor'].tolist()
#m = df['shape'].tolist()
#s = df['minimo']._values
#s = 120*pd.np.log10(s+1)
# plt.scatter(x, y, s=s, c=c, marker=m)