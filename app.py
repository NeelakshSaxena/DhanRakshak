# app.py
# This is the main file for the Streamlit web application.
# This version adds more graphs and an editable, downloadable transaction table.

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

@st.cache_data
def convert_df_to_csv(df):
    # IMPORTANT: Cache the conversion to prevent computation on every rerun
    return df.to_csv(index=False).encode('utf-8')

# --- Sidebar ---
with st.sidebar:
    st.title("Dhanrakshak 📊")
    st.write("Your personal finance dashboard.")

    uploaded_file = st.file_uploader(
        "Upload your bank statement (.txt or .csv)",
        type=['txt', 'csv'],
        key="file_uploader"
    )

    # If a new file is uploaded, store it and clear old results/errors
    if uploaded_file is not None:
        if st.session_state.uploaded_file_obj is None or uploaded_file.name != st.session_state.uploaded_file_obj.name:
            st.session_state.uploaded_file_obj = uploaded_file
            st.session_state.processed_data = None
            st.session_state.edited_data = None
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
                    st.session_state.edited_data = df.copy() # Initialize edited_data
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
            st.session_state.edited_data = None
            st.session_state.uploaded_file_obj = None
            st.session_state.error_message = None
            st.rerun()

# --- Main Page Display ---
# First, check if there's an error to display
if st.session_state.error_message:
    st.error(f"An error occurred: {st.session_state.error_message}")
    st.warning("Please check the file format and try again.")

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
    # Use original data for analytics, and edited_data for the table
    df = st.session_state.processed_data

    # Defensive check: if edited_data is missing or got cleared, re-initialize it
    if 'edited_data' not in st.session_state or st.session_state.edited_data is None:
        st.session_state.edited_data = df.copy()

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
        # --- Visualization Section ---
        col1, col2 = st.columns(2)
        with col1:
            # 1. Pie Chart for Expense Categories
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
            # 2. Bar Chart for Payment Methods (Sorted)
            payment_method_expenses = expense_df.groupby('payment_method')['debit'].sum().sort_values(ascending=True).reset_index()
            fig_bar = px.bar(
                payment_method_expenses, y='payment_method', x='debit',
                title='Total Spending by Payment Method', labels={'debit': 'Total Expenses (₹)', 'payment_method': 'Payment Method'},
                orientation='h', text_auto='.2s'
            )
            fig_bar.update_layout(title_x=0.5, yaxis_title=None)
            st.plotly_chart(fig_bar, use_container_width=True)
            
        # 3. Daily Spending Line Chart
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
    
    # --- Editable Data Table ---
    # Define the columns to display in the new, cleaner table
    display_cols = ['date', 'merchant', 'debit', 'credit', 'category', 'remark']
    # IMPORTANT: Check against the edited_data dataframe's columns
    visible_cols = [col for col in display_cols if col in st.session_state.edited_data.columns]

    # The data editor now modifies the session state directly
    edited_df_from_editor = st.data_editor(
        st.session_state.edited_data,
        column_config={
            "remark": st.column_config.TextColumn(
                "Remarks (Editable)",
                help="Add your personal notes for this transaction",
                max_chars=100,
            ),
            "debit": st.column_config.NumberColumn(
                "Debit (₹)", format="₹ %.2f"
            ),
            "credit": st.column_config.NumberColumn(
                "Credit (₹)", format="₹ %.2f"
            ),
            # Hide other columns from the editor view but keep them in the dataframe
            "description": None,
            "payment_method": None,
            "gateway": None,
        },
        column_order=visible_cols, # Control which columns are visible and in what order
        use_container_width=True,
        key="data_editor"
    )
    
    # Persist edits back to session state to make them sticky
    st.session_state.edited_data = edited_df_from_editor

    # --- Save and Download Button ---
    st.download_button(
        label="Download Updated Statement",
        data=convert_df_to_csv(st.session_state.edited_data), # Download the latest edited data
        file_name=f"edited_{st.session_state.uploaded_file_obj.name}.csv",
        mime="text/csv",
        help="Saves your edited remarks to a new CSV file."
    )
