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
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT

# Page config
st.set_page_config(page_title="GST Invoice Generator", page_icon="🧾", layout="wide")

# Initialize Supabase client
@st.cache_resource
def init_supabase():
    url = st.secrets.get("SUPABASE_URL", os.getenv("SUPABASE_URL"))
    key = st.secrets.get("SUPABASE_KEY", os.getenv("SUPABASE_KEY"))
    if not url or not key:
        st.error("⚠️ Supabase credentials not found! Please add SUPABASE_URL and SUPABASE_KEY to your secrets.")
        st.stop()
    return create_client(url, key)

supabase = init_supabase()

# Initialize session state IMMEDIATELY after supabase
if 'items' not in st.session_state:
    st.session_state.items = []
if 'invoice_generated' not in st.session_state:
    st.session_state.invoice_generated = False

# Ensure items is always a list
if not isinstance(st.session_state.items, list):
    st.session_state.items = []

# Number to words conversion
def number_to_words(num):
    """Convert number to Indian number system words"""
    ones = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine"]
    tens = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]
    teens = ["Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen", "Seventeen", "Eighteen", "Nineteen"]
    
    def convert_below_thousand(n):
        if n == 0:
            return ""
        elif n < 10:
            return ones[n]
        elif n < 20:
            return teens[n - 10]
        elif n < 100:
            return tens[n // 10] + (" " + ones[n % 10] if n % 10 != 0 else "")
        else:
            return ones[n // 100] + " Hundred" + (" " + convert_below_thousand(n % 100) if n % 100 != 0 else "")
    
    if num == 0:
        return "Zero Rupees Only"
    
    # Split into rupees and paise
    rupees = int(num)
    paise = round((num - rupees) * 100)
    
    result = ""
    
    # Crores
    if rupees >= 10000000:
        crores = rupees // 10000000
        result += convert_below_thousand(crores) + " Crore "
        rupees %= 10000000
    
    # Lakhs
    if rupees >= 100000:
        lakhs = rupees // 100000
        result += convert_below_thousand(lakhs) + " Lakh "
        rupees %= 100000
    
    # Thousands
    if rupees >= 1000:
        thousands = rupees // 1000
        result += convert_below_thousand(thousands) + " Thousand "
        rupees %= 1000
    
    # Remaining
    if rupees > 0:
        result += convert_below_thousand(rupees)
    
    result = result.strip() + " Rupees"
    
    if paise > 0:
        result += " and " + convert_below_thousand(paise) + " Paise"
    
    return result + " Only"

# Database functions
def get_next_invoice_number():
    """Get next invoice number from database"""
    try:
        result = supabase.table('invoice_counter').select('*').execute()
        if result.data and len(result.data) > 0:
            current = result.data[0]['counter']
            next_num = current + 1
            supabase.table('invoice_counter').update({'counter': next_num}).eq('id', 1).execute()
            return f"INV-{next_num:05d}"
        else:
            # Initialize counter
            supabase.table('invoice_counter').insert({'id': 1, 'counter': 1}).execute()
            return "INV-00001"
    except Exception as e:
        st.error(f"Error getting invoice number: {e}")
        return f"INV-{datetime.now().strftime('%Y%m%d%H%M%S')}"

def save_customer(customer_data):
    """Save or update customer in database"""
    try:
        # Check if customer exists
        result = supabase.table('customers').select('*').eq('name', customer_data['name']).execute()
        if result.data and len(result.data) > 0:
            # Update
            supabase.table('customers').update(customer_data).eq('name', customer_data['name']).execute()
        else:
            # Insert
            supabase.table('customers').insert(customer_data).execute()
        return True
    except Exception as e:
        st.error(f"Error saving customer: {e}")
        return False

def get_customers():
    """Get all customers from database"""
    try:
        result = supabase.table('customers').select('*').order('name').execute()
        return result.data if result.data else []
    except:
        return []

def save_invoice(invoice_data):
    """Save invoice to database"""
    try:
        supabase.table('invoices').insert(invoice_data).execute()
        return True
    except Exception as e:
        st.error(f"Error saving invoice: {e}")
        return False

def generate_pdf(invoice_data, company_data):
    """Generate PDF invoice"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    
    elements = []
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'], fontSize=20, textColor=colors.HexColor('#1f4788'), alignment=TA_CENTER, spaceAfter=12)
    heading_style = ParagraphStyle('CustomHeading', parent=styles['Heading2'], fontSize=12, textColor=colors.HexColor('#1f4788'), spaceAfter=6)
    normal_style = styles['Normal']
    
    # Title
    elements.append(Paragraph("TAX INVOICE", title_style))
    elements.append(Spacer(1, 12))
    
    # Company and Invoice details side by side
    company_invoice_data = [
        [Paragraph(f"<b>{company_data['name']}</b><br/>{company_data['address']}<br/>GSTIN: {company_data['gstin']}<br/>State: {company_data['state']}<br/>Phone: {company_data.get('phone', 'N/A')}", normal_style),
         Paragraph(f"<b>Invoice No:</b> {invoice_data['invoice_number']}<br/><b>Date:</b> {invoice_data['invoice_date']}<br/><b>Place of Supply:</b> {invoice_data['place_of_supply']}", normal_style)]
    ]
    
    t = Table(company_invoice_data, colWidths=[3.5*inch, 2.5*inch])
    t.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 12))
    
    # Bill To and Ship To
    bill_ship_data = [
        [Paragraph("<b>Bill To:</b>", heading_style), Paragraph("<b>Ship To:</b>", heading_style)],
        [Paragraph(f"{invoice_data['customer_name']}<br/>{invoice_data['billing_address']}<br/>GSTIN: {invoice_data.get('customer_gstin', 'N/A')}<br/>State: {invoice_data.get('customer_state', 'N/A')}", normal_style),
         Paragraph(f"{invoice_data['customer_name']}<br/>{invoice_data['shipping_address']}", normal_style)]
    ]
    
    t = Table(bill_ship_data, colWidths=[3*inch, 3*inch])
    t.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 12))
    
    # Items table
    items_data = [['S.No', 'Product/Service', 'HSN/SAC', 'Qty', 'Rate', 'Taxable Value', 'GST', 'Amount']]
    
    for idx, item in enumerate(invoice_data['items'], 1):
        items_data.append([
            str(idx),
            item['product_name'],
            item['hsn_code'],
            str(item['quantity']),
            f"₹{item['rate']:.2f}",
            f"₹{item['taxable_value']:.2f}",
            f"{item['gst_rate']}%",
            f"₹{item['total']:.2f}"
        ])
    
    # Add totals
    items_data.append(['', '', '', '', '', f"₹{invoice_data['subtotal']:.2f}", 'Total:', f"₹{invoice_data['subtotal']:.2f}"])
    
    if invoice_data['is_intrastate']:
        cgst = invoice_data['total_tax'] / 2
        sgst = invoice_data['total_tax'] / 2
        items_data.append(['', '', '', '', '', '', f"CGST:", f"₹{cgst:.2f}"])
        items_data.append(['', '', '', '', '', '', f"SGST:", f"₹{sgst:.2f}"])
    else:
        items_data.append(['', '', '', '', '', '', f"IGST:", f"₹{invoice_data['total_tax']:.2f}"])
    
    items_data.append(['', '', '', '', '', '', Paragraph('<b>Grand Total:</b>', normal_style), Paragraph(f"<b>₹{invoice_data['grand_total']:.2f}</b>", normal_style)])
    
    t = Table(items_data, colWidths=[0.5*inch, 2*inch, 0.8*inch, 0.6*inch, 0.8*inch, 1*inch, 0.8*inch, 1*inch])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f4788')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, -1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('ALIGN', (3, 1), (3, -1), 'RIGHT'),
        ('ALIGN', (4, 1), (-1, -1), 'RIGHT'),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 12))
    
    # Amount in words
    elements.append(Paragraph(f"<b>Amount in Words:</b> {invoice_data['amount_in_words']}", normal_style))
    elements.append(Spacer(1, 12))
    
    # Bank details
    if company_data.get('bank_details'):
        elements.append(Paragraph("<b>Bank Details:</b>", heading_style))
        elements.append(Paragraph(company_data['bank_details'].replace('\n', '<br/>'), normal_style))
        elements.append(Spacer(1, 12))
    
    # Terms and signature
    elements.append(Spacer(1, 24))
    elements.append(Paragraph("<b>Terms & Conditions:</b><br/>1. Payment due within 30 days<br/>2. Interest @18% p.a. will be charged on delayed payments", normal_style))
    elements.append(Spacer(1, 24))
    elements.append(Paragraph(f"<b>For {company_data['name']}</b><br/><br/><br/>Authorized Signatory", ParagraphStyle('RightAlign', parent=normal_style, alignment=TA_RIGHT)))
    
    doc.build(elements)
    buffer.seek(0)
    return buffer

# Main app
st.title("🧾 GST Invoice Generator")
st.markdown("---")

# Sidebar for company details
with st.sidebar:
    st.header("⚙️ Company Details")
    company_name = st.text_input("Company Name", "Your Company Pvt Ltd")
    company_address = st.text_area("Address", "123, Business Street\nCity - 400001\nMaharashtra, India")
    company_gstin = st.text_input("GSTIN", "27AABCU9603R1ZM")
    company_state = st.text_input("State", "Maharashtra")
    company_phone = st.text_input("Phone", "+91-9876543210")
    company_bank = st.text_area("Bank Details (Optional)", "Bank: HDFC Bank\nA/c No: 12345678901234\nIFSC: HDFC0001234\nBranch: Mumbai")

company_data = {
    'name': company_name,
    'address': company_address,
    'gstin': company_gstin,
    'state': company_state,
    'phone': company_phone,
    'bank_details': company_bank
}

# Main form
tab1, tab2, tab3, tab4 = st.tabs(["📝 Create Invoice", "📊 Invoice History", "👥 Customers", "📈 HSN Analytics"])

with tab1:
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Customer Details")
        
        # Load existing customers
        customers = get_customers()
        customer_names = ["-- New Customer --"] + [c['name'] for c in customers]
        
        selected_customer = st.selectbox("Select Customer", customer_names)
        
        # Initialize variables
        customer_name = ""
        customer_gstin = ""
        billing_address = ""
        shipping_address = ""
        customer_state = ""
        
        if selected_customer != "-- New Customer --":
            customer = next((c for c in customers if c['name'] == selected_customer), None)
            if customer:
                customer_name = customer['name']
                customer_gstin = customer.get('gstin', '')
                billing_address = customer.get('billing_address', '')
                shipping_address = customer.get('shipping_address', '')
                customer_state = customer.get('state', '')
                
                # Display in text inputs (read-only style)
                st.text_input("Customer/Company Name *", value=customer_name, key="existing_customer", disabled=True)
                st.text_input("Customer GSTIN", value=customer_gstin, key="existing_gstin", disabled=True)
                st.text_area("Billing Address *", value=billing_address, key="existing_billing", disabled=True)
                st.text_area("Shipping Address *", value=shipping_address, key="existing_shipping", disabled=True)
                st.text_input("Customer State *", value=customer_state, key="existing_state", disabled=True)
        else:
            customer_name = st.text_input("Customer/Company Name *", key="new_customer")
            customer_gstin = st.text_input("Customer GSTIN (Optional)", key="new_gstin")
            billing_address = st.text_area("Billing Address *", key="new_billing")
            shipping_address = st.text_area("Shipping Address *", key="new_shipping")
            customer_state = st.text_input("Customer State *", key="new_state")
        
        if selected_customer == "-- New Customer --":
            if st.button("💾 Save Customer"):
                if customer_name and billing_address:
                    customer_data = {
                        'name': customer_name,
                        'gstin': customer_gstin,
                        'billing_address': billing_address,
                        'shipping_address': shipping_address,
                        'state': customer_state,
                        'created_at': datetime.now().isoformat()
                    }
                    if save_customer(customer_data):
                        st.success("✅ Customer saved successfully!")
                        st.rerun()
    
    with col2:
        st.subheader("Invoice Details")
        invoice_number = get_next_invoice_number()
        st.text_input("Invoice Number", invoice_number, disabled=True)
        invoice_date = st.date_input("Invoice Date", datetime.now())
        place_of_supply = st.text_input("Place of Supply", customer_state if 'customer_state' in locals() else "")
    
    st.markdown("---")
    st.subheader("Add Products/Services")
    
    col1, col2, col3, col4, col5 = st.columns([3, 2, 1, 1, 1])
    
    with col1:
        product_name = st.text_input("Product/Service Name", key="product")
    with col2:
        hsn_code = st.text_input("HSN/SAC Code", key="hsn")
    with col3:
        quantity = st.number_input("Quantity", min_value=1, value=1, key="qty")
    with col4:
        rate = st.number_input("Rate (₹)", min_value=0.0, value=0.0, step=0.01, key="rate")
    with col5:
        gst_rate = st.selectbox("GST %", [0, 5, 12, 18, 28], key="gst")
    
    if st.button("➕ Add Item"):
        if product_name and hsn_code:
            taxable_value = quantity * rate
            tax_amount = (taxable_value * gst_rate) / 100
            total = taxable_value + tax_amount
            
            item = {
                'product_name': product_name,
                'hsn_code': hsn_code,
                'quantity': quantity,
                'rate': rate,
                'taxable_value': taxable_value,
                'gst_rate': gst_rate,
                'tax_amount': tax_amount,
                'total': total
            }
            # Multiple safety checks
            try:
                if 'items' not in st.session_state:
                    st.session_state['items'] = []
                if st.session_state.items is None:
                    st.session_state['items'] = []
                if not isinstance(st.session_state.items, list):
                    st.session_state['items'] = []
                
                # Create a new list, append, then reassign
                current_items = list(st.session_state.items)
                current_items.append(item)
                st.session_state.items = current_items
                st.rerun()
            except Exception as e:
                st.error(f"Error adding item: {e}")
                st.session_state['items'] = [item]
                st.rerun()
        else:
            st.error("Please fill product name and HSN code")
    
    # Display items
    try:
        items_list = st.session_state.get('items', [])
    except:
        items_list = []
        st.session_state.items = []
    
    if len(items_list) > 0:
        st.markdown("### 📦 Items Added")
        
        items_df = pd.DataFrame(items_list)
        items_df['S.No'] = range(1, len(items_df) + 1)
        items_df = items_df[['S.No', 'product_name', 'hsn_code', 'quantity', 'rate', 'taxable_value', 'gst_rate', 'tax_amount', 'total']]
        items_df.columns = ['S.No', 'Product', 'HSN', 'Qty', 'Rate', 'Taxable Value', 'GST%', 'Tax', 'Total']
        
        st.dataframe(items_df, use_container_width=True, hide_index=True)
        
        col1, col2 = st.columns([3, 1])
        with col2:
            if st.button("🗑️ Clear All Items"):
                st.session_state.items = []
                st.rerun()
        
        st.markdown("---")
        st.markdown("### ➕ Add More Products")
        
        # Show add product form even when items exist
        col1, col2, col3, col4, col5 = st.columns([3, 2, 1, 1, 1])
        
        with col1:
            extra_product = st.text_input("Product/Service Name", key="extra_product")
        with col2:
            extra_hsn = st.text_input("HSN/SAC Code", key="extra_hsn")
        with col3:
            extra_qty = st.number_input("Quantity", min_value=1, value=1, key="extra_qty")
        with col4:
            extra_rate = st.number_input("Rate (₹)", min_value=0.0, value=0.0, step=0.01, key="extra_rate")
        with col5:
            extra_gst = st.selectbox("GST %", [0, 5, 12, 18, 28], key="extra_gst")
        
        if st.button("➕ Add Another Item", key="add_extra"):
            if extra_product and extra_hsn:
                extra_taxable = extra_qty * extra_rate
                extra_tax = (extra_taxable * extra_gst) / 100
                extra_total = extra_taxable + extra_tax
                
                extra_item = {
                    'product_name': extra_product,
                    'hsn_code': extra_hsn,
                    'quantity': extra_qty,
                    'rate': extra_rate,
                    'taxable_value': extra_taxable,
                    'gst_rate': extra_gst,
                    'tax_amount': extra_tax,
                    'total': extra_total
                }
                try:
                    current_items = list(st.session_state.items)
                    current_items.append(extra_item)
                    st.session_state.items = current_items
                    st.success("✅ Item added!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
            else:
                st.error("Please fill product name and HSN code")
        
        st.markdown("---")
        
        # Calculate totals
        subtotal = sum(item['taxable_value'] for item in items_list)
        total_tax = sum(item['tax_amount'] for item in items_list)
        grand_total = sum(item['total'] for item in items_list)
        
        # Check if intrastate or interstate
        is_intrastate = company_state.strip().lower() == (customer_state.strip().lower() if 'customer_state' in locals() else '')
        
        # Display totals
        st.markdown("---")
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col2:
            st.metric("Subtotal", f"₹{subtotal:.2f}")
            if is_intrastate:
                st.metric("CGST", f"₹{total_tax/2:.2f}")
                st.metric("SGST", f"₹{total_tax/2:.2f}")
            else:
                st.metric("IGST", f"₹{total_tax:.2f}")
        
        with col3:
            st.metric("**Grand Total**", f"**₹{grand_total:.2f}**")
        
        amount_in_words = number_to_words(grand_total)
        st.info(f"**Amount in Words:** {amount_in_words}")
        
        st.markdown("---")
        
        # Generate invoice button
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            if st.button("📄 Generate Invoice", type="primary", use_container_width=True):
                # Validate customer details
                if 'customer_name' not in locals() or not customer_name:
                    st.error("❌ Please fill customer name")
                elif 'billing_address' not in locals() or not billing_address:
                    st.error("❌ Please fill billing address")
                elif 'customer_state' not in locals() or not customer_state:
                    st.error("❌ Please fill customer state")
                elif len(items_list) == 0:
                    st.error("❌ Please add at least one item to the invoice")
                else:
                    try:
                        invoice_data = {
                            'invoice_number': invoice_number,
                            'invoice_date': invoice_date.strftime('%Y-%m-%d'),
                            'customer_name': customer_name,
                            'customer_gstin': customer_gstin if 'customer_gstin' in locals() else '',
                            'customer_state': customer_state,
                            'billing_address': billing_address,
                            'shipping_address': shipping_address if 'shipping_address' in locals() else billing_address,
                            'place_of_supply': place_of_supply,
                            'items': items_list,
                            'subtotal': subtotal,
                            'total_tax': total_tax,
                            'grand_total': grand_total,
                            'is_intrastate': is_intrastate,
                            'amount_in_words': amount_in_words,
                            'created_at': datetime.now().isoformat()
                        }
                        
                        # Generate PDF
                        with st.spinner('Generating PDF...'):
                            pdf_buffer = generate_pdf(invoice_data, company_data)
                        
                        # Save to database
                        with st.spinner('Saving to database...'):
                            if save_invoice(invoice_data):
                                st.session_state.invoice_generated = True
                                st.session_state.pdf_buffer = pdf_buffer
                                st.session_state.current_invoice_number = invoice_number
                                st.session_state.current_invoice_date = invoice_date.strftime('%Y%m%d')
                                st.success("✅ Invoice generated successfully!")
                                st.balloons()
                                st.rerun()
                            else:
                                st.error("❌ Failed to save invoice to database")
                    except Exception as e:
                        st.error(f"❌ Error generating invoice: {str(e)}")
                        import traceback
                        st.code(traceback.format_exc())
    
    # Download and reset section
    if st.session_state.invoice_generated and hasattr(st.session_state, 'pdf_buffer'):
        st.markdown("---")
        st.success("🎉 Invoice Generated Successfully!")
        
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            st.download_button(
                label="⬇️ Download Invoice PDF",
                data=st.session_state.pdf_buffer,
                file_name=f"Invoice_{st.session_state.get('current_invoice_number', 'INV')}_{st.session_state.get('current_invoice_date', datetime.now().strftime('%Y%m%d'))}.pdf",
                mime="application/pdf",
                use_container_width=True,
                key="main_download"
            )
            
            st.write("")
            
            if st.button("🔄 Create New Invoice", use_container_width=True, type="primary"):
                st.session_state.items = []
                st.session_state.invoice_generated = False
                if hasattr(st.session_state, 'pdf_buffer'):
                    delattr(st.session_state, 'pdf_buffer')
                if hasattr(st.session_state, 'current_invoice_number'):
                    delattr(st.session_state, 'current_invoice_number')
                if hasattr(st.session_state, 'current_invoice_date'):
                    delattr(st.session_state, 'current_invoice_date')
                st.rerun()
    else:
        st.info("👆 Add items to the invoice to see totals and generate PDF")

with tab2:
    st.subheader("📊 Invoice History")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        search_term = st.text_input("🔍 Search by Invoice No or Customer Name", "")
    with col2:
        st.write("")
        st.write("")
        if st.button("🔄 Refresh", use_container_width=True):
            st.rerun()
    
    try:
        result = supabase.table('invoices').select('*').order('created_at', desc=True).execute()
        if result.data and len(result.data) > 0:
            invoices = result.data
            
            # Filter if search term provided
            if search_term:
                invoices = [inv for inv in invoices if 
                           search_term.lower() in inv.get('invoice_number', '').lower() or 
                           search_term.lower() in inv.get('customer_name', '').lower()]
            
            if invoices:
                # Display invoices as cards with action buttons
                for invoice in invoices:
                    with st.container():
                        col1, col2, col3, col4 = st.columns([2, 2, 1, 2])
                        
                        with col1:
                            st.markdown(f"**Invoice:** {invoice['invoice_number']}")
                            st.caption(f"Date: {invoice['invoice_date']}")
                        
                        with col2:
                            st.markdown(f"**Customer:** {invoice['customer_name']}")
                            st.caption(f"GSTIN: {invoice.get('customer_gstin', 'N/A')}")
                        
                        with col3:
                            st.metric("Amount", f"₹{invoice['grand_total']:,.2f}")
                        
                        with col4:
                            col_view, col_download = st.columns(2)
                            
                            with col_view:
                                if st.button("👁️ View", key=f"view_{invoice['id']}", use_container_width=True):
                                    st.session_state.selected_invoice = invoice
                                    st.session_state.show_invoice_modal = True
                            
                            with col_download:
                                # Generate PDF for download
                                pdf_buffer = generate_pdf(invoice, company_data)
                                st.download_button(
                                    label="📥",
                                    data=pdf_buffer,
                                    file_name=f"{invoice['invoice_number']}.pdf",
                                    mime="application/pdf",
                                    key=f"download_{invoice['id']}",
                                    use_container_width=True
                                )
                        
                        st.markdown("---")
                
                # Invoice Detail Modal
                if st.session_state.get('show_invoice_modal', False) and st.session_state.get('selected_invoice'):
                    invoice = st.session_state.selected_invoice
                    
                    st.markdown("### 📄 Invoice Details")
                    
                    # Close button
                    if st.button("✖️ Close", key="close_modal"):
                        st.session_state.show_invoice_modal = False
                        st.session_state.selected_invoice = None
                        st.rerun()
                    
                    # Invoice header
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown(f"""
                        **Invoice Number:** {invoice['invoice_number']}  
                        **Date:** {invoice['invoice_date']}  
                        **Place of Supply:** {invoice.get('place_of_supply', 'N/A')}
                        """)
                    
                    with col2:
                        st.markdown(f"""
                        **Customer:** {invoice['customer_name']}  
                        **GSTIN:** {invoice.get('customer_gstin', 'N/A')}  
                        **State:** {invoice.get('customer_state', 'N/A')}
                        """)
                    
                    st.markdown("---")
                    
                    # Items table
                    st.markdown("#### 📦 Items")
                    items = invoice.get('items', [])
                    if items:
                        items_df = pd.DataFrame(items)
                        items_df['S.No'] = range(1, len(items_df) + 1)
                        items_df = items_df[['S.No', 'product_name', 'hsn_code', 'quantity', 'rate', 'taxable_value', 'gst_rate', 'tax_amount', 'total']]
                        items_df.columns = ['S.No', 'Product', 'HSN', 'Qty', 'Rate (₹)', 'Taxable Value (₹)', 'GST %', 'Tax (₹)', 'Total (₹)']
                        
                        # Format currency columns
                        for col in ['Rate (₹)', 'Taxable Value (₹)', 'Tax (₹)', 'Total (₹)']:
                            items_df[col] = items_df[col].apply(lambda x: f"{x:.2f}")
                        
                        st.dataframe(items_df, use_container_width=True, hide_index=True)
                    
                    # Totals
                    col1, col2, col3 = st.columns([2, 1, 1])
                    with col2:
                        st.markdown(f"""
                        **Subtotal:** ₹{invoice['subtotal']:,.2f}  
                        """)
                        if invoice.get('is_intrastate', True):
                            st.markdown(f"""
                            **CGST:** ₹{invoice['total_tax']/2:,.2f}  
                            **SGST:** ₹{invoice['total_tax']/2:,.2f}
                            """)
                        else:
                            st.markdown(f"**IGST:** ₹{invoice['total_tax']:,.2f}")
                    
                    with col3:
                        st.markdown(f"### **Grand Total:** ₹{invoice['grand_total']:,.2f}")
                    
                    st.info(f"**Amount in Words:** {invoice.get('amount_in_words', '')}")
                    
                    st.markdown("---")
                    
                    # Download button
                    pdf_buffer = generate_pdf(invoice, company_data)
                    col1, col2, col3 = st.columns([1, 1, 1])
                    with col2:
                        st.download_button(
                            label="📥 Download Invoice PDF",
                            data=pdf_buffer,
                            file_name=f"{invoice['invoice_number']}.pdf",
                            mime="application/pdf",
                            key="download_modal",
                            use_container_width=True
                        )
            else:
                st.info("No invoices match your search.")
        else:
            st.info("No invoices found. Create your first invoice!")
    except Exception as e:
        st.error(f"Error loading invoices: {e}")

with tab3:
    st.subheader("👥 Customer Database")
    customers = get_customers()
    if customers:
        customers_df = pd.DataFrame(customers)
        customers_df = customers_df[['name', 'gstin', 'state', 'billing_address']]
        customers_df.columns = ['Name', 'GSTIN', 'State', 'Address']
        st.dataframe(customers_df, use_container_width=True, hide_index=True)
    else:
        st.info("No customers found. Add customers while creating invoices!")

with tab4:
    st.subheader("📈 HSN Code Analytics")
    
    # Month selector
    col1, col2 = st.columns([1, 3])
    with col1:
        selected_month = st.selectbox(
            "Select Month",
            options=list(range(1, 13)),
            format_func=lambda x: datetime(2024, x, 1).strftime('%B'),
            index=datetime.now().month - 1
        )
    with col2:
        selected_year = st.number_input("Year", min_value=2020, max_value=2030, value=datetime.now().year)
    
    try:
        # Fetch all invoices for the selected month
        start_date = f"{selected_year}-{selected_month:02d}-01"
        if selected_month == 12:
            end_date = f"{selected_year + 1}-01-01"
        else:
            end_date = f"{selected_year}-{selected_month + 1:02d}-01"
        
        result = supabase.table('invoices').select('*').gte('invoice_date', start_date).lt('invoice_date', end_date).execute()
        
        if result.data and len(result.data) > 0:
            # Process invoices to extract HSN data
            hsn_data = {}
            total_invoices = len(result.data)
            total_value = 0
            
            for invoice in result.data:
                items = invoice.get('items', [])
                for item in items:
                    hsn_code = item.get('hsn_code', 'Unknown')
                    product_name = item.get('product_name', 'Unknown')
                    quantity = item.get('quantity', 0)
                    taxable_value = item.get('taxable_value', 0)
                    gst_rate = item.get('gst_rate', 0)
                    tax_amount = item.get('tax_amount', 0)
                    total = item.get('total', 0)
                    
                    if hsn_code not in hsn_data:
                        hsn_data[hsn_code] = {
                            'hsn_code': hsn_code,
                            'product_names': set(),
                            'total_quantity': 0,
                            'total_taxable_value': 0,
                            'total_tax': 0,
                            'total_value': 0,
                            'invoice_count': 0,
                            'avg_gst_rate': []
                        }
                    
                    hsn_data[hsn_code]['product_names'].add(product_name)
                    hsn_data[hsn_code]['total_quantity'] += quantity
                    hsn_data[hsn_code]['total_taxable_value'] += taxable_value
                    hsn_data[hsn_code]['total_tax'] += tax_amount
                    hsn_data[hsn_code]['total_value'] += total
                    hsn_data[hsn_code]['avg_gst_rate'].append(gst_rate)
                    
                total_value += invoice.get('grand_total', 0)
            
            # Convert to DataFrame
            hsn_list = []
            for hsn, data in hsn_data.items():
                hsn_list.append({
                    'HSN/SAC Code': hsn,
                    'Products': ', '.join(list(data['product_names'])[:3]) + ('...' if len(data['product_names']) > 3 else ''),
                    'Total Qty': data['total_quantity'],
                    'Taxable Value': data['total_taxable_value'],
                    'Total Tax': data['total_tax'],
                    'Total Value': data['total_value'],
                    'Avg GST %': sum(data['avg_gst_rate']) / len(data['avg_gst_rate']) if data['avg_gst_rate'] else 0
                })
            
            hsn_df = pd.DataFrame(hsn_list)
            hsn_df = hsn_df.sort_values('Total Value', ascending=False)
            
            # Display summary metrics
            st.markdown(f"### Summary for {datetime(selected_year, selected_month, 1).strftime('%B %Y')}")
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Invoices", total_invoices)
            with col2:
                st.metric("Unique HSN Codes", len(hsn_data))
            with col3:
                st.metric("Total Taxable Value", f"₹{sum(d['total_taxable_value'] for d in hsn_data.values()):,.2f}")
            with col4:
                st.metric("Total Invoice Value", f"₹{total_value:,.2f}")
            
            st.markdown("---")
            
            # Display HSN-wise breakdown
            st.markdown("### HSN/SAC Code Breakdown")
            
            # Format currency columns
            hsn_df_display = hsn_df.copy()
            hsn_df_display['Taxable Value'] = hsn_df_display['Taxable Value'].apply(lambda x: f"₹{x:,.2f}")
            hsn_df_display['Total Tax'] = hsn_df_display['Total Tax'].apply(lambda x: f"₹{x:,.2f}")
            hsn_df_display['Total Value'] = hsn_df_display['Total Value'].apply(lambda x: f"₹{x:,.2f}")
            hsn_df_display['Avg GST %'] = hsn_df_display['Avg GST %'].apply(lambda x: f"{x:.1f}%")
            
            st.dataframe(hsn_df_display, use_container_width=True, hide_index=True)
            
            # Download button
            csv = hsn_df.to_csv(index=False)
            st.download_button(
                label="📥 Download HSN Report (CSV)",
                data=csv,
                file_name=f"HSN_Report_{selected_year}_{selected_month:02d}.csv",
                mime="text/csv"
            )
            
            # Visualization
            st.markdown("---")
            st.markdown("### Top 10 HSN Codes by Value")
            
            top_10 = hsn_df.head(10).copy()
            top_10['Total Value'] = top_10['Total Value'].apply(lambda x: float(x.replace('₹', '').replace(',', '')) if isinstance(x, str) else x)
            
            import plotly.express as px
            fig = px.bar(
                top_10,
                x='HSN/SAC Code',
                y='Total Value',
                title=f'Top 10 HSN Codes - {datetime(selected_year, selected_month, 1).strftime("%B %Y")}',
                labels={'Total Value': 'Total Value (₹)'},
                text='Total Value'
            )
            fig.update_traces(texttemplate='₹%{text:,.0f}', textposition='outside')
            fig.update_layout(showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
            
        else:
            st.info(f"No invoices found for {datetime(selected_year, selected_month, 1).strftime('%B %Y')}")
    
    except Exception as e:
        st.error(f"Error loading HSN analytics: {e}")
        st.info("Make sure you have generated some invoices first!")

st.markdown("---")
st.caption("💡 Tip: Make sure to set up your Supabase tables before using this app. See setup instructions in the documentation.")
