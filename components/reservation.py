import streamlit as st
from datetime import date
import pandas as pd
from pymongo import MongoClient

# MongoDB connection
client = MongoClient("mongodb://localhost:27017/")  # MongoDB running on localhost
db = client["lapmatrix"]
reservations_collection = db["reservations"]

# Load laptops from CSV
def load_laptops_from_csv(csv_file):
    df = pd.read_csv(csv_file)
    return df['Recommended Laptop'].drop_duplicates().tolist()  # Assuming the CSV has a 'laptop_model' column

# Reservation System
def reservation_system():
    st.subheader("Laptop Reservation")
    today = date.today()

    # Load laptops from CSV
    all_laptops = load_laptops_from_csv('data/train_laptops.csv')  # Change the path if needed

    # Remove expired reservations
    reservations = list(reservations_collection.find())
    for reservation in reservations:
        if reservation["reservation_date"] < today.isoformat():
            reservations_collection.delete_one({"_id": reservation["_id"]})

    # Fetch reserved laptops
    reserved_laptops = reservations_collection.distinct("laptop_model")
    available_laptops = [laptop for laptop in all_laptops if laptop not in reserved_laptops]

    # Display Available Laptops (Dropdown)
    if available_laptops:
        st.markdown("### Available Laptops")
        laptop_model = st.selectbox("Select Laptop to Reserve", available_laptops)
        reservation_date = st.date_input("Reservation Date")

        if st.button("Reserve"):
            if laptop_model in reserved_laptops:
                st.error(f"Sorry, {laptop_model} is already reserved. Please select another laptop.")
            else:
                # Add reservation to MongoDB
                reservation = {
                    "laptop_model": laptop_model,
                    "reservation_date": reservation_date.isoformat(),  # Ensure it's stored as ISO format string
                    "status": "Reserved"
                }
                reservations_collection.insert_one(reservation)
                st.success(f"{laptop_model} has been reserved successfully until {reservation_date.isoformat()}!")
                
                # Trigger a page refresh to show the updated reservation status
                st.rerun()  # This will reload the page and reflect the changes

    else:
        st.warning("No laptops are available for reservation at the moment.")

    # Display Reserved Laptops in Grid Layout with Color Coding
    st.markdown("### Reserved Laptops")
    if reserved_laptops:
        reserved_columns = st.columns(3)  # Adjust the number based on how many laptops to display per row
        for i, laptop in enumerate(reserved_laptops):
            res = reservations_collection.find_one({"laptop_model": laptop})
            with reserved_columns[i % 3]:  # Dynamically creates the grid
                st.markdown(
                    f"**{laptop}** (Reserved until: {res['reservation_date']})",
                    unsafe_allow_html=True
                )
                st.markdown(f'<p style="color:red;">Reserved</p>', unsafe_allow_html=True)  # Red color for reserved
    else:
        st.write("No laptops are currently reserved.")

    # Display All Laptops (With Reservation Status) in Grid Format
    st.markdown("### All Laptops in the System")
    laptop_columns = st.columns(3)  # Display laptops in 3 columns per row
    for i, laptop in enumerate(all_laptops):
        if laptop in reserved_laptops:
            res = reservations_collection.find_one({"laptop_model": laptop})
            with laptop_columns[i % 3]:  # Dynamically creates the grid
                st.markdown(
                    f"**{laptop}** (Reserved until: {res['reservation_date']})",
                    unsafe_allow_html=True
                )
                st.markdown(f'<p style="color:red;">Reserved</p>', unsafe_allow_html=True)  # Red color for reserved
        else:
            with laptop_columns[i % 3]:
                st.markdown(f"**{laptop}** (Available for Reservation)", unsafe_allow_html=True)
                st.markdown(f'<p style="color:#00FF00;">Available</p>', unsafe_allow_html=True)  # Bright green color for available

    # Add override option for HR/Admin at the bottom
    role = st.session_state.get("role", "Employee")
    if role in ["HR", "admin"]:
        st.markdown("### Override Reservation")
        laptop_to_override = st.selectbox("Select Laptop to Remove from System", reserved_laptops)

        # Warning message for override
        if laptop_to_override:
            st.warning("**Warning: This will revoke the reservation. Only override in emergency.**")
            
            # Confirmation buttons
            col1, col2 = st.columns([1, 1])
            with col1:
                if st.button(f"Yes, Remove {laptop_to_override}"):
                    # Remove the laptop from reservations collection
                    reservations_collection.delete_one({"laptop_model": laptop_to_override})
                    st.success(f"The laptop {laptop_to_override} has been permanently removed from the system.")
                    # Trigger a page refresh to show updated reservation status
                    st.rerun()  # This will reload the page and reflect the changes

            with col2:
                if st.button("No, Cancel"):
                    st.warning("Laptop removal has been cancelled.")
