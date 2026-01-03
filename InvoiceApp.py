import streamlit as st
import pandas as pd
from datetime import datetime
from supabase import create_client
import os
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER

# --- 1. CRITICAL INITIALIZATION ---
st.set_page_config(page_title="GST Invoice Pro", layout="wide")

# This block ensures st.session_state.items is NEVER None
if 'items' not in st.session_state or not isinstance(st.session_state.items, list):
    st.session_state.items = []
if 'invoice_generated' not in st.session_state:
    st.session_state.invoice_generated = False

@st.cache_resource
def init_supabase():
    url = st.secrets.get("SUPABASE_URL", os.getenv("SUPABASE_URL"))
    key = st.secrets.get("SUPABASE_KEY", os.getenv("SUPABASE_KEY"))
    return create_client(url, key)

db = init_supabase()

# --- 2. HELPERS ---
def number_to_words(num):
    # (Abbreviated for space - use your previous working function here)
    return f"{num:.2f} Rupees Only"

def get_next_invoice_number():
    try:
        res = db.table('invoice_counter').select('counter').eq('id', 1).execute()
        next_val = (res.data[0]['counter'] if res.data else 0) + 1
        db.table('invoice_counter').update({'counter': next_val}).eq('id', 1).execute()
        return f"INV-{next_val:05d}"
    except: return f"INV-{datetime.now().strftime('%H%M%S')}"

# --- 3. UI TABS ---
t1, t2, t3, t4 = st.tabs(["📝 Create", "📊 History", "👥 Customers", "📈 Analytics"])

with t1:
    # --- Sidebars/Header ---
    with st.sidebar:
        st.header("My Business")
        c_name = st.text_input("Name", "Business Name")
        c_state = st.text_input("State", "Maharashtra")
        c_gst = st.text_input("GSTIN", "27AABCU...")

    # --- Customer Selection ---
    col1, col2 = st.columns(2)
    with col1:
        cust_data = db.table('customers').select("*").execute().data or []
        choice = st.selectbox("Select Customer", ["-- New --"] + [c['name'] for c in cust_data])
        if choice == "-- New --":
            cust_name = st.text_input("Cust Name")
            cust_state = st.text_input("Cust State")
            cust_addr = st.text_area("Cust Address")
        else:
            c_match = next(c for c in cust_data if c['name'] == choice)
            cust_name, cust_state, cust_addr = c_match['name'], c_match['state'], c_match['billing_address']
            st.info(f"Billing to: {cust_name}")

    with col2:
        inv_no = get_next_invoice_number()
        inv_date = st.date_input("Date", datetime.now())

    st.divider()

    # --- Line Item Entry ---
    l1, l2, l3, l4, l5 = st.columns([3, 1, 1, 1, 1])
    prod = l1.text_input("Product", key="p_in")
    hsn = l2.text_input("HSN", key="h_in")
    qty = l3.number_input("Qty", 1, key="q_in")
    rate = l4.number_input("Rate", 0.0, key="r_in")
    gst_pct = l5.selectbox("GST%", [0, 5, 12, 18, 28], index=3, key="g_in")

    if st.button("➕ Add Item"):
        if prod and hsn:
            taxable = qty * rate
            tax_amt = (taxable * gst_pct) / 100
            # DEFENSIVE: Re-check list type before append
            if not isinstance(st.session_state.items, list):
                st.session_state.items = []
                
            st.session_state.items.append({
                "product_name": prod, "hsn_code": hsn, "quantity": qty,
                "rate": rate, "taxable_value": taxable, "gst_rate": gst_pct,
                "tax_amount": tax_amt, "total": taxable + tax_amt
            })
            st.rerun()

    # --- Display Items Table ---
    current_items = st.session_state.get('items', [])
    if isinstance(current_items, list) and len(current_items) > 0:
        items_df = pd.DataFrame(current_items)
        st.table(items_df[['product_name', 'hsn_code', 'quantity', 'total']])
        
        g_total = items_df['total'].sum()
        if st.button("🚀 Save & Generate Invoice"):
            is_intra = c_state.strip().lower() == cust_state.strip().lower()
            payload = {
                "invoice_number": inv_no, "invoice_date": inv_date.isoformat(),
                "customer_name": cust_name, "customer_state": cust_state,
                "billing_address": cust_addr, "items": st.session_state.items,
                "subtotal": items_df['taxable_value'].sum(), "total_tax": items_df['tax_amount'].sum(),
                "grand_total": g_total, "is_intrastate": is_intra,
                "amount_in_words": number_to_words(g_total)
            }
            db.table('invoices').insert(payload).execute()
            if choice == "-- New --":
                db.table('customers').insert({"name": cust_name, "state": cust_state, "billing_address": cust_addr}).execute()
            
            st.session_state.invoice_generated = True
            st.success("Invoice Saved!")
            st.rerun()
    
    if st.session_state.invoice_generated:
        if st.button("Reset for New Invoice"):
            st.session_state.items = []
            st.session_state.invoice_generated = False
            st.rerun()

with t4:
    st.subheader("📈 Business Analytics & GST Summary")
    inv_res = db.table('invoices').select("*").execute()
    if inv_res.data:
        df_all = pd.DataFrame(inv_res.data)
        df_all['invoice_date'] = pd.to_datetime(df_all['invoice_date'])
        
        # Monthly Chart
        df_all['Month'] = df_all['invoice_date'].dt.strftime('%b %Y')
        st.bar_chart(df_all.groupby('Month')['grand_total'].sum())

        # HSN & Tax Summary
        hsn_list, tax_list = [], []
        for _, row in df_all.iterrows():
            for item in row['items']:
                hsn_list.append({"HSN": item['hsn_code'], "Value": item['taxable_value']})
                tax_list.append({
                    "Rate": f"{item['gst_rate']}%",
                    "Taxable": item['taxable_value'],
                    "CGST": item['tax_amount']/2 if row['is_intrastate'] else 0,
                    "SGST": item['tax_amount']/2 if row['is_intrastate'] else 0,
                    "IGST": item['tax_amount'] if not row['is_intrastate'] else 0
                })
        
        c1, c2 = st.columns(2)
        with c1:
            st.write("**HSN Totals**")
            st.dataframe(pd.DataFrame(hsn_list).groupby("HSN").sum(), use_container_width=True)
        with c2:
            st.write("**GST Tax Summary**")
            st.dataframe(pd.DataFrame(tax_list).groupby("Rate").sum(), use_container_width=True)
