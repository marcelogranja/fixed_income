 # -*- coding: utf-8 -*-
"""
Created on Wed May 18 18:34:10 2016

@author: marcelo

run daily by crontab at 1200 localtime
"""

import datetime
import sqlite3
from splinter import Browser
from bs4 import BeautifulSoup
from unidecode import unidecode
import re
import pandas as pd


# regex to remove nondecimal
non_decimal = re.compile(r'[^\d]+')

# regex to remove nonvalue
non_value = re.compile(r'[^\d,.]+')


# webscrapper
browser = Browser('phantomjs')
url = 'http://jurus.com.br/#/rendafixa/cdb'
browser.visit(url)

#click todos investimentos
browser.find_by_xpath('//*[@id="dvmodulo"]/nav/ul/li[1]/a')[0].click()

indices = {
'PRE' : '//*[@id="dvmodulo"]/div/div[2]/button[1]',
'CDI' : '//*[@id="dvmodulo"]/div/div[2]/button[2]',
'IPCA' : '//*[@id="dvmodulo"]/div/div[2]/button[3]',
'IGPM' : '//*[@id="dvmodulo"]/div/div[2]/button[4]' 
}

# struct html into table

table = []

for indice, indice_button in indices.items():
    
    #click button    
    browser.find_by_xpath(indice_button)[0].click()
    print'scrapping', indice    

    #get results
    page = browser.find_by_xpath('//*[@id="dvmodulo"]/div/table')[0].html
    soup = BeautifulSoup(page)
    
    for idx, row in enumerate(soup.find_all('tr')):
        if idx % 2 == 1:        
            tmp = row.find_all('th')
            tmp.extend(row.find_all('td'))
            
            tmp = map( lambda x: x.get_text(), tmp)
            tmp = map( lambda x: x.replace('\t','').replace('\n',''), tmp)
            table.append(tmp + [indice])
    

# cleans table and saves into dataframe

datum = []

for line in table:
    
    try:
        data = {}
        data['corretora'] = unidecode(line[0])
        data['nome'] = unidecode(line[1])
        data['tipo'] = line[2].replace(' ','')
        indice = line[7]    
        data['indice'] = indice
    
        #days to maturity
        date = line[3][:10]
        date = datetime.datetime.strptime(date,'%d/%m/%Y')
        delta = (date - datetime.datetime.now()).days
        data['vencimento'] = delta
        
        #rate
        taxa = line[4].split('~')[0]
        taxa = non_value.sub('', taxa) #removes non decimals        
        taxa = taxa.replace(',','.')
        taxa = float( taxa )
        data['taxa'] = taxa    

        #minimum investment value        
        value = non_decimal.sub('', line[6]) #removes non decimals
        value = float(value)/100
        data['minimo'] = value
        
        datum.append(data)

    except Exception, e:
        print str(e)
        print line
# todo: classificacao, liquidez, juros semestrais ou mensai    

#    data['classificacao'] = line
    
df = pd.DataFrame(datum)

date = str(datetime.datetime.now().date())
df['data'] = date

# save to db
con = sqlite3.connect('data.db')
df.to_sql('data',con, if_exists='append')
#df.to_pickle('data/'+date+'.pck')