import os
import json
import gspread
import pandas as pd 
import streamlit as st
from agents import SearchAgent
from dotenv import load_dotenv
from oauth2client.service_account import ServiceAccountCredentials
load_dotenv(dotenv_path='.env')

serpapi_key = os.environ['SERPAPI_API_KEY']
openai_key = os.environ['OPENAI_API_KEY']

if not openai_key or not serpapi_key:
    st.error("Your API key(s) are missing!", icon='🚨')
    st.stop()
st.title("Data Retrieval Dashboard")
col1, col2 = st.columns(2)

if 'button_clicked' not in st.session_state:
    st.session_state.button_clicked = False
else : st.session_state.button_clicked = True
if 'data_source' not in st.session_state:    
    st.session_state.data_source = ''
if 'file_uploaded' not in st.session_state:
    st.session_state.file_uploaded = False
if 'csv_file' not in st.session_state:
    st.session_state.csv_file = None    
if 'google_sheet' not in st.session_state:
    st.session_state.google_sheet = None  
if 'google_sheet_link' not in st.session_state:
    st.session_state.google_sheet_link = None  
if 'google_sheet_client' not in st.session_state:
    st.session_state.google_sheet_client = None  
if 'df' not in st.session_state:
    st.session_state.df = None  
if 'user_prompt' not in st.session_state:
    st.session_state.user_prompt = None  
if 'user_selection' not in st.session_state:
    st.session_state.user_selection = False   
if 'item_list' not in st.session_state:
    st.session_state.item_list = None 
if 'update_record' not in st.session_state:
    st.session_state.update_record = False
if 'worksheet' not in st.session_state:
    st.session_state.worksheet = None  
if 'results' not in st.session_state:
    st.session_state.results = None  
       

selection_content = st.empty()       


with selection_content.container():
    with col1:
        if not st.session_state.button_clicked:
            st.button("Upload CSV File", on_click = lambda : setattr(st.session_state, 'data_source', 'csv'))


    with col2:
        if not st.session_state.button_clicked:
            button2 = st.button("Connect to Google Sheets", on_click = lambda : setattr(st.session_state, 'data_source', 'google_sheet'))

    data_source = st.session_state.data_source
    if data_source == 'csv' and (st.session_state.df is None or st.session_state.df.empty) and not st.session_state.user_prompt:
        if st.session_state.csv_file is None:
            st.subheader("Upload a .csv file")
            st.session_state.csv_file = st.file_uploader("Choose a .csv file", type = 'csv')
            if st.session_state.csv_file : st.rerun()
        else:
            st.session_state.df = pd.read_csv(st.session_state.csv_file)
            st.success("File loaded successfully", icon = '✅')
            st.table(st.session_state.df.head())


    elif data_source == 'google_sheet' and (st.session_state.df is None or st.session_state.df.empty) and not st.session_state.user_prompt:
        if st.session_state.google_sheet is None:
            st.subheader("Provide your JSON keyfile")
            st.session_state.google_sheet = st.file_uploader("Choose the JSON file", type='json')
            
            if st.session_state.google_sheet:
                data = st.session_state.google_sheet.read()
                data_str = data.decode('utf-8')
                json_file = json.loads(data_str)
                try:
                    credentials = ServiceAccountCredentials.from_json_keyfile_dict(json_file)
                    st.session_state.google_sheet_client = gspread.authorize(credentials)
                    st.success("Credentials loaded successfully", icon='✅')
                except Exception as e:
                    st.error("The provided file was invalid", icon='🚨')
                    st.stop()

        if st.session_state.google_sheet_client and not st.session_state.google_sheet_link:
            st.subheader("Enter Google Sheets Link")
            st.session_state.google_sheet_link = st.text_input(
                "Provide the link to your Google Sheet",
                help="Remember to share this Google Sheet with the `client email` from your JSON keyfile."
            )
            if st.session_state.google_sheet_link : st.rerun()
        if st.session_state.google_sheet_link:
            try:
                sheet = st.session_state.google_sheet_client.open_by_url(st.session_state.google_sheet_link)
                st.session_state.worksheet = sheet.sheet1
                data = st.session_state.worksheet.get_all_records()
                st.session_state.df = pd.DataFrame(data)
                st.success("Sheet loaded successfully", icon='✅')
                st.table(st.session_state.df.head())
            
            except PermissionError:
                st.error("Share the Google Sheet with the `client email` from your JSON keyfile.", icon='🚨')
                st.stop()
            except Exception as e:
                st.error(f"Error loading the Google Sheet: {str(e)}", icon='🚨')
                st.stop()

    if st.session_state.df is not None and not st.session_state.user_prompt:
        df = st.session_state.df
        column_list = df.columns.to_list()
        selected_column = st.radio("Choose one of the columns :", column_list)
        st.button("Confirm Choice", on_click = lambda : setattr(st.session_state, 'user_selection', True))
        if st.session_state.user_selection:
            if df[selected_column].nunique() > 5:
                st.error("Please select a column with at most 5 unique values", icon='🚨')
                st.rerun()
            else:
                st.session_state.item_list = df[selected_column].to_list()
                st.table(df[selected_column])   
                st.session_state.user_prompt = st.text_input("Enter the prompt corresponding to the selected column : ", help = 'To generalise the prompt to all items in the column, you can include `{placeholder}` in your prompt.')
            
if st.session_state.user_prompt:
    selection_content.empty()
    if not st.session_state.update_record:
        with st.spinner('Looking for answers...'):
            search_agent = SearchAgent(st.session_state.item_list)
            st.session_state.results = search_agent.invoke(st.session_state.user_prompt)
    
    new_page = st.empty()
    result_df = pd.DataFrame(st.session_state.results)
    with new_page.container():
        st.table(result_df)
        st.button('Update results to orginal record', on_click = lambda : setattr(st.session_state, 'update_record', True))

    if st.session_state.update_record:
        new_page.empty()   
        if data_source == 'google_sheet':
            print(f'Worksheet type is okay : {isinstance(st.session_state.worksheet, gspread.worksheet.Worksheet)}')
            page = chr(ord('A') + len(st.session_state.df.columns.to_list())) + '1'
            write = [result_df.columns.to_list()] + result_df.values.tolist()
            for item in write:
                for element in item:
                    if isinstance(element, list) : 
                        replace = str(element)
                        replace = replace[1:-1] #removing the brackets from the string 
                        item.remove(element)
                        item.append(replace)

            st.session_state.worksheet.update(write, page)
            merged_df = pd.merge(st.session_state.df, result_df, left_index=True, right_index=True)
            st.table(merged_df)
            st.write('Your Google Sheet has been updated!')
            
        else:
            merged_df = pd.merge(st.session_state.df, result_df, left_index=True, right_index=True)
            updated_csv = merged_df.to_csv()
            st.table(merged_df)
            st.download_button('Download Updated CSV file', updated_csv, f'updated_{st.session_state.csv_file.name}', mime = 'text/csv')