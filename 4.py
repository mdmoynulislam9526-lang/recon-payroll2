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
 # --- Pay Slip HTML generation ---
                    payslip_preview_html = f"""
                    <div style="font-family: 'Segoe UI', Arial, sans-serif; padding: 35px; background: white; color: black; border: 1px solid #c8d6e5; border-radius: 8px; max-width: 700px; margin: 15px auto; box-sizing: border-box; box-shadow: 0 4px 20px rgba(0,0,0,0.06);">
                        
                        <div style="text-align: center; margin-bottom: 25px; padding-bottom: 15px; border-bottom: 3px solid #1F4E78;">
                            {"<div style='margin-bottom: 5px; display: block;'><img src='data:image/png;base64," + logo_base64_str + "' style='max-height: 65px; width: auto; object-fit: contain; display: inline-block;' alt='RECON Logo'></div>" if logo_base64_str else ""}
                        </div>
                        
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 25px; width: 100%;">
                            <div style="width: 25%;"></div>
                            <div style="width: 50%; text-align: center;">
                                <span style="font-size: 16px; color: #1F4E78; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px;">Employee Pay Slip</span>
                            </div>
                            <div style="width: 25%; text-align: right;">
                                <span style="font-size: 12px; color: #1F4E78; font-weight: 700; background-color: #f0f4f8; padding: 4px 10px; border-radius: 4px; border: 1px solid #b4c6e7; text-transform: uppercase;">{select_m[:3]} {select_y}</span>
                            </div>
                        </div>
                        
                        <table style="width: 100%; border-collapse: collapse; margin-bottom: 30px; font-size: 13px; border: 1px solid #cbd5e1;">
                            <tr style="background-color: #f8fafc;">
                                <td style="padding: 10px; font-weight: 600; color: #475569; width: 25%; border: 1px solid #cbd5e1;">Employee ID</td>
                                <td style="padding: 10px; font-weight: 700; color: #0f172a; width: 25%; border: 1px solid #cbd5e1;">#{selected_emp['emp_id']}</td>
                                <td style="padding: 10px; font-weight: 600; color: #475569; width: 25%; border: 1px solid #cbd5e1;">Department</td>
                                <td style="padding: 10px; font-weight: 600; color: #1F4E78; width: 25%; border: 1px solid #cbd5e1;">{selected_emp['department']}</td>
                            </tr>
                            <tr>
                                <td style="padding: 10px; font-weight: 600; color: #475569; border: 1px solid #cbd5e1;">Full Name</td>
                                <td style="padding: 10px; font-weight: 700; color: #0f172a; border: 1px solid #cbd5e1;">{selected_emp['name']}</td>
                                <td style="padding: 10px; font-weight: 600; color: #475569; border: 1px solid #cbd5e1;">Designation</td>
                                <td style="padding: 10px; font-weight: 600; color: #1F4E78; border: 1px solid #cbd5e1;">{selected_emp['designation']}</td>
                            </tr>
                            <tr style="background-color: #f8fafc;">
                                <td style="padding: 10px; font-weight: 600; color: #475569; border: 1px solid #cbd5e1;">Category</td>
                                <td style="padding: 10px; font-weight: 600; color: #334155; border: 1px solid #cbd5e1;">{selected_emp['category']}</td>
                                <td style="padding: 10px; font-weight: 600; color: #475569; border: 1px solid #cbd5e1;">Attendance Status</td>
                                <td style="padding: 10px; font-weight: 700; color: #2563eb; border: 1px solid #cbd5e1;">{rec['present']} P  /  {rec['absent']} A</td>
                            </tr>
                        </table>
                        
                        <!-- Earnings & Deductions Table logic remains the same with updated dict keys -->
                        <table style="width: 100%; font-size: 13px; border-collapse: collapse; margin-bottom: 25px;">
                            <thead>
                                <tr style="background-color: #F8FAFC; border-top: 1px solid #E2E8F0; border-bottom: 1px solid #E2E8F0;">
                                    <th style="padding: 10px 8px; text-align: left; color: #1F4E78; font-weight: 700; width: 30%; border-right: 1px solid #EDF2F7;">Earnings</th>
                                    <th style="padding: 10px 8px; text-align: right; color: #1F4E78; font-weight: 700; width: 20%; border-right: 2px solid #E2E8F0;">Amount (Tk)</th>
                                    <th style="padding: 10px 8px; text-align: left; color: #9B2C2C; font-weight: 700; width: 30%; padding-left: 15px; border-right: 1px solid #EDF2F7;">Deductions</th>
                                    <th style="padding: 10px 8px; text-align: right; color: #9B2C2C; font-weight: 700; width: 20%;">Amount (Tk)</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr>
                                    <td style="padding: 9px 8px; border-bottom: 1px dashed #E2E8F0; border-right: 1px solid #EDF2F7;">Base Pay</td>
                                    <td style="padding: 9px 8px; text-align: right; border-bottom: 1px dashed #E2E8F0; font-weight: 500; border-right: 2px solid #E2E8F0;">{gross:,.2f}</td>
                                    <td style="padding: 9px 8px; border-bottom: 1px dashed #E2E8F0; padding-left: 15px; color: #C53030; border-right: 1px solid #EDF2F7;">Absent Cut</td>
                                    <td style="padding: 9px 8px; text-align: right; border-bottom: 1px dashed #E2E8F0; color: #C53030; font-weight: 500;">{absent_cut:,.2f}</td>
                                </tr>
                                <tr>
                                    <td style="padding: 9px 8px; border-bottom: 1px dashed #E2E8F0; color: #4A5568; border-right: 1px solid #EDF2F7;">House Rent</td>
                                    <td style="padding: 9px 8px; text-align: right; border-bottom: 1px dashed #E2E8F0; color: #4A5568; border-right: 2px solid #E2E8F0;">{house_rent:,.2f}</td>
                                    <td style="padding: 9px 8px; border-bottom: 1px dashed #E2E8F0; padding-left: 15px; color: #C53030; border-right: 1px solid #EDF2F7;">Fine / Penalty</td>
                                    <td style="padding: 9px 8px; text-align: right; border-bottom: 1px dashed #E2E8F0; color: #C53030; font-weight: 500;">{rec['fine']:,.2f}</td>
                                </tr>
                                <tr>
                                    <td style="padding: 9px 8px; border-bottom: 1px dashed #E2E8F0; color: #4A5568; border-right: 1px solid #EDF2F7;">Medical</td>
                                    <td style="padding: 9px 8px; text-align: right; border-bottom: 1px dashed #E2E8F0; color: #4A5568; border-right: 2px solid #E2E8F0;">{medical:,.2f}</td>
                                    <td style="padding: 9px 8px; border-bottom: 1px dashed #E2E8F0; padding-left: 15px; color: #C53030; border-right: 1px solid #EDF2F7;">Advance Cut</td>
                                    <td style="padding: 9px 8px; text-align: right; border-bottom: 1px dashed #E2E8F0; color: #C53030; font-weight: 500;">{adv_paid:,.2f}</td>
                                </tr>
                                <tr>
                                    <td style="padding: 9px 8px; border-bottom: 1px dashed #E2E8F0; color: #2F855A; font-weight: 500; border-right: 1px solid #EDF2F7;">Overtime ({rec['ot_hrs']} hrs)</td>
                                    <td style="padding: 9px 8px; text-align: right; border-bottom: 1px dashed #E2E8F0; color: #2F855A; font-weight: 500; border-right: 2px solid #E2E8F0;">{total_ot_emp:,.2f}</td>
                                    <td style="padding: 9px 8px; border-bottom: 1px dashed #E2E8F0; border-right: 1px solid #EDF2F7; padding-left: 15px;"></td>
                                    <td style="padding: 9px 8px; text-align: right; border-bottom: 1px dashed #E2E8F0;"></td>
                                </tr>
                                <tr>
                                    <td style="padding: 9px 8px; border-bottom: 1px solid #E2E8F0; color: #2F855A; font-weight: 500; border-right: 1px solid #EDF2F7;">Bonus</td>
                                    <td style="padding: 9px 8px; text-align: right; border-bottom: 1px solid #E2E8F0; color: #2F855A; font-weight: 500; border-right: 2px solid #E2E8F0;">{rec['bonus']:,.2f}</td>
                                    <td style="padding: 9px 8px; border-bottom: 1px solid #E2E8F0; border-right: 1px solid #EDF2F7; padding-left: 15px;"></td>
                                    <td style="padding: 9px 8px; text-align: right; border-bottom: 1px solid #E2E8F0;"></td>
                                </tr>
                                <tr style="background-color: #F8FAFC; font-weight: bold; border-top: 2px solid #E2E8F0;">
                                    <td style="padding: 12px 8px; color: #1F4E78; font-size: 14px;" colspan="2">Net Payable Salary:</td>
                                    <td style="padding: 12px 8px; text-align: right; color: #1F4E78; font-size: 15px; font-weight: 700;" colspan="2">Tk {net_final:,.2f}</td>
                                </tr>
                            </tbody>
                        </table>
                        
                        <div style="margin-top: 50px; display: flex; justify-content: flex-end;">
                            <div style="text-align: center; width: 190px; position: relative;">
                                {sig_html_element}
                                <div style="border-top: 1.5px solid #333; padding-top: 6px; font-size: 12px; font-weight: 600; color: #333; position: relative; z-index: 5; letter-spacing: 0.3px;">Authorized Signature</div>
                            </div>
                        </div>
                    </div>
                    """
                    st.components.v1.html(payslip_preview_html, height=560, scrolling=True)
                    
                    # PDF generation data updated to dict keys
                    pdf_emp_data = (
                        selected_emp['emp_id'], selected_emp['name'], selected_emp['designation'], 
                        selected_emp['category'], selected_emp['department'],
                        house_rent, medical, adv_paid, net_final
                    )
                    
                    pdf_buf = BytesIO()
                    generate_pdf_bytes(pdf_emp_data, full_month, rec['absent'], rec['fine'], rec['present'], pdf_buf)
                    st.download_button("📥 Download Pay Slip (PDF)", data=pdf_buf.getvalue(), file_name=f"PaySlip_{selected_emp['emp_id']}_{select_m}.pdf", mime="application/pdf", use_container_width=True)
   # --- TAB 2: ATTENDANCE & PROCESSOR ---
with tab2:
    view_cat = st.selectbox("Select Category to Process", ["Manager", "Officer", "Worker (Permanent)", "Worker (Daily Basis)"], key="att_sheet_cat")

    # ডাটা ফিল্টার করা (Supabase এর ডিকশনারি কী ব্যবহার করে)
    filtered_rows = [r for r in rows if r['category'] == view_cat]
    
    sheet_data = []
    if filtered_rows:
        with st.form("bulk_sheet_form_v5"):
            for r in filtered_rows:
                # ডিকশনারি কী ব্যবহার করে নাম ও পদবি দেখানো হচ্ছে
                st.markdown(f"**🔹 {r['emp_id']} - {r['name']}** ({r['designation']})")
                
                # অ্যাটেনডেন্স রেকর্ড ট্র্যাক করা
                rec = saved_db_tracker.get(str(r['emp_id']), {
                    "present": days_in_month if r['category'] == 'Worker (Daily Basis)' else 26, 
                    "absent": 0, "fine": 0.0, "ot_hrs": 0.0, "ot_rate": 0.0, "bonus": 0.0, "advance": 0.0
                })
                
                col_in1, col_in2, col_in3 = st.columns(3)
                with col_in1:
                    default_target = int(rec['present'] + rec['absent']) if rec['absent'] > 0 else (days_in_month if r['category'] == 'Worker (Daily Basis)' else max(26, int(rec['present'])))
                    total_target_days = st.number_input("Total Target Days", 1, 100, default_target, key=f"target_{r['emp_id']}")
                    a_d = st.number_input("Absent Days", 0, total_target_days, int(rec['absent']), key=f"a_{r['emp_id']}")
                    p_d = total_target_days - a_d
                    f_d = st.number_input("Penalty/Fine (Tk)", 0.0, value=float(rec['fine']), key=f"f_{r['emp_id']}")
                
                with col_in2:
                    ot_h = st.number_input("Overtime Hours", 0.0, 200.0, value=float(rec['ot_hrs']), key=f"oth_{r['emp_id']}")
                    ot_r = st.number_input("OT Rate per Hour (Tk)", 0.0, 1000.0, value=float(rec['ot_rate']), key=f"otr_{r['emp_id']}")
                
                with col_in3:
                    bonus_amt = st.number_input("Bonus Amount (Tk)", 0.0, 200000.0, value=float(rec['bonus']), key=f"bn_{r['emp_id']}")
                    adv_cut = st.number_input("Advanced Salary Cut (Tk)", 0.0, 200000.0, value=float(rec['advance']), key=f"adv_{r['emp_id']}")
                
                sheet_data.append({'eid': r['emp_id'], 'p': p_d, 'a': a_d, 'f': f_d, 'oth': ot_h, 'otr': ot_r, 'bonus': bonus_amt, 'adv': adv_cut})
                st.markdown("<hr style='margin:2px 0; border-color:#eee;'>", unsafe_allow_html=True)
            
            # সেভ করার আগে কনফার্মেশন
            confirm_save = st.checkbox(f"I intentionally want to save/overwrite data for **{full_month}**.")
            
            if st.form_submit_button("💾 Save Entry to Database", use_container_width=True, type="primary"):
                if not confirm_save:
                    st.error(f"❌ Please check the permission box to confirm saving data for **{full_month}**.")
                else:
                    # Supabase এ ডেটা সেভ করা (Upsert লজিক)
                    for item in sheet_data:
                        supabase.table("monthly_attendance_records").upsert({
                            "month_year": full_month,
                            "emp_id": item['eid'],
                            "present": item['p'],
                            "absent": item['a'],
                            "fine": item['f'],
                            "ot_hrs": item['oth'],
                            "ot_rate": item['otr'],
                            "bonus": item['bonus'],
                            "advance": item['adv']
                        }).execute()
                    st.success("✅ Records saved successfully to Supabase!")
                    st.rerun()

    else:
        st.info("No records found to process.")             
# --- MAIN SUMMARY SHEET WITH MATCHING ALIGNMENT FOR BULK VIEW ---
            print_html = f"""
            <div style="font-family: 'Segoe UI', 'Helvetica Neue', Arial, sans-serif; padding: 25px; background: white; color: black; border-radius: 12px;">
                <div style="text-align: center; margin-bottom: 25px; padding-bottom: 15px; border-bottom: 3px solid #1F4E78;">
                    {"<div style='margin-bottom: 5px; display: block;'><img src='data:image/png;base64," + logo_base64_str + "' style='max-height: 70px; width: auto; object-fit: contain; display: inline-block;' alt='RECON Logo'></div>" if logo_base64_str else ""}
                </div>
                
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px; width: 100%;">
                    <div style="width: 20%;"></div>
                    <div style="width: 60%; text-align: center;">
                        <span style="font-size: 17px; color: #1F4E78; font-weight: 700; text-transform: uppercase; letter-spacing: 0.8px;">Employee Monthly Payroll Statement Sheet</span>
                    </div>
                    <div style="width: 20%; text-align: right;">
                        <span style="font-size: 13px; color: #555; font-weight: 600; background-color: #f8f9fa; padding: 4px 10px; border-radius: 6px; border: 1px solid #e9ecef;">Period: {full_month}</span>
                    </div>
                </div>
            """

            categories_list = ["Manager", "Officer", "Worker (Permanent)", "Worker (Daily Basis)"]
            display_titles = ["💼 Managers Summary", "👔 Officers Summary", "🛠️ Workers (Permanent) Summary", "📆 Workers (Daily Basis) Summary"]
            
            has_any_data = False
            for cat_name, title_text in zip(categories_list, display_titles):
                cat_rows = [r for r in rows if r['category'] == cat_name]
                if not cat_rows: continue
                
                has_any_data = True
                print_html += f"""
                <h3 style="color: #1F4E78; border-left: 5px solid #1F4E78; padding-left: 10px; margin-top: 30px; margin-bottom: 12px; font-size: 16px; font-weight: 700;">{title_text}</h3>
                <div style="overflow-x: auto; max-width: 100%; box-shadow: 0 2px 5px rgba(0,0,0,0.02); border-radius: 6px;">
                    <table style="width: 100%; border-collapse: collapse; font-size: 12.5px; margin-bottom: 20px; background: white; min-width: 1150px;">
                        <thead>
                            <tr style="background-color: #1F4E78; color: white; text-align: center; font-weight: 600;">
                                <th style="border: 1px solid #dee2e6; padding: 8px;">ID</th>
                                <th style="border: 1px solid #dee2e6; padding: 8px; text-align: left; width: 15%;">Employee Name</th>
                                <th style="border: 1px solid #dee2e6; padding: 8px; text-align: left;">Department</th>
                                <th style="border: 1px solid #dee2e6; padding: 8px;">Base Pay</th>
                                <th style="border: 1px solid #dee2e6; padding: 8px;">H.Rent</th>
                                <th style="border: 1px solid #dee2e6; padding: 8px;">Medical</th>
                                <th style="border: 1px solid #dee2e6; padding: 8px;">P/A Days</th>
                                <th style="border: 1px solid #dee2e6; padding: 8px; color: #ffbcbc;">Abs Cut</th>
                                <th style="border: 1px solid #dee2e6; padding: 8px; color: #ffbcbc;">Fine</th>
                                <th style="border: 1px solid #dee2e6; padding: 8px; color: #b4ffb4;">OT Earn</th>
                                <th style="border: 1px solid #dee2e6; padding: 8px; color: #b4ffb4;">Bonus</th>
                                <th style="border: 1px solid #dee2e6; padding: 8px; color: #ffbcbc;">Adv Cut</th>
                                <th style="border: 1px solid #dee2e6; padding: 8px; background-color: #163654; font-weight: 700;">Net Payable</th>
                            </tr>
                        </thead>
                        <tbody>
                """
                
                for r in cat_rows:
                    eid, name, cat, dept, base_sal = r['emp_id'], r['name'], r['category'], r['department'], r['salary']
                    rec = saved_db_tracker.get(str(eid), {"present": days_in_month if cat == 'Worker (Daily Basis)' else 26, "absent": 0, "fine": 0.0, "ot_hrs": 0.0, "ot_rate": 0.0, "bonus": 0.0, "advance": 0.0})
                    
                    gross, house_rent, medical, _, ab_cut, net_p, adv_paid = calculate_salary_breakdown(base_sal, rec['absent'], rec['fine'], cat, rec['present'], rec['advance'])
                    ot_total = rec['ot_hrs'] * rec['ot_rate']
                    final_payable = net_p + ot_total + rec['bonus']
                    
