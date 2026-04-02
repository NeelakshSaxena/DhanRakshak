# app.py
# This is the main file for the Streamlit web application.
# This version has a robust UI, correct processing calls, and visual feedback with local loading animation.

import streamlit as st
import pandas as pd
import plotly.express as px
import time
from pathlib import Path
import os
from user_mapping_store import load_user_mappings, save_user_mapping
from transaction_modes import summarize_modes

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


def show_loading_animation():
    """Display animated loading animation using proper HTML rendering."""
    animation_path = Path(__file__).parent / "animations" / "loading.gif"
    
    if animation_path.exists():
        # Read GIF as base64 for embedding in HTML
        import base64
        with open(animation_path, 'rb') as img_file:
            img_data = base64.b64encode(img_file.read()).decode()
        
        # Centered, clean display with animation and loading text
        st.markdown(
            f"""
            <div style="display: flex; flex-direction: column; justify-content: center; align-items: center; min-height: 60vh;">
                <img src="data:image/gif;base64,{img_data}" width="220" alt="Loading..." style="margin-bottom: 20px;">
                <p style="font-size: 18px; color: #666; margin-top: 10px; text-align: center; letter-spacing: 2px;">Loading...</p>
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        st.info("⏳ Loading... (add loading.gif to src/animations/)")

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

# This container will hold animations or the welcome message
main_placeholder = st.empty()

if st.session_state.get('processing'):
    with main_placeholder.container():
        show_loading_animation()
    
    try:
        df = process_statement(st.session_state.uploaded_file_obj, account_holder_name, ai_provider, api_config)
        st.session_state.processed_data = df
        st.session_state.edited_data = df.copy()
        st.session_state.processing = False
        
        # Show completion message briefly
        with main_placeholder.container():
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                st.success("✅ Analysis complete!")
        time.sleep(1)
        st.rerun()

    except Exception as e:
        st.session_state.error_message = str(e)
        st.session_state.processing = False
        st.rerun()

elif st.session_state.get('error_message'):
    # --- ERROR SCREEN ---
    with main_placeholder.container():
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.error("⚠️ An error occurred")
        st.error(f"{st.session_state.error_message}")
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

    # Prepare date/balance helper columns for visualizations.
    viz_df = df.copy()
    viz_df['date_dt'] = pd.to_datetime(viz_df.get('date'), errors='coerce')

    st.header("Financial Overview")
    total_income = df['credit'].sum()
    total_expenses = df['debit'].sum()
    net_savings = total_income - total_expenses

    balance_series = pd.to_numeric(viz_df.get('closing_balance'), errors='coerce').dropna()
    current_balance = balance_series.iloc[-1] if not balance_series.empty else 0.0
    statement_closing_balance = current_balance
    
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Total Income", f"₹{total_income:,.2f}")
    col2.metric("Total Expenses", f"₹{total_expenses:,.2f}")
    col3.metric("Net Savings", f"₹{net_savings:,.2f}")
    col4.metric("Current Balance", f"₹{current_balance:,.2f}")
    col5.metric("Closing Balance", f"₹{statement_closing_balance:,.2f}")

    st.markdown("---")
    st.header("Expense Analysis")
    expense_df = df[df['debit'] > 0].copy()

    if 'transaction_mode' in df.columns:
        mode_summary_all = summarize_modes(df, amount_col='debit')
        detected_modes = mode_summary_all['transaction_mode'].tolist() if not mode_summary_all.empty else []
        st.subheader("Detected India Transaction Modes")
        if detected_modes:
            st.write(", ".join(detected_modes))
        else:
            st.info("No transaction modes could be derived from this statement.")

    if 'mode_confidence' in df.columns:
        low_conf_count = int((df['mode_confidence'] == 'Low').sum())
        med_conf_count = int((df['mode_confidence'] == 'Medium').sum())
        high_conf_count = int((df['mode_confidence'] == 'High').sum())
        c1, c2, c3 = st.columns(3)
        c1.metric("High Confidence Rows", f"{high_conf_count}")
        c2.metric("Medium Confidence Rows", f"{med_conf_count}")
        c3.metric("Low Confidence Rows", f"{low_conf_count}")
    
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
            
        daily_expenses = expense_df.groupby('date')['debit'].sum().reset_index()
        fig_line = px.line(
            daily_expenses, x='date', y='debit',
            title='Daily Spending Over Time', labels={'date': 'Date', 'debit': 'Total Expenses (₹)'},
            markers=True
        )
        fig_line.update_layout(title_x=0.5)
        st.plotly_chart(fig_line, use_container_width=True)

        col3, col4 = st.columns(2)
        with col3:
            top_merchants = (
                expense_df.groupby('merchant', as_index=False)['debit']
                .sum()
                .sort_values('debit', ascending=False)
                .head(10)
            )
            fig_top_merchants = px.bar(
                top_merchants,
                x='debit',
                y='merchant',
                orientation='h',
                title='Top 10 Merchants by Spend',
                labels={'debit': 'Spend (₹)', 'merchant': 'Merchant'},
                text_auto='.2s'
            )
            fig_top_merchants.update_layout(title_x=0.5, yaxis={'categoryorder': 'total ascending'})
            st.plotly_chart(fig_top_merchants, use_container_width=True)

        with col4:
            income_vs_expense = pd.DataFrame(
                {
                    'Type': ['Income', 'Expense'],
                    'Amount': [total_income, total_expenses],
                }
            )
            fig_income_expense = px.bar(
                income_vs_expense,
                x='Type',
                y='Amount',
                color='Type',
                title='Income vs Expense Comparison',
                labels={'Amount': 'Amount (₹)'},
                text_auto='.2s'
            )
            fig_income_expense.update_layout(title_x=0.5, showlegend=False)
            st.plotly_chart(fig_income_expense, use_container_width=True)

        if 'transaction_type' in expense_df.columns:
            tx_type_df = expense_df.copy()
            tx_type_df['transaction_type'] = tx_type_df['transaction_type'].replace('', pd.NA).fillna('Other')
            tx_split = (
                tx_type_df.groupby('transaction_type', as_index=False)['debit']
                .sum()
                .sort_values('debit', ascending=False)
            )
            if not tx_split.empty:
                fig_tx_split = px.pie(
                    tx_split,
                    names='transaction_type',
                    values='debit',
                    title='Spend Split by Transaction Type (UPI vs POS vs Other)',
                    hole=0.35
                )
                fig_tx_split.update_traces(textposition='inside', textinfo='percent+label')
                fig_tx_split.update_layout(title_x=0.5)
                st.plotly_chart(fig_tx_split, use_container_width=True)

        if 'transaction_mode' in expense_df.columns:
            mode_spend = summarize_modes(expense_df, amount_col='debit')
            if not mode_spend.empty:
                fig_mode_spend = px.bar(
                    mode_spend,
                    x='amount',
                    y='transaction_mode',
                    orientation='h',
                    title='Spend by India Transaction Mode',
                    labels={'amount': 'Spend (₹)', 'transaction_mode': 'Transaction Mode'},
                    text_auto='.2s'
                )
                fig_mode_spend.update_layout(title_x=0.5, yaxis={'categoryorder': 'total ascending'})
                st.plotly_chart(fig_mode_spend, use_container_width=True)

        balance_curve_df = viz_df.dropna(subset=['date_dt']).copy()
        if 'closing_balance' in balance_curve_df.columns:
            balance_curve_df['closing_balance'] = pd.to_numeric(balance_curve_df['closing_balance'], errors='coerce')
            balance_curve_df = balance_curve_df.dropna(subset=['closing_balance'])
            if not balance_curve_df.empty:
                balance_curve_df = balance_curve_df.sort_values('date_dt')
                fig_balance_curve = px.area(
                    balance_curve_df,
                    x='date_dt',
                    y='closing_balance',
                    title='Closing Balance Trend Over Time',
                    labels={'date_dt': 'Date', 'closing_balance': 'Closing Balance (₹)'}
                )
                fig_balance_curve.update_layout(title_x=0.5)
                st.plotly_chart(fig_balance_curve, use_container_width=True)

    st.markdown("---")
    st.header("Transaction Details")
    st.write("You can edit the 'remark' column below to add your own notes.")
    
    if 'edited_data' not in st.session_state or st.session_state.edited_data is None:
        st.session_state.edited_data = df.copy()

    visible_cols = ['date', 'merchant', 'transaction_mode', 'mode_confidence', 'debit', 'credit', 'category', 'remark']
    edited_df_from_editor = st.data_editor(
        st.session_state.edited_data,
        column_config={
            "remark": st.column_config.TextColumn("Remarks (Editable)", max_chars=100),
            "transaction_mode": st.column_config.TextColumn("Transaction Mode", disabled=True),
            "mode_confidence": st.column_config.TextColumn("Mode Confidence", disabled=True),
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

    st.markdown("---")
    st.header("Teach The App New Narration Rules")
    st.write("Save your own narration to category/remark mapping. These rules are reused automatically in future analyses.")

    narration_source_col = 'description' if 'description' in st.session_state.edited_data.columns else 'narration'
    narration_options = []
    if narration_source_col in st.session_state.edited_data.columns:
        narration_options = sorted(
            [
                str(x) for x in st.session_state.edited_data[narration_source_col].dropna().unique().tolist()
                if str(x).strip() != ''
            ]
        )

    if narration_options:
        with st.form("save_narration_rule_form"):
            selected_narration = st.selectbox("Narration", options=narration_options)
            pattern_input = st.text_input("Pattern to Match", value=selected_narration)
            match_type = st.selectbox("Match Type", options=["contains", "exact", "similar"], index=0)
            category_input = st.text_input("Category", value="Shopping")
            remark_input = st.text_input("Remark", value="General Purchase / Transaction", help="Tip: use 'UPI Payment to <name>' for person-to-person UPI rules. Similar UPI narrations can auto-infer the payee name.")
            save_rule_clicked = st.form_submit_button("Save Rule")

            if save_rule_clicked:
                try:
                    pattern = pattern_input.strip() if pattern_input.strip() else selected_narration
                    save_user_mapping(pattern, category_input, remark_input, match_type=match_type)
                    st.success("Rule saved. It will be used in upcoming analysis runs.")
                except Exception as save_error:
                    st.error(f"Failed to save rule: {save_error}")
    else:
        st.info("No narration values available yet for rule creation.")

    with st.expander("View Saved Rules"):
        saved_rules = load_user_mappings()
        if saved_rules:
            st.dataframe(pd.DataFrame(saved_rules), use_container_width=True)
        else:
            st.write("No saved rules yet.")
