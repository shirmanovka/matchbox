import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import streamlit as st
import requests
import json

moex_url = 'https://iss.moex.com/iss/engines/stock/markets/bonds/boards/TQCB/securities.json'
response = requests.get(moex_url) #получим ответ от сервера
result = json.loads(response.text)
col_name = result['securities']['columns'] # описываем какие колонки нахоядтся в матоданных #securuties или #history
data_bonds_securities = pd.DataFrame(columns = col_name)
# Часть_2 заполняем дата фрейм
moex_url_securities = 'https://iss.moex.com/iss/engines/stock/markets/bonds/boards/TQCB/securities.json' #TQOB ОФЗ
response = requests.get(moex_url_securities)
result = json.loads(response.text)
resp_date = result['securities']['data']
securities_data_bonds = pd.DataFrame(resp_date, columns = col_name)
a = len(resp_date)

#Маленькая таблица сформированная из основной, показывающая краткий свод информации.
securities_data_bonds = securities_data_bonds[securities_data_bonds['FACEUNIT'] == 'SUR']
s_df = securities_data_bonds[['SECID',  'PREVLEGALCLOSEPRICE']].copy()
s_df = s_df.rename(columns ={'SECID': 'ISIN'})
s_df = s_df.rename(columns ={'PREVLEGALCLOSEPRICE': 'Цена, пп'})

 


# Читаем файл xlsx
df = pd.read_excel(('Карта рынка.xlsx'), skiprows=1)
df = df.rename(columns ={'Цена, пп': 'Цена, пп1'}) # переименовал столбец чтобы его заменить


df = pd.merge(s_df, df, on='ISIN', how='inner') #соеденил две таблицы, а дальше как в обычном расчете.


df['Объем, млн'] = pd.to_numeric(df['Объем, млн'], errors='coerce')  # Преобразует в NaN некорректные значения
# Формируем расчетные столбцы
df['spread'] = (df['Спред, пп'] * 100)
df['Yield'] = ((100 - df['Цена, пп']) * 100) / df['Срок  до погашения / оферты, лет']
df['Cupon'] = df['spread'] / df['Цена, пп'] * 100 - df['spread']
df['Cspread'] = round(df['spread'] + df['Cupon'] + df['Yield'])
df['deltaS'] = round((df['Cspread'] - df['spread']),0)
df['Name_rating_gap'] = df.apply(lambda row: f"{row['Тикер']}, {row['Рейтинг']}, {row['deltaS']}", axis=1)
df['Размещениеt'] = pd.to_datetime(df['Размещение'], dayfirst=True)
df['Размещениеt'] = df['Размещениеt'].dt.date
df = df.sort_values(by='Размещениеt',ascending=True) #Cортируем от малых к большим

#Создаем новый дата фрейм который и выводим на экран
df1 = df[['ISIN', 'Тикер', 'Рейтинг', 'Валюта', 'Цена, пп', 
           'Срок  до погашения / оферты, лет', 'Частота купонных выплат', 
           'Базовая ставка', 'Опцион', 'Погашение','Размещениеt',
           'spread', 'Cspread', 'deltaS', 'Name_rating_gap']].copy()

# Создаем Streamlit интерфейс
st.title('Matchbox')
st.header('Карта рынка флоутеров, данные отражены в режиме Т-1')

          
# Поле для ввода списка ISIN
isin_input = st.text_area("Введите свои ISIN (по одному на строку):", height=150)

# Преобразуем введенный текст в список ISIN
input_isin_list = [line.strip() for line in isin_input.splitlines() if line.strip()]
 
# Фильтры для столбцов
tickers = df1['Тикер'].unique()
selected_tickers = st.multiselect('Выберите тикер:', tickers)
 
ratings = df1['Рейтинг'].unique()
selected_ratings = st.multiselect('Выберите рейтинг:', ratings)
 
# Фильтр по дате
#min_date = df1['Размещениеt'].min()
#max_date = df1['Размещениеt'].max()
#start_date = st.date_input('Выберите начальную дату:', min_value=min_date, max_value=max_date, value=min_date)
#end_date = st.date_input('Выберите конечную дату:', min_value=start_date, max_value=max_date, value=max_date)

# Установка дат для фильтрации
min_date = df1['Размещениеt'].min()  # Минимальная дата из датафрейма
max_date = df1['Размещениеt'].max()  # Максимальная дата из датафрейма
default_start_date = pd.to_datetime('2024-01-01').date()  # Дата по умолчанию

# Установка фильтров с дефолтной датой 01.01.2024
start_date = st.date_input('Выберите начальную дату:', 
                            min_value=min_date, 
                            max_value=max_date, 
                            value=default_start_date)
end_date = st.date_input('Выберите конечную дату:', 
                          min_value=start_date, 
                          max_value=max_date, 
                          value=max_date)

#Фильтрация данных
f_df = df1[
    (df1['ISIN'].isin(input_isin_list) | (len(input_isin_list) == 0)) &
    (df1['Тикер'].isin(selected_tickers) | (len(selected_tickers) == 0)) &
    (df1['Рейтинг'].isin(selected_ratings) | (len(selected_ratings) == 0)) &
    (df1['Размещениеt'] >= start_date) &
    (df1['Размещениеt'] <= end_date)
]

# Возможность удаления строк
if not f_df.empty:
    # Позволяем пользователю выбрать строки для удаления по индексу
    indices_to_delete = st.multiselect(
        'Выберите строки для удаления (по индексу):', options=f_df.index.tolist(), default=[]
    )
    
    # Удаляем выбранные строки из отфильтрованного DataFrame
    f_df = f_df.drop(index=indices_to_delete)

# Отображение отфильтрованного DataFrame
st.dataframe(f_df)
 
# Построение графика
if not f_df.empty:
    plt.figure(figsize=(12, 6))
 
    plt.scatter(f_df['Размещениеt'], f_df['Cspread'], color='darkred', marker='o', s=80, label='Текущий спред')
    plt.scatter(f_df['Размещениеt'], f_df['spread'], color='tan', marker='o', s=80, label='Спред при размещении')
 
    for i, row in f_df.iterrows():
        plt.text(row['Размещениеt'], row['spread'] + 4, row['Name_rating_gap'], ha='left', fontsize=10)
        
    for i in range(len(f_df)):
        for j in range(len(f_df)):
                    if f_df['Размещениеt'].iloc[i] == f_df['Размещениеt'].iloc[j]:
                    
                            plt.annotate ('', xy = (f_df['Размещениеt'].iloc[j], f_df['Cspread'].iloc[j]),
                                            xytext=(f_df['Размещениеt'].iloc[i], f_df['spread'].iloc[i]),
                                            arrowprops =dict(arrowstyle='->', color='goldenrod', linewidth=2, shrinkA=7,shrinkB=7)) #Рисуем стрелки над точками.    
 
    plt.title('Карта рынка', fontsize=18)
    plt.xlabel('Дата размещения', fontsize=16)
    plt.ylabel('Спред к КС', fontsize=16)
    plt.legend()
    plt.grid()
    plt.xticks(rotation=45)
 
    # Показываем график в Streamlit
    st.pyplot(plt)
else:
    st.write("Нет данных для отображения.")



st.write("*Если облигационный выпуск имеет амортизацию, то расчет изменения спреда ее не учитывает.")
