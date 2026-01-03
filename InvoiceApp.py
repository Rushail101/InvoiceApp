import streamlit as st
import pandas as pd
from datetime import datetime
from supabase import create_client, Client
import os
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_RIGHT

# --- INITIALIZATION ---
st.set_page_config(page_title="GST Invoice Pro", page_icon="🧾", layout="wide")

# Safe Session State Init
if 'items' not in st.session_state:
    st.session_state.items = []
if 'invoice_generated' not in st.session_state:
    st.session_state.invoice_generated = False
if 'pdf_buffer' not in st.session_state:
    st.session_state.pdf_buffer = None

@st.cache_resource
def init_supabase():
    url = st.secrets.get("SUPABASE_URL", os.getenv("SUPABASE_URL"))
    key = st.secrets.get("SUPABASE_KEY", os.getenv("SUPABASE_KEY"))
    if not url or not key:
        st.error("Credentials missing in .streamlit/secrets.toml")
        st.stop()
    return create_client(url, key)

db = init_supabase()

# --- UTILS ---
def number_to_words(num):
    ones = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine"]
    tens = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]
    teens = ["Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen", "Seventeen", "Eighteen", "Nineteen"]
    
    def convert_below_thousand(n):
        if n == 0: return ""
        elif n < 10: return ones[n]
        elif n < 20: return teens[n - 10]
        elif n < 100: return tens[n // 10] + (" " + ones[n % 10] if n % 10 != 0 else "")
        else: return ones[n // 100] + " Hundred" + (" " + convert_below_thousand(n % 100) if n % 100 != 0 else "")
    
    rupees = int(num)
    paise = round((num - rupees) * 100)
    res = ""
    if rupees >= 10000000: res += convert_below_thousand(rupees // 10000000) + " Crore "
    if (rupees % 10000000) >= 100000: res += convert_below_thousand((rupees % 10000000) // 100000) + " Lakh "
    if (rupees % 100000) >= 1000: res += convert_below_thousand((rupees % 100000) // 1000) + " Thousand "
    if (rupees % 1000) > 0: res += convert_below_thousand(rupees % 1000)
    
    res = res.strip() + " Rupees"
    if paise > 0: res += f" and {convert_below_thousand(paise)} Paise"
    return res + " Only"

def get_next_invoice_number():
    try:
        res = db.table('invoice_counter').select('counter').eq('id', 1).execute()
        next_val = res.data[0]['counter'] + 1
        db.table('invoice_counter').update({'counter': next_val}).eq('id', 1).execute()
        return f"INV-{next_val:05d}"
    except: return f"INV-{datetime.now().strftime('%H%M%S')}"

def generate_pdf(inv, comp):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []
    
    elements.append(Paragraph("TAX INVOICE", ParagraphStyle('Title', fontSize=18, alignment=TA_CENTER)))
    elements.append(Spacer(1, 12))
    
    # Header
    data = [[f"{comp['name']}\n{comp['address']}\nGSTIN: {comp['gstin']}", 
             f"Invoice No: {inv['invoice_number']}\nDate: {inv['invoice_date']}"]]
    t = Table(data, colWidths=[4*inch, 2*inch])
    elements.append(t)
    elements.append(Spacer(1, 12))
    
    # Items
    item_data = [['Product', 'HSN', 'Qty', 'Rate', 'Total']]
    for i in inv['items']:
        item_data.append([i['product_name'], i['hsn_code'], i['quantity'], i['rate'], i['total']])
    
    it = Table(item_data, colWidths=[2.5*inch, 1*inch, 0.5*inch, 1*inch, 1*inch])
    it.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 0.5, colors.grey), ('BACKGROUND', (0,0), (-1,0), colors.whitesmoke)]))
    elements.append(it)
    
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(f"<b>Grand Total: ₹{inv['grand_total']:.2f}</b>", styles['Normal']))
    elements.append(Paragraph(f"Words: {inv['amount_in_words']}", styles['Normal']))
    
    doc.build(elements)
    buffer.seek(0)
    return buffer

# --- MAIN UI ---
st.title("🧾 GST Invoice System")

with st.sidebar:
    st.header("Company Settings")
    c_name = st.text_input("Name", "My Business")
    c_addr = st.text_area("Address", "Main Street, City")
    c_gst = st.text_input("GSTIN", "27AABCU9603R1ZM")
    c_state = st.text_input("State", "Maharashtra")
    company_data = {"name": c_name, "address": c_addr, "gstin": c_gst, "state": c_state}

t1, t2, t3, t4 = st.tabs(["📝 Create", "📊 History", "👥 Customers", "📈 Analytics"])

with t1:
    col1, col2 = st.columns(2)
    with col1:
        customers = db.table('customers').select("*").execute().data
        choice = st.selectbox("Customer", ["-- New --"] + [c['name'] for c in customers])
        if choice == "-- New --":
            cust_name = st.text_input("Name")
            cust_gst = st.text_input("GSTIN (Optional)")
            cust_addr = st.text_area("Address")
            cust_state = st.text_input("State")
        else:
            c_obj = next(c for c in customers if c['name'] == choice)
            cust_name, cust_gst, cust_addr, cust_state = c_obj['name'], c_obj['gstin'], c_obj['billing_address'], c_obj['state']
            st.success(f"Selected: {cust_name}")

    with col2:
        inv_no = get_next_invoice_number()
        st.info(f"Assigning: {inv_no}")
        inv_date = st.date_input("Invoice Date")

    st.divider()
    # Line Items
    l1, l2, l3, l4, l5 = st.columns([3, 1, 1, 1, 1])
    prod = l1.text_input("Item Name")
    hsn = l2.text_input("HSN")
    qty = l3.number_input("Qty", 1)
    rate = l4.number_input("Rate", 0.0)
    gst_pct = l5.selectbox("GST%", [0, 5, 12, 18, 28], index=3)

    if st.button("➕ Add to Invoice"):
        taxable = qty * rate
        tax_amt = (taxable * gst_pct) / 100
        st.session_state.items.append({
            "product_name": prod, "hsn_code": hsn, "quantity": qty, 
            "rate": rate, "taxable_value": taxable, "gst_rate": gst_pct, 
            "tax_amount": tax_amt, "total": taxable + tax_amt
        })
        st.rerun()

    if st.session_state.items:
        items_df = pd.DataFrame(st.session_state.items)
        st.dataframe(items_df[['product_name', 'hsn_code', 'total']], use_container_width=True)
        
        g_total = items_df['total'].sum()
        s_total = items_df['taxable_value'].sum()
        t_tax = items_df['tax_amount'].sum()
        
        st.metric("Total Payable", f"₹{g_total:,.2f}")
        
        if st.button("💾 Generate & Save"):
            is_intra = c_state.lower() == cust_state.lower()
            inv_payload = {
                "invoice_number": inv_no, "invoice_date": inv_date.isoformat(),
                "customer_name": cust_name, "customer_gstin": cust_gst,
                "customer_state": cust_state, "billing_address": cust_addr,
                "items": st.session_state.items, "subtotal": s_total,
                "total_tax": t_tax, "grand_total": g_total,
                "is_intrastate": is_intra, "amount_in_words": number_to_words(g_total)
            }
            db.table('invoices').insert(inv_payload).execute()
            if choice == "-- New --":
                db.table('customers').insert({"name": cust_name, "gstin": cust_gst, "billing_address": cust_addr, "state": cust_state}).execute()
            
            st.session_state.pdf_buffer = generate_pdf(inv_payload, company_data)
            st.session_state.invoice_generated = True
            st.rerun()

    if st.session_state.invoice_generated:
        st.download_button("📩 Download PDF", st.session_state.pdf_buffer, f"{inv_no}.pdf")
        if st.button("New Invoice"):
            st.session_state.items = []; st.session_state.invoice_generated = False; st.rerun()

with t2:
    hist = db.table('invoices').select("invoice_number, invoice_date, customer_name, grand_total").order('invoice_date', desc=True).execute()
    if hist.data: st.dataframe(pd.DataFrame(hist.data), use_container_width=True)

with t3:
    st.dataframe(pd.DataFrame(db.table('customers').select("*").execute().data), use_container_width=True)

with t4:
    st.subheader("📊 Analytics & GST Tax Summary")
    data_res = db.table('invoices').select("*").execute()
    if data_res.data:
        df_an = pd.DataFrame(data_res.data)
        df_an['invoice_date'] = pd.to_datetime(df_an['invoice_date'])
        
        # Monthly
        df_an['Month'] = df_an['invoice_date'].dt.strftime('%b %Y')
        st.write("**Monthly Revenue**")
        st.bar_chart(df_an.groupby('Month')['grand_total'].sum())

        # HSN & Tax Summary Calculation
        hsn_data = []
        tax_summary = []
        for _, row in df_an.iterrows():
            for item in row['items']:
                hsn_data.append({"HSN": item['hsn_code'], "Value": item['taxable_value']})
                
                # Tax Summary Logic
                rate = item['gst_rate']
                tax = item['tax_amount']
                tax_summary.append({
                    "Rate": f"{rate}%", "Taxable": item['taxable_value'],
                    "CGST": tax/2 if row['is_intrastate'] else 0,
                    "SGST": tax/2 if row['is_intrastate'] else 0,
                    "IGST": tax if not row['is_intrastate'] else 0
                })

        c1, c2 = st.columns(2)
        with c1:
            st.write("**HSN Breakdown**")
            st.dataframe(pd.DataFrame(hsn_data).groupby("HSN").sum(), use_container_width=True)
        with c2:
            st.write("**Tax Summary (By Rate)**")
            st.dataframe(pd.DataFrame(tax_summary).groupby("Rate").sum(), use_container_width=True)
    else:
        st.info("No data yet.")
