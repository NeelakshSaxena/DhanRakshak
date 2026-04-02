# app.py
# This is the main file for the Streamlit web application.
# This version adds persistent error handling.

import streamlit as st
import pandas as pd
import plotly.express as px
from processor import process_statement
import time

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
</style>
""", unsafe_allow_html=True)

# --- Initialize Session State ---
if 'processed_data' not in st.session_state:
    st.session_state.processed_data = None
if 'uploaded_file_obj' not in st.session_state:
    st.session_state.uploaded_file_obj = None
if 'error_message' not in st.session_state:
    st.session_state.error_message = None


# --- Sidebar ---
with st.sidebar:
    st.title("Dhanrakshak 📊")
    st.write("Your personal finance dashboard.")

    uploaded_file = st.file_uploader(
        "Upload your bank statement",
        type=['csv', 'xls', 'xlsx'],
        key="file_uploader"
    )

    # If a new file is uploaded, store it and clear old results/errors
    if uploaded_file is not None:
        if st.session_state.uploaded_file_obj is None or uploaded_file.name != st.session_state.uploaded_file_obj.name:
            st.session_state.uploaded_file_obj = uploaded_file
            st.session_state.processed_data = None
            st.session_state.error_message = None # Clear previous errors

    # If a file is ready, show its name and the "Process" button
    if st.session_state.uploaded_file_obj is not None:
        st.success(f"File '{st.session_state.uploaded_file_obj.name}' ready.")
        if st.button("Process Statement", type="primary"):
            st.session_state.error_message = None # Clear previous errors before processing
            with st.status("Analyzing your statement...", expanded=True) as status:
                try:
                    df = process_statement(st.session_state.uploaded_file_obj, status)
                    st.session_state.processed_data = df
                    status.update(label="Analysis complete!", state="complete", expanded=False)
                    time.sleep(1)
                except Exception as e:
                    # Store the error message in the session state
                    st.session_state.error_message = str(e)
                    status.update(label=f"Processing failed!", state="error")
                    st.session_state.processed_data = None
            st.rerun()

    if st.session_state.processed_data is not None or st.session_state.error_message is not None:
        if st.button("Clear Data and Start Over"):
            st.session_state.processed_data = None
            st.session_state.uploaded_file_obj = None
            st.session_state.error_message = None
            st.rerun()

# --- Main Page Display ---
# First, check if there's an error to display
if st.session_state.error_message:
    st.error(f"An error occurred: {st.session_state.error_message}")
    st.warning("Please check your API key in the .env file or the file format and try again.")

elif st.session_state.processed_data is None:
    # --- Welcome Page ---
    st.header("Welcome to Dhanrakshak!")
    st.subheader("Analyze Your Finances Intelligently")
    st.markdown("""
    **Get started in 3 simple steps:**

    1.  **Upload your statement** using the uploader on the left.
    2.  **Click 'Process Statement'** to begin the analysis.
    3.  **Explore your finances!** The dashboard will appear here.
    """)
else:
    # --- Dashboard View ---
    df = st.session_state.processed_data
    st.header("Financial Overview")
    total_income = df[df['credit'] > 0]['credit'].sum()
    total_expenses = df[df['debit'] > 0]['debit'].sum()
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
        col1, col2 = st.columns([0.6, 0.4])
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
            expense_by_payment = expense_df.groupby('payment_method')['debit'].sum().reset_index()
            fig_bar = px.bar(
                expense_by_payment, x='payment_method', y='debit',
                title='Expenses by Payment Method', labels={'debit': 'Total Amount (₹)', 'payment_method': 'Payment Method'},
                text_auto='.2s', color='payment_method', color_discrete_sequence=px.colors.qualitative.Set2
            )
            fig_bar.update_layout(xaxis_title=None, title_x=0.5)
            st.plotly_chart(fig_bar, use_container_width=True)

    st.markdown("---")
    st.header("Transaction Details")
    st.dataframe(df[['date', 'description', 'debit', 'credit', 'category', 'payment_method']].style.format({
        'debit': "₹{:,.2f}", 'credit': "₹{:,.2f}", 'date': '{:%d-%m-%Y}'
    }), use_container_width=True, height=400)
