"""
Needle Point — Full Business ERP
Single-file Streamlit app. Run: streamlit run needle_invoice.py
"""

import streamlit as st
import json
import pandas as pd
from datetime import date, datetime, timedelta
from io import BytesIO
from supabase import create_client, Client
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer, HRFlowable
from reportlab.lib.enums import TA_RIGHT, TA_LEFT

COMPANY = {
    "name":    "Needle Point",
    "address": "C-157, 3rd Floor\nMayapuri Industrial Area, Phase 2\nNew Delhi Delhi 110064\nIndia",
    "gstin":   "07AAXFN6403D1Z5",
    "state":   "Delhi",
    "phone":   "9988998727",
    "email":   "rushailharjai10@gmail.com",
    "bank":    "ICICI Bank Ltd, WH-9 Mayapuri Phase 1, 110064",
    "account": "181805001556",
    "ifsc":    "ICIC0001818",
    "upi":     "needlepoint.ibz@icici",
}

FISCAL_YEAR   = "26-27"
TAX_START_NUM = 1001
PRO_START_NUM = 1

STATES = [
    "Andaman and Nicobar Islands","Andhra Pradesh","Arunachal Pradesh","Assam",
    "Bihar","Chandigarh","Chhattisgarh","Dadra and Nagar Haveli","Daman and Diu",
    "Delhi","Goa","Gujarat","Haryana","Himachal Pradesh","Jammu and Kashmir",
    "Jharkhand","Karnataka","Kerala","Ladakh","Lakshadweep","Madhya Pradesh",
    "Maharashtra","Manipur","Meghalaya","Mizoram","Nagaland","Odisha","Puducherry",
    "Punjab","Rajasthan","Sikkim","Tamil Nadu","Telangana","Tripura",
    "Uttar Pradesh","Uttarakhand","West Bengal",
]
GST_RATES   = [0,5,12,18,28]
PAY_MODES   = ["NEFT","RTGS","UPI","Cheque","Cash","IMPS","Other"]
EXPENSE_CATS= ["Raw Materials","Fabric","Shipping","Marketing","Rent","Utilities",
               "Salaries","Equipment","Printing","Packaging","Software","Travel","Miscellaneous"]
ACC_GROUPS  = ["asset","liability","equity","income","expense"]
ACC_SUBGROUPS={"asset":["Current Assets","Fixed Assets","Investments"],
               "liability":["Current Liabilities","Long-term Liabilities"],
               "equity":["Equity"],"income":["Direct Income","Indirect Income"],
               "expense":["Direct Expenses","Indirect Expenses"]}

_BLACK=colors.HexColor("#0f0f0f"); _LGREY=colors.HexColor("#f5f5f5")
_MGREY=colors.HexColor("#cccccc"); _DGREY=colors.HexColor("#555555")
_WHITE=colors.white; _W,_H=A4

st.set_page_config(page_title="Needle Point ERP",page_icon="🪡",layout="wide",initial_sidebar_state="expanded")
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&display=swap');
html,body,[class*="css"]{font-family:'DM Sans',sans-serif}
[data-testid="stSidebar"]{background:#0f0f0f}
[data-testid="stSidebar"] *{color:#e8e0d4!important}
.metric-box{background:#0f0f0f;color:#e8e0d4;border-radius:8px;padding:1rem 1.2rem;text-align:center;margin-bottom:8px}
.metric-box .val{font-size:1.5rem;font-weight:700;color:#c8f064}
.metric-box .lbl{font-size:.72rem;opacity:.6;text-transform:uppercase;letter-spacing:.06em;margin-top:4px}
.bp{background:#d1fae5;color:#065f46;padding:2px 8px;border-radius:99px;font-size:.75rem;font-weight:600}
.bpa{background:#fef3c7;color:#92400e;padding:2px 8px;border-radius:99px;font-size:.75rem;font-weight:600}
.bu{background:#fee2e2;color:#991b1b;padding:2px 8px;border-radius:99px;font-size:.75rem;font-weight:600}
.bpf{background:#ede9fe;color:#4c1d95;padding:2px 8px;border-radius:99px;font-size:.75rem;font-weight:600}
.bd{background:#f3f4f6;color:#374151;padding:2px 8px;border-radius:99px;font-size:.75rem;font-weight:600}
.bs{background:#dbeafe;color:#1e40af;padding:2px 8px;border-radius:99px;font-size:.75rem;font-weight:600}
.intra{background:#dbeafe;color:#1e40af;padding:1px 7px;border-radius:4px;font-size:.72rem;font-weight:600;display:inline-block}
.inter{background:#fef3c7;color:#92400e;padding:1px 7px;border-radius:4px;font-size:.72rem;font-weight:600;display:inline-block}
</style>""",unsafe_allow_html=True)

@st.cache_resource
def _sb():
    return create_client(st.secrets["SUPABASE_URL"],st.secrets["SUPABASE_KEY"])
def sb(): return _sb()

def load_businesses(): return sb().table("businesses").select("*").order("name").execute().data or []
def load_parties(bid=None):
    q=sb().table("parties").select("*").order("name")
    if bid: q=q.eq("business_id",bid)
    return q.execute().data or []
def load_invoices(bid=None,itype=None,istatus=None):
    q=sb().table("invoices").select("*").order("created_at",desc=True)
    if bid: q=q.eq("business_id",bid)
    if itype: q=q.eq("type",itype)
    if istatus: q=q.eq("status",istatus)
    return q.execute().data or []
def load_inv_items(iid): return sb().table("invoice_items").select("*").eq("invoice_id",iid).execute().data or []
def load_payments(bid=None,iid=None,pid=None):
    q=sb().table("payments").select("*").order("payment_date",desc=True)
    if bid: q=q.eq("business_id",bid)
    if iid: q=q.eq("invoice_id",iid)
    if pid: q=q.eq("party_id",pid)
    return q.execute().data or []
def load_expenses(bid=None):
    q=sb().table("expenses").select("*").order("expense_date",desc=True)
    if bid: q=q.eq("business_id",bid)
    return q.execute().data or []
def load_items(bid=None):
    q=sb().table("items").select("*").order("name")
    if bid: q=q.eq("business_id",bid)
    return q.execute().data or []
def load_accounts(bid=None):
    q=sb().table("accounts").select("*").order("code")
    if bid: q=q.eq("business_id",bid)
    return q.execute().data or []
def load_journal_entries(bid=None):
    q=sb().table("journal_entries").select("*").order("entry_date",desc=True)
    if bid: q=q.eq("business_id",bid)
    return q.execute().data or []
def load_journal_lines(jid): return sb().table("journal_lines").select("*").eq("journal_id",jid).execute().data or []
def load_all_journal_lines(bid=None):
    entries=load_journal_entries(bid); eids=[e["id"] for e in entries]
    if not eids: return []
    return sb().table("journal_lines").select("*").in_("journal_id",eids).execute().data or []
def load_credit_notes(bid=None):
    q=sb().table("credit_notes").select("*").order("created_at",desc=True)
    if bid: q=q.eq("business_id",bid)
    return q.execute().data or []
def load_bank_accounts(bid=None):
    q=sb().table("bank_accounts").select("*").order("name")
    if bid: q=q.eq("business_id",bid)
    return q.execute().data or []
def load_bank_txns(bank_id): return sb().table("bank_transactions").select("*").eq("bank_account_id",bank_id).order("txn_date",desc=True).execute().data or []

def fmt(n): return f"₹{float(n or 0):,.2f}"
def fmtd(d): return str(d)[:10] if d else "—"
def gst_type(bs,ps):
    if not bs or not ps: return "igst"
    norm=lambda s:s.lower().replace(" ","").replace("(","").replace(")","")
    return "intrastate" if norm(bs)==norm(ps) else "igst"
def calc_gst(taxable,pct,is_intra):
    t=taxable*pct/100
    return (t/2,t/2,0.0) if is_intra else (0.0,0.0,t)
def next_num(itype="tax"):
    prefix=f"PRO/{FISCAL_YEAR}/" if itype=="proforma" else f"{FISCAL_YEAR}/"
    start=PRO_START_NUM if itype=="proforma" else TAX_START_NUM
    res=sb().table("invoices").select("invoice_number").like("invoice_number",f"{prefix}%").order("invoice_number",desc=True).limit(1).execute()
    if res.data:
        try: return f"{prefix}{int(res.data[0]['invoice_number'].split('/')[-1])+1}"
        except: pass
    return f"{prefix}{start}"
def refresh_status(iid):
    inv=sb().table("invoices").select("total").eq("id",iid).single().execute().data
    if not inv: return
    paid=sum(float(p["amount"]) for p in load_payments(iid=iid))
    total=float(inv["total"])
    s="paid" if paid>=total-0.01 else("partially_paid" if paid>0 else "unpaid")
    sb().table("invoices").update({"status":s}).eq("id",iid).execute()
def pname(pid,parties):
    p=next((x for x in parties if x["id"]==pid),None)
    return (p.get("company") or p.get("name") or "—") if p else "—"
def badge(status):
    m={"paid":"bp","partial":"bpa","partially_paid":"bpa","unpaid":"bu","proforma":"bpf","draft":"bd","sent":"bs","cancelled":"bd","overdue":"bu","active":"bp"}
    cls=m.get(status,"bd")
    return f'<span class="{cls}">{status.replace("_"," ").upper()}</span>'

def num_words(n):
    ones=["","One","Two","Three","Four","Five","Six","Seven","Eight","Nine","Ten","Eleven","Twelve","Thirteen","Fourteen","Fifteen","Sixteen","Seventeen","Eighteen","Nineteen"]
    tw=["","","Twenty","Thirty","Forty","Fifty","Sixty","Seventy","Eighty","Ninety"]
    def c(x):
        if x==0: return ""
        if x<20: return ones[x]
        if x<100: return tw[x//10]+(" "+ones[x%10] if x%10 else "")
        return ones[x//100]+" Hundred"+(" "+c(x%100) if x%100 else "")
    r=int(n); p=round((n-r)*100); parts=[]
    for d,l in [(10000000,"Crore"),(100000,"Lakh"),(1000,"Thousand"),(1,"")]:
        v=r//d; r%=d
        if v: parts.append(c(v)+(" "+l if l else ""))
    word=" ".join(parts) or "Zero"
    res=f"Indian Rupee {word}"
    if p: res+=f" and {c(p)} Paise"
    return res+" Only"

def gen_pdf(invoice,line_items,client,is_cn=False):
    buf=BytesIO()
    doc=SimpleDocTemplate(buf,pagesize=A4,leftMargin=15*mm,rightMargin=15*mm,topMargin=12*mm,bottomMargin=15*mm)
    def P(t,fn="Helvetica",fs=8.5,leading=13,clr=_BLACK,align=TA_LEFT):
        return Paragraph(t,ParagraphStyle("_",fontName=fn,fontSize=fs,leading=leading,textColor=clr,alignment=align))
    def Pb(t,**k): return P(t,fn="Helvetica-Bold",**k)
    def Pr(t,**k): return P(t,align=TA_RIGHT,**k)
    def Pbr(t,**k): return P(t,fn="Helvetica-Bold",align=TA_RIGHT,**k)
    def Ps(t): return P(t,fs=7.5,leading=11,clr=_DGREY)
    title="CREDIT NOTE" if is_cn else("PROFORMA INVOICE" if invoice.get("status")=="proforma" else "TAX INVOICE")
    inv_no=invoice.get("invoice_number") or invoice.get("cn_number","")
    story=[]
    story.append(Table([[Pb(f"<b>{COMPANY['name']}</b>",fs=14,leading=18),P(title,fn="Helvetica-Bold",fs=22,leading=28,align=TA_RIGHT)]],colWidths=[_W*.5-20*mm,_W*.5-10*mm]))
    story.append(Spacer(1,3*mm))
    addr=COMPANY["address"].replace("\n","<br/>")
    story.append(Ps(f"{addr}<br/>GSTIN {COMPANY['gstin']}<br/>{COMPANY['phone']}<br/>{COMPANY['email']}"))
    story.append(Spacer(1,4*mm)); story.append(HRFlowable(width="100%",thickness=1,color=_BLACK)); story.append(Spacer(1,3*mm))
    story.append(Table([[Pb("#"),P(f": {inv_no}"),Pb("Place Of Supply"),P(f": {client.get('state','')}")],
                        [Pb("Date"),P(f": {fmtd(invoice.get('issue_date') or invoice.get('cn_date',''))}"),Pb("Due"),P(f": {fmtd(invoice.get('due_date',''))}")],
                        ],colWidths=[28*mm,65*mm,42*mm,50*mm],
                   style=TableStyle([("FONTSIZE",(0,0),(-1,-1),8.5),("BOTTOMPADDING",(0,0),(-1,-1),2),("TOPPADDING",(0,0),(-1,-1),2)])))
    story.append(Spacer(1,3*mm)); story.append(HRFlowable(width="100%",thickness=0.5,color=_MGREY)); story.append(Spacer(1,3*mm))
    def ccol(lbl):
        rows=[Pb(f"<b>{lbl}</b>")]
        if client.get("company"): rows.append(Pb(f"<b>{client['company']}</b>"))
        if client.get("name"): rows.append(P(client["name"]))
        ap=", ".join(filter(None,[client.get("address",""),client.get("city",""),client.get("pincode",""),client.get("state",""),"India"]))
        rows.append(P(ap))
        if client.get("gstin"): rows.append(P(f"GSTIN {client['gstin']}"))
        if client.get("phone"): rows.append(P(client["phone"]))
        return rows
    cw=(_W-30*mm)/2
    story.append(Table([[ccol("Bill To"),ccol("Ship To")]],colWidths=[cw,cw],
        style=TableStyle([("VALIGN",(0,0),(-1,-1),"TOP"),("BOX",(0,0),(0,0),0.5,_MGREY),("BOX",(1,0),(1,0),0.5,_MGREY),("BACKGROUND",(0,0),(-1,-1),_LGREY),("PADDING",(0,0),(-1,-1),6)])))
    story.append(Spacer(1,4*mm))
    is_intra=invoice.get("is_interstate")==False
    items=line_items if isinstance(line_items,list) else json.loads(line_items or "[]")
    cws=[8*mm,60*mm,22*mm,15*mm,18*mm,14*mm,18*mm,22*mm]
    rows=[[Pb("#"),Pb("Item &amp; Description"),Pb("HSN/SAC"),Pb("Qty"),Pb("Rate"),Pb("GST%"),Pb("GST Amt"),Pb("Amount")]]
    sub_v=cgst_v=sgst_v=igst_v=0
    for idx,it in enumerate(items,1):
        qty=float(it.get("quantity") or it.get("qty",0)); rate=float(it.get("unit_price") or it.get("rate",0))
        disc=float(it.get("discount_percent",0)); gp=float(it.get("tax_percent") or it.get("gst_pct",5))
        base=qty*rate; disc_a=base*disc/100; taxable=base-disc_a
        cgst,sgst,igst=calc_gst(taxable,gp,is_intra)
        sub_v+=taxable; cgst_v+=cgst; sgst_v+=sgst; igst_v+=igst; gst_a=cgst+sgst+igst
        rows.append([P(str(idx)),P(str(it.get("description",""))),P(str(it.get("hsn_code",""))),
                     P(f"{qty:.2f}"),P(f"{rate:,.2f}"),P(f"{gp:.0f}%"),P(f"{gst_a:,.2f}"),P(f"{taxable:,.2f}")])
    story.append(Table(rows,colWidths=cws,repeatRows=1,
        style=TableStyle([("BACKGROUND",(0,0),(-1,0),_BLACK),("TEXTCOLOR",(0,0),(-1,0),_WHITE),
                          ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),("FONTSIZE",(0,0),(-1,-1),8),
                          ("ROWBACKGROUNDS",(0,1),(-1,-1),[_WHITE,_LGREY]),("GRID",(0,0),(-1,-1),0.4,_MGREY),
                          ("ALIGN",(3,0),(-1,-1),"RIGHT"),("TOPPADDING",(0,0),(-1,-1),4),("BOTTOMPADDING",(0,0),(-1,-1),4)])))
    story.append(Spacer(1,4*mm))
    tv=cgst_v+sgst_v+igst_v; total_v=sub_v+tv; sw=_W-30*mm-70*mm-35*mm
    gst_rows=([["",Pr("CGST"),Pr(f"Rs.{cgst_v:,.2f}")],["",Pr("SGST"),Pr(f"Rs.{sgst_v:,.2f}")]] if is_intra
              else [["",Pr("IGST"),Pr(f"Rs.{igst_v:,.2f}")]])
    tr=[["",Pr("Sub Total"),Pr(f"Rs.{sub_v:,.2f}")]]+gst_rows+[["",Pbr("<b>Total</b>"),Pbr(f"<b>Rs.{total_v:,.2f}</b>")],["",Pbr("<b>Balance Due</b>"),Pbr(f"<b>Rs.{total_v:,.2f}</b>")]]
    story.append(Table(tr,colWidths=[sw,70*mm,35*mm],
        style=TableStyle([("ALIGN",(1,0),(-1,-1),"RIGHT"),("LINEABOVE",(1,-2),(-1,-2),0.5,_MGREY),
                          ("LINEABOVE",(1,-1),(-1,-1),1,_BLACK),("LINEBELOW",(1,-1),(-1,-1),1,_BLACK),
                          ("TOPPADDING",(0,0),(-1,-1),2),("BOTTOMPADDING",(0,0),(-1,-1),2),("FONTSIZE",(0,0),(-1,-1),8.5)])))
    story.append(Spacer(1,3*mm)); story.append(Pb("<b>Total In Words</b>")); story.append(Ps(f"<i>{num_words(total_v)}</i>"))
    story.append(Spacer(1,4*mm)); story.append(HRFlowable(width="100%",thickness=0.5,color=_MGREY)); story.append(Spacer(1,3*mm))
    bh=(f"<b>Bank Details:</b><br/>Ac no. - {COMPANY['account']}<br/>IFSC - {COMPANY['ifsc']}<br/>{COMPANY['bank']}<br/>UPI: {COMPANY['upi']}")
    nh="<b>Notes</b><br/>Computer generated. No signature required."
    story.append(Table([[Ps(bh),Ps(nh)]],colWidths=[(_W-30*mm)*.55,(_W-30*mm)*.45],style=TableStyle([("VALIGN",(0,0),(-1,-1),"TOP")])))
    doc.build(story); return buf.getvalue()

DEFAULT_ACCOUNTS=[
    ("1001","Cash","asset","Current Assets"),("1002","Bank Account","asset","Current Assets"),
    ("1003","Accounts Receivable","asset","Current Assets"),("1004","Inventory","asset","Current Assets"),
    ("1101","Machinery & Equipment","asset","Fixed Assets"),("1102","Furniture & Fixtures","asset","Fixed Assets"),
    ("2001","Accounts Payable","liability","Current Liabilities"),
    ("2002","GST Payable CGST","liability","Current Liabilities"),
    ("2003","GST Payable SGST","liability","Current Liabilities"),
    ("2004","GST Payable IGST","liability","Current Liabilities"),
    ("2005","Salary Payable","liability","Current Liabilities"),
    ("3001","Owner Capital","equity","Equity"),("3002","Retained Earnings","equity","Equity"),
    ("4001","Sales Revenue","income","Direct Income"),("4002","Service Income","income","Direct Income"),
    ("4003","Other Income","income","Indirect Income"),
    ("5001","Cost of Goods Sold","expense","Direct Expenses"),
    ("5002","Raw Material Cost","expense","Direct Expenses"),
    ("5003","Salaries & Wages","expense","Indirect Expenses"),
    ("5004","Rent","expense","Indirect Expenses"),("5005","Utilities","expense","Indirect Expenses"),
    ("5006","Marketing","expense","Indirect Expenses"),("5007","Shipping","expense","Indirect Expenses"),
    ("5008","Printing & Packaging","expense","Indirect Expenses"),
    ("5009","Bank Charges","expense","Indirect Expenses"),
    ("5010","Miscellaneous","expense","Indirect Expenses"),
]
def seed_accounts(bid):
    existing={a["code"] for a in load_accounts(bid)}
    rows=[{"business_id":bid,"code":c,"name":n,"group":g,"sub_group":s} for c,n,g,s in DEFAULT_ACCOUNTS if c not in existing]
    if rows: sb().table("accounts").insert(rows).execute()

# ── PAGES ──────────────────────────────────────────────────────────────────────

def page_dashboard():
    st.markdown("## Dashboard")
    try: businesses=load_businesses()
    except Exception as e: st.error(f"Supabase connection failed: {e}"); st.info("Set SUPABASE_URL and SUPABASE_KEY in secrets."); return
    biz_opts={"All":None}|{b["name"]:b["id"] for b in businesses}
    bid=biz_opts[st.selectbox("Business",list(biz_opts.keys()),key="db_biz")]
    invoices=load_invoices(bid); expenses=load_expenses(bid); payments=load_payments(bid); parties=load_parties(bid)
    si=[i for i in invoices if i["type"]=="sale" and i["status"] not in ("cancelled","proforma","draft")]
    rev=sum(float(i.get("subtotal",0)) for i in si)
    coll=sum(float(p["amount"]) for p in payments)
    out=sum(float(i["total"]) for i in si if i["status"] in ("sent","unpaid","partially_paid","overdue"))
    exp=sum(float(e["amount"]) for e in expenses)
    c1,c2,c3,c4,c5=st.columns(5)
    for col,val,lbl in [(c1,fmt(rev),"Revenue"),(c2,fmt(coll),"Collected"),(c3,fmt(out),"Outstanding"),(c4,fmt(exp),"Expenses"),(c5,fmt(rev-exp),"Net Profit")]:
        col.markdown(f'<div class="metric-box"><div class="val">{val}</div><div class="lbl">{lbl}</div></div>',unsafe_allow_html=True)
    st.markdown("<br>",unsafe_allow_html=True)
    st.markdown("#### Monthly Revenue")
    md={}
    for i in si:
        if i.get("issue_date"): ym=str(i["issue_date"])[:7]; md[ym]=md.get(ym,0)+float(i.get("subtotal",0))
    if md:
        df=pd.DataFrame(list(md.items()),columns=["Month","Revenue"]).sort_values("Month").tail(6)
        st.bar_chart(df.set_index("Month"))
    ca,cb=st.columns(2)
    with ca:
        st.markdown("#### Recent Invoices")
        for inv in invoices[:8]:
            pn=pname(inv.get("party_id"),parties)
            st.markdown(f'<div style="display:flex;justify-content:space-between;align-items:center;padding:8px 12px;border:1px solid #e5e7eb;border-radius:6px;margin-bottom:4px;background:#fff"><div><b style="font-size:.88rem">{inv["invoice_number"]}</b> <span style="color:#888;font-size:.8rem;margin-left:8px">{pn}</span></div><div style="display:flex;gap:8px;align-items:center"><b>{fmt(inv["total"])}</b>{badge(inv.get("status","draft"))}</div></div>',unsafe_allow_html=True)
    with cb:
        st.markdown("#### Top Clients")
        cr={}
        for i in si:
            pn=pname(i.get("party_id"),parties); cr[pn]=cr.get(pn,0)+float(i.get("subtotal",0))
        top5=sorted(cr.items(),key=lambda x:-x[1])[:5]
        if top5: st.dataframe(pd.DataFrame(top5,columns=["Client","Revenue"]).assign(Revenue=lambda df:df.Revenue.apply(fmt)),use_container_width=True,hide_index=True)

def page_invoices(is_pro=False):
    ikey="proforma" if is_pro else "tax"
    st.markdown(f"## {'Proforma' if is_pro else 'Tax'} Invoices")
    businesses=load_businesses()
    if not businesses: st.warning("Add a business first."); return
    biz_opts={b["name"]:b["id"] for b in businesses}
    bsn=st.selectbox("Business",list(biz_opts.keys()),key=f"inv_biz_{ikey}")
    bid=biz_opts[bsn]; bobj=next((b for b in businesses if b["id"]==bid),{})
    tab1,tab2=st.tabs(["📋 List","➕ New"])
    with tab1:
        invoices=load_invoices(bid); parties=load_parties(bid)
        invoices=[i for i in invoices if (i["status"]=="proforma")==is_pro]
        search=st.text_input("🔍 Search",key=f"isrch_{ikey}")
        if search:
            q=search.lower()
            invoices=[i for i in invoices if q in i["invoice_number"].lower() or q in pname(i.get("party_id"),parties).lower()]
        payments_all=load_payments(bid); pbi={}
        for p in payments_all: pbi.setdefault(p["invoice_id"],[]).append(p)
        for inv in invoices:
            pays=pbi.get(inv["id"],[]); paid=sum(float(p["amount"]) for p in pays)
            bal=float(inv["total"])-paid; pn=pname(inv.get("party_id"),parties)
            is_intra=inv.get("is_interstate")==False
            gc=f'<span class="intra">C+S</span>' if is_intra else '<span class="inter">IGST</span>'
            with st.expander(f"📄 {inv['invoice_number']} — {pn} — {fmt(inv['total'])} {badge(inv['status'])}",expanded=False):
                c1,c2,c3=st.columns(3)
                c1.markdown(f"**Date:** {fmtd(inv.get('issue_date'))}  \n**Due:** {fmtd(inv.get('due_date'))}")
                c2.markdown(f"**Subtotal:** {fmt(inv.get('subtotal',0))}  \n**GST:** {fmt(inv.get('tax_amount',0))}")
                c3.markdown(f"**Paid:** {fmt(paid)}  \n**Balance:** {fmt(bal)}")
                st.markdown(f"GST: {gc}",unsafe_allow_html=True)
                b1,b2,b3,b4=st.columns(4)
                if b1.button("📥 PDF",key=f"pdf_{inv['id']}"):
                    items=load_inv_items(inv["id"]); client=next((p for p in parties if p["id"]==inv.get("party_id")),{})
                    pdf=gen_pdf(inv,items,client)
                    st.download_button("⬇ Download",data=pdf,file_name=f"{inv['invoice_number'].replace('/','-')}.pdf",mime="application/pdf",key=f"dl_{inv['id']}")
                if not is_pro and inv["status"] not in ("paid","cancelled") and bal>0:
                    if b2.button("💰 Pay",key=f"pay_{inv['id']}"):
                        st.session_state[f"pm_{inv['id']}"]=True
                if is_pro and b2.button("→ Tax Invoice",key=f"cv_{inv['id']}"):
                    nn=next_num("tax")
                    sb().table("invoices").update({"status":"sent","invoice_number":nn}).eq("id",inv["id"]).execute()
                    st.success(f"Converted to {nn}"); st.rerun()
                if b4.button("🗑 Del",key=f"dl2_{inv['id']}"):
                    sb().table("invoices").delete().eq("id",inv["id"]).execute(); st.rerun()
                if st.session_state.get(f"pm_{inv['id']}"):
                    st.markdown("---"); st.markdown("**Record Payment**")
                    pa,pb=st.columns(2)
                    amt=pa.number_input("Amount",min_value=0.01,max_value=float(bal)+0.01,value=float(round(bal,2)),step=100.0,key=f"pamt_{inv['id']}")
                    pd_=pa.date_input("Date",value=date.today(),key=f"pdt_{inv['id']}")
                    md=pb.selectbox("Mode",PAY_MODES,key=f"pmd_{inv['id']}"); ref=pb.text_input("Ref",key=f"prf_{inv['id']}")
                    if st.button("✅ Record",key=f"prec_{inv['id']}"):
                        sb().table("payments").insert({"invoice_id":inv["id"],"business_id":bid,"party_id":inv.get("party_id"),"amount":round(float(amt),2),"payment_date":str(pd_),"method":md,"reference":ref or None}).execute()
                        refresh_status(inv["id"]); del st.session_state[f"pm_{inv['id']}"]; st.success(f"Recorded {fmt(amt)}"); st.rerun()
    with tab2:
        parties=load_parties(bid); catalog=load_items(bid)
        if not parties: st.warning("Add parties first."); return
        popts={f"{p.get('company') or p['name']} ({p.get('phone','')})":p["id"] for p in parties}
        c1,c2=st.columns(2)
        with c1:
            sp=st.selectbox("Party *",list(popts.keys()),key=f"np_{ikey}"); pid=popts[sp]
            pobj=next((p for p in parties if p["id"]==pid),{})
            an=next_num(ikey); manual=st.checkbox("Manual invoice number",key=f"nm_{ikey}")
            inv_num=st.text_input("Invoice #",value=an,key=f"nn_{ikey}") if manual else an
            if not manual: st.markdown(f"**Invoice #:** `{an}`")
            idate=st.date_input("Invoice Date",value=date.today(),key=f"nd_{ikey}")
        with c2:
            ddate=st.date_input("Due Date",value=date.today(),key=f"ndd_{ikey}")
            dsi=STATES.index(pobj.get("state","Delhi")) if pobj.get("state") in STATES else 9
            pos=st.selectbox("Place of Supply",STATES,index=dsi,key=f"np2_{ikey}")
            notes=st.text_area("Notes",height=60,key=f"nnotes_{ikey}")
            idisc=st.number_input("Invoice Discount %",min_value=0.0,max_value=100.0,value=0.0,step=0.5,key=f"ndisc_{ikey}")
        is_intra=gst_type(bobj.get("state",COMPANY["state"]),pobj.get("state",""))=="intrastate"
        if pid: st.markdown(f'<span class="{"intra" if is_intra else "inter"}">{"CGST+SGST Intra-state" if is_intra else "IGST Inter-state"}</span>',unsafe_allow_html=True)
        st.markdown("---"); st.markdown("#### Line Items")
        sk=f"li_{ikey}_{bid}"
        if sk not in st.session_state: st.session_state[sk]=[{"description":"","hsn_code":"","quantity":1.0,"unit_price":0.0,"discount_percent":0,"tax_percent":5}]
        if catalog:
            cpopts={f"{it['name']} — {fmt(it.get('sale_price',0))}":it for it in catalog}
            pk=st.selectbox("📦 Pick from catalog",["—"]+list(cpopts.keys()),key=f"pk_{ikey}")
            if pk!="—":
                it=cpopts[pk]
                st.session_state[sk].append({"description":it["name"],"hsn_code":it.get("hsn_code",""),"quantity":1.0,"unit_price":float(it.get("sale_price",0)),"discount_percent":0,"tax_percent":float(it.get("tax_percent",5))})
                st.rerun()
        h1,h2,h3,h4,h5,h6,h7=st.columns([3,2,1.2,1.5,1,1,0.5])
        for c,l in zip([h1,h2,h3,h4,h5,h6,h7],["Description","HSN","Qty","Rate","Disc%","GST%",""]):
            c.markdown(f"<small style='color:#888'>{l}</small>",unsafe_allow_html=True)
        rm=[]
        for i,row in enumerate(st.session_state[sk]):
            r1,r2,r3,r4,r5,r6,r7=st.columns([3,2,1.2,1.5,1,1,0.5])
            row["description"]=r1.text_input("d",value=row["description"],key=f"d_{ikey}_{i}",label_visibility="collapsed",placeholder="Item name")
            row["hsn_code"]=r2.text_input("h",value=row["hsn_code"],key=f"h_{ikey}_{i}",label_visibility="collapsed",placeholder="HSN")
            row["quantity"]=r3.number_input("q",value=float(row["quantity"]),min_value=0.0,step=1.0,key=f"q_{ikey}_{i}",label_visibility="collapsed")
            row["unit_price"]=r4.number_input("r",value=float(row["unit_price"]),min_value=0.0,step=10.0,key=f"r_{ikey}_{i}",label_visibility="collapsed")
            row["discount_percent"]=r5.number_input("di",value=float(row.get("discount_percent",0)),min_value=0.0,max_value=100.0,step=1.0,key=f"di_{ikey}_{i}",label_visibility="collapsed")
            gi=GST_RATES.index(int(row["tax_percent"])) if int(row["tax_percent"]) in GST_RATES else 1
            row["tax_percent"]=r6.selectbox("g",GST_RATES,index=gi,key=f"g_{ikey}_{i}",label_visibility="collapsed")
            if i>0 and r7.button("✕",key=f"rm_{ikey}_{i}"): rm.append(i)
        for i in reversed(rm): st.session_state[sk].pop(i); st.rerun()
        if st.button("+ Row",key=f"ar_{ikey}"): st.session_state[sk].append({"description":"","hsn_code":"","quantity":1.0,"unit_price":0.0,"discount_percent":0,"tax_percent":5}); st.rerun()
        sub=cgst=sgst=igst_v=0
        for row in st.session_state[sk]:
            base=float(row["quantity"])*float(row["unit_price"]); da=base*float(row.get("discount_percent",0))/100; tax=base-da
            c,s,ig=calc_gst(tax,float(row["tax_percent"]),is_intra)
            sub+=tax; cgst+=c; sgst+=s; igst_v+=ig
        ttax=cgst+sgst+igst_v; grand=sub+ttax; ida=grand*float(idisc)/100; final=grand-ida
        st.markdown("---")
        _,t2,t3=st.columns([3,1,1])
        t2.markdown(f"Sub: {fmt(sub)}")
        t2.markdown(f"{'CGST: '+fmt(cgst)+'  SGST: '+fmt(sgst) if is_intra else 'IGST: '+fmt(igst_v)}")
        if ida>0: t2.markdown(f"Disc: -{fmt(ida)}")
        t3.markdown(f"### {fmt(final)}")
        b1,b2,_=st.columns([1,1,3])
        save_btn=b1.button("💾 Save",type="primary",key=f"sv_{ikey}")
        prev_btn=b2.button("👁 Preview",key=f"pv_{ikey}")
        if save_btn:
            if not any(r["description"].strip() for r in st.session_state[sk]):
                st.error("Add at least one line item.")
            else:
                try:
                    inv_data={"business_id":bid,"party_id":pid,"invoice_number":inv_num,"type":"sale","status":"proforma" if is_pro else "draft","issue_date":str(idate),"due_date":str(ddate),"place_of_supply":pos,"notes":notes,"discount_percent":float(idisc),"discount_amount":round(ida,2),"subtotal":round(sub,2),"cgst_amount":round(cgst,2),"sgst_amount":round(sgst,2),"igst_amount":round(igst_v,2),"tax_amount":round(ttax,2),"total":round(final,2),"is_interstate":not is_intra}
                    res=sb().table("invoices").insert(inv_data).select().single().execute(); nid=res.data["id"]
                    rows=[]
                    for row in st.session_state[sk]:
                        if not row["description"].strip(): continue
                        base=float(row["quantity"])*float(row["unit_price"]); da=base*float(row.get("discount_percent",0))/100; tax=base-da
                        c,s,ig=calc_gst(tax,float(row["tax_percent"]),is_intra)
                        rows.append({"invoice_id":nid,"description":row["description"],"hsn_code":row.get("hsn_code",""),"quantity":float(row["quantity"]),"unit_price":float(row["unit_price"]),"discount_percent":float(row.get("discount_percent",0)),"taxable_amount":round(tax,2),"tax_percent":float(row["tax_percent"]),"cgst_amount":round(c,2),"sgst_amount":round(s,2),"igst_amount":round(ig,2),"amount":round(tax+c+s+ig,2)})
                    if rows: sb().table("invoice_items").insert(rows).execute()
                    st.success(f"✅ {inv_num} saved!")
                    pdf=gen_pdf(inv_data,rows,pobj)
                    st.download_button("📥 PDF",data=pdf,file_name=f"{inv_num.replace('/','-')}.pdf",mime="application/pdf")
                    st.session_state[sk]=[{"description":"","hsn_code":"","quantity":1.0,"unit_price":0.0,"discount_percent":0,"tax_percent":5}]
                except Exception as ex: st.error(f"Save failed: {ex}")
        if prev_btn:
            inv_d={"invoice_number":inv_num,"status":"proforma" if is_pro else "draft","issue_date":str(idate),"due_date":str(ddate),"is_interstate":not is_intra}
            rows2=[]
            for row in st.session_state[sk]:
                base=float(row["quantity"])*float(row["unit_price"]); da=base*float(row.get("discount_percent",0))/100; tax=base-da
                c,s,ig=calc_gst(tax,float(row["tax_percent"]),is_intra)
                rows2.append({**row,"taxable_amount":tax,"cgst_amount":c,"sgst_amount":s,"igst_amount":ig})
            pdf=gen_pdf(inv_d,rows2,pobj)
            st.download_button("📥 Preview",data=pdf,file_name=f"preview-{inv_num.replace('/','-')}.pdf",mime="application/pdf")

def page_parties():
    st.markdown("## Parties")
    businesses=load_businesses()
    if not businesses: st.warning("Add a business first."); return
    biz_opts={b["name"]:b["id"] for b in businesses}; bid=biz_opts[st.selectbox("Business",list(biz_opts.keys()),key="pt_biz")]
    tab1,tab2=st.tabs(["📋 List","➕ Add/Edit"])
    with tab1:
        parties=load_parties(bid); tf=st.radio("Type",["All","Clients","Vendors"],horizontal=True)
        if tf=="Clients": parties=[p for p in parties if p["type"]=="client"]
        elif tf=="Vendors": parties=[p for p in parties if p["type"]=="vendor"]
        search=st.text_input("🔍 Search",key="pt_srch")
        if search:
            q=search.lower(); parties=[p for p in parties if q in (p.get("name","")+p.get("company","")+p.get("gstin","")).lower()]
        st.markdown(f"<small>{len(parties)} parties</small>",unsafe_allow_html=True)
        for p in parties:
            dn=p.get("company") or p["name"]; sub=" · ".join(filter(None,[p.get("city"),p.get("state"),p.get("phone")]))
            with st.expander(f"**{dn}** ({p['type']}) — {sub}"):
                c1,c2,c3=st.columns([2,2,1])
                c1.markdown(f"**Contact:** {p.get('name','—')}  \n**Phone:** {p.get('phone','—')}  \n**Email:** {p.get('email','—')}")
                c2.markdown(f"**Address:** {p.get('address','—')}  \n**GSTIN:** {p.get('gstin','—')}  \n**State:** {p.get('state','—')}")
                with c3:
                    if st.button("✏ Edit",key=f"ep_{p['id']}"): st.session_state["edit_party"]=p; st.rerun()
                    if st.button("🗑 Del",key=f"dp_{p['id']}"): sb().table("parties").delete().eq("id",p["id"]).execute(); st.rerun()
    with tab2:
        ed=st.session_state.get("edit_party"); df=ed or {}
        if ed:
            st.info(f"Editing: **{ed.get('company') or ed['name']}**")
            if st.button("✕ Cancel"): st.session_state.pop("edit_party"); st.rerun()
        with st.form("pf",clear_on_submit=True):
            fa,fb=st.columns(2)
            with fa:
                nv=st.text_input("Name *",value=df.get("name","")); cv=st.text_input("Company",value=df.get("company",""))
                phv=st.text_input("Phone *",value=df.get("phone","")); ev=st.text_input("Email",value=df.get("email",""))
                tv=st.selectbox("Type",["client","vendor"],index=0 if df.get("type","client")=="client" else 1)
            with fb:
                av=st.text_area("Address",value=df.get("address",""),height=80); city=st.text_input("City",value=df.get("city",""))
                si=STATES.index(df["state"]) if df.get("state") in STATES else 0
                stv=st.selectbox("State",STATES,index=si); pv=st.text_input("Pincode",value=df.get("pincode",""))
                gv=st.text_input("GSTIN",value=df.get("gstin",""))
            if st.form_submit_button("💾 Save",type="primary"):
                if not nv.strip() or not phv.strip(): st.error("Name and phone required.")
                else:
                    data={"name":nv.strip(),"company":cv.strip(),"phone":phv.strip(),"email":ev.strip(),"address":av.strip(),"city":city.strip(),"state":stv,"pincode":pv.strip(),"gstin":gv.strip().upper(),"type":tv,"business_id":bid}
                    try:
                        if ed: sb().table("parties").update(data).eq("id",ed["id"]).execute(); st.success("Updated!"); st.session_state.pop("edit_party",None)
                        else: sb().table("parties").insert(data).execute(); st.success(f"Added: {cv or nv}")
                    except Exception as ex: st.error(str(ex))

def page_items():
    st.markdown("## Item Master")
    businesses=load_businesses()
    if not businesses: st.warning("Add a business first."); return
    biz_opts={b["name"]:b["id"] for b in businesses}; bid=biz_opts[st.selectbox("Business",list(biz_opts.keys()),key="it_biz")]
    tab1,tab2=st.tabs(["📦 Items","➕ Add Item"])
    UNITS=["Pcs","Nos","Kg","Gm","Mtr","Cm","Ltr","Box","Set","Pair","Roll","Sheet","Bag","Other"]
    CATS=["Fabric","Garments","Accessories","Raw Material","Finished Goods","Services","Packaging","Other"]
    with tab1:
        items=load_items(bid); search=st.text_input("🔍 Search",key="it_srch")
        if search:
            q=search.lower(); items=[i for i in items if q in (i["name"]+i.get("hsn_code","")+i.get("category","")).lower()]
        if items:
            df=pd.DataFrame([{"Name":i["name"],"Category":i.get("category","—"),"HSN":i.get("hsn_code","—"),"Unit":i.get("unit","Pcs"),"Sale Price":fmt(i.get("sale_price",0)),"GST%":f"{i.get('tax_percent',0)}%"} for i in items])
            st.dataframe(df,use_container_width=True,hide_index=True)
            for it in items:
                if st.button(f"🗑 Del {it['name']}",key=f"di_{it['id']}"): sb().table("items").delete().eq("id",it["id"]).execute(); st.rerun()
        else: st.info("No items yet.")
    with tab2:
        with st.form("itf",clear_on_submit=True):
            fa,fb=st.columns(2)
            with fa: iname=st.text_input("Name *"); icat=st.selectbox("Category",[""]+CATS); ihsn=st.text_input("HSN/SAC"); iunit=st.selectbox("Unit",UNITS)
            with fb: isale=st.number_input("Sale Price",min_value=0.0,step=1.0); ipurch=st.number_input("Purchase Price",min_value=0.0,step=1.0); igst=st.selectbox("GST%",GST_RATES,index=1); idesc=st.text_area("Description",height=60)
            if st.form_submit_button("💾 Save",type="primary"):
                if not iname.strip(): st.error("Name required.")
                else:
                    try: sb().table("items").insert({"business_id":bid,"name":iname.strip(),"category":icat,"hsn_code":ihsn.strip(),"unit":iunit,"sale_price":float(isale),"purchase_price":float(ipurch),"tax_percent":float(igst),"description":idesc.strip()}).execute(); st.success(f"Added: {iname}")
                    except Exception as ex: st.error(str(ex))

def page_expenses():
    st.markdown("## Expenses")
    businesses=load_businesses()
    if not businesses: st.warning("Add a business first."); return
    biz_opts={b["name"]:b["id"] for b in businesses}; bid=biz_opts[st.selectbox("Business",list(biz_opts.keys()),key="ex_biz")]
    tab1,tab2=st.tabs(["💸 List","➕ Add"])
    with tab1:
        expenses=load_expenses(bid); parties=load_parties(bid); search=st.text_input("🔍",key="ex_srch")
        if search:
            q=search.lower(); expenses=[e for e in expenses if q in (e["category"]+e.get("description","")).lower()]
        total=sum(float(e["amount"]) for e in expenses); st.markdown(f"**Total: {fmt(total)}**")
        if expenses:
            df=pd.DataFrame([{"Date":fmtd(e["expense_date"]),"Category":e["category"],"Desc":e.get("description","—"),"Vendor":pname(e.get("vendor_id"),parties),"Mode":e.get("method","—"),"Ref":e.get("reference","—"),"Amount":fmt(e["amount"])} for e in expenses])
            st.dataframe(df,use_container_width=True,hide_index=True)
        else: st.info("No expenses.")
    with tab2:
        parties=load_parties(bid); vendors=[p for p in parties if p["type"]=="vendor"]
        with st.form("exf",clear_on_submit=True):
            fa,fb=st.columns(2)
            with fa: ecat=st.selectbox("Category *",EXPENSE_CATS); eamt=st.number_input("Amount *",min_value=0.01,step=100.0); edate=st.date_input("Date",value=date.today())
            with fb:
                evnd=st.selectbox("Vendor",["None"]+[p.get("company") or p["name"] for p in vendors])
                emode=st.selectbox("Mode",PAY_MODES); eref=st.text_input("Ref/UTR"); edesc=st.text_input("Description")
            if st.form_submit_button("💾 Save",type="primary"):
                vid=None
                if evnd!="None":
                    v=next((p for p in vendors if (p.get("company") or p["name"])==evnd),None)
                    if v: vid=v["id"]
                try: sb().table("expenses").insert({"business_id":bid,"category":ecat,"amount":round(float(eamt),2),"expense_date":str(edate),"vendor_id":vid,"method":emode,"reference":eref or None,"description":edesc or None}).execute(); st.success(f"Saved {fmt(eamt)}")
                except Exception as ex: st.error(str(ex))

def page_payments():
    st.markdown("## Payments")
    businesses=load_businesses()
    if not businesses: st.warning("Add a business first."); return
    biz_opts={b["name"]:b["id"] for b in businesses}; bid=biz_opts[st.selectbox("Business",list(biz_opts.keys()),key="py_biz")]
    payments=load_payments(bid); invoices=load_invoices(bid); parties=load_parties(bid)
    imap={i["id"]:i["invoice_number"] for i in invoices}
    search=st.text_input("🔍 Filter",key="py_srch")
    if search:
        q=search.lower(); payments=[p for p in payments if q in imap.get(p.get("invoice_id"),"").lower() or q in (p.get("reference") or "").lower()]
    total=sum(float(p["amount"]) for p in payments); st.markdown(f"**Total Collected: {fmt(total)}**")
    if payments:
        df=pd.DataFrame([{"Date":fmtd(p["payment_date"]),"Party":pname(p.get("party_id"),parties),"Invoice":imap.get(p.get("invoice_id"),"—"),"Mode":p.get("method","—"),"Ref":p.get("reference","—"),"Amount":fmt(p["amount"])} for p in payments])
        st.dataframe(df,use_container_width=True,hide_index=True)
    else: st.info("No payments.")

def page_ar():
    st.markdown("## AR Ledger — Accounts Receivable")
    businesses=load_businesses()
    if not businesses: st.warning("Add a business first."); return
    biz_opts={b["name"]:b["id"] for b in businesses}; bid=biz_opts[st.selectbox("Business",list(biz_opts.keys()),key="ar_biz")]
    parties=[p for p in load_parties(bid) if p["type"]=="client"]
    invoices=[i for i in load_invoices(bid) if i["type"]=="sale" and i["status"]!="proforma"]
    payments=load_payments(bid); pbi={}
    for p in payments: pbi.setdefault(p["invoice_id"],[]).append(p)
    now=date.today(); summaries=[]
    for party in parties:
        pinvs=[i for i in invoices if i["party_id"]==party["id"]]
        billed=sum(float(i["total"]) for i in pinvs)
        paid=sum(float(p["amount"]) for i in pinvs for p in pbi.get(i["id"],[]))
        bal=billed-paid; age0=age30=age60=age90=0
        for inv in pinvs:
            if inv["status"] in ("paid","cancelled"): continue
            ip=sum(float(p["amount"]) for p in pbi.get(inv["id"],[])); ib=float(inv["total"])-ip
            if ib<=0: continue
            days=(now-date.fromisoformat(str(inv.get("due_date",now))[:10])).days if inv.get("due_date") else 0
            if days<=0: age0+=ib
            elif days<=30: age30+=ib
            elif days<=60: age60+=ib
            else: age90+=ib
        if billed>0: summaries.append({**party,"billed":billed,"paid":paid,"balance":bal,"age0":age0,"age30":age30,"age60":age60,"age90":age90})
    total_bal=sum(s["balance"] for s in summaries); overdue=sum(s["age30"]+s["age60"]+s["age90"] for s in summaries)
    c1,c2,c3=st.columns(3)
    c1.markdown(f'<div class="metric-box"><div class="val">{fmt(total_bal)}</div><div class="lbl">Total Receivable</div></div>',unsafe_allow_html=True)
    c2.markdown(f'<div class="metric-box"><div class="val">{fmt(overdue)}</div><div class="lbl">Overdue</div></div>',unsafe_allow_html=True)
    c3.markdown(f'<div class="metric-box"><div class="val">{len(summaries)}</div><div class="lbl">Active Clients</div></div>',unsafe_allow_html=True)
    st.markdown("<br>",unsafe_allow_html=True)
    if summaries:
        df=pd.DataFrame([{"Client":s.get("company") or s["name"],"Billed":fmt(s["billed"]),"Paid":fmt(s["paid"]),"Balance":fmt(s["balance"]),"Not Due":fmt(s["age0"]),"1-30d":fmt(s["age30"]),"31-60d":fmt(s["age60"]),"60d+":fmt(s["age90"])} for s in summaries])
        st.dataframe(df,use_container_width=True,hide_index=True)
        st.markdown("---"); st.markdown("#### Client Statement")
        popts={(s.get("company") or s["name"]):s["id"] for s in summaries}
        if popts:
            sel=st.selectbox("Select Client",list(popts.keys()),key="ar_sel"); sid=popts[sel]
            pinvs=[i for i in invoices if i["party_id"]==sid]
            rows=[]
            for inv in sorted(pinvs,key=lambda x:x.get("issue_date","")):
                ip=sum(float(p["amount"]) for p in pbi.get(inv["id"],[])); ib=float(inv["total"])-ip
                rows.append({"Date":fmtd(inv.get("issue_date")),"Invoice #":inv["invoice_number"],"Total":fmt(inv["total"]),"Paid":fmt(ip),"Balance":fmt(ib),"Status":inv.get("status","—").upper()})
            if rows: st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)

def page_ap():
    st.markdown("## AP Ledger — Accounts Payable")
    businesses=load_businesses()
    if not businesses: st.warning("Add a business first."); return
    biz_opts={b["name"]:b["id"] for b in businesses}; bid=biz_opts[st.selectbox("Business",list(biz_opts.keys()),key="ap_biz")]
    vendors=[p for p in load_parties(bid) if p["type"]=="vendor"]
    invoices=[i for i in load_invoices(bid) if i["type"]=="purchase"]
    expenses=load_expenses(bid); summaries=[]
    for v in vendors:
        vi=sum(float(i["total"]) for i in invoices if i["party_id"]==v["id"])
        ve=sum(float(e["amount"]) for e in expenses if e.get("vendor_id")==v["id"])
        if vi+ve>0: summaries.append({**v,"total_inv":vi,"total_exp":ve,"total_owed":vi+ve})
    grand=sum(s["total_owed"] for s in summaries)
    st.markdown(f'<div class="metric-box" style="max-width:240px"><div class="val">{fmt(grand)}</div><div class="lbl">Total Payable</div></div>',unsafe_allow_html=True)
    st.markdown("<br>",unsafe_allow_html=True)
    if summaries:
        df=pd.DataFrame([{"Vendor":s.get("company") or s["name"],"Purchase Bills":fmt(s["total_inv"]),"Expenses":fmt(s["total_exp"]),"Total Owed":fmt(s["total_owed"])} for s in summaries])
        st.dataframe(df,use_container_width=True,hide_index=True)
    else: st.info("No payable data.")

def page_credit_notes():
    st.markdown("## Credit Notes")
    businesses=load_businesses()
    if not businesses: st.warning("Add a business first."); return
    biz_opts={b["name"]:b["id"] for b in businesses}; bid=biz_opts[st.selectbox("Business",list(biz_opts.keys()),key="cn_biz")]
    tab1,tab2=st.tabs(["📋 List","➕ New"])
    with tab1:
        cns=load_credit_notes(bid); parties=load_parties(bid)
        if not cns: st.info("No credit notes.")
        for cn in cns:
            pn=pname(cn.get("party_id"),parties)
            with st.expander(f"↩ {cn['cn_number']} — {pn} — {fmt(cn['total'])}"):
                st.markdown(f"**Date:** {fmtd(cn.get('cn_date'))}  \n**Reason:** {cn.get('reason','—')}  \n**Total:** {fmt(cn['total'])}")
                if st.button("🗑 Delete",key=f"dcn_{cn['id']}"): sb().table("credit_notes").delete().eq("id",cn["id"]).execute(); st.rerun()
    with tab2:
        parties=load_parties(bid); invoices=[i for i in load_invoices(bid) if i["type"]=="sale" and i["status"]!="proforma"]
        if not parties: st.warning("Add parties first."); return
        popts={f"{p.get('company') or p['name']}":p["id"] for p in parties}
        iopts={"None":None}|{i["invoice_number"]:i["id"] for i in invoices}
        res=sb().table("credit_notes").select("cn_number").like("cn_number",f"CN/{FISCAL_YEAR}/%").order("cn_number",desc=True).limit(1).execute()
        if res.data:
            try: cn_num=f"CN/{FISCAL_YEAR}/{int(res.data[0]['cn_number'].split('/')[-1])+1}"
            except: cn_num=f"CN/{FISCAL_YEAR}/1"
        else: cn_num=f"CN/{FISCAL_YEAR}/1"
        with st.form("cnf",clear_on_submit=True):
            fa,fb=st.columns(2)
            with fa: sp=st.selectbox("Party *",list(popts.keys())); sinv=st.selectbox("Against Invoice",list(iopts.keys())); cndate=st.date_input("Date",value=date.today())
            with fb: cnamt=st.number_input("Amount *",min_value=0.01,step=100.0); cntax=st.number_input("Tax Amount",min_value=0.0,step=10.0); cnrsn=st.text_area("Reason",height=60)
            st.markdown(f"**CN Number:** `{cn_num}`")
            if st.form_submit_button("💾 Save",type="primary"):
                try:
                    sb().table("credit_notes").insert({"business_id":bid,"invoice_id":iopts[sinv],"party_id":popts[sp],"cn_number":cn_num,"cn_date":str(cndate),"reason":cnrsn,"subtotal":round(float(cnamt),2),"tax_amount":round(float(cntax),2),"total":round(float(cnamt)+float(cntax),2),"status":"active"}).execute()
                    st.success(f"Saved {cn_num}")
                except Exception as ex: st.error(str(ex))

def page_bank():
    st.markdown("## Bank Accounts")
    businesses=load_businesses()
    if not businesses: st.warning("Add a business first."); return
    biz_opts={b["name"]:b["id"] for b in businesses}; bid=biz_opts[st.selectbox("Business",list(biz_opts.keys()),key="bk_biz")]
    banks=load_bank_accounts(bid); tab1,tab2,tab3=st.tabs(["🏦 Transactions","➕ Add Bank","➕ Add Txn"])
    with tab1:
        if not banks: st.info("Add a bank account first.")
        else:
            bopts={f"{b['name']} — {b.get('account_number','?')}":b for b in banks}
            slb=bopts[st.selectbox("Account",list(bopts.keys()),key="bk_sel")]
            txns=load_bank_txns(slb["id"]); ob=float(slb.get("opening_balance",0))
            cr=sum(float(t["amount"]) for t in txns if t["type"]=="credit")
            db=sum(float(t["amount"]) for t in txns if t["type"]=="debit")
            c1,c2,c3=st.columns(3); c1.metric("Balance",fmt(ob+cr-db)); c2.metric("Credits",fmt(cr)); c3.metric("Debits",fmt(db))
            if txns:
                run=ob; rows=[]
                for t in reversed(txns):
                    run+=float(t["amount"]) if t["type"]=="credit" else -float(t["amount"])
                    rows.append({"Date":fmtd(t["txn_date"]),"Description":t.get("description",""),"Ref":t.get("reference","—"),"Type":t["type"].upper(),"Amount":fmt(t["amount"]),"Balance":fmt(run)})
                st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)
    with tab2:
        with st.form("bkf",clear_on_submit=True):
            fa,fb=st.columns(2)
            with fa: bn=st.text_input("Label *"); bbn=st.text_input("Bank Name"); bnum=st.text_input("Account No.")
            with fb: bifsc=st.text_input("IFSC"); bop=st.number_input("Opening Balance",min_value=0.0,step=100.0)
            if st.form_submit_button("💾 Add Bank",type="primary"):
                if not bn.strip(): st.error("Label required.")
                else:
                    try: sb().table("bank_accounts").insert({"business_id":bid,"name":bn.strip(),"bank_name":bbn,"account_number":bnum,"ifsc_code":bifsc,"opening_balance":float(bop)}).execute(); st.success("Added!")
                    except Exception as ex: st.error(str(ex))
    with tab3:
        if not banks: st.info("Add a bank account first.")
        else:
            bopts2={f"{b['name']} — {b.get('account_number','?')}":b["id"] for b in banks}
            with st.form("tkf",clear_on_submit=True):
                fa,fb=st.columns(2)
                with fa: sb2=st.selectbox("Account",list(bopts2.keys())); tdesc=st.text_input("Description *"); tdate=st.date_input("Date",value=date.today())
                with fb: ttype=st.selectbox("Type",["credit","debit"],format_func=lambda x:"Credit (In)" if x=="credit" else "Debit (Out)"); tamt=st.number_input("Amount *",min_value=0.01,step=100.0); tref=st.text_input("Reference/UTR")
                if st.form_submit_button("💾 Add",type="primary"):
                    if not tdesc.strip(): st.error("Description required.")
                    else:
                        try: sb().table("bank_transactions").insert({"bank_account_id":bopts2[sb2],"txn_date":str(tdate),"description":tdesc.strip(),"amount":round(float(tamt),2),"type":ttype,"reference":tref or None}).execute(); st.success("Added!")
                        except Exception as ex: st.error(str(ex))

def page_accounts():
    st.markdown("## Chart of Accounts")
    businesses=load_businesses()
    if not businesses: st.warning("Add a business first."); return
    biz_opts={b["name"]:b["id"] for b in businesses}; bid=biz_opts[st.selectbox("Business",list(biz_opts.keys()),key="ac_biz")]
    tab1,tab2=st.tabs(["📒 Accounts","➕ Add"])
    with tab1:
        accs=load_accounts(bid)
        if not accs:
            st.info("No accounts. Seed defaults to get started.")
            if st.button("⚡ Seed Default Accounts"): seed_accounts(bid); st.success("Seeded!"); st.rerun()
        else:
            for grp in ACC_GROUPS:
                ga=[a for a in accs if a["group"]==grp]
                if not ga: continue
                st.markdown(f"**{grp.upper()}** — {len(ga)} accounts")
                df=pd.DataFrame([{"Code":a["code"],"Name":a["name"],"Sub-Group":a.get("sub_group","—"),"Description":a.get("description","—")} for a in ga])
                st.dataframe(df,use_container_width=True,hide_index=True)
    with tab2:
        with st.form("acf",clear_on_submit=True):
            fa,fb=st.columns(2)
            with fa: acode=st.text_input("Code *",placeholder="e.g. 1010"); aname=st.text_input("Name *"); agrp=st.selectbox("Group",ACC_GROUPS,format_func=str.capitalize)
            with fb:
                asg=st.selectbox("Sub-Group",[""]+(ACC_SUBGROUPS.get(agrp,[]))); adesc=st.text_area("Description",height=60)
            if st.form_submit_button("💾 Save",type="primary"):
                if not acode.strip() or not aname.strip(): st.error("Code and name required.")
                else:
                    try: sb().table("accounts").insert({"business_id":bid,"code":acode.strip(),"name":aname.strip(),"group":agrp,"sub_group":asg or None,"description":adesc or None}).execute(); st.success(f"Added {aname}")
                    except Exception as ex: st.error(str(ex))

def page_journal():
    st.markdown("## Journal Vouchers")
    businesses=load_businesses()
    if not businesses: st.warning("Add a business first."); return
    biz_opts={b["name"]:b["id"] for b in businesses}; bid=biz_opts[st.selectbox("Business",list(biz_opts.keys()),key="jl_biz")]
    tab1,tab2=st.tabs(["📋 Entries","➕ New Entry"])
    with tab1:
        entries=load_journal_entries(bid); accs={a["id"]:a for a in load_accounts(bid)}
        if not entries: st.info("No journal entries.")
        for entry in entries:
            lines=load_journal_lines(entry["id"])
            dr=sum(float(l["amount"]) for l in lines if l["type"]=="debit")
            cr=sum(float(l["amount"]) for l in lines if l["type"]=="credit")
            with st.expander(f"📝 {fmtd(entry['entry_date'])} — {entry['description']} — {entry.get('reference','')}"):
                for l in lines:
                    an=accs.get(l["account_id"],{}).get("name","Unknown")
                    if l["type"]=="debit": st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;**Dr** {an} — **{fmt(l['amount'])}**")
                    else: st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;**Cr** {an} — **{fmt(l['amount'])}**")
                bal=abs(dr-cr)<0.01
                st.markdown(f"Dr: {fmt(dr)} | Cr: {fmt(cr)} | {'✅ Balanced' if bal else '❌ Not balanced'}")
                if st.button("🗑 Delete",key=f"dj_{entry['id']}"):
                    sb().table("journal_lines").delete().eq("journal_id",entry["id"]).execute()
                    sb().table("journal_entries").delete().eq("id",entry["id"]).execute(); st.rerun()
    with tab2:
        accs_list=load_accounts(bid)
        if not accs_list: st.warning("Seed Chart of Accounts first."); return
        aopts={f"{a['code']} — {a['name']}":a["id"] for a in accs_list}
        fa,fb,fc=st.columns(3)
        jdate=fa.date_input("Date",value=date.today(),key="jdate")
        jref=fb.text_input("Reference",key="jref",placeholder="JV-001")
        jdesc=fc.text_input("Description *",key="jdesc",placeholder="e.g. Paid rent")
        st.markdown("**Lines**")
        if "jlines" not in st.session_state: st.session_state.jlines=[{"account_id":"","type":"debit","amount":0.0},{"account_id":"","type":"credit","amount":0.0}]
        rm=[]
        for i,line in enumerate(st.session_state.jlines):
            c1,c2,c3,c4=st.columns([3,1.5,1.5,0.5])
            klist=list(aopts.keys())
            try: ci=list(aopts.values()).index(line["account_id"]) if line["account_id"] in aopts.values() else 0
            except: ci=0
            sa=c1.selectbox("a",klist,index=ci,key=f"ja_{i}",label_visibility="collapsed")
            line["account_id"]=aopts[sa]
            line["type"]=c2.selectbox("t",["debit","credit"],index=0 if line["type"]=="debit" else 1,key=f"jt_{i}",label_visibility="collapsed",format_func=lambda x:"Dr" if x=="debit" else "Cr")
            line["amount"]=c3.number_input("a",min_value=0.0,value=float(line["amount"]),step=100.0,key=f"ja2_{i}",label_visibility="collapsed")
            if len(st.session_state.jlines)>2 and c4.button("✕",key=f"jrm_{i}"): rm.append(i)
        for i in reversed(rm): st.session_state.jlines.pop(i); st.rerun()
        if st.button("+ Line"): st.session_state.jlines.append({"account_id":"","type":"credit","amount":0.0}); st.rerun()
        tdr=sum(l["amount"] for l in st.session_state.jlines if l["type"]=="debit")
        tcr=sum(l["amount"] for l in st.session_state.jlines if l["type"]=="credit")
        bal=abs(tdr-tcr)<0.01
        st.markdown(f"Dr: {fmt(tdr)} | Cr: {fmt(tcr)} — {'✅ Balanced' if bal else '❌ Not balanced'}")
        if st.button("📝 Post Entry",type="primary",disabled=not bal or not st.session_state.get("jdesc","")):
            try:
                res=sb().table("journal_entries").insert({"business_id":bid,"entry_date":str(jdate),"reference":jref or None,"description":st.session_state.jdesc}).select().single().execute()
                jid=res.data["id"]
                vlines=[l for l in st.session_state.jlines if l["account_id"] and l["amount"]>0]
                sb().table("journal_lines").insert([{**l,"journal_id":jid} for l in vlines]).execute()
                st.success("Entry posted!"); st.session_state.jlines=[{"account_id":"","type":"debit","amount":0.0},{"account_id":"","type":"credit","amount":0.0}]; st.rerun()
            except Exception as ex: st.error(str(ex))

def page_trial_balance():
    st.markdown("## Trial Balance")
    businesses=load_businesses()
    if not businesses: st.warning("Add a business first."); return
    biz_opts={b["name"]:b["id"] for b in businesses}; bid=biz_opts[st.selectbox("Business",list(biz_opts.keys()),key="tb_biz")]
    accs=load_accounts(bid); entries=load_journal_entries(bid); eids=[e["id"] for e in entries]
    if not accs: st.info("No accounts."); return
    if not eids: st.info("No journal entries."); return
    all_lines=sb().table("journal_lines").select("*").in_("journal_id",eids).execute().data or []
    ab={a["id"]:{"dr":0.0,"cr":0.0} for a in accs}
    for l in all_lines:
        if l["account_id"] in ab:
            if l["type"]=="debit": ab[l["account_id"]]["dr"]+=float(l["amount"])
            else: ab[l["account_id"]]["cr"]+=float(l["amount"])
    rows=[]
    for a in accs:
        b=ab.get(a["id"],{"dr":0,"cr":0})
        if b["dr"]==0 and b["cr"]==0: continue
        net=b["dr"]-b["cr"]; idn=a["group"] in ("asset","expense")
        cdr=max(net,0) if idn else max(-net,0); ccr=max(-net,0) if idn else max(net,0)
        rows.append({"Code":a["code"],"Account":a["name"],"Group":a["group"].upper(),"Total Dr":fmt(b["dr"]),"Total Cr":fmt(b["cr"]),"Closing Dr":fmt(cdr) if cdr>0.01 else "—","Closing Cr":fmt(ccr) if ccr>0.01 else "—","_dr":b["dr"],"_cr":b["cr"]})
    sdr=sum(r["_dr"] for r in rows); scr=sum(r["_cr"] for r in rows); bal=abs(sdr-scr)<0.01
    c1,c2=st.columns(2); c1.metric("Total Debits",fmt(sdr)); c2.metric("Total Credits",fmt(scr))
    st.success("✅ Balanced") if bal else st.error(f"❌ Difference: {fmt(abs(sdr-scr))}")
    disp=[{k:v for k,v in r.items() if not k.startswith("_")} for r in rows]
    if disp: st.dataframe(pd.DataFrame(disp),use_container_width=True,hide_index=True)

def page_balance_sheet():
    st.markdown("## Balance Sheet")
    businesses=load_businesses()
    if not businesses: st.warning("Add a business first."); return
    biz_opts={b["name"]:b["id"] for b in businesses}; bid=biz_opts[st.selectbox("Business",list(biz_opts.keys()),key="bs_biz")]
    accs=load_accounts(bid); entries=load_journal_entries(bid); eids=[e["id"] for e in entries]
    if not accs: st.info("No accounts."); return
    all_lines=sb().table("journal_lines").select("*").in_("journal_id",eids).execute().data or [] if eids else []
    def gb(aid):
        dr=sum(float(l["amount"]) for l in all_lines if l["account_id"]==aid and l["type"]=="debit")
        cr=sum(float(l["amount"]) for l in all_lines if l["account_id"]==aid and l["type"]=="credit")
        return dr-cr
    def gt(grp,sg=None):
        return sum((gb(a["id"])) * (1 if grp in ("asset","expense") else -1) for a in accs if a["group"]==grp and (not sg or a.get("sub_group")==sg) if abs(gb(a["id"]))>0.01)
    ca=gt("asset","Current Assets"); fa=gt("asset","Fixed Assets"); ta=ca+fa
    cl=gt("liability","Current Liabilities"); ll=gt("liability","Long-term Liabilities"); tl=cl+ll
    eq=gt("equity","Equity"); inc=sum(-gb(a["id"]) for a in accs if a["group"]=="income")
    exv=sum(gb(a["id"]) for a in accs if a["group"]=="expense"); ni=inc-exv; te=eq+ni; tle=tl+te
    bal=abs(ta-tle)<0.01
    st.success("✅ Assets = Liabilities + Equity") if bal else st.warning(f"⚠ Difference: {fmt(abs(ta-tle))}")
    c1,c2=st.columns(2)
    with c1:
        st.markdown("### ASSETS")
        st.markdown("**Current Assets**")
        for a in accs:
            if a["group"]=="asset" and a.get("sub_group")=="Current Assets":
                b=gb(a["id"]);
                if abs(b)>0.01: st.markdown(f"&nbsp;&nbsp;{a['name']}: **{fmt(b)}**")
        st.markdown(f"*Total Current Assets: **{fmt(ca)}***")
        st.markdown("**Fixed Assets**")
        for a in accs:
            if a["group"]=="asset" and a.get("sub_group")=="Fixed Assets":
                b=gb(a["id"]);
                if abs(b)>0.01: st.markdown(f"&nbsp;&nbsp;{a['name']}: **{fmt(b)}**")
        st.markdown(f"*Total Fixed Assets: **{fmt(fa)}***")
        st.markdown(f"## Total Assets: {fmt(ta)}")
    with c2:
        st.markdown("### LIABILITIES & EQUITY")
        st.markdown("**Current Liabilities**")
        for a in accs:
            if a["group"]=="liability" and a.get("sub_group")=="Current Liabilities":
                b=-gb(a["id"]);
                if abs(b)>0.01: st.markdown(f"&nbsp;&nbsp;{a['name']}: **{fmt(b)}**")
        st.markdown(f"*Total Liabilities: **{fmt(tl)}***")
        st.markdown("**Equity**")
        for a in accs:
            if a["group"]=="equity":
                b=-gb(a["id"]);
                if abs(b)>0.01: st.markdown(f"&nbsp;&nbsp;{a['name']}: **{fmt(b)}**")
        st.markdown(f"&nbsp;&nbsp;Net Income: **{fmt(ni)}**")
        st.markdown(f"*Total Equity: **{fmt(te)}***")
        st.markdown(f"## Total L+E: {fmt(tle)}")

def page_pl():
    st.markdown("## P&L Report")
    businesses=load_businesses()
    if not businesses: st.warning("Add a business first."); return
    biz_opts={b["name"]:b["id"] for b in businesses}; bid=biz_opts[st.selectbox("Business",list(biz_opts.keys()),key="pl_biz")]
    period=st.radio("Period",["This FY","This Quarter","This Month"],horizontal=True)
    now=date.today()
    if period=="This FY": start=date(now.year if now.month>=4 else now.year-1,4,1)
    elif period=="This Quarter": q=(now.month-1)//3; start=date(now.year,q*3+1,1)
    else: start=date(now.year,now.month,1)
    def inp(d): return d and date.fromisoformat(str(d)[:10])>=start
    invoices=load_invoices(bid); expenses=load_expenses(bid); payments=load_payments(bid)
    si=[i for i in invoices if i["type"]=="sale" and i["status"] not in ("cancelled","proforma","draft") and inp(i.get("issue_date"))]
    pi=[i for i in invoices if i["type"]=="purchase" and i["status"] not in ("cancelled","proforma","draft") and inp(i.get("issue_date"))]
    pe=[e for e in expenses if inp(e.get("expense_date"))]
    rev=sum(float(i.get("subtotal",0)) for i in si); purch=sum(float(i.get("subtotal",0)) for i in pi); gp=rev-purch
    ec={}
    for e in pe: ec[e["category"]]=ec.get(e["category"],0)+float(e["amount"])
    te=sum(ec.values()); np_v=gp-te
    pbi={}
    for p in payments: pbi.setdefault(p["invoice_id"],[]).append(p)
    coll=sum(float(p["amount"]) for i in si for p in pbi.get(i["id"],[]))
    c1,c2,c3,c4,c5=st.columns(5)
    for col,val,lbl in [(c1,fmt(rev),"Revenue"),(c2,fmt(coll),"Collected"),(c3,fmt(gp),"Gross Profit"),(c4,fmt(te),"Expenses"),(c5,fmt(abs(np_v)),f"Net {'Profit' if np_v>=0 else 'Loss'}")]:
        col.markdown(f'<div class="metric-box"><div class="val">{val}</div><div class="lbl">{lbl}</div></div>',unsafe_allow_html=True)
    st.markdown("<br>",unsafe_allow_html=True)
    ca,cb=st.columns(2)
    with ca:
        st.markdown("#### Income Statement")
        for lbl,val,ie in [("Sales Revenue",rev,False),("(-) Purchases / COGS",purch,True),("**Gross Profit**",gp,False)]+[(k,v,True) for k,v in sorted(ec.items(),key=lambda x:-x[1])]+[("**(Net Profit)**",np_v,False)]:
            color="#16a34a" if val>=0 else "#dc2626"; sign="-" if ie and val>0 else ""
            st.markdown(f'<div style="display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px solid #f0f0f0"><span>{lbl}</span><span style="font-family:monospace;color:{color}">{sign}{fmt(abs(val))}</span></div>',unsafe_allow_html=True)
    with cb:
        st.markdown("#### Expense Breakdown")
        if ec: st.bar_chart(pd.DataFrame(list(ec.items()),columns=["Category","Amount"]).sort_values("Amount",ascending=False).set_index("Category"))
        else: st.info("No expenses.")

def page_gstr1():
    st.markdown("## GSTR-1 Summary")
    businesses=load_businesses()
    if not businesses: st.warning("Add a business first."); return
    biz_opts={b["name"]:b["id"] for b in businesses}; bid=biz_opts[st.selectbox("Business",list(biz_opts.keys()),key="gs_biz")]
    c1,c2=st.columns(2)
    month=c1.selectbox("Month",range(1,13),index=date.today().month-1,format_func=lambda x:date(2024,x,1).strftime("%B"))
    year=c2.selectbox("Year",[2024,2025,2026,2027],index=2)
    invoices=load_invoices(bid); parties=load_parties(bid)
    si=[i for i in invoices if i["type"]=="sale" and i["status"] not in ("cancelled","proforma","draft") and str(i.get("issue_date","")).startswith(f"{year}-{str(month).zfill(2)}")]
    if not si: st.info(f"No invoices for {date(year,month,1).strftime('%B %Y')}."); return
    tt=sum(float(i.get("subtotal",0)) for i in si); tc=sum(float(i.get("cgst_amount",0)) for i in si)
    ts=sum(float(i.get("sgst_amount",0)) for i in si); tig=sum(float(i.get("igst_amount",0)) for i in si); ttax=tc+ts+tig
    c1,c2,c3,c4=st.columns(4)
    c1.metric("Taxable",fmt(tt)); c2.metric("CGST+SGST",fmt(tc+ts)); c3.metric("IGST",fmt(tig)); c4.metric("Total Tax",fmt(ttax))
    tab1,tab2,tab3=st.tabs(["B2B","B2C","Summary"])
    def get_party(pid): return next((p for p in parties if p["id"]==pid),{})
    b2b=[i for i in si if get_party(i.get("party_id",{})).get("gstin")]
    b2c=[i for i in si if not get_party(i.get("party_id",{})).get("gstin")]
    with tab1:
        st.markdown(f"**B2B — {len(b2b)} invoices**")
        if b2b:
            rows=[]
            for inv in b2b:
                p=get_party(inv.get("party_id"))
                rows.append({"Invoice #":inv["invoice_number"],"Date":fmtd(inv.get("issue_date")),"Party":p.get("company") or p.get("name","—"),"GSTIN":p.get("gstin","—"),"State":p.get("state","—"),"Type":"Intra" if inv.get("is_interstate")==False else "Inter","Taxable":fmt(inv.get("subtotal",0)),"CGST":fmt(inv.get("cgst_amount",0)),"SGST":fmt(inv.get("sgst_amount",0)),"IGST":fmt(inv.get("igst_amount",0)),"Total":fmt(inv["total"])})
            st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)
    with tab2:
        st.markdown(f"**B2C — {len(b2c)} invoices**")
        if b2c:
            rows=[]
            for inv in b2c:
                p=get_party(inv.get("party_id"))
                rows.append({"Invoice #":inv["invoice_number"],"Date":fmtd(inv.get("issue_date")),"Party":p.get("company") or p.get("name","—"),"State":p.get("state","—"),"Type":"Intra" if inv.get("is_interstate")==False else "Inter","Taxable":fmt(inv.get("subtotal",0)),"Tax":fmt(float(inv.get("cgst_amount",0))+float(inv.get("sgst_amount",0))+float(inv.get("igst_amount",0))),"Total":fmt(inv["total"])})
            st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)
    with tab3:
        st.markdown(f"#### {date(year,month,1).strftime('%B %Y')} Summary")
        for k,v in {"Total Invoices":len(si),"B2B":len(b2b),"B2C":len(b2c),"Taxable Value":fmt(tt),"CGST":fmt(tc),"SGST":fmt(ts),"IGST":fmt(tig),"Total Tax":fmt(ttax),"Grand Total":fmt(sum(float(i["total"]) for i in si))}.items():
            st.markdown(f"**{k}:** {v}")
        csv_rows=[{"Invoice No.":i["invoice_number"],"Date":i.get("issue_date",""),"Party":get_party(i.get("party_id")).get("name",""),"GSTIN":get_party(i.get("party_id")).get("gstin",""),"State":get_party(i.get("party_id")).get("state",""),"Type":"Intra" if i.get("is_interstate")==False else "Inter","Taxable":i.get("subtotal",0),"CGST":i.get("cgst_amount",0),"SGST":i.get("sgst_amount",0),"IGST":i.get("igst_amount",0),"Total":i["total"]} for i in si]
        csv=pd.DataFrame(csv_rows).to_csv(index=False).encode("utf-8")
        st.download_button("⬇ Export CSV",data=csv,file_name=f"GSTR1_{year}_{str(month).zfill(2)}.csv",mime="text/csv")
    st.caption("ℹ️ GSTR-1 due by 11th of following month. File on GST portal using these figures.")

def page_businesses():
    st.markdown("## Businesses")
    tab1,tab2=st.tabs(["🏢 List","➕ Add/Edit"])
    with tab1:
        businesses=load_businesses()
        if not businesses: st.info("No businesses. Add one to get started.")
        for b in businesses:
            with st.expander(f"**{b['name']}** — GSTIN: {b.get('gstin','—')} — State: {b.get('state','⚠ Not set')}"):
                c1,c2,c3=st.columns([2,2,1])
                c1.markdown(f"**Phone:** {b.get('phone','—')}  \n**Email:** {b.get('email','—')}  \n**GSTIN:** {b.get('gstin','—')}")
                c2.markdown(f"**State:** {b.get('state','⚠ Set this for GST')}  \n**UPI:** {b.get('upi_id','—')}  \n**Bank:** {b.get('bank_name','—')}")
                with c3:
                    if st.button("✏ Edit",key=f"edb_{b['id']}"): st.session_state["edit_biz"]=b; st.rerun()
                    if st.button("🗑 Del",key=f"ddb_{b['id']}"):
                        try: sb().table("businesses").delete().eq("id",b["id"]).execute(); st.rerun()
                        except Exception as ex: st.error(str(ex))
    with tab2:
        ed=st.session_state.get("edit_biz"); df=ed or {}
        if ed:
            st.info(f"Editing: **{ed['name']}**")
            if st.button("✕ Cancel"): st.session_state.pop("edit_biz"); st.rerun()
        with st.form("bzf",clear_on_submit=True):
            fa,fb=st.columns(2)
            with fa:
                bname=st.text_input("Business Name *",value=df.get("name",""))
                bgstin=st.text_input("GSTIN",value=df.get("gstin",""))
                bsi=STATES.index(df["state"]) if df.get("state") in STATES else 9
                bstate=st.selectbox("Home State *",STATES,index=bsi,help="Required for CGST/SGST auto-detection")
                bphone=st.text_input("Phone",value=df.get("phone",""))
                bemail=st.text_input("Email",value=df.get("email",""))
            with fb:
                baddr=st.text_area("Address",value=df.get("address",""),height=80)
                bacc=st.text_input("Bank Account No.",value=df.get("bank_account",""))
                bifsc=st.text_input("IFSC Code",value=df.get("ifsc_code",""))
                bbank=st.text_input("Bank Name",value=df.get("bank_name",""))
                bupi=st.text_input("UPI ID",value=df.get("upi_id",""))
                blogo=st.text_input("Logo URL",value=df.get("logo_url",""))
            if st.form_submit_button("💾 Save Business",type="primary"):
                if not bname.strip(): st.error("Name required.")
                else:
                    data={"name":bname.strip(),"gstin":bgstin.strip().upper(),"state":bstate,"phone":bphone.strip(),"email":bemail.strip(),"address":baddr.strip(),"bank_account":bacc.strip(),"ifsc_code":bifsc.strip().upper(),"bank_name":bbank.strip(),"upi_id":bupi.strip(),"logo_url":blogo.strip()}
                    try:
                        if ed: sb().table("businesses").update(data).eq("id",ed["id"]).execute(); st.success(f"✅ Updated: {bname}"); st.session_state.pop("edit_biz",None)
                        else: sb().table("businesses").insert(data).execute(); st.success(f"✅ Added: {bname}")
                    except Exception as ex: st.error(f"Save failed: {ex}")

# ── NAV ───────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🪡 Needle Point")
    st.markdown("<small style='opacity:.45'>Business ERP</small>",unsafe_allow_html=True)
    st.divider()
    page=st.radio("Navigation",["📊 Dashboard","── SALES ──","🧾 Tax Invoices","📋 Proforma Invoices","↩ Credit Notes","👥 Parties","📦 Item Master","── PURCHASES ──","💸 Expenses","💳 Payments","🏦 Bank","── LEDGERS ──","🟢 AR Ledger","🔴 AP Ledger","── ACCOUNTING ──","📒 Chart of Accounts","📝 Journal Vouchers","⚖ Trial Balance","📊 Balance Sheet","📈 P&L Report","── GST ──","🧾 GSTR-1","── SETTINGS ──","🏢 Businesses"],label_visibility="collapsed")
    st.divider()
    st.markdown(f"<small style='opacity:.4'>FY {FISCAL_YEAR} · Mayapuri</small>",unsafe_allow_html=True)

if   page=="📊 Dashboard":         page_dashboard()
elif page=="🧾 Tax Invoices":       page_invoices(False)
elif page=="📋 Proforma Invoices":  page_invoices(True)
elif page=="↩ Credit Notes":        page_credit_notes()
elif page=="👥 Parties":            page_parties()
elif page=="📦 Item Master":        page_items()
elif page=="💸 Expenses":           page_expenses()
elif page=="💳 Payments":           page_payments()
elif page=="🏦 Bank":               page_bank()
elif page=="🟢 AR Ledger":          page_ar()
elif page=="🔴 AP Ledger":          page_ap()
elif page=="📒 Chart of Accounts":  page_accounts()
elif page=="📝 Journal Vouchers":   page_journal()
elif page=="⚖ Trial Balance":       page_trial_balance()
elif page=="📊 Balance Sheet":      page_balance_sheet()
elif page=="📈 P&L Report":         page_pl()
elif page=="🧾 GSTR-1":            page_gstr1()
elif page=="🏢 Businesses":         page_businesses()
