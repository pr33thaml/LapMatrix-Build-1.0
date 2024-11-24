import streamlit as st
from pymongo import MongoClient
import pandas as pd

# MongoDB connection
client = MongoClient("mongodb://localhost:27017/")  # MongoDB running on localhost
db = client["lapmatrix"]
employee_details_collection = db["employees"]

# Function to display Employee Overview with updated styling
def employee_overview():
    # Fetch employee data from MongoDB excluding Admin and HR roles
    employees = list(employee_details_collection.find({"role": {"$nin": ["Admin", "HR"]}}))

    if employees:
        # Convert MongoDB data to a DataFrame for better handling
        employee_data = pd.DataFrame(employees)

        # Ensure the 'allocated_laptop' and 'laptop_assigned' columns exist
        if 'allocated_laptop' not in employee_data.columns:
            employee_data['allocated_laptop'] = None
        if 'laptop_assigned' not in employee_data.columns:
            employee_data['laptop_assigned'] = False

        # Dashboard Title
        st.title("Employee Overview Dashboard")

        # Display Total Employees
        total_employees = len(employee_data)
        st.subheader(f"Total Employees: {total_employees}")

        # Show basic stats: Available, Allocated laptops, etc.
        allocated_laptops = len(employee_data[employee_data['laptop_assigned'] == True])
        available_employees = total_employees - allocated_laptops

        st.write(f"**Employees with Laptops Assigned**: {allocated_laptops}")
        st.write(f"**Employees without Laptops Assigned**: {available_employees}")

        # Create columns for employee cards using grid layout
        employee_columns = st.columns(3)

        for i, employee in enumerate(employee_data.itertuples(index=False)):
            with employee_columns[i % 3]:
                # Styled employee cards with background color changes
                laptop_name = employee.allocated_laptop if employee.laptop_assigned else "N/A"
                employee_card = f"""
                    <div style="background-color:#2f3640; border-radius:10px; padding:20px; margin:15px; box-shadow:0 6px 12px rgba(0, 0, 0, 0.1); border-left:6px solid { 'green' if employee.laptop_assigned else 'red' };">
                        <h5 style="color:white; font-size:18px; font-weight:600;">{getattr(employee, 'employee_name', 'N/A')}</h5>
                        <h6 style="color:white; font-size:16px;">{getattr(employee, 'position', 'N/A')}</h6>
                        <p style="font-size:14px; color:white;"><strong>Email:</strong> {getattr(employee, 'email', 'N/A')}</p>
                        <p style="font-size:14px; color:white;"><strong>Laptop Assigned:</strong> <span style="color:{'green' if employee.laptop_assigned else '#e74c3c'}; font-weight:600;">{'Yes' if employee.laptop_assigned else 'No'}</span></p>
                        <p style="font-size:14px; color:white;"><strong>Laptop Name:</strong> {laptop_name}</p>
                        <p style="font-size:14px; color:white;"><strong>Date Joined:</strong> {getattr(employee, 'date_of_joining', 'N/A')}</p>
                    </div>
                """
                st.markdown(employee_card, unsafe_allow_html=True)

    else:
        st.warning("No employee data found.")

# Call the function to display the dashboard
employee_overview()
