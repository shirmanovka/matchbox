import pandas as pd
import numpy as np
import streamlit as st
import requests
import json
import plotly.graph_objects as go

# Получение данных с MOEX
moex_url = 'https://iss.moex.com/iss/engines/stock/markets/bonds/boards/TQCB/securities.json'
response = requests.get(moex_url)
result = json.loads(response.text)
col_name = result['securities']['columns']
data_bonds_securities = pd.DataFrame(columns=col_name)

# Заполнение датафрейма
resp_date = result['securities']['data']
securities_data_bonds = pd.DataFrame(resp_date, columns=col_name)

# Фильтрация данных
securities_data_bonds = securities_data_bonds[securities_data_bonds['FACEUNIT'] == 'SUR']
s_df = securities_data_bonds[['SECID', 'PREVLEGALCLOSEPRICE']].copy()
s_df = s_df.rename(columns={'SECID': 'ISIN', 'PREVLEGALCLOSEPRICE': 'Цена, пп'})

# Чтение файла xlsx
df = pd.read_excel('Карта рынка.xlsx', skiprows=1)
df = df.rename(columns={'Цена, пп': 'Цена, пп1'})

# Объединение таблиц
df = pd.merge(s_df, df, on='ISIN', how='inner')

# Преобразование столбца
df['Объем, млн'] = pd.to_numeric(df['Объем, млн'], errors='coerce')

# Формирование расчетных столбцов
df['spread'] = (df['Спред, пп'] * 100)
df['Yield'] = ((100 - df['Цена, пп']) * 100) / df['Срок  до погашения / оферты, лет']
df['Cupon'] = df['spread'] / df['Цена, пп'] * 100 - df['spread']
df['Cspread'] = round(df['spread'] + df['Cupon'] + df['Yield'])
df['deltaS'] = round((df['Cspread'] - df['spread']), 0)
df['Name_rating_gap'] = df.apply(lambda row: f"{row['Тикер']}, {row['Рейтинг']}, {row['deltaS']}", axis=1)
df['Размещениеt'] = pd.to_datetime(df['Размещение'], dayfirst=True).dt.date
df = df.sort_values(by='Размещениеt', ascending=True)

# Создание нового датафрейма для отображения
df1 = df[['ISIN', 'Тикер', 'Рейтинг', 'Валюта', 'Цена, пп', 
           'Срок  до погашения / оферты, лет', 'Частота купонных выплат', 
           'Базовая ставка', 'Опцион', 'Погашение', 'Размещениеt',
           'spread', 'Cspread', 'deltaS', 'Name_rating_gap']].copy()

# Создание Streamlit интерфейса
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
min_date = df1['Размещениеt'].min()
max_date = df1['Размещениеt'].max()
start_date = st.date_input('Выберите начальную дату:', min_value=min_date, max_value=max_date, value=min_date)
end_date = st.date_input('Выберите конечную дату:', min_value=start_date, max_value=max_date, value=max_date)

# Фильтрация данных
f_df = df1[
    (df1['ISIN'].isin(input_isin_list) | (len(input_isin_list) == 0)) &
    (df1['Тикер'].isin(selected_tickers) | (len(selected_tickers) == 0)) &
    (df1['Рейтинг'].isin(selected_ratings) | (len(selected_ratings) == 0)) &
    (df1['Размещениеt'] >= start_date) &
    (df1['Размещениеt'] <= end_date)
]

# Возможность удаления строк
if not f_df.empty:
    indices_to_delete = st.multiselect(
        'Выберите строки для удаления (по индексу):', options=f_df.index.tolist(), default=[]
    )
    
    f_df = f_df.drop(index=indices_to_delete)

# Отображение отфильтрованного DataFrame
st.dataframe(f_df)

# Построение графика с использованием Plotly
if not f_df.empty:
    fig = go.Figure()

    # Добавление точек для текущего спреда
    fig.add_trace(go.Scatter(
        x=f_df['Размещениеt'],
        y=f_df['Cspread'],
        mode='markers+text',
        marker=dict(color='darkred', size=10),
        text=f_df['Name_rating_gap'],
        textposition='top center',
        name='Текущий спред'
    ))

    # Добавление точек для спреда при размещении
    fig.add_trace(go.Scatter(
        x=f_df['Размещениеt'],
        y=f_df['spread'],
        mode='markers',
        marker=dict(color='tan', size=10),
        name='Спред при размещении'
    ))

    # Добавление стрелок между точками с одинаковой датой размещения
    for i in range(len(f_df)):
        for j in range(len(f_df)):
            if f_df['Размещениеt'].iloc[i] == f_df['Размещениеt'].iloc[j] and i != j:
                fig.add_trace(go.Scatter(
                    x=[f_df['Размещениеt'].iloc[i], f_df['Размещениеt'].iloc[j]],
                    y=[f_df['spread'].iloc[i], f_df['Cspread'].iloc[j]],
                    mode='lines+text',
                    line=dict(color='goldenrod', width=2),
                    showlegend=False
                ))

    # Настройка графика
    fig.update_layout(
        title='Карта рынка',
        xaxis_title='Дата размещения',
        yaxis_title='Спред к КС',
        legend=dict(x=0, y=1),
        xaxis_tickformat='%Y-%m-%d',
        hovermode='closest'
    )

    # Показываем график в Streamlit
    st.plotly_chart(fig)
else:
    st.write("Нет данных для отображения.")

st.write("*Если облигационный выпуск имеет амортизацию, то расчет изменения спреда ее не учитывает.")
