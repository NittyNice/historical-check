import streamlit as st
from streamlit_option_menu import option_menu

import pandas as pd
import numpy as np
from dateutil.relativedelta import relativedelta
import missingno as msno
import matplotlib.pyplot as plt
import plotly.graph_objects as go

## Setup page config
st.set_page_config(page_title="Historical data", layout="wide")

## Sidebar markdown
st.sidebar.markdown("## Select TDT")

## Upload TDT file
uploaded_tdt = st.sidebar.file_uploader("Choose a file", type=['xlsx'])

if uploaded_tdt is not None:
    ## Read TDT excel file page "Point Survey"
    df_tdt = pd.read_excel(uploaded_tdt, sheet_name="Point Survey")
    df_tdt = df_tdt.drop(columns=["Unnamed: 0"])

    st.markdown(f'# TDT name : {df_tdt.columns[0]}')

    ## Remove none matric rows
    df_dropna = df_tdt[~(df_tdt.iloc[:,0].str.contains("Metric Name|Add additional metrics as needed"))]

    ## Find plant unit
    plant_units = df_dropna.columns
    plant_units = plant_units[~plant_units.str.contains("Unnamed")]
    plant_units = plant_units.drop(plant_units[0])
    num_unit = len(plant_units)

    ## Create dataframe contain metric name and type
    df_metrics = df_dropna.iloc[:,0:2].copy()

    ## Create dataframe of each unit and contain to dict
    units_tdt = dict()
    for i in range(num_unit):
        df_unit_point_name = df_dropna.iloc[:,i*5+2:i*5+7]
        
        df_unit_point_survey = pd.concat([df_metrics, df_unit_point_name], axis=1)
        df_unit_point_survey.columns = df_unit_point_survey.iloc[0].tolist()
        df_unit_point_survey = df_unit_point_survey.drop(0)
        
        units_tdt[plant_units[i]] = df_unit_point_survey

    ## Set st.session of tdt and historical dict
    def init_session_state():
        if 'tdt' not in st.session_state:
            st.session_state.tdt = uploaded_tdt
        if st.session_state.tdt != uploaded_tdt:
            st.session_state.tdt = uploaded_tdt
            if 'hist_dict' in st.session_state:
                del st.session_state.hist_dict
                del st.session_state.hist_filename
        if 'hist_dict' not in st.session_state:
            st.session_state.hist_dict = {key: None for key in plant_units}
        if 'hist_filename' not in st.session_state:
            st.session_state.hist_filename = {key: None for key in plant_units}

    # Initialize session state
    init_session_state()
    
    ## Display and selete unit
    units = st.sidebar.radio(
        label='Select unit.', 
        options=plant_units)


    ## Show page with select unit
    hide_upload_hist = st.toggle('Hide upload historical file', value=True)
    if hide_upload_hist:
        if units is not None:
            ## Upload historical data to selected unit
            st.markdown(f"### Upload historical data of {units}")
            with st.form("form", clear_on_submit=True):
                uploaded_hist = st.file_uploader("Choose a file", type=['csv'])
                submitted = st.form_submit_button("Upload")
                if submitted:
                    st.session_state.hist_dict[units] = pd.read_csv(uploaded_hist)
                    st.session_state.hist_filename[units] = uploaded_hist.name
            st.markdown("---")


    ## Get point survey dataframe
    df_unit = units_tdt[units]
    ## Get historical dataframe from session
    df_hist = st.session_state.hist_dict[units]
    if df_hist is not None:     
        # Page select       
        selected = option_menu(None, ["Summary", "Format", "Header", "Timestamp", "Data"], 
                                icons=["Summary", "Format", "Header", "Timestamp", "Data"], 
                                default_index=0, orientation="horizontal")
        if selected == "Summary":
            st.markdown('### Next version!!')
        if selected == "Format":
            st.markdown("## Data table")
            # cols_to_drop = [col for col in df_hist.columns if 'Unnamed' in col or 'TAG' in col]         # Drop columns with names containing 'Unnamed'
            # df_hist.drop(columns=cols_to_drop, inplace=True)
        

            ## 1) Historical data format ----------------------------------------------------------------------------------------------------------------------------------
            st.markdown("### 1) Check the format structure matches the PRiSM Client format.")
            st.dataframe(df_hist.head(6), use_container_width=True, height=300, hide_index=True)

        if selected == "Header":
            ## 2) Header of historical data check lists -------------------------------------------------------------------------------------------------------------------
            st.markdown("### 2) Header data comparison")
            hist_head = df_hist.iloc[:4,:].copy()
            hist_head_t = hist_head.T.reset_index()
            hist_head_t.columns = hist_head_t.iloc[0].tolist()
            hist_head_t = hist_head_t.drop(0)
            hist_head_t['Point Name'] = hist_head_t['Point Name'].str.replace(r'V\..', 'V', regex=True)

            ## 2.1) Check unique point name. -------------------------------------------------------------
            st.markdown("##### 2.1) [Hist] Point Name duplicated")
            condition_2_1 = hist_head_t['Point Name'].duplicated().any()
            if not condition_2_1:
                st.write('<mark>Point name in historical data are : :white_check_mark: <span style="color: green; font-weight:bold;">Unique</span>.</mark>', unsafe_allow_html=True)
            else:
                st.write('<mark>Point name in historical data are : :x: <span style="color: red; font-weight:bold;">Duplicated</span>.</mark>', unsafe_allow_html=True)
                st.write('Table: Point name that are duplicated.')
                st.dataframe(hist_head_t[hist_head_t['Point Name'].duplicated(keep=False)], use_container_width=True)

            try:
                ## 2.2) Check Point Name of historical data similar to Canary Point Name in TDT. ------------------------------------
                st.markdown("##### 2.2) [Hist] Point Name == [TDT] Canary Point Name")
                tdt_points = df_unit[df_unit['Point Type'] == "Analog"]['Canary Point Name']
                hist_points = hist_head_t['Point Name']

                tdt_points = tdt_points.reset_index().rename(columns={'index':'[TDT] Index'}).set_index('Canary Point Name', drop=False)
                hist_points = hist_points.reset_index().rename(columns={'index':'[Hist] Index'}).set_index('Point Name', drop=False)
                joined_points = pd.concat([tdt_points, hist_points], axis=1).reset_index(drop=True)
                joined_points.index += 1

                condition_2_2 = joined_points.isnull().values.any()
                if not condition_2_2:
                    st.write('<mark>Point name in historical data and TDT are : :white_check_mark: <span style="color: green; font-weight:bold;">Similar</span>.</mark>', unsafe_allow_html=True)
                else:
                    st.write('<mark>Point name in historical data and TDT are : :x: <span style="color: red; font-weight:bold;">Difference</span>.</mark>', unsafe_allow_html=True)
                show_point = st.toggle('Show all Point Name')
                if show_point:
                    st.dataframe(joined_points, use_container_width=True)
                else:
                    if condition_2_2:
                        st.dataframe(joined_points[joined_points.isnull().any(axis=1)], use_container_width=True)


                ## 2.3) Check Discription of historical data similar to Canary Description in TDT. ------------------------------------
                st.markdown("##### 2.3) [Hist] Description == [TDT] Canary Description")
                tdt_desc = df_unit[df_unit['Point Type'] == "Analog"][['Canary Point Name', 'Canary Description']].set_index('Canary Point Name')
                tdt_desc = tdt_desc.rename(columns={'Canary Description':'[TDT] Canary Description'})
                hist_desc = hist_head_t[['Point Name', 'Description']].set_index('Point Name')
                hist_desc = hist_desc.rename(columns={'Description':'[Hist] Description'})
                compare_desc = pd.concat([tdt_desc, hist_desc], axis=1)
                compare_desc['Check'] = compare_desc['[TDT] Canary Description'] == compare_desc['[Hist] Description']
                if compare_desc['Check'].all():
                    st.write('<mark>Description in historical data : :white_check_mark: <span style="color: green; font-weight:bold;">Similar</span>.</mark>', unsafe_allow_html=True)
                else:
                    st.write('<mark>Description in historical data : :x: <span style="color: red; font-weight:bold;">Difference</span>.</mark>', unsafe_allow_html=True)
                
                show_desc = st.toggle('Show all Description.')
                if show_desc:
                    st.dataframe(compare_desc)
                else:
                    if not compare_desc['Check'].all():
                        st.dataframe(compare_desc[~compare_desc['Check']])


                ## 2.4) Check Extended Name of historical data similar to Metric in TDT. --------------------------
                st.markdown("##### 2.4) [Hist] Extended Name == [TDT] Metric")
                tdt_exname = df_unit[df_unit['Point Type'] == "Analog"][['Canary Point Name', 'Metric']].set_index('Canary Point Name')
                tdt_exname = tdt_exname.rename(columns={'Metric':'[TDT] Metric'})
                hist_exname = hist_head_t[['Point Name', 'Extended Name']].set_index('Point Name')
                hist_exname = hist_exname.rename(columns={'Extended Name':'[Hist] Extended Name'})
                compare_exname = pd.concat([tdt_exname, hist_exname], axis=1)
                compare_exname['Check'] = compare_exname['[TDT] Metric'] == compare_exname['[Hist] Extended Name']
                if compare_exname['Check'].all():
                    st.write('<mark>Extended Name in historical data and Metric in TDT : :white_check_mark: <span style="color: green; font-weight:bold;">Similar</span>.</mark>', unsafe_allow_html=True)
                else:
                    st.write('<mark>Extended Name in historical data and Metric in TDT : :x: <span style="color: red; font-weight:bold;">Difference</span>.</mark>', unsafe_allow_html=True)
                
                show_exname = st.toggle('Show all Extended Name')
                if show_exname:
                    st.dataframe(compare_exname)
                else:
                    if not compare_exname['Check'].all():
                        st.dataframe(compare_exname[~compare_exname['Check']])


                ## 2.5) Check Extended Description of historical data freely to fill. --------------------------
                st.markdown("##### 2.5) [Hist] Extended Description == None")
                hist_exdesc = hist_head_t[['Point Name', 'Extended Description']].set_index('Point Name')
                hist_exdesc = hist_exdesc.rename(columns={'Extended Description':'[Hist] Extended Description'})
                st.write('<mark>Description in historical data : :white_check_mark: <span style="color: green; font-weight:bold;">Freely to fill</span>.</mark>', unsafe_allow_html=True)
                show_exdesc = st.toggle('Show all Extended Description')
                if show_exdesc:
                    st.dataframe(hist_exdesc)


                ## 2.6) Check unit of historical data similar to unit in TDT. --------------------------
                st.markdown("##### 2.4) [Hist] Unit == [TDT] Unit")
                tdt_unit = df_unit[df_unit['Point Type'] == "Analog"][['Canary Point Name', 'Unit']].set_index('Canary Point Name')
                tdt_unit = tdt_unit.rename(columns={'Unit':'[TDT] Unit'})
                hist_unit = hist_head_t[['Point Name', 'Unit']].set_index('Point Name')
                hist_unit = hist_unit.rename(columns={'Unit':'[Hist] Unit'})
                compare_unit = pd.concat([tdt_unit, hist_unit], axis=1)
                compare_unit['Check'] = compare_unit['[TDT] Unit'] == compare_unit['[Hist] Unit']
                if compare_unit['Check'].all():
                    st.write('<mark>Unit in historical data and Unit in TDT : :white_check_mark: <span style="color: green; font-weight:bold;">Similar</span>.</mark>', unsafe_allow_html=True)
                else:
                    st.write('<mark>Unit in historical data and Unit in TDT : :x: <span style="color: red; font-weight:bold;">Difference</span>.</mark>', unsafe_allow_html=True)
                show_unit = st.toggle('Show all Unit')
                if show_unit:
                    st.dataframe(compare_unit)
                else:
                    if not compare_unit['Check'].all():
                        st.dataframe(compare_unit[~compare_unit['Check']])
            except:
                if condition_2_1:
                    st.write('<span style="color: red; font-weight:bold;">Error to comparison :</span> Becourse Point name are duplicated.', unsafe_allow_html=True)
                    col1, col2 = st.columns(2)
                    with col1:
                        st.dataframe(df_unit["Canary Point Name"], use_container_width=True)
                    with col2:
                        st.dataframe(hist_head_t["Point Name"], use_container_width=True)
                else:
                    st.write('<span style="color: red; font-weight:bold;">Error to comparison :</span> Please manual check.', unsafe_allow_html=True)
                    col1, col2 = st.columns(2)
                    with col1:
                        st.dataframe(df_unit, use_container_width=True)
                    with col2:
                        st.dataframe(hist_head_t, use_container_width=True)
            


        if selected == "Timestamp":
            ## 3) Check format timestamp -------------------------------------------------------------------------------------------------------------------
            st.markdown("### 3) Check format timestamp")
            hist_data = df_hist.iloc[4:,:].copy()
            hist_data = hist_data.rename(columns={"Point Name":"Datetime"}).set_index("Datetime")
            try:
                hist_data.index = pd.to_datetime(hist_data.index, format="%m/%d/%Y %H:%M")
                st.write('<mark>Datetime are in format **mm/dd/yy hh\:mm** : :white_check_mark: <span style="color: green; font-weight:bold;">Currect</span>.</mark>', unsafe_allow_html=True)
            except:
                st.write('<mark>Datetime are in format **mm/dd/yy hh\:mm** : :x: <span style="color: red; font-weight:bold;">Incurrect</span>.</mark>', unsafe_allow_html=True)
                hist_data.index = pd.to_datetime(hist_data.index)
        
            start_date = hist_data.index.min()
            end_date = hist_data.index.max()
            difference = relativedelta(end_date, start_date)
            st.write(f'<mark>Historical data start from <code>{start_date}</code> to <code>{end_date}</code></mark>', unsafe_allow_html=True)
            st.write(f'''<mark>Duration: <code>{difference.years}</code> years 
                                        <code>{difference.months}</code> months 
                                        <code>{difference.days}</code> days 
                                        <code>{difference.hours}</code> hours 
                                        <code>{difference.minutes}</code> minutes</mark>''', unsafe_allow_html=True)
            st.write(f'<mark>Time interval : <code>{hist_data.index.to_series().diff().min().seconds//60}</code> minutes</mark>', unsafe_allow_html=True)
            st.write(f'<mark>Total points : <code>{hist_data.shape[0]}</code> points</mark>', unsafe_allow_html=True)


        if selected == "Data":
            ## 4) Check data quality -------------------------------------------------------------------------------------------------------------------
            st.markdown("### 4) Check historian data quality")
            hist_data = df_hist.iloc[4:,:].copy()
            hist_data = hist_data.rename(columns={"Point Name":"Datetime"}).set_index("Datetime")
            hist_data.index = pd.to_datetime(hist_data.index)

            ## Change type from object to numeric and fill null for non-numeric
            for col in hist_data.columns:
                hist_data[col] = pd.to_numeric(hist_data[col], errors='coerce')

            show_hist = st.toggle('Display historical dataframe')
            if show_hist:
                show_max = st.toggle('All data')
                if show_max:
                    st.markdown(f"**Historical data of {units}**")
                    st.dataframe(hist_data, use_container_width=True, height=400)
                else:
                    st.markdown(f"**Historical data of {units}**")
                    st.dataframe(hist_data.head(100), use_container_width=True, height=400)

            ## Shorten tag names by cutting out unnecessary text.
            hist_data_short = hist_data.rename(columns=lambda x: x.replace('VIRTUAL_VIEW.LocalHistorian.', ''))
            
            ## 4) Check missing data -------------------------------
            st.markdown('##### 4.1) Missing data check')
            st.markdown('When data is present, the plot is shaded in grey and when it is absent the plot is displayed in white.')
            # Calculate the proportion of missing data for each column
            missing_data_proportion = hist_data_short.isnull().mean()*100
            missing_data_proportion.rename("Missing data proportion (%)", inplace=True)

            # Print column names and their proportion of missing data
            st.dataframe(missing_data_proportion, use_container_width=True, height=300)

            fig, ax = plt.subplots()
            msno.matrix(hist_data_short, ax=ax, fontsize=7)
            ax.set_title("Matrix visualization patterns in data completion")
            st.set_option('deprecation.showPyplotGlobalUse', False)
            _, col2, _ = st.columns([1,6,1])
            with col2:
                st.pyplot(fig, use_container_width=True)

            st.markdown('##### 4.2) Check Freeze data')
            st.markdown('When data is present, the plot is shaded in grey and when it is absent the plot is displayed in white.')
            roll_hr = st.slider(
                'Select a window range to check freeze data (hrs.)',
                1, 240, 6)
            # roll_hr = 6
            rolling_std = hist_data.rolling(window=roll_hr*6).std()
            rolling_std = rolling_std.mask(rolling_std < 0.0001)

            # Calculate the proportion of missing data for each column
            freeze_data_proportion = rolling_std.isnull().mean()*100
            freeze_data_proportion.rename("Missing data proportion (%)", inplace=True)

            # Print column names and their proportion of missing data
            st.dataframe(freeze_data_proportion, use_container_width=True, height=300)
            # for column, proportion in missing_data_proportion.items():
            #     st.write(f"Column '{column}' has missing data: {proportion:.2%}")
            
            rolling_std_short = rolling_std.rename(columns=lambda x: x.replace('VIRTUAL_VIEW.LocalHistorian.', ''))
            fig, ax = plt.subplots()
            msno.matrix(rolling_std_short, ax=ax, fontsize=7)
            ax.set_title("Matrix visualization freeze data")
            _, col2, _ = st.columns([1,6,1])
            with col2:
                st.pyplot(fig, use_container_width=True)


            # Create a figure
            fig = go.Figure()

            options = st.multiselect('Select options:', hist_data_short.columns)

            norm_select = st.toggle("Nomalization")
            if not norm_select:
                for column in options:
                    fig.add_trace(go.Scatter(x=hist_data_short.index, y=hist_data_short[column], mode='lines', name=column))
            else:
                for column in options:
                    hist_data_short_norm = (hist_data_short - hist_data_short.min()) / (hist_data_short.max() - hist_data_short.min())
                    fig.add_trace(go.Scatter(x=hist_data_short_norm.index, y=hist_data_short_norm[column], mode='lines', name=column))

            # Update figure layout
            fig.update_layout(
                title='Time Series Plot',
                xaxis_title='Date',
                yaxis_title='Value',
                legend_title='Columns'
            )

            # Plot the figure using st.plotly_chart
            st.plotly_chart(fig, use_container_width=True)

            st.dataframe(df_unit)

            
