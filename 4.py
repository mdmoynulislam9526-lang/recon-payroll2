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

# --- ট্যাবস ডিক্লেয়ার করা (এটি এখানে থাকলে আর NameError আসবে না) ---
tab1, tab2, tab3 = st.tabs(["Individual Pay Slip", "Attendance & Processor", "Summary Sheet"])
# --- LOGO & IMAGES ---
logo_base64_str = ""
current_dir = os.path.dirname(os.path.abspath(__file__))

local_logo_path = os.path.join(current_dir, "logo.png")
if os.path.exists(local_logo_path):
    with open(local_logo_path, "rb") as img_file:
        logo_base64_str = base64.b64encode(img_file.read()).decode('utf-8')

sig_html_element = f"<img src='data:image/png;base64,{sig_base64_str}' style='width: 150px;'>" if sig_base64_str else "____________________"

st.title("💼 RECON LABORATORIES LTD - Advanced Payroll Management System")
st.markdown("---")

col1, col2 = st.columns([1, 2.3])

with col1:
    st.header("➕ Add New Person")
    with st.form("employee_form", clear_on_submit=True):
        input_id = st.text_input("ID (Numbers only)").strip()
        name = st.text_input("Name")
        department = st.selectbox("Select Department", ["Production", "Quality Control", "Development", "Maintenance", "Accounts & Finance", "HR & Admin", "Store & Inventory", "Sales & Marketing"])
        category = st.selectbox("Select Category", ["Manager", "Officer", "Worker (Permanent)", "Worker (Daily Basis)"])
        designation = st.text_input("Designation")
        salary = st.text_input("Gross Salary / Daily Wage Rate (Tk)")
        
        if st.form_submit_button("Add to Database", use_container_width=True, type="primary"):
            if not (input_id and name and designation and salary):
                st.error("Please fill all fields!")
            elif not re.match(r"^[0-9]+$", input_id):
                st.error("⚠️ Invalid ID Format!")
            else:
                try:
                    # Supabase Insert Operation
                    supabase.table("employees_final_version").insert({
                        "emp_id": input_id,
                        "name": name,
                        "designation": designation,
                        "category": category,
                        "department": department,
                        "salary": float(salary)
                    }).execute()
                    st.success(f"{name} added successfully!")
                    st.rerun()
                except Exception as e:
                    st.error(f"⚠️ Error: {e}")
                  
def render_inline_management(r, prefix=""):
    # r একটি ডিকশনারি, তাই কী (key) ব্যবহার করছি
    eid, ename, edesg, ecat, edept, esalary = r['emp_id'], r['name'], r['designation'], r['category'], r['department'], r['salary']

    with st.container():
        col_info, col_act1, col_act2 = st.columns([3, 0.6, 0.6])
        with col_info:
            st.markdown(f"**[{eid}] {ename}** — {edesg} ({edept}) | Tk {esalary:,.2f}")
        
        with col_act1:
            if st.button("Edit 📝", key=f"{prefix}_edit_{eid}"):
                st.session_state[f"emode_{prefix}_{eid}"] = True
        
        with col_act2:
            if st.button("Delete ❌", key=f"{prefix}_del_{eid}", type="secondary"):
                # Supabase Delete অপারেশন
                supabase.table("employees_final_version").delete().eq("emp_id", eid).execute()
                supabase.table("monthly_attendance_records").delete().eq("emp_id", eid).execute()
                st.rerun()

        if st.session_state.get(f"emode_{prefix}_{eid}", False):
            with st.form(key=f"form_{prefix}_{eid}"):
                ch_name = st.text_input("Name", value=ename)
                ch_salary = st.text_input("Salary", value=str(esalary))
                
                if st.form_submit_button("Save"):
                    # Supabase Update অপারেশন
                    supabase.table("employees_final_version").update({
                        "name": ch_name, 
                        "salary": float(ch_salary)
                    }).eq("emp_id", eid).execute()
                    
                    st.session_state[f"emode_{prefix}_{eid}"] = False
                    st.rerun()
                    
with col2:
    # Supabase থেকে ডাটা ফেচ করা
    response = supabase.table("employees_final_version").select("*").execute()
    rows = response.data 

    if rows:
        # --- FIXED MONTH SELECTION ---
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
        
        # Supabase থেকে অ্যাটেনডেন্স রেকর্ড ফেচ করা
        att_response = supabase.table("monthly_attendance_records").select("*").eq("month_year", full_month).execute()
        db_records = att_response.data
        
        # ডিকশনারি কম্প্রিহেনশন (Supabase রেসপন্স অনুযায়ী কীগুলো ব্যবহার করা হয়েছে)
        saved_db_tracker = {str(r['emp_id']): {
            "present": r['present'], "absent": r['absent'], "fine": r['fine'], 
            "ot_hrs": r['ot_hrs'], "ot_rate": r['ot_rate'], "bonus": r['bonus'], "advance": r['advance']
        } for r in db_records}

        total_payout = 0.0
        total_bonus = 0.0
        total_ot = 0.0
        total_deductions = 0.0
        total_advance = 0.0

        for r in rows:
            # ডিকশনারি কী ব্যবহার করা হয়েছে
            base_sal = r['salary']
            cat = r['category']
            eid = r['emp_id']
            
            rec = saved_db_tracker.get(str(eid), {"present": days_in_month if cat == 'Worker (Daily Basis)' else 26, "absent": 0, "fine": 0.0, "ot_hrs": 0.0, "ot_rate": 0.0, "bonus": 0.0, "advance": 0.0})
            
            _, _, _, _, absent_cut, net_p, adv_paid = calculate_salary_breakdown(
                base_sal, rec['absent'], rec['fine'], cat, rec['present'], rec['advance']
            )
            ot_earned = rec['ot_hrs'] * rec['ot_rate']
            final_payable = net_p + ot_earned + rec['bonus']
            
            total_payout += final_payable
            total_bonus += rec['bonus']
            total_ot += ot_earned
            total_deductions += (absent_cut + rec['fine'])
            total_advance += adv_paid
st.markdown("### 📊 Financial Dashboard Summary")
        m_col1, m_col2, m_col3, m_col4, m_col5, m_col6 = st.columns(6)
        m_col1.metric("Total Employees", len(rows))
        m_col2.metric("Total Bonus (Tk)", f"{total_bonus:,.2f}")
        m_col3.metric("Total Overtime (Tk)", f"{total_ot:,.2f}")
        m_col4.metric("Total Fine & Abs Cut (Tk)", f"{total_deductions:,.2f}")
        m_col5.metric("Total Advance Cut (Tk)", f"{total_advance:,.2f}")
        m_col6.metric("Total Payout (Tk)", f"{total_payout:,.2f}")
        st.markdown("---")

        # আপনার আগের ডিফাইন করা ট্যাবগুলো এখানে ব্যবহার করছি
        tab_emp, tab0, tab1, tab2 = st.tabs(["👥 All Employees", "🔍 Search Employee", "📄 Individual Pay Slip", "📊 Attendance & Payroll Processor"])
        
        with tab_emp:
            categories_map = {"💼 Managers": "Manager", "👔 Officers": "Officer", "🛠️ Workers (Permanent)": "Worker (Permanent)", "📆 Workers (Daily Basis)": "Worker (Daily Basis)"}
            for title, cat_value in categories_map.items():
                # ইনডেক্স এর পরিবর্তে কী (key) ব্যবহার করা হয়েছে
                cat_members = [r for r in rows if r['category'] == cat_value]
                with st.expander(f"{title} ({len(cat_members)})", expanded=False):
                    if not cat_members: 
                        st.info("No records.")
                    else:
                        for r in cat_members: 
                            render_inline_management(r, prefix="all_tab")

        with tab0:
            search_query = st.text_input("Enter Employee ID or Name to search", placeholder="Type here...", key="search_tab_input")
            if search_query:
                # emp_id এবং name ফিল্ড অনুযায়ী সার্চ
                search_results = [r for r in rows if search_query.lower() in str(r['emp_id']).lower() or search_query.lower() in r['name'].lower()]
                for emp in search_results: 
                    render_inline_management(emp, prefix="search_tab")
                    
