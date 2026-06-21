import streamlit as st
from supabase import create_client
from datetime import datetime
import calendar
from io import BytesIO
import pandas as pd
import re
import os
import base64
from calculations import calculate_salary_breakdown, generate_pdf_bytes

# --- SUPABASE CONFIGURATION ---
SUPABASE_URL = "https://qoelqzaodnxjfsmsyvhc.supabase.co"
SUPABASE_KEY = "sb_publishable_polNmuBnDGzfd91wFvCozw_eUJUtGrx"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="RECON Payroll System", layout="wide", page_icon="💼")

# --- SUPABASE FETCH FUNCTIONS ---
def get_employees():
    return supabase.table("employees_final_version").select("*").execute().data

def get_attendance(month_year):
    return supabase.table("monthly_attendance_records").select("*").eq("month_year", month_year).execute().data

# --- LOGO & IMAGES ---
logo_base64_str = ""
current_dir = os.path.dirname(os.path.abspath(__file__))
local_logo_path = os.path.join(current_dir, "logo.png")
if os.path.exists(local_logo_path):
    with open(local_logo_path, "rb") as img_file:
        logo_base64_str = base64.b64encode(img_file.read()).decode('utf-8')

sig_base64_str = ""
local_sig_path = os.path.join(current_dir, "signature.png")
if os.path.exists(local_sig_path):
    with open(local_sig_path, "rb") as img_file:
        sig_base64_str = base64.b64encode(img_file.read()).decode('utf-8')

seal_base64_str = ""
local_seal_path = os.path.join(current_dir, "seal.png")
if os.path.exists(local_seal_path):
    with open(local_seal_path, "rb") as img_file:
        seal_base64_str = base64.b64encode(img_file.read()).decode('utf-8')
      st.title("💼 RECON LABORATORIES LTD - Advanced Payroll Management System")
st.markdown("---")

col1, col2 = st.columns([1, 2.3])

with col1:
    st.header("➕ Add New Person")
    if "emp_id_val" not in st.session_state: st.session_state.emp_id_val = ""
    if "name_val" not in st.session_state: st.session_state.name_val = ""
    if "desg_val" not in st.session_state: st.session_state.desg_val = ""
    if "salary_val" not in st.session_state: st.session_state.salary_val = ""

    with st.form("employee_form", clear_on_submit=True):
        input_id = st.text_input("ID (Numbers only)", value=st.session_state.emp_id_val).strip()
        name = st.text_input("Name", value=st.session_state.name_val)
        department = st.selectbox("Select Department", ["Production", "Quality Control", "Development", "Maintenance", "Accounts & Finance", "HR & Admin", "Store & Inventory", "Sales & Marketing"])
        category = st.selectbox("Select Category", ["Manager", "Officer", "Worker (Permanent)", "Worker (Daily Basis)"])
        designation = st.text_input("Designation", value=st.session_state.desg_val)
        salary = st.text_input("Gross Salary / Daily Wage Rate (Tk)", value=st.session_state.salary_val)
        
        if st.form_submit_button("Add to Database", use_container_width=True, type="primary"):
            st.session_state.emp_id_val = input_id
            st.session_state.name_val = name
            st.session_state.desg_val = designation
            st.session_state.salary_val = salary
            if not (input_id and name and designation and salary):
                st.error("Please fill all fields!")
            elif not re.match(r"^[0-9]+$", input_id):
                st.error("⚠️ Invalid ID Format!")
            else:
                try:
                    supabase.table("employees_final_version").insert({
                        "emp_id": input_id, "name": name, "designation": designation,
                        "category": category, "department": department, "salary": float(salary)
                    }).execute()
                    st.success(f"{name} added!")
                    st.rerun()
                except Exception as e:
                    st.error(f"⚠️ Error: {e}")

def render_inline_management(r, prefix=""):
    eid, ename, edesg, ecat, edept, esalary = r['emp_id'], r['name'], r['designation'], r['category'], r['department'], r['salary']
    with st.container():
        col_info, col_act1, col_act2 = st.columns([3, 0.6, 0.6])
        with col_info:
            st.markdown(f"**[{eid}] {ename}** — {edesg} ({edept}) | Tk {esalary:,.2f}")
        with col_act1:
            if st.button("Edit 📝", key=f"{prefix}_edit_{eid}"): st.session_state[f"emode_{prefix}_{eid}"] = True
        with col_act2:
            if st.button("Delete ❌", key=f"{prefix}_del_{eid}", type="secondary"):
                supabase.table("employees_final_version").delete().eq("emp_id", eid).execute()
                supabase.table("monthly_attendance_records").delete().eq("emp_id", eid).execute()
                st.rerun()
        if st.session_state.get(f"emode_{prefix}_{eid}", False):
            with st.form(key=f"form_{prefix}_{eid}"):
                ch_name = st.text_input("Name", value=ename)
                ch_salary = st.text_input("Salary", value=str(esalary))
                if st.form_submit_button("Save"):
                    supabase.table("employees_final_version").update({"name": ch_name, "salary": float(ch_salary)}).eq("emp_id", eid).execute()
                    st.session_state[f"emode_{prefix}_{eid}"] = False
                    st.rerun()
                  with col2:
    rows = get_employees()
    if rows:
        months_list = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
        if 'selected_month' not in st.session_state:
            st.session_state.selected_month = datetime.now().strftime("%B")
            
        c_col1, c_col2 = st.columns(2)
        with c_col1:
            select_m = st.selectbox("Select Month", months_list, index=months_list.index(st.session_state.selected_month))
            st.session_state.selected_month = select_m
        
        current_year = datetime.now().year
        available_years = [str(y) for y in range(2023, current_year + 5)]
        with c_col2:
            select_y = st.selectbox("Select Year", available_years, index=available_years.index(str(current_year)))
        
        full_month = f"{select_m}, {select_y}"
        month_num = months_list.index(select_m) + 1
        days_in_month = calendar.monthrange(int(select_y), month_num)[1]
        
        db_records = get_attendance(full_month)
        saved_db_tracker = {str(r['emp_id']): r for r in db_records}

        total_payout = 0.0
        total_bonus = 0.0
        total_ot = 0.0
        total_deductions = 0.0
        total_advance = 0.0

        for r in rows:
            eid, base_sal, cat = r['emp_id'], r['salary'], r['category']
            rec = saved_db_tracker.get(str(eid), {"present": days_in_month if cat == 'Worker (Daily Basis)' else 26, "absent": 0, "fine": 0.0, "ot_hrs": 0.0, "ot_rate": 0.0, "bonus": 0.0, "advance": 0.0})
            _, _, _, _, absent_cut, net_p, adv_paid = calculate_salary_breakdown(base_sal, rec['absent'], rec['fine'], cat, rec['present'], rec['advance'])
            ot_earned = rec['ot_hrs'] * rec['ot_rate']
            total_payout += (net_p + ot_earned + rec['bonus'])
            total_bonus += rec['bonus']
            total_ot += ot_earned
            total_deductions += (absent_cut + rec['fine'])
            total_advance += adv_paid

        st.markdown("### 📊 Financial Dashboard Summary")
        m1, m2, m3, m4, m5, m6 = st.columns(6)
        m1.metric("Total Employees", len(rows))
        m2.metric("Total Bonus", f"{total_bonus:,.2f}")
        m3.metric("Total OT", f"{total_ot:,.2f}")
        m4.metric("Total Deduction", f"{total_deductions:,.2f}")
        m5.metric("Total Advance", f"{total_advance:,.2f}")
        m6.metric("Total Payout", f"{total_payout:,.2f}")
        st.markdown("---")

        tab_emp, tab0, tab1, tab2 = st.tabs(["👥 All Employees", "🔍 Search Employee", "📄 Individual Pay Slip", "📊 Attendance & Payroll Processor"])
        
        with tab_emp:
            for cat_value in ["Manager", "Officer", "Worker (Permanent)", "Worker (Daily Basis)"]:
                cat_members = [r for r in rows if r['category'] == cat_value]
                with st.expander(f"{cat_value} ({len(cat_members)})"):
                    for r in cat_members: render_inline_management(r, prefix="all_tab")

        with tab0:
            search_query = st.text_input("Search ID or Name", key="search_tab_input")
            if search_query:
                for emp in [r for r in rows if search_query.lower() in str(r['emp_id']).lower() or search_query.lower() in r['name'].lower()]:
                    render_inline_management(emp, prefix="search_tab")

        with tab1:
            pay_search = st.text_input("Search for Pay Slip", key="pay_slip_search_input")
            if pay_search:
                results = [r for r in rows if pay_search.lower() in str(r['emp_id']).lower() or pay_search.lower() in r['name'].lower()]
                if results:
                    selected_emp = results[0]
                    rec = saved_db_tracker.get(str(selected_emp['emp_id']), {"present": days_in_month if selected_emp['category'] == 'Worker (Daily Basis)' else 26, "absent": 0, "fine": 0.0, "ot_hrs": 0.0, "ot_rate": 0.0, "bonus": 0.0, "advance": 0.0})
                    # (আপনার আগের পে-স্লিপ HTML এবং PDF ডাউনলোড বাটন এখানে বসবে)

        with tab2:
            view_cat = st.selectbox("Select Category", ["Manager", "Officer", "Worker (Permanent)", "Worker (Daily Basis)"])
            filtered = [r for r in rows if r['category'] == view_cat]
            with st.form("bulk_sheet_form"):
                sheet_data = []
                for r in filtered:
                    st.markdown(f"**{r['emp_id']} - {r['name']}**")
                    c1, c2, c3 = st.columns(3)
                    p_days = c1.number_input("Present Days", value=26, key=f"p_{r['emp_id']}")
                    a_days = c1.number_input("Absent Days", value=0, key=f"a_{r['emp_id']}")
                    fine = c1.number_input("Fine", value=0.0, key=f"f_{r['emp_id']}")
                    ot_h = c2.number_input("OT Hours", value=0.0, key=f"oth_{r['emp_id']}")
                    ot_r = c2.number_input("OT Rate", value=0.0, key=f"otr_{r['emp_id']}")
                    bonus = c3.number_input("Bonus", value=0.0, key=f"bn_{r['emp_id']}")
                    adv = c3.number_input("Advance", value=0.0, key=f"adv_{r['emp_id']}")
                    sheet_data.append({'eid': r['emp_id'], 'p': p_days, 'a': a_days, 'f': fine, 'oth': ot_h, 'otr': ot_r, 'bonus': bonus, 'adv': adv})
                
                if st.form_submit_button("💾 Save Entry to Database"):
                    for item in sheet_data:
                        supabase.table("monthly_attendance_records").upsert({
                            "month_year": full_month, "emp_id": item['eid'], "present": item['p'], 
                            "absent": item['a'], "fine": item['f'], "ot_hrs": item['oth'], 
                            "ot_rate": item['otr'], "bonus": item['bonus'], "advance": item['adv']
                        }).execute()
                    st.success("Saved!")
                    st.rerun()
