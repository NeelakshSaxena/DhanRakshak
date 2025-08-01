# app.py
# This is the main file for the Streamlit web application.
# This version has a robust UI, correct processing calls, and visual feedback.

import streamlit as st
import pandas as pd
import plotly.express as px
import time

# Import the processor function
from processor import process_statement

# --- Page Configuration ---
st.set_page_config(
    page_title="Dhanrakshak - Expense Analyzer",
    page_icon="💰",
    layout="wide"
)

# --- App Styling ---
st.markdown("""
<style>
    .reportview-container {
        background: #f0f2f6;
    }
    .sidebar .sidebar-content {
        background: #f0f2f6;
    }
    .stMetric {
        border-radius: 10px;
        padding: 15px;
        background-color: #ffffff;
        box-shadow: 0 1px 3px rgba(0,0,0,0.12), 0 1px 2px rgba(0,0,0,0.24);
    }
    .stButton>button {
        width: 100%;
        border-radius: 10px;
    }
    .gif-container {
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        height: 50vh;
    }
</style>
""", unsafe_allow_html=True)

# --- Initialize Session State ---
if 'processed_data' not in st.session_state:
    st.session_state.processed_data = None
if 'edited_data' not in st.session_state:
    st.session_state.edited_data = None
if 'uploaded_file_obj' not in st.session_state:
    st.session_state.uploaded_file_obj = None
if 'error_message' not in st.session_state:
    st.session_state.error_message = None
if 'processing' not in st.session_state:
    st.session_state.processing = False


@st.cache_data
def convert_df_to_csv(df):
    # IMPORTANT: Cache the conversion to prevent computation on every rerun
    return df.to_csv(index=False).encode('utf-8')

# --- Sidebar ---
with st.sidebar:
    st.title("Dhanrakshak 📊")
    st.write("Your personal finance dashboard.")
    
    st.header("1. AI Configuration")
    ai_provider = st.radio(
        "Select AI Provider", 
        ("Local Server", "Gemini API"),
        help="Use a local model for 100% privacy or Google's Gemini API for power."
    )
    
    api_config = {}
    if ai_provider == "Local Server":
        api_config['url'] = st.text_input("Local Server URL", "http://localhost:1234/v1/chat/completions")
    else: # Gemini API
        api_config['key'] = st.text_input("Gemini API Key", type="password")

    st.header("2. Your Information")
    account_holder_name = st.text_input("Your Full Name (as in statement)", value="Neelaksh Saxena", help="This helps identify self-transfers accurately.")

    st.header("3. Upload Statement")
    uploaded_file = st.file_uploader(
        "Upload your bank statement (.txt or .csv)",
        type=['txt', 'csv'],
        key="file_uploader"
    )

    # If a new file is uploaded, store it and clear old results/errors
    if uploaded_file is not None:
        if st.session_state.get('uploaded_file_obj') is None or uploaded_file.name != st.session_state.uploaded_file_obj.name:
            st.session_state.uploaded_file_obj = uploaded_file
            st.session_state.processed_data = None
            st.session_state.edited_data = None
            st.session_state.error_message = None

    # If a file is ready, show its name and the "Process" button
    if st.session_state.get('uploaded_file_obj') is not None:
        st.success(f"File '{st.session_state.uploaded_file_obj.name}' ready.")
        if st.button("Process Statement", type="primary"):
            st.session_state.processing = True
            st.session_state.error_message = None
            st.session_state.processed_data = None
            st.rerun() # Rerun to show the loading GIF

    if st.session_state.get('processed_data') is not None or st.session_state.get('error_message') is not None:
        if st.button("Clear Data and Start Over"):
            # Clear all relevant session state keys
            for key in ['processed_data', 'edited_data', 'uploaded_file_obj', 'error_message', 'processing']:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()

# --- Main Page Display ---

# This container will hold our GIFs or the welcome message
main_placeholder = st.empty()

if st.session_state.get('processing'):
    with main_placeholder.container():
        st.markdown("<div class='gif-container'><img src='https://media.tenor.com/Un_bT5R7i-8AAAAC/yibo-wangyibo.gif' width='200'><h3 style='text-align: center;'>Analyzing your statement...</h3></div>", unsafe_allow_html=True)
    
    try:
        df = process_statement(st.session_state.uploaded_file_obj, account_holder_name, ai_provider, api_config)
        st.session_state.processed_data = df
        st.session_state.edited_data = df.copy()
        st.session_state.processing = False
        
        # Show the "Done" GIF briefly
        with main_placeholder.container():
            st.markdown("<div class='gif-container'><img src='https://media.tenor.com/A15iB2OL_n4AAAAC/done-finished.gif' width='200'></div>", unsafe_allow_html=True)
        time.sleep(2)
        st.rerun()

    except Exception as e:
        st.session_state.error_message = str(e)
        st.session_state.processing = False
        st.rerun()

elif st.session_state.get('error_message'):
    # --- ERROR SCREEN ---
    with main_placeholder.container():
        st.markdown("<div class='gif-container'><img src='https://media.tenor.com/fY9_t4Imu-4AAAAC/epikube-headbang.gif' width='200'></div>", unsafe_allow_html=True)
        st.error(f"An error occurred: {st.session_state.error_message}")
        st.warning("Please check your settings on the left and try again.")

elif st.session_state.get('processed_data') is None:
    with main_placeholder.container():
        st.header("Welcome to Dhanrakshak!")
        st.subheader("Analyze Your Finances Intelligently")
        st.markdown("""
        **Get started in 3 simple steps:**

        1.  Configure your AI Provider and enter your name on the left.
        2.  Upload your statement.
        3.  Click 'Process Statement' to begin the analysis.
        """)
else:
    # --- Dashboard View ---
    df = st.session_state.processed_data
    st.header("Financial Overview")
    total_income = df['credit'].sum()
    total_expenses = df['debit'].sum()
    net_savings = total_income - total_expenses
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Income", f"₹{total_income:,.2f}")
    col2.metric("Total Expenses", f"₹{total_expenses:,.2f}")
    col3.metric("Net Savings", f"₹{net_savings:,.2f}")

    st.markdown("---")
    st.header("Expense Analysis")
    expense_df = df[df['debit'] > 0].copy()
    
    if expense_df.empty:
        st.info("No expenses found in this statement.")
    else:
        col1, col2 = st.columns(2)
        with col1:
            expense_by_category = expense_df.groupby('category')['debit'].sum().reset_index().sort_values('debit', ascending=False)
            fig_pie = px.pie(
                expense_by_category, names='category', values='debit',
                title='Expense Distribution by Category', hole=0.4,
                color_discrete_sequence=px.colors.qualitative.Pastel1
            )
            fig_pie.update_traces(textposition='inside', textinfo='percent+label', pull=[0.05 if i == 0 else 0 for i in range(len(expense_by_category))])
            fig_pie.update_layout(legend_title_text='Categories', title_x=0.5)
            st.plotly_chart(fig_pie, use_container_width=True)

        with col2:
            payment_method_expenses = expense_df.groupby('payment_method')['debit'].sum().sort_values(ascending=True).reset_index()
            fig_bar = px.bar(
                payment_method_expenses, y='payment_method', x='debit',
                title='Total Spending by Payment Method', labels={'debit': 'Total Expenses (₹)', 'payment_method': 'Payment Method'},
                orientation='h', text_auto='.2s'
            )
            fig_bar.update_layout(title_x=0.5, yaxis_title=None)
            st.plotly_chart(fig_bar, use_container_width=True)
            
        daily_expenses = expense_df.groupby(df['date'].dt.date)['debit'].sum().reset_index()
        fig_line = px.line(
            daily_expenses, x='date', y='debit',
            title='Daily Spending Over Time', labels={'date': 'Date', 'debit': 'Total Expenses (₹)'},
            markers=True
        )
        fig_line.update_layout(title_x=0.5)
        st.plotly_chart(fig_line, use_container_width=True)

    st.markdown("---")
    st.header("Transaction Details")
    st.write("You can edit the 'remark' column below to add your own notes.")
    
    if 'edited_data' not in st.session_state or st.session_state.edited_data is None:
        st.session_state.edited_data = df.copy()

    visible_cols = ['date', 'merchant', 'debit', 'credit', 'category', 'remark']
    edited_df_from_editor = st.data_editor(
        st.session_state.edited_data,
        column_config={
            "remark": st.column_config.TextColumn("Remarks (Editable)", max_chars=100),
            "debit": st.column_config.NumberColumn("Debit (₹)", format="₹ %.2f"),
            "credit": st.column_config.NumberColumn("Credit (₹)", format="₹ %.2f"),
            "description": None, "payment_method": None, "gateway": None,
        },
        column_order=[col for col in visible_cols if col in st.session_state.edited_data.columns],
        use_container_width=True, key="data_editor"
    )
    st.session_state.edited_data = edited_df_from_editor

    st.download_button(
        label="Download Updated Statement",
        data=convert_df_to_csv(st.session_state.edited_data),
        file_name=f"edited_{st.session_state.uploaded_file_obj.name}.csv",
        mime="text/csv",
        help="Saves your edited remarks to a new CSV file."
    )
