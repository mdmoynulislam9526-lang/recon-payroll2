import streamlit as st
import sqlite3
from datetime import datetime
import calendar
from io import BytesIO
import pandas as pd
import re
import os
import base64
from calculations import calculate_salary_breakdown, generate_pdf_bytes

st.set_page_config(page_title="RECON Payroll System", layout="wide", page_icon="💼")

# --- DATABASE INITIALIZATION ---
def init_db():
    conn = sqlite3.connect("payroll_v5.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS employees_final_version (
            emp_id TEXT PRIMARY KEY, name TEXT NOT NULL, designation TEXT NOT NULL,
            category TEXT NOT NULL, department TEXT NOT NULL, salary REAL NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS monthly_attendance_records (
            month_year TEXT, emp_id TEXT, present_days INTEGER, absent_days INTEGER, 
            fine_amount REAL, overtime_hours REAL, overtime_rate REAL, bonus_amount REAL, advance_cut REAL,
            PRIMARY KEY (month_year, emp_id)
        )
    """)
    conn.commit()
    conn.close()

init_db()

def get_db_connection():
    return sqlite3.connect("payroll_v5.db", check_same_thread=False)

# --- LOGO BASE64 CONVERSION ---
logo_base64_str = ""
current_dir = os.path.dirname(os.path.abspath(__file__))
local_logo_path = os.path.join(current_dir, "logo.png")
if os.path.exists(local_logo_path):
    with open(local_logo_path, "rb") as img_file:
        logo_base64_str = base64.b64encode(img_file.read()).decode('utf-8')

# --- LIVE REPO SIGNATURE LOADING ---
sig_base64_str = ""
local_sig_path = os.path.join(current_dir, "signature.png")
if os.path.exists(local_sig_path):
    with open(local_sig_path, "rb") as img_file:
        sig_base64_str = base64.b64encode(img_file.read()).decode('utf-8')

# --- LIVE REPO SEAL LOADING ---
seal_base64_str = ""
local_seal_path = os.path.join(current_dir, "seal.png")
if os.path.exists(local_seal_path):
    with open(local_seal_path, "rb") as img_file:
        seal_base64_str = base64.b64encode(img_file.read()).decode('utf-8')

# --- MAIN TITLE ---
st.title("💼 RECON LABORATORIES LTD - Advanced Payroll Management System")
st.markdown("---")

col1, col2 = st.columns([1, 2.3])

# --- LEFT SIDE: ADD EMPLOYEE ---
with col1:
    st.header("➕ Add New Person")
    
    if "emp_id_val" not in st.session_state: st.session_state.emp_id_val = ""
    if "name_val" not in st.session_state: st.session_state.name_val = ""
    if "desg_val" not in st.session_state: st.session_state.desg_val = ""
    if "salary_val" not in st.session_state: st.session_state.salary_val = ""

    with st.form("employee_form", clear_on_submit=True):
        input_id = st.text_input("ID (Numbers only, e.g., 101)", value=st.session_state.emp_id_val).strip()
        name = st.text_input("Name", value=st.session_state.name_val)
        department = st.selectbox("Select Department", [
            "Production", "Quality Control", "Development",
            "Maintenance", "Accounts & Finance", "HR & Admin", "Store & Inventory", "Sales & Marketing"
        ])
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
                st.error("⚠️ Invalid ID Format! ID must only contain numbers.")
            else:
                try:
                    conn = get_db_connection()
                    conn.cursor().execute("INSERT INTO employees_final_version VALUES (?, ?, ?, ?, ?, ?)",
                                   (input_id, name, designation, category, department, float(salary)))
                    conn.commit()
                    conn.close()
                    st.success(f"{name} successfully added!")
                    st.session_state.emp_id_val = ""
                    st.session_state.name_val = ""
                    st.session_state.desg_val = ""
                    st.session_state.salary_val = ""
                    st.rerun()
                except sqlite3.IntegrityError:
                    st.error(f"⚠️ Warning: Employee ID '{input_id}' already exists!")
                except ValueError: 
                    st.error("Salary must be a number!")

# --- REUSABLE FUNCTION FOR EDIT/DELETE ---
def render_inline_management(r, prefix=""):
    eid, ename, edesg, ecat, edept, esalary = r
    with st.container():
        col_info, col_act1, col_act2 = st.columns([3, 0.6, 0.6])
        with col_info:
            st.markdown(f"**[{eid}] {ename}** — {edesg} ({edept}) | Salary: Tk {esalary:,.2f}")
        with col_act1:
            if st.button("Edit 📝", key=f"{prefix}_edit_{eid}", use_container_width=True):
                st.session_state[f"emode_{prefix}_{eid}"] = True
        with col_act2:
            if st.button("Delete ❌", key=f"{prefix}_del_{eid}", use_container_width=True, type="secondary"):
                conn = get_db_connection()
                conn.cursor().execute("DELETE FROM employees_final_version WHERE emp_id=?", (eid,))
                conn.commit()
                conn.close()
                st.success("Deleted!")
                st.rerun()

        if st.session_state.get(f"emode_{prefix}_{eid}", False):
            with st.form(key=f"form_{prefix}_{eid}"):
                ch_name = st.text_input("Edit Name", value=ename)
                dept_list = ["Production", "Quality Control", "Development", "Maintenance", "Accounts & Finance", "HR & Admin", "Store & Inventory", "Sales & Marketing"]
                ch_dept = st.selectbox("Edit Department", dept_list, index=dept_list.index(edept) if edept in dept_list else 0)
                cat_list = ["Manager", "Officer", "Worker (Permanent)", "Worker (Daily Basis)"]
                ch_cat = st.selectbox("Edit Category", cat_list, index=cat_list.index(ecat) if ecat in cat_list else 0)
                ch_desg = st.text_input("Edit Designation", value=edesg)
                ch_salary = st.text_input("Edit Salary/Rate", value=str(esalary))
                
                b1, b2 = st.columns(2)
                with b1:
                    if st.form_submit_button("Save Changes", use_container_width=True):
                        conn = get_db_connection()
                        conn.cursor().execute("UPDATE employees_final_version SET name=?, designation=?, category=?, department=?, salary=? WHERE emp_id=?", (ch_name, ch_desg, ch_cat, ch_dept, float(ch_salary), eid))
                        conn.commit()
                        conn.close()
                        st.session_state[f"emode_{prefix}_{eid}"] = False
                        st.success("Updated!")
                        st.rerun()
                with b2:
                    if st.form_submit_button("Cancel", use_container_width=True):
                        st.session_state[f"emode_{prefix}_{eid}"] = False
                        st.rerun()
        st.markdown("<hr style='margin:4px 0px; border-color:#eee;'>", unsafe_allow_html=True)

# --- RIGHT SIDE: PAYROLL MANAGEMENT ---
with col2:
    conn = get_db_connection()
    rows = conn.cursor().execute("SELECT * FROM employees_final_version").fetchall()
    conn.close()
    
    if rows:
        months_list = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
        c_col1, c_col2 = st.columns(2)
        with c_col1: select_m = st.selectbox("Select Month", months_list, index=int(datetime.now().strftime("%m")) - 1)
        with c_col2: select_y = st.selectbox("Select Year", [str(y) for y in range(2024, 2031)], index=2)
        full_month = f"{select_m}, {select_y}"
        
        month_num = months_list.index(select_m) + 1
        days_in_month = calendar.monthrange(int(select_y), month_num)[1]
        
        conn = get_db_connection()
        db_records = conn.cursor().execute("SELECT * FROM monthly_attendance_records WHERE month_year=?", (full_month,)).fetchall()
        conn.close()
        
        saved_db_tracker = {str(r[1]): {"present": r[2], "absent": r[3], "fine": r[4], "ot_hrs": r[5], "ot_rate": r[6], "bonus": r[7], "advance": r[8]} for r in db_records}

        total_payout = 0.0
        for r in rows:
            eid, _, _, cat, _, base_sal = r
            rec = saved_db_tracker.get(str(eid), {"present": days_in_month if cat == 'Worker (Daily Basis)' else 26, "absent": 0, "fine": 0.0, "ot_hrs": 0.0, "ot_rate": 0.0, "bonus": 0.0, "advance": 0.0})
            
            _, _, _, _, _, net_p, _ = calculate_salary_breakdown(
                base_sal, rec['absent'], rec['fine'], cat, rec['present'], rec['advance']
            )
            ot_total = rec['ot_hrs'] * rec['ot_rate']
            final_payable = net_p + ot_total + rec['bonus']
            total_payout += final_payable

        st.markdown("### 📊 Financial Dashboard Summary")
        m_col1, m_col2 = st.columns(2)
        m_col1.metric("Total Employees", len(rows))
        m_col2.metric("Total Payout (Tk)", f"{total_payout:,.2f}")
        st.markdown("---")

        tab_emp, tab0, tab1, tab2 = st.tabs(["👥 All Employees", "🔍 Search Employee", "📄 Individual Pay Slip", "📊 Attendance & Payroll Processor"])
        
        with tab_emp:
            categories_map = {"💼 Managers": "Manager", "👔 Officers": "Officer", "🛠️ Workers (Permanent)": "Worker (Permanent)", "📆 Workers (Daily Basis)": "Worker (Daily Basis)"}
            for title, cat_value in categories_map.items():
                cat_members = [r for r in rows if r[3] == cat_value]
                with st.expander(f"{title} ({len(cat_members)})", expanded=False):
                    if not cat_members: st.info("No records.")
                    else:
                        for r in cat_members: render_inline_management(r, prefix="all_tab")

        with tab0:
            search_query = st.text_input("Enter Employee ID or Name to search", placeholder="Type here...", key="search_tab_input")
            if search_query:
                search_results = [r for r in rows if search_query.lower() in r[0].lower() or search_query.lower() in r[1].lower()]
                for emp in search_results: render_inline_management(emp, prefix="search_tab")

        # --- TAB 1: INDIVIDUAL PAY SLIP ---
        with tab1:
            pay_search = st.text_input("Enter Employee ID or Name for Pay Slip", key="pay_slip_search_input")
            if pay_search:
                pay_results = [r for r in rows if pay_search.lower() in r[0].lower() or pay_search.lower() in r[1].lower()]
                if pay_results:
                    selected_emp = pay_results[0]
                    rec = saved_db_tracker.get(str(selected_emp[0]), {"present": days_in_month if selected_emp[3] == 'Worker (Daily Basis)' else 26, "absent": 0, "fine": 0.0, "ot_hrs": 0.0, "ot_rate": 0.0, "bonus": 0.0, "advance": 0.0})
                    
                    st.success(f"Selected: {selected_emp[1]} ({selected_emp[0]})")
                    
                    gross, house_rent, medical, _, absent_cut, net_p, adv_paid = calculate_salary_breakdown(
                        selected_emp[5], rec['absent'], rec['fine'], selected_emp[3], rec['present'], rec['advance']
                    )
                    
                    total_ot = rec['ot_hrs'] * rec['ot_rate']
                    net_final = net_p + total_ot + rec['bonus']
                    
                    # সিগনেচার ও সিলের ইমেজ কন্ডিশনাল রেন্ডারিং এবং ওভারল্যাপিং স্টাইল
                    sig_html_element = ""
                    
                    # প্রথমে সিলটি নিচে ব্যাকগ্রাউন্ড হিসেবে বসবে
                    if seal_base64_str:
                        sig_html_element += f"<img src='data:image/png;base64,{seal_base64_str}' style='max-height: 75px; width: auto; display: block; margin: 0 auto -45px auto; z-index: 8; position: relative; opacity: 0.85;' alt='Seal'>"
                    
                    # সিগনেচারটি সিলের ওপরে ভাসবে
                    if sig_base64_str:
                        sig_html_element += f"<img src='data:image/png;base64,{sig_base64_str}' style='max-height: 60px; width: auto; display: block; margin: 0 auto -25px auto; z-index: 12; position: relative;' alt='Signature'>"
                    
                    if not sig_base64_str and not seal_base64_str:
                        sig_html_element = "<div style='height: 57px; color:#aaa; font-size:11px; padding-top:20px;'>[Images Not Found]</div>"

                    payslip_preview_html = f"""
                    <div style="font-family: 'Arial', sans-serif; padding: 25px; background: white; color: black; border: 1px solid #d9d9d9; border-radius: 8px; max-width: 650px; margin: 15px auto; box-sizing: border-box;">
                        <div style="text-align: center; border-bottom: 3px solid #1F4E78; padding-bottom: 12px; margin-bottom: 15px;">
                            {"<div style='margin-bottom: 10px; display: block;'><img src='data:image/png;base64," + logo_base64_str + "' style='max-height: 65px; width: auto; object-fit: contain; display: inline-block;' alt='RECON Logo'></div>" if logo_base64_str else ""}
                            <p style="margin: 5px 0 0 0; font-size: 13px; color: #1F4E78; font-weight: bold; text-transform: uppercase; letter-spacing: 0.5px;">Employee Pay Slip</p>
                            <span style="display: inline-block; margin-top: 4px; padding: 2px 10px; background: #E2EFDA; color: #375623; border-radius: 15px; font-size: 11px; font-weight: bold;">{full_month}</span>
                        </div>
                        <table style="width: 100%; font-size: 12px; border-collapse: collapse; margin-bottom: 15px;">
                            <tr>
                                <td style="padding: 4px 0; font-weight: bold; color: #555; width: 30%;">Employee ID:</td>
                                <td style="padding: 4px 0; font-weight: bold; color: #000;">{selected_emp[0]}</td>
                                <td style="padding: 4px 0; font-weight: bold; color: #555; width: 25%;">Department:</td>
                                <td style="padding: 4px 0; color: #000;">{selected_emp[4]}</td>
                            </tr>
                            <tr>
                                <td style="padding: 4px 0; font-weight: bold; color: #555;">Name:</td>
                                <td style="padding: 4px 0; font-weight: bold; color: #1F4E78;">{selected_emp[1]}</td>
                                <td style="padding: 4px 0; font-weight: bold; color: #555;">Designation:</td>
                                <td style="padding: 4px 0; color: #000;">{selected_emp[2]}</td>
                            </tr>
                            <tr>
                                <td style="padding: 4px 0; font-weight: bold; color: #555;">Category:</td>
                                <td style="padding: 4px 0; color: #000;">{selected_emp[3]}</td>
                                <td style="padding: 4px 0; font-weight: bold; color: #555;">Attendance:</td>
                                <td style="padding: 4px 0; font-weight: bold; color: #2F5597;">{rec['present']}P / {rec['absent']}A</td>
                            </tr>
                        </table>
                        
                        <table style="width: 100%; font-size: 12px; border-collapse: collapse; margin-bottom: 20px;">
                            <thead>
                                <tr style="background-color: #F2F4F7; border-top: 1px solid #ddd; border-bottom: 1px solid #ddd;">
                                    <th style="padding: 6px; text-align: left; color: #1F4E78;">Earnings</th>
                                    <th style="padding: 6px; text-align: right; color: #1F4E78; width: 25%;">Amount (Tk)</th>
                                    <th style="padding: 6px; text-align: left; color: #7F2020; padding-left: 15px;">Deductions</th>
                                    <th style="padding: 6px; text-align: right; color: #7F2020; width: 25%;">Amount (Tk)</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr>
                                    <td style="padding: 6px; border-bottom: 1px dashed #eee;">Base Pay</td>
                                    <td style="padding: 6px; text-align: right; border-bottom: 1px dashed #eee;">{gross:,.2f}</td>
                                    <td style="padding: 6px; border-bottom: 1px dashed #eee; padding-left: 15px; color: #c00;">Absent Cut</td>
                                    <td style="padding: 6px; text-align: right; border-bottom: 1px dashed #eee; color: #c00;">{absent_cut:,.2f}</td>
                                </tr>
                                <tr>
                                    <td style="padding: 6px; border-bottom: 1px dashed #eee; color: #555;">House Rent</td>
                                    <td style="padding: 6px; text-align: right; border-bottom: 1px dashed #eee; color: #555;">{house_rent:,.2f}</td>
                                    <td style="padding: 6px; border-bottom: 1px dashed #eee; padding-left: 15px; color: #c00;">Fine / Penalty</td>
                                    <td style="padding: 6px; text-align: right; border-bottom: 1px dashed #eee; color: #c00;">{rec['fine']:,.2f}</td>
                                </tr>
                                <tr>
                                    <td style="padding: 6px; border-bottom: 1px dashed #eee; color: #555;">Medical</td>
                                    <td style="padding: 6px; text-align: right; border-bottom: 1px dashed #eee; color: #555;">{medical:,.2f}</td>
                                    <td style="padding: 6px; border-bottom: 1px dashed #eee; padding-left: 15px; color: #c00;">Advance Cut</td>
                                    <td style="padding: 6px; text-align: right; border-bottom: 1px dashed #eee; color: #c00;">{adv_paid:,.2f}</td>
                                </tr>
                                <tr>
                                    <td style="padding: 6px; border-bottom: 1px dashed #eee; color: green;">Overtime ({rec['ot_hrs']} hrs)</td>
                                    <td style="padding: 6px; text-align: right; border-bottom: 1px dashed #eee; color: green;">{total_ot:,.2f}</td>
                                    <td style="padding: 6px; border-bottom: 1px dashed #eee; padding-left: 15px;"></td>
                                    <td style="padding: 6px; text-align: right; border-bottom: 1px dashed #eee;"></td>
                                </tr>
                                <tr>
                                    <td style="padding: 6px; border-bottom: 1px solid #ddd; color: green;">Bonus</td>
                                    <td style="padding: 6px; text-align: right; border-bottom: 1px solid #ddd; color: green;">{rec['bonus']:,.2f}</td>
                                    <td style="padding: 6px; border-bottom: 1px solid #ddd; padding-left: 15px;"></td>
                                    <td style="padding: 6px; text-align: right; border-bottom: 1px solid #ddd;"></td>
                                </tr>
                                <tr style="background-color: #F2F4F7; font-weight: bold;">
                                    <td style="padding: 8px 6px; color: #1F4E78;">Net Payable Salary:</td>
                                    <td style="padding: 8px 6px; text-align: right; color: #1F4E78; font-size: 13px;" colspan="3">Tk {net_final:,.2f}</td>
                                </tr>
                            </tbody>
                        </table>
                        
                        <div style="margin-top: 60px; display: flex; justify-content: flex-end;">
                            <div style="text-align: center; width: 180px; position: relative;">
                                {sig_html_element}
                                <div style="border-top: 1px solid #000; padding-top: 5px; font-size: 11px; font-weight: bold; color: #333; position: relative; z-index: 5;">Authorized Signature</div>
                            </div>
                        </div>
                    </div>
                    """
                    st.components.v1.html(payslip_preview_html, height=450, scrolling=True)
                    
                    pdf_emp_data = (
                        selected_emp[0], selected_emp[1], selected_emp[2], selected_emp[3], selected_emp[4],
                        house_rent, medical, adv_paid, net_final
                    )
                    
                    pdf_buf = BytesIO()
                    generate_pdf_bytes(pdf_emp_data, full_month, rec['absent'], rec['fine'], rec['present'], pdf_buf)
                    st.download_button("📥 Download Pay Slip (PDF)", data=pdf_buf.getvalue(), file_name=f"PaySlip_{selected_emp[0]}_{select_m}.pdf", mime="application/pdf", use_container_width=True)

        with tab2:
            view_cat = st.selectbox("Select Category to Process", ["Manager", "Officer", "Worker (Permanent)", "Worker (Daily Basis)"], key="att_sheet_cat")
            filtered_rows = [r for r in rows if r[3] == view_cat]
            
            sheet_data = []
            if filtered_rows:
                with st.form("bulk_sheet_form_v5"):
                    for r in filtered_rows:
                        st.markdown(f"**🔹 {r[0]} - {r[1]}** ({r[2]})")
                        rec = saved_db_tracker.get(str(r[0]), {"present": days_in_month if r[3] == 'Worker (Daily Basis)' else 26, "absent": 0, "fine": 0.0, "ot_hrs": 0.0, "ot_rate": 0.0, "bonus": 0.0, "advance": 0.0})
                        
                        col_in1, col_in2, col_in3 = st.columns(3)
                        with col_in1:
                            total_target_days = st.number_input("Total Target Days", 1, 100, int(rec['present'] + rec['absent']) if rec['absent'] > 0 else (days_in_month if r[3] == 'Worker (Daily Basis)' else max(26, int(rec['present']))), key=f"target_{r[0]}")
                            a_d = st.number_input("Absent Days", 0, total_target_days, int(rec['absent']), key=f"a_{r[0]}")
                            p_d = total_target_days - a_d
                            f_d = st.number_input("Penalty/Fine (Tk)", 0.0, value=float(rec['fine']), key=f"f_{r[0]}")
                        
                        with col_in2:
                            ot_h = st.number_input("Overtime Hours", 0.0, 200.0, value=float(rec['ot_hrs']), key=f"oth_{r[0]}")
                            ot_r = st.number_input("OT Rate per Hour (Tk)", 0.0, 1000.0, value=float(rec['ot_rate']), key=f"otr_{r[0]}")
                        
                        with col_in3:
                            bonus_amt = st.number_input("Bonus Amount (Tk)", 0.0, 200000.0, value=float(rec['bonus']), key=f"bn_{r[0]}")
                            adv_cut = st.number_input("Advanced Salary Cut (Tk)", 0.0, 200000.0, value=float(rec['advance']), key=f"adv_{r[0]}")
                        
                        sheet_data.append({'eid': r[0], 'p': p_d, 'a': a_d, 'f': f_d, 'oth': ot_h, 'otr': ot_r, 'bonus': bonus_amt, 'adv': adv_cut})
                        st.markdown("<hr style='margin:2px 0; border-color:#eee;'>", unsafe_allow_html=True)
                    
                    if st.form_submit_button("💾 Save Entry to Database", use_container_width=True, type="primary"):
                        conn = get_db_connection()
                        for item in sheet_data:
                            conn.cursor().execute("""
                                INSERT OR REPLACE INTO monthly_attendance_records VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, (full_month, item['eid'], item['p'], item['a'], item['f'], item['oth'], item['otr'], item['bonus'], item['adv']))
                        conn.commit()
                        conn.close()
                        st.success(f"Successfully saved records!")
                        st.rerun()

            # --- HTML/CSS PRINTABLE LEDGER SHEET SYSTEM ---
            st.markdown("---")
            st.markdown("### 🖨️ Print Preview Panel (Live Database Sheet)")

            print_html = f"""
            <div style="font-family: 'Arial', sans-serif; padding: 20px; background: white; color: black; border-radius: 8px;">
                <div style="text-align: center; border-bottom: 3px solid #1F4E78; padding-bottom: 14px; margin-bottom: 18px;">
                    {"<div style='margin-bottom: 10px; display: block;'><img src='data:image/png;base64," + logo_base64_str + "' style='max-height: 75px; width: auto; object-fit: contain; display: inline-block;' alt='RECON Logo'></div>" if logo_base64_str else ""}
                    <p style="margin: 8px 0 4px 0 !important; font-size: 14px !important; color: #1F4E78 !important; font-weight: bold !important; text-transform: uppercase !important; letter-spacing: 0.8px !important;">Employee Monthly Payroll Statement Sheet</p>
                    <span style="display: inline-block; margin-top: 4px; padding: 3px 14px; background: #E2EFDA; color: #375623; border-radius: 20px; font-size: 12px; font-weight: bold;">
                        Statement Period: {full_month}
                    </span>
                </div>
            """

            categories_list = ["Manager", "Officer", "Worker (Permanent)", "Worker (Daily Basis)"]
            display_titles = ["💼 Managers Summary", "👔 Officers Summary", "🛠️ Workers (Permanent) Summary", "📆 Workers (Daily Basis) Summary"]
            
            has_any_data = False
            for cat_name, title_text in zip(categories_list, display_titles):
                cat_rows = [r for r in rows if r[3] == cat_name]
                if not cat_rows: continue
                
                has_any_data = True
                print_html += f"""
                <h3 style="color: #2F5597; border-left: 5px solid #2F5597; padding-left: 8px; margin-top: 25px; margin-bottom: 10px; font-size: 16px;">{title_text}</h3>
                <div style="overflow-x: auto; max-width: 100%;">
                    <table style="width: 100%; border-collapse: collapse; font-size: 12px; margin-bottom: 15px; background: white; min-width: 1100px;">
                        <thead>
                            <tr style="background-color: #2F5597; color: white; text-align: center;">
                                <th style="border: 1px solid #A6A6A6; padding: 6px;">ID</th>
                                <th style="border: 1px solid #A6A6A6; padding: 6px; text-align: left;">Employee Name</th>
                                <th style="border: 1px solid #A6A6A6; padding: 6px; text-align: left;">Department</th>
                                <th style="border: 1px solid #A6A6A6; padding: 6px;">Base Pay</th>
                                <th style="border: 1px solid #A6A6A6; padding: 6px;">H.Rent</th>
                                <th style="border: 1px solid #A6A6A6; padding: 6px;">Medical</th>
                                <th style="border: 1px solid #A6A6A6; padding: 6px;">P/A Days</th>
                                <th style="border: 1px solid #A6A6A6; padding: 6px;">Abs Cut</th>
                                <th style="border: 1px solid #A6A6A6; padding: 6px;">Fine</th>
                                <th style="border: 1px solid #A6A6A6; padding: 6px;">OT Earn</th>
                                <th style="border: 1px solid #A6A6A6; padding: 6px;">Bonus</th>
                                <th style="border: 1px solid #A6A6A6; padding: 6px;">Adv Cut</th>
                                <th style="border: 1px solid #A6A6A6; padding: 6px; background-color: #1F4E78;">Net Payable</th>
                            </tr>
                        </thead>
                        <tbody>
                """
                
                for r in cat_rows:
                    eid, name, desg, cat, dept, base_sal = r
                    rec = saved_db_tracker.get(str(eid), {"present": days_in_month if cat == 'Worker (Daily Basis)' else 26, "absent": 0, "fine": 0.0, "ot_hrs": 0.0, "ot_rate": 0.0, "bonus": 0.0, "advance": 0.0})
                    
                    gross, house_rent, medical, _, ab_cut, net_p, adv_paid = calculate_salary_breakdown(base_sal, rec['absent'], rec['fine'], cat, rec['present'], rec['advance'])
                    ot_total = rec['ot_hrs'] * rec['ot_rate']
                    final_payable = net_p + ot_total + rec['bonus']
                    
                    print_html += f"""
                            <tr style="text-align: center; background-color: white;">
                                <td style="border: 1px solid #D9D9D9; padding: 5px; font-weight: bold;">{str(eid)}</td>
                                <td style="border: 1px solid #D9D9D9; padding: 5px; text-align: left; font-weight: bold;">{name}</td>
                                <td style="border: 1px solid #D9D9D9; padding: 5px; text-align: left;">{dept}</td>
                                <td style="border: 1px solid #D9D9D9; padding: 5px; text-align: right;">{base_sal:,.2f}</td>
                                <td style="border: 1px solid #D9D9D9; padding: 5px; text-align: right; color: #555;">{house_rent:,.2f}</td>
                                <td style="border: 1px solid #D9D9D9; padding: 5px; text-align: right; color: #555;">{medical:,.2f}</td>
                                <td style="border: 1px solid #D9D9D9; padding: 5px;">{rec['present']}P / {rec['absent']}A</td>
                                <td style="border: 1px solid #D9D9D9; padding: 5px; text-align: right; color: red;">{ab_cut:,.2f}</td>
                                <td style="border: 1px solid #D9D9D9; padding: 5px; text-align: right; color: red;">{rec['fine']:,.2f}</td>
                                <td style="border: 1px solid #D9D9D9; padding: 5px; text-align: right; color: green;">{ot_total:,.2f}</td>
                                <td style="border: 1px solid #D9D9D9; padding: 5px; text-align: right; color: green;">{rec['bonus']:,.2f}</td>
                                <td style="border: 1px solid #D9D9D9; padding: 5px; text-align: right; color: red;">{adv_paid:,.2f}</td>
                                <td style="border: 1px solid #D9D9D9; padding: 5px; text-align: right; font-weight: bold; color: #1F4E78; background-color: #F2F4F7;">{final_payable:,.2f}</td>
                            </tr>
                    """
                print_html += "</tbody></table></div>"
            print_html += "</div>"

            if has_any_data:
                st.components.v1.html(print_html, height=600, scrolling=True)
                if st.button("🖨️ CLICK HERE TO PRINT THIS FULL SHEET", use_container_width=True, type="primary"):
                    st.components.v1.html(f"{print_html}<script>window.print();</script>", height=0)
            else:
                st.info("No records loaded yet.")
                
    else: st.info("Database is empty. Please add people from the left panel.")
