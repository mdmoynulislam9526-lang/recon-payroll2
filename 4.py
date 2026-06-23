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
                  
