import re
import streamlit as st
from components.utils import generate_password, send_email
from pymongo import MongoClient
import pandas as pd
from datetime import datetime


# Connect to MongoDB (Assuming MongoDB is running locally)
client = MongoClient("mongodb://localhost:27017/")
db = client["lapmatrix"]
employee_details_collection = db["employees"]
data = pd.read_csv(r'C:\Users\Maverick\Documents\College\Project\Lap_Rec\data\train_laptops.csv')

# Regular expression for validating an email address
def is_valid_email(email: str) -> bool:
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(email_regex, email) is not None

# Regular expression for validating employee ID format (must be either 3 digits or 3 letters)
def is_valid_employee_id(employee_id: str) -> bool:
    # Employee ID should be either 3 digits or 3 alphabetic characters
    employee_id_regex = r'^[0-9]{3}$|^[a-zA-Z]{3}$'
    return re.match(employee_id_regex, employee_id) is not None

def onboarding_page():
    st.subheader("Employee Onboarding")

    # Input fields for employee details
    employee_name = st.text_input("Employee Name")
    employee_id = st.text_input("Employee ID")
    email = st.text_input("Employee Email")

    # Role dropdown: HR or Employee
    roles = ["HR", "Employee"]
    role = st.selectbox("Select Role", roles)

    # Fetch roles for the position from the CSV
    positions = data['Role'].unique().tolist()  # Get all unique roles from the 'Role' column
    position = st.selectbox("Select Position", positions)

    # Check if the employee ID format is valid
    if employee_id:
        if not is_valid_employee_id(employee_id):
            st.error("Employee ID must be 3 digits (e.g., 001) or 3 letters (e.g., ABC).")
            return

        # Check if the employee ID already exists in the database
        existing_employee = employee_details_collection.find_one({"employee_id": employee_id})
        if existing_employee:
            st.error(f"Employee ID {employee_id} is already taken. Please use a different ID.")
            return

    # Check if email is valid and unique
    if email:
        if not is_valid_email(email):
            st.error("Please enter a valid email address.")
            return
        existing_email = employee_details_collection.find_one({"email": email})
        if existing_email:
            st.error(f"The email address {email} is already associated with another employee. Please use a different email.")
            return

    if st.button("Submit Details"):
        if employee_name and employee_id and email and role and position:
            # Generate random password
            password = generate_password()

            # Create username based on employee's name (can be customized)
            username = employee_name.lower().replace(" ", "_")  # Example: john_doe

            # Get current date for date_of_joining
            date_of_joining = datetime.now().strftime("%Y-%m-%d")

            # Create employee data with username, password, role, position, and date of joining
            employee_data = {
                "employee_name": employee_name,
                "employee_id": employee_id,
                "role": role,  # Storing the role as either HR or Employee
                "position": position,  # Storing the position
                "email": email,
                "password": password,  # Store password securely (hashed in real-world apps)
                "username": username,   # Store the username
                "status": "Active",
                "laptop_assigned": False,  # Default laptop_assigned value set to False
                "date_of_joining": date_of_joining  # Added date of joining
            }

            # Insert employee data into the database
            employee_details_collection.insert_one(employee_data)
            st.success(f"Employee {employee_name} has been onboarded successfully!")

            # Send email with password and webapp link
            subject = "Welcome to LapMatrix - Onboarding Details"
            body = f"""
            Hello {employee_name},

            Welcome to the team! We are excited to have you onboard.

            Here are your login credentials:
            Web app link: [Your web app link here]
            Username: {username}
            Password: {password}

            Please change your password after your first login.

            Best Regards,
            LapMatrix Team
            """
            send_email(email, subject, body)
        else:
            st.error("Please fill in all the fields.")


# Offboarding Page: Admin/HR manages employee offboarding
# Offboarding Page: Admin/HR manages employee offboarding
def offboarding_page():
    st.subheader("Employee Offboarding")

    # Get list of employees who are still active
    employees = list(employee_details_collection.find({"status": "Active"}))
    employee_ids = [emp['employee_id'] for emp in employees]

    # Allow admin to select the employee for offboarding
    employee_id = st.selectbox("Select Employee ID to Offboard", employee_ids)
    
    if employee_id:
        employee = employee_details_collection.find_one({"employee_id": employee_id})
        
        st.write(f"Employee Name: {employee['employee_name']}")
        st.write(f"Position: {employee.get('position', 'N/A')}")  # Display position instead of department
        
        if st.button("Offboard Employee"):
            # Delete the employee record from the database
            employee_details_collection.delete_one({"employee_id": employee_id})
            
            # Notify the user of the success
            st.success(f"Employee {employee['employee_name']} has been offboarded and removed from the system.")
            
            # Refresh the page to update the employee list
            st.session_state.offboarded_employee = employee_id  # Save offboarding state
            st.rerun()  # Refresh the page to reflect the changes