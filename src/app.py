#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Streamlit dashboard showing tweets and their trend!
"""

import datetime

import numpy as np
import pandas as pd
import streamlit as st
from st_aggrid import AgGrid, JsCode, GridOptionsBuilder

from lambda_.lambda_function import get_db_connection


@st.cache(suppress_st_warning=True)
def get_data(start_date: str = '2020-01-01',
             end_date: str = '2025-01-01') -> pd.DataFrame:

    conn = get_db_connection()
    # query the database with start and end data
    sql = f"""select * from tweets_analytics
              where timestamp between date('{start_date}') and date('{end_date}')
              """
    print(sql)
    df = pd.read_sql_query(sql, conn)
    # add some metadata to the string to show more details
    now = str(datetime.datetime.now())[:-7]
    st.sidebar.markdown(f"""**Latest update data :**
                            {now}
                        Adjust starting date or ending date to refresh data""")
    return df


def get_local_tz() -> datetime.timezone:
    return datetime.datetime.now(datetime.timezone.utc).astimezone().tzinfo

@st.cache
def process_data(df: pd.DataFrame,
                 keyword: str,
                 start_date: str,
                 end_date: str) -> pd.DataFrame:
    # convert to local timezone
    local_tz = get_local_tz()
    df['timestamp'] = df['timestamp'].dt.tz_convert(local_tz)
    # remove author column as that is always reuters
    df = df.drop(columns=['author'])
    # select only tweets with the keyword we selected
    if keyword:
        df = df.loc[df['text'].str.contains(keyword),: ]
    # avoid to display 10 decimal places
    df['sentiment_score'] = df['sentiment_score'].round(2)
    # sort column order
    df = df.reindex(['timestamp', 'sentiment_score', 'text'], axis=1)
    return df


def display_table(df: pd.DataFrame) -> None:
    # this is some javascript code
    # to color cells
    # positive -> green, neuter -> white negative -> red
    sentiment_score_style = JsCode("""
    function(params) {
        if (params.value < 0) {
            return {
                'color': 'black',
                'backgroundColor': 'darkred'
            }
        } else if (params.value == 0) {
            return {
                'color': 'black',
                'backgroundColor': 'gray'
            }
        } else {
            return {
                'color': 'black',
                'backgroundColor': 'green'
            }
        }
    };
    """)
    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_column("sentiment_score",
                        cellStyle=sentiment_score_style)

    AgGrid(df, height=500, width=1000,
           fit_columns_on_grid_load=False,
           gridOptions = gb.build(),
           allow_unsafe_jscode=True)
    return None

st.set_page_config(layout="wide")

print('If this is printed and the app is not running on the public IP, check port mappings and security group inbound rules')
if __name__ == "__main__":

    # here we define the layout of the sidebar
    st.title('Tweet analytics sentiment score dashboard')
    view_name = st.sidebar.radio("", ('View tweets', 'Analytics'))
    keyword = st.sidebar.text_input("Keyword", "")
    start_date = st.sidebar.text_input("Starting date", "2021-01-01")
    end_date = st.sidebar.text_input("End date", "2022-01-01")
    st.sidebar.subheader('Explanation')
    st.sidebar.markdown('''
                        **Sentiment score indicates a positive sentiment
                        when the sentiment is positive and conversely,
                        when the score is negative the sentiment is also negative.**  
                        ***Consider that scores above 0.2 or under -0.2 are a
                         small part and can therefore be seen as very positive 
                         or very negative.***
                         ''')
    # here we run the main 'functionality' of the app
    df = get_data(start_date=start_date, end_date=end_date)
    df = process_data(df,
                      keyword=keyword,
                      start_date=start_date,
                      end_date=end_date)
    # error handling message
    if df.empty:
            st.error('Your search parameters resulted in no data!')

    col1, col2, col3 = st.columns(3)
    if view_name == 'View tweets':
        # view tweets View
        display_table(df)

    else:
         # Analytics view
        # plot sentiment over time
        st.markdown(f"**Sentiment score over time**")
        keyword_info = f"keyword={keyword}" if keyword else ""
        st.markdown(f"{keyword_info} start date={start_date} \n end date={end_date}")
        # make sure timestamp index is seen on the plot
        df = df.set_index('timestamp')
        st.line_chart(df['sentiment_score'])
