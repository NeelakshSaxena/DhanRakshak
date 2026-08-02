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
    page_icon="D",
    layout="wide"
)

# --- App Styling ---
st.markdown("""
<style>
    /* Remove hardcoded backgrounds so Streamlit's native Light/Dark theme works */
    .stMetric {
        border-radius: 10px;
        padding: 15px;
        background-color: var(--secondary-background-color);
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

@st.cache_data
def convert_df_to_excel(df):
    import io
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()


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
        st.info("Loading... (add loading.gif to src/animations/)")

# --- Sidebar ---
with st.sidebar:
    st.title(":blue[Dhanrakshak]")
    st.write("Your personal finance dashboard.")
    
    if st.session_state.get('processed_data') is not None or st.session_state.get('error_message') is not None:
        st.markdown("---")
        if st.button("Clear Data and Start Over"):
            for key in ['processed_data', 'edited_data', 'uploaded_file_obj', 'error_message', 'processing', 'api_config_state', 'ai_provider_state', 'name_state', 'skip_ai_state']:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()

# --- Main Page Display ---
main_placeholder = st.empty()

if st.session_state.get('processing'):
    with main_placeholder.container():
        show_loading_animation()
    
    try:
        force_skip = st.session_state.get('skip_ai_state', False)
        raw_val = st.session_state.get('raw_scrubbed_text')
        payload = raw_val if raw_val is not None else st.session_state.uploaded_file_obj
        
        df = process_statement(
            payload, 
            st.session_state.get('name_state', 'User'), 
            st.session_state.get('ai_provider_state'), 
            st.session_state.get('api_config_state', {}),
            force_skip_ai=force_skip,
            use_ai_mapper=st.session_state.get('use_ai_mapper_state', False)
        )
        st.session_state.processed_data = df
        st.session_state.original_columns = df.attrs.get('original_columns', [])
        st.session_state.edited_data = df.copy()
        st.session_state.processing = False
        
        # Show completion message briefly
        with main_placeholder.container():
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                if df.attrs.get('is_pre_processed'):
                    st.success("Edited file detected! Skipped AI processing and loaded your data instantly.")
                else:
                    st.success("Analysis complete!")
        time.sleep(1.5)
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
            st.error("An error occurred")
        st.error(f"{st.session_state.error_message}")
        st.warning("Please check your settings or clear data to try again.")

elif st.session_state.get('processed_data') is None:
    # --- SETUP SCREEN ---
    with main_placeholder.container():
        st.header("Welcome to :blue[Dhanrakshak]!")
        st.subheader("Analyze Your Finances Intelligently")
        st.markdown("---")
        
        col1, col2 = st.columns(2, gap="large")
        
        with col1:
            st.header("1. Upload Statement")
            
            statement_type = st.radio(
                "Statement Type",
                ["Raw Bank Statement (Run AI)", "Previously Edited Statement (Visualize Only)"],
                help="Choose whether you need the AI to analyze new data, or if you just want to visualize a statement you already edited and downloaded."
            )
            force_skip_ai = statement_type == "Previously Edited Statement (Visualize Only)"
            
            uploaded_file = st.file_uploader(
                "Upload your bank statement (.csv, .xlsx, .xls)",
                type=['csv', 'xlsx', 'xls'],
                key="file_uploader"
            )
            
            use_ai_mapper = st.checkbox(
                "Use AI to understand unfamiliar statement format", 
                value=False, 
                help="Check this if the app fails to read your bank statement. It will use AI to figure out the column names.",
                disabled=force_skip_ai
            )
            
        with col2:
            st.header("2. AI Configuration")
            ai_provider = st.radio(
                "Select AI Provider", 
                ("Local Server", "Gemini API", "Custom Endpoint"),
                help="Use a local model for 100% privacy, Google's Gemini API for power, or a custom API endpoint."
            )
            
            # --- Privacy Warning ---
            if ai_provider in ["Gemini API", "Custom Endpoint"]:
                st.warning("⚠️ **Privacy Risk**: Sending sensitive bank statements to online hosted APIs (like OpenAI, Claude, or Gemini) comes with privacy risks. For personal and local use, we highly recommend using **Local Server (Local LLMs)**.")
                accept_privacy_risk = st.checkbox("I understand the privacy risks and want to proceed with a hosted API.")
            else:
                st.success("🔒 You are using a Local Server. Your data remains 100% private and never leaves your machine.")
                accept_privacy_risk = True

            api_config = {}
            if not force_skip_ai:
                if ai_provider == "Local Server":
                    local_url = st.text_input("Local Server URL", value="http://localhost:1234/v1/chat/completions", help="URL for LM Studio, Ollama, etc.")
                    api_config['url'] = local_url
                
                elif ai_provider == "Custom Endpoint":
                    custom_url = st.text_input("Custom API URL", value="")
                    custom_key = st.text_input("Custom API Key", type="password")
                    api_config['url'] = custom_url
                    api_config['key'] = custom_key
                    
                elif ai_provider == "Gemini API":
                    api_key_input = st.text_input("Gemini API Key", type="password")
                    api_config['key'] = api_key_input
                    try:
                        import requests
                        response = requests.get(f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key_input}")
                        if response.status_code == 200:
                            models = [m['name'].split('/')[-1] for m in response.json().get('models', []) if 'generateContent' in m.get('supportedGenerationMethods', []) and '2.5' not in m['name']]
                            if models:
                                default_index = models.index('gemini-1.5-flash') if 'gemini-1.5-flash' in models else 0
                                selected_model = st.selectbox("Select Gemini Model", models, index=default_index)
                                api_config['model'] = selected_model
                            else:
                                st.warning("No suitable models found for this API key.")
                                api_config['model'] = "gemini-1.5-flash"
                        else:
                            st.error(f"Error fetching models: {response.status_code}")
                            api_config['model'] = "gemini-1.5-flash"
                    except Exception as e:
                        st.error(f"Could not fetch models: {e}")
                        api_config['model'] = "gemini-1.5-flash"
        
        st.markdown("---")
        
        # If a new file is uploaded, store it
        if uploaded_file is not None:
            if st.session_state.get('uploaded_file_obj') is None or uploaded_file.name != st.session_state.uploaded_file_obj.name:
                st.session_state.uploaded_file_obj = uploaded_file
                st.session_state.error_message = None
                
                is_excel = uploaded_file.name.lower().endswith(('.xlsx', '.xls'))
                
                if is_excel:
                    st.session_state.raw_scrubbed_text = None
                else:
                    # Pre-read the file for the privacy scrub step
                    try:
                        uploaded_file.seek(0)
                        raw_content = uploaded_file.getvalue().decode('utf-8')
                    except (UnicodeDecodeError, AttributeError):
                        uploaded_file.seek(0)
                        raw_content = uploaded_file.getvalue().decode('latin-1')
                    st.session_state.raw_scrubbed_text = raw_content
                
            st.success(f"File '{uploaded_file.name}' ready.")
            
            is_excel_mode = uploaded_file.name.lower().endswith(('.xlsx', '.xls'))
            
            if is_excel_mode:
                st.markdown("### 3. Processing Options")
                st.info("Excel files are structured automatically. Privacy Scrub is disabled for binary formats.")
                confirm_scrub = True
                scrubbed_text = None
            else:
                st.markdown("### 3. Privacy Scrub (Mandatory)")
                st.warning("Review the raw data below. You MUST manually delete any sensitive information (like your address or account number) before processing.")
                
                scrubbed_text = st.text_area(
                    "Raw File Contents", 
                    value=st.session_state.get('raw_scrubbed_text', ''), 
                    height=250,
                    key="scrubbed_text_area",
                    help="Edit the text here. Deleting rows from the top won't affect the processor as long as the main table remains."
                )
                
                confirm_scrub = st.checkbox("I confirm that I have reviewed the text and removed any sensitive information.")
            
            col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
            with col_btn2:
                can_process = confirm_scrub and accept_privacy_risk
                if st.button("Confirm & Process", type="primary", use_container_width=True, disabled=not can_process):
                    # Save UI state
                    st.session_state.raw_scrubbed_text = scrubbed_text
                    st.session_state.api_config_state = api_config
                    st.session_state.ai_provider_state = ai_provider
                    st.session_state.name_state = "The User"
                    st.session_state.skip_ai_state = force_skip_ai
                    st.session_state.use_ai_mapper_state = use_ai_mapper
                    
                    st.session_state.processing = True
                    st.rerun()

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
    if not balance_series.empty:
        statement_closing_balance = balance_series.iloc[-1]
        # Mathematical absolute truth: Opening Balance + Net Savings = Closing Balance
        opening_balance = statement_closing_balance - net_savings
    else:
        statement_closing_balance = 0.0
        opening_balance = 0.0
    
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Total Income", f"₹{total_income:,.2f}")
    col2.metric("Total Expenses", f"₹{total_expenses:,.2f}")
    col3.metric("Net Savings", f"₹{net_savings:,.2f}")
    col4.metric("Opening Balance", f"₹{opening_balance:,.2f}")
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
            st.plotly_chart(fig_pie, use_container_width=True, theme="streamlit")

        with col2:
            payment_method_expenses = expense_df.groupby('payment_method')['debit'].sum().sort_values(ascending=True).reset_index()
            fig_bar = px.bar(
                payment_method_expenses, y='payment_method', x='debit',
                title='Total Spending by Payment Method', labels={'debit': 'Total Expenses (₹)', 'payment_method': 'Payment Method'},
                orientation='h', text_auto='.2s'
            )
            fig_bar.update_layout(title_x=0.5, yaxis_title=None)
            st.plotly_chart(fig_bar, use_container_width=True, theme="streamlit")
            
        daily_expenses = expense_df.groupby('date')['debit'].sum().reset_index()
        fig_line = px.line(
            daily_expenses, x='date', y='debit',
            title='Daily Spending Over Time', labels={'date': 'Date', 'debit': 'Total Expenses (₹)'},
            markers=True
        )
        fig_line.update_layout(title_x=0.5)
        st.plotly_chart(fig_line, use_container_width=True, theme="streamlit")

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
            st.plotly_chart(fig_top_merchants, use_container_width=True, theme="streamlit")

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
            st.plotly_chart(fig_income_expense, use_container_width=True, theme="streamlit")

        # Use Streamlit columns to display the two charts side by side
        chart_col1, chart_col2 = st.columns(2)
        
        with chart_col1:
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
                        title='Spend Split by Transaction Type',
                        hole=0.35
                    )
                    fig_tx_split.update_traces(textposition='inside', textinfo='percent+label')
                    fig_tx_split.update_layout(title_x=0.5)
                    st.plotly_chart(fig_tx_split, use_container_width=True, theme="streamlit")

        with chart_col2:
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
                    st.plotly_chart(fig_mode_spend, use_container_width=True, theme="streamlit")

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
                st.plotly_chart(fig_balance_curve, use_container_width=True, theme="streamlit")

    st.markdown("---")
    st.header("Transaction Details")
    st.write("You can edit the 'remark' column below to add your own notes.")
    
    if 'edited_data' not in st.session_state or st.session_state.edited_data is None:
        st.session_state.edited_data = df.copy()

    with st.expander("Filter Transactions", expanded=False):
        col1, col2, col3 = st.columns(3)
        with col1:
            try:
                temp_dates = pd.to_datetime(st.session_state.edited_data['date'], errors='coerce')
                valid_dates = temp_dates.dropna()
                min_date = valid_dates.min().date() if not valid_dates.empty else None
                max_date = valid_dates.max().date() if not valid_dates.empty else None
                date_range = st.date_input("Date Range", value=(min_date, max_date) if min_date and max_date else [], min_value=min_date, max_value=max_date)
            except Exception:
                date_range = []
                st.write("Date filtering unavailable")
        
        with col2:
            unique_cats = sorted([str(c) for c in st.session_state.edited_data.get('category', pd.Series(dtype=str)).dropna().unique() if str(c).strip()])
            selected_categories = st.multiselect("Filter by Category", options=unique_cats)
            
        with col3:
            search_query = st.text_input("Search (Merchant / Remark)")

    filtered_df = st.session_state.edited_data.copy()

    if date_range and len(date_range) == 2:
        start_date, end_date = date_range
        date_col = pd.to_datetime(filtered_df['date'], errors='coerce')
        filtered_df = filtered_df[date_col.dt.date.between(start_date, end_date) | date_col.isna()]
    
    if selected_categories:
        filtered_df = filtered_df[filtered_df['category'].isin(selected_categories)]
        
    if search_query:
        query = search_query.lower()
        merchant_match = filtered_df.get('merchant', pd.Series(dtype=str)).astype(str).str.lower().str.contains(query)
        remark_match = filtered_df.get('remark', pd.Series(dtype=str)).astype(str).str.lower().str.contains(query)
        filtered_df = filtered_df[merchant_match | remark_match]

    visible_cols = ['date', 'merchant', 'transaction_mode', 'mode_confidence', 'debit', 'credit', 'category', 'remark']
    edited_filtered_df = st.data_editor(
        filtered_df,
        column_config={
            "remark": st.column_config.TextColumn("Remarks (Editable)", max_chars=100),
            "transaction_mode": st.column_config.TextColumn("Transaction Mode", disabled=True),
            "mode_confidence": st.column_config.TextColumn("Mode Confidence", disabled=True),
            "debit": st.column_config.NumberColumn("Debit (₹)", format="₹ %.2f"),
            "credit": st.column_config.NumberColumn("Credit (₹)", format="₹ %.2f"),
            "description": None, "payment_method": None, "gateway": None,
        },
        column_order=[col for col in visible_cols if col in filtered_df.columns],
        use_container_width=True, key="data_editor"
    )
    
    st.session_state.edited_data.update(edited_filtered_df)

    export_df = st.session_state.edited_data.copy()
    if st.session_state.get('original_columns'):
        # Keep original columns in their original order, plus the new enrichments
        cols_to_export = st.session_state.original_columns + ['merchant', 'category', 'remark']
        # Preserve order, ignore missing
        cols_to_export = [c for c in dict.fromkeys(cols_to_export) if c in export_df.columns]
        export_df = export_df[cols_to_export]

    # Handle the `.csv` extension properly so we don't get `.csv.csv`
    original_name = st.session_state.uploaded_file_obj.name
    if not original_name.endswith('.csv'):
        original_name += '.csv'

    col_dl1, col_dl2 = st.columns(2)
    with col_dl1:
        st.download_button(
            label="Download as CSV",
            data=convert_df_to_csv(export_df),
            file_name=f"edited_{original_name}",
            mime="text/csv",
            help="Saves your edited remarks to a new CSV file."
        )
    with col_dl2:
        st.download_button(
            label="Download as Excel (.xlsx)",
            data=convert_df_to_excel(export_df),
            file_name=f"edited_{original_name.replace('.csv', '.xlsx')}",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            help="Saves your edited remarks to a new Excel file."
        )

    st.markdown("---")
    st.header("Teach The App New Narration Rules")
    st.write("Save your own narration to category/remark mapping. These rules are reused automatically in future analyses.")

    narration_source_col = 'description' if 'description' in st.session_state.edited_data.columns else 'narration'
    if narration_source_col in st.session_state.edited_data.columns:
        # Group by narration to get unique ones and their current assigned category/remark
        grouped = st.session_state.edited_data.copy()
        grouped[narration_source_col] = grouped[narration_source_col].astype(str)
        grouped = grouped[grouped[narration_source_col].str.strip() != '']
        
        if not grouped.empty:
            grouped = grouped.groupby(narration_source_col).first().reset_index()
            st.write("Check the **Save?** box to save a rule. You can edit the pattern, category, and remark before saving.")
            
            rules_df = pd.DataFrame({
                "Save?": [False] * len(grouped),
                "Pattern to Match": grouped[narration_source_col],
                "Match Type": ["contains"] * len(grouped),
                "Category": grouped.get("category", pd.Series(["Shopping"] * len(grouped))),
                "Remark": grouped.get("remark", pd.Series([""] * len(grouped)))
            })
            
            edited_rules_df = st.data_editor(
                rules_df,
                column_config={
                    "Save?": st.column_config.CheckboxColumn("Save?", default=False),
                    "Pattern to Match": st.column_config.TextColumn("Pattern to Match (Editable)"),
                    "Match Type": st.column_config.SelectboxColumn("Match Type", options=["contains", "exact", "similar"], required=True),
                    "Category": st.column_config.TextColumn("Category"),
                    "Remark": st.column_config.TextColumn("Remark"),
                },
                hide_index=True,
                use_container_width=True,
                key="rules_bulk_editor"
            )
            
            if st.button("Save Selected Rules", type="primary"):
                saved_count = 0
                for _, row in edited_rules_df[edited_rules_df["Save?"] == True].iterrows():
                    pat = row.get("Pattern to Match")
                    cat = row.get("Category")
                    rem = row.get("Remark")
                    mtype = row.get("Match Type")
                    
                    if pd.notna(pat) and str(pat).strip() != "" and pd.notna(cat) and str(cat).strip() != "":
                        try:
                            save_user_mapping(str(pat).strip(), str(cat).strip(), str(rem).strip() if pd.notna(rem) else "", match_type=mtype)
                            saved_count += 1
                        except Exception as e:
                            st.error(f"Failed to save rule for {pat}: {e}")
                
                if saved_count > 0:
                    st.success(f"Successfully saved {saved_count} new rule(s)!")
                else:
                    st.warning("No valid rules were selected to save.")
        else:
            st.info("No narration values available yet for rule creation.")
    else:
        st.info("No narration values available yet for rule creation.")

    with st.expander("View Saved Rules"):
        saved_rules = load_user_mappings()
        if saved_rules:
            st.dataframe(pd.DataFrame(saved_rules), use_container_width=True)
        else:
            st.write("No saved rules yet.")
