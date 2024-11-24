import streamlit as st
from pymongo import MongoClient
import time
import psutil
import platform
from streamlit import components  
import pandas as pd
import plotly.express as px
import platform
import calendar
import screeninfo
from datetime import datetime, timedelta
from components.utils import authenticate, send_email, generate_password
from components.reservation import reservation_system
from components.recommendation import get_closest_laptop, get_data, get_roles  # Import functions from recommendation.py
from components.employee_management import onboarding_page, offboarding_page 
from components.ticketing_system import get_tickets, filter_tickets, update_ticket
from components.login import login_page
from components.employee_overview import employee_overview
from components.apps import apps
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from screeninfo import get_monitors

# MongoDB connection
client = MongoClient("mongodb://localhost:27017/")  # MongoDB running on localhost
db = client["lapmatrix"]

tickets_collection = db["tickets"]
laptops_collection = db["laptops"]
reservations_collection = db["reservations"]
employee_details_collection = db["employees"]
available_laptops_collection = db['available_laptops']

maintenance_date = datetime(2024, 12, 15)
current_date = datetime.now()
# Calculate the number of days remaining
days_left = (maintenance_date - current_date).days

# Function to load laptops from a CSV file
def load_laptops_from_csv(csv_file):
    import pandas as pd
    df = pd.read_csv(csv_file)
    return df['Recommended Laptop'].drop_duplicates().tolist()  # Adjust column name if needed

def get_system_info():
    # Basic system information
    system_info = {}
    system_info['Laptop Name'] = platform.node()
    system_info['OS'] = platform.system()
    system_info['OS Version'] = platform.version()
    system_info['CPU'] = platform.processor()
    system_info['CPU Cores'] = psutil.cpu_count(logical=False)
    system_info['RAM'] = round(psutil.virtual_memory().total / (1024 ** 3))  # GB
    system_info['Storage'] = round(psutil.disk_usage('/').total / (1024 ** 3))  # GB
    system_info['CPU Usage'] = psutil.cpu_percent(interval=1)
    system_info['RAM Usage'] = psutil.virtual_memory().percent
    system_info['Storage Usage'] = psutil.disk_usage('/').percent
    
    # Add Screen info
    screens = get_monitors()
    system_info['Screen Resolution'] = f"{screens[0].width}x{screens[0].height}" if screens else "N/A"
    
    return system_info

def diagnose_system(system_info):
    # Heuristic diagnostics based on system info (can be replaced by ML models)
    diagnostics = []
    
    # Check for high CPU usage
    if system_info['CPU Usage'] > 85:
        diagnostics.append("High CPU Usage: Consider closing unnecessary applications.")
        
    # Check for high RAM usage
    if system_info['RAM Usage'] > 85:
        diagnostics.append("High RAM Usage: Consider closing applications or upgrading RAM.")
        
    # Check for low storage space
    if system_info['Storage Usage'] > 85:
        diagnostics.append("Low Storage Space: Free up space or consider upgrading your storage.")
    
    return diagnostics

def fetch_available_laptops():
    return list(available_laptops_collection.find({"status": "Available"}))

def find_similar_laptops(cpu_speed, ram, storage, available_laptops):
    similar_laptops = []
    for laptop in available_laptops:
        # Compare specs using tolerances
        if (laptop['cpu_speed'] >= cpu_speed - 0.5 and laptop['cpu_speed'] <= cpu_speed + 0.5) and \
           (laptop['ram'] >= ram - 4 and laptop['ram'] <= ram + 4) and \
           (laptop['storage'] >= storage - 128 and laptop['storage'] <= storage + 128):
            similar_laptops.append(laptop)
    return similar_laptops[:3]  # Return only top 3 similar laptops

def allocate_laptop_to_employee(laptop_model, employee_id):
    """
    Allocates a laptop to an employee by updating the database.

    Args:
        laptop_model (str): The model of the laptop to allocate.
        employee_id (str): The ID of the employee receiving the laptop.
    """
    try:
        # Update the employee record to assign the laptop
        employee_details_collection.update_one(
            {"employee_id": employee_id},
            {"$set": {"laptop_assigned": True, "allocated_laptop": laptop_model}}
        )

        # Send an email notification to the employee
        employee = employee_details_collection.find_one({"employee_id": employee_id})
        send_email(
            employee['email'],
            "Laptop Allocation",
            f"Laptop '{laptop_model}' has been allocated to you."
        )
        st.success(f"Laptop '{laptop_model}' successfully allocated to Employee ID: {employee_id}")
    except Exception as e:
        st.error(f"Failed to allocate laptop: {e}")

# Authentication check
if "authenticated" not in st.session_state or not st.session_state["authenticated"]:
    login_page()
else:
    # Sidebar and role setup
    role = st.session_state.get("role", "Employee")
        # Dynamic title based on role
    if role in ["HR", "admin"]:
        # Title for Admin role
        st.sidebar.title("LapMatrix")
        st.sidebar.markdown("### Admin-Dashboard")  # Adds the "Admin-Dashboard" below "LapMatrix"
    elif role == "Employee":
        # Title for Employee role
        st.sidebar.title("LapMatrix")
        st.sidebar.markdown("### E-Dashboard")

    if role in ["HR", "admin"]:
        option = st.sidebar.radio("Choose an Option", [
            "Laptop Recommendation",
            "Onboarding/Offboarding",
            "Reservation System",
            "Ticketing System",
            "Employee Overview",
        ])
    elif role == "Employee":
        option = st.sidebar.radio("Choose an Option", [
            "System Info",
            "Drivers and Downloads",
            "Raise a Ticket",
            "Request Upgrade",
            "Laptop Maintenance"
        ])
    else:
        st.sidebar.error("Unknown role detected.")

    # Fetch data and roles
    data = get_data()
    roles = get_roles()

    if option == "Laptop Recommendation" and role in ["HR", "admin"]:
        st.title("Laptop Recommendation & Allocation")

        # Laptop recommendation sliders
        selected_role = st.selectbox("Select Role", roles)
        role_specs = data[data['Role'] == selected_role].iloc[0]

        cpu_speed = st.slider("CPU Speed (GHz)", 1.0, 5.0, role_specs['Required CPU Speed (GHz)'])
        ram = st.slider("RAM (GB)", 4, 64, int(role_specs['Required RAM (GB)']))
        storage = st.slider("Storage (GB)", 128, 2048, int(role_specs['Required Storage (GB)']))

        if st.button("Get Recommendation"):
            available_laptops = fetch_available_laptops()
            recommended_laptop = get_closest_laptop(cpu_speed, ram, storage)
            st.session_state.recommended_laptop = recommended_laptop
            st.session_state.laptop_recommended = True

            # Fetch similar laptops
            similar_laptops = find_similar_laptops(cpu_speed, ram, storage, available_laptops)
            st.session_state.similar_laptops = similar_laptops
            st.session_state.cpu_speed = cpu_speed
            st.session_state.ram = ram
            st.session_state.storage = storage

            st.rerun()  # Refresh the page after clicking the button

        if st.session_state.get("laptop_recommended", False):
            recommended_laptop = st.session_state["recommended_laptop"]
            similar_laptops = st.session_state.get("similar_laptops", [])

            # Display recommended laptop or alternatives
            reserved_laptops = reservations_collection.distinct("laptop_model")
            if recommended_laptop in reserved_laptops:
                st.warning(f"The recommended laptop '{recommended_laptop}' is reserved.")
                if similar_laptops:
                    st.subheader("Similar Laptops Available:")
                    for idx, laptop in enumerate(similar_laptops):
                        st.write(f"**{laptop['laptop_model']}** | CPU: {laptop['cpu_speed']} GHz | RAM: {laptop['ram']} GB | Storage: {laptop['storage']} GB")

                        # Capture employee for allocation
                        available_employees = list(employee_details_collection.find({
                            "laptop_assigned": {"$in": [False, "False"]}
                        }))

                        if available_employees:
                            employee_names = {emp['employee_name']: emp['employee_id'] for emp in available_employees}
                            selected_employee_name = st.selectbox(
                                f"Select Employee for {laptop['laptop_model']} (Option {idx+1})",
                                list(employee_names.keys()),
                                key=f"employee_select_{idx}"
                            )
                            selected_employee_id = employee_names[selected_employee_name]

                            selected_employee = next((emp for emp in available_employees if emp['employee_id'] == selected_employee_id), None)
                            if selected_employee:
                                st.write(f"**Selected Employee:** {selected_employee_name}")
                                st.write(f"**Position:** {selected_employee.get('position', 'N/A')}")

                            if st.button(f"Allocate {laptop['laptop_model']} to {selected_employee_name}", key=f"allocate_btn_{idx}"):
                                allocate_laptop_to_employee(laptop['laptop_model'], selected_employee_id)
                                st.success(f"Laptop '{laptop['laptop_model']}' allocated to {selected_employee_name}.")
                        else:
                            st.warning("No employees without laptops found.")
            else:
                st.success(f"Laptop '{recommended_laptop}' is available.")
                available_employees = list(employee_details_collection.find({
                    "laptop_assigned": {"$in": [False, "False"]}
                }))

                if available_employees:
                    employee_names = {emp['employee_name']: emp['employee_id'] for emp in available_employees}
                    selected_employee_name = st.selectbox("Select Employee", list(employee_names.keys()))

                    if selected_employee_name:
                        selected_employee_id = employee_names[selected_employee_name]
                        selected_employee = next((emp for emp in available_employees if emp['employee_id'] == selected_employee_id), None)
                        st.write(f"**Selected Employee:** {selected_employee_name}")
                        st.write(f"**Position:** {selected_employee.get('position', 'N/A')}")

                        if st.button(f"Allocate '{recommended_laptop}' to {selected_employee_name}"):
                            allocate_laptop_to_employee(recommended_laptop, selected_employee_id)
                else:
                    st.warning("No employees without laptops found.")

    elif option == "Reservation System" and role in ["HR", "admin"]:
        reservation_system()
    
    elif option == "Employee Overview":
        employee_overview()

    elif option == "Ticketing System" and role in ["HR", "admin"]:
        st.subheader("Ticketing Dashboard")

        # Load tickets from the database
        tickets = get_tickets()  # Get all tickets from MongoDB

        # Filter tickets (optional)
        status_filter = st.selectbox('Filter by Status', ['All', 'Open', 'In Progress', 'Closed'])
        priority_filter = st.selectbox('Filter by Priority', ['All', 'High', 'Medium', 'Low'])

        # Apply filters if not 'All'
        if status_filter != 'All':
            tickets = filter_tickets(status=status_filter)

        if priority_filter != 'All':
            tickets = filter_tickets(priority=priority_filter)

        # Display tickets in a card layout
        st.markdown("### Active Tickets")
        ticket_columns = st.columns(3)

        for i, ticket in enumerate(tickets.to_dict(orient='records')):  # Convert to dict for easy use in the loop
            ticket_id = str(ticket['_id'])[:8]  # Safely convert ObjectId to string and shorten it

            with ticket_columns[i % 3]:
                ticket_card = f"""
                    <div style="background-color:#2c2f3f; border-radius:10px; padding:20px; margin:15px; box-shadow:0 6px 12px rgba(0, 0, 0, 0.1); border-left:6px solid { 'green' if ticket['status'] == 'Closed' else 'orange' if ticket['status'] == 'In Progress' else 'red' };">
                        <h5 style="color:white; font-size:18px; font-weight:600;">Ticket ID: {ticket_id}</h5>
                        <h6 style="color:white; font-size:16px;">Subject: {ticket['subject']}</h6>
                        <p style="font-size:14px; color:white;"><strong>Status:</strong> <span style="color:{'green' if ticket['status'] == 'Closed' else 'orange' if ticket['status'] == 'In Progress' else '#e74c3c'}; font-weight:600;">{ticket['status']}</span></p>
                        <p style="font-size:14px; color:white;"><strong>Priority:</strong> <span style="color:{'red' if ticket['priority'] == 'High' else '#f39c12' if ticket['priority'] == 'Medium' else '#27ae60'}; font-weight:600;">{ticket['priority']}</span></p>
                    </div>
                """
                st.markdown(ticket_card, unsafe_allow_html=True)

                # Add a dropdown to allow HR to change the status
                with st.expander(f"Details for Ticket {ticket_id}"):
                    st.write(f"**Status**: {ticket['status']}")
                    st.write(f"**Priority**: {ticket['priority']}")
                    st.write(f"**Description**: {ticket['details']}")
                    
                    new_status = st.radio("Update Ticket Status", ["In Progress", "Closed"], key=ticket_id)

                    if st.button("Update Ticket", key=f"update-{ticket_id}"):
                        if new_status:
                            update_ticket(ticket['_id'], new_status, ticket['priority'], ticket['details'])
                            st.success(f"Ticket {ticket_id} status updated to {new_status}.")
                            st.rerun()

    elif option == "System Info" and role == "Employee":
        st.title("System Information")
        system_info = get_system_info()
        
        # Display system information
        laptop_card = f"""
        <div style="background-color:#2c2f3f; border-radius:10px; padding:20px; margin:15px; box-shadow:0 6px 12px rgba(0, 0, 0, 0.1);">
            <h2 style="color:white; font-size:22px; font-weight:600; margin-bottom:20px;">System Specifications</h2>
            <table style="width:100%; font-size:16px; color:white;">
                <tr>
                    <td style="font-weight:600; padding:8px;">Laptop Name</td>
                    <td style="padding:8px; color:#1abc9c;">{system_info['Laptop Name']}</td>
                </tr>
                <tr>
                    <td style="font-weight:600; padding:8px;">Operating System</td>
                    <td style="padding:8px; color:#1abc9c;">{system_info['OS']} {system_info['OS Version']}</td>
                </tr>
                <tr>
                    <td style="font-weight:600; padding:8px;">Processor</td>
                    <td style="padding:8px; color:#e67e22;">{system_info['CPU']}</td>
                </tr>
                <tr>
                    <td style="font-weight:600; padding:8px;">CPU Cores</td>
                    <td style="padding:8px; color:#3498db;">{system_info['CPU Cores']}</td>
                </tr>
                <tr>
                    <td style="font-weight:600; padding:8px;">RAM</td>
                    <td style="padding:8px; color:#9b59b6;">{system_info['RAM']} GB</td>
                </tr>
                <tr>
                    <td style="font-weight:600; padding:8px;">Storage</td>
                    <td style="padding:8px; color:#f1c40f;">{system_info['Storage']} GB</td>
                </tr>
                <tr>
                    <td style="font-weight:600; padding:8px;">CPU Usage</td>
                    <td style="padding:8px; color:#f1c40f;">{system_info['CPU Usage']}%</td>
                </tr>
                <tr>
                    <td style="font-weight:600; padding:8px;">RAM Usage</td>
                    <td style="padding:8px; color:#f1c40f;">{system_info['RAM Usage']}%</td>
                </tr>
                <tr>
                    <td style="font-weight:600; padding:8px;">Storage Usage</td>
                    <td style="padding:8px; color:#f1c40f;">{system_info['Storage Usage']}%</td>
                </tr>
                <tr>
                    <td style="font-weight:600; padding:8px;">Screen Resolution</td>
                    <td style="padding:8px; color:#9b59b6;">{system_info['Screen Resolution']}</td>
                </tr>
            </table>
        </div>
        """
        st.markdown(laptop_card, unsafe_allow_html=True)
        
        # Show system diagnostics
        diagnostics = diagnose_system(system_info)
        if diagnostics:
            st.subheader("Diagnostics:")
            for diag in diagnostics:
                st.markdown(f"- {diag}")
        
        # Optional: Adding a visual representation of resource utilization
        utilization_data = {
            "Component": ["CPU", "RAM", "Storage"],
            "Utilized": [system_info["CPU Usage"], system_info["RAM Usage"], system_info["Storage Usage"]],
            "Maximum": [100, 100, 100],
        }
        df = pd.DataFrame(utilization_data)

        fig = px.bar(
            df,
            x="Component",
            y="Utilized",
            color="Component",
            text="Utilized",
            title="Utilization Overview",
            labels={"Utilized": "Utilized (%)"},
            color_discrete_sequence=["#1abc9c", "#e67e22", "#3498db"],
        )
        fig.update_layout(
            title_font=dict(size=20, color="white"),
            font=dict(size=14, color="white"),
            plot_bgcolor="#2c2f3f",
            paper_bgcolor="#2c2f3f",
            xaxis=dict(title="", showgrid=False, color="white"),
            yaxis=dict(showgrid=True, color="white"),
        )
        st.plotly_chart(fig)

    elif option == "Drivers and Downloads" and role == "Employee":
        st.title("Drivers and Downloads")
        st.write("Here you can download the necessary drivers or software.")
        
        # Iterate over the categories in apps.py
        for category, apps_dict in apps.items():
            st.subheader(f"{category} Apps")
            
            # Create a container to hold each category's content
            with st.expander(f"{category} Apps", expanded=True):
                # Use a grid layout for more visual appeal
                cols = st.columns(3)
                
                # Iterate over each app within the category
                for idx, (app_name, app_info) in enumerate(apps_dict.items()):
                    # Check if the app has an icon URL in the dictionary, else use a fallback image URL
                    if "image_url" in app_info and app_info["image_url"]:
                        icon_url = app_info["image_url"]  # Use the URL from the dictionary
                    else:
                        # Fallback to a default icon if the app doesn't have an image_url
                        icon_url = "https://img.icons8.com/ios/50/ffffff/application.png"
                    
                    # Display each app in a card-like format
                    with cols[idx % 3]:
                        # Display the app icon
                        st.image(icon_url, width=50)
                        st.write(f"**{app_name}**")
                        
                        # Create a download button for the app URL
                        st.download_button(
                            label=f"Download {app_name}",
                            data=app_info["url"],  # The URL from the dictionary
                            file_name=f"{app_name}.exe",  # The default name for the file when downloaded
                            mime="application/octet-stream",
                            use_container_width=True
                        )
                        
                        # Provide a clickable link to the app's website
                        st.markdown(f"[Learn more about {app_name}]({app_info['link']})", unsafe_allow_html=True)

    elif option == "Raise a Ticket" and role == "Employee":
        st.title("Raise a Support Ticket")
        ticket_subject = st.text_input("Ticket Subject")
        ticket_details = st.text_area("Ticket Details")
        
        if st.button("Submit Ticket"):
            if ticket_subject and ticket_details:
                # Save ticket to the database
                ticket_created_at = time.time()  # Store the current timestamp when the ticket is created
                
                # Save the ticket to the database with the creation timestamp
                ticket = {
                    "employee_id": st.session_state.get('employee_id'),
                    "subject": ticket_subject,
                    "details": ticket_details,
                    "status": "Open",
                    "priority": "Medium",  # Default to medium priority
                    "created_at": ticket_created_at
                }
                tickets_collection.insert_one(ticket)
                st.success("Ticket successfully raised! You'll be notified when it's resolved.")

                # Now you can calculate priority based on the creation time
                current_time = time.time()
                time_diff = current_time - ticket_created_at  # Difference in seconds

                if time_diff < 60 * 60:  # Less than an hour (Low Priority)
                    priority = "Low"
                elif time_diff < 60 * 60 * 24:  # Less than a day (Medium Priority)
                    priority = "Medium"
                else:  # More than a day (High Priority)
                    priority = "High"
                
                # Update the ticket's priority (optional, to change default priority)
                tickets_collection.update_one(
                    {"_id": ticket["_id"]},
                    {"$set": {"priority": priority}}
                )
                
            else:
                st.error("Please fill out both subject and details.")

    # Header for Laptop Maintenance
    elif option == "Laptop Maintenance" and role == "Employee":
        st.title("Laptop Maintenance Schedule")
        st.write(f"Your laptop is due for maintenance on **{maintenance_date.strftime('%Y-%m-%d')}**.")
        st.write(f"Make sure to back up important data and notify IT if any issues arise.")
        
        # Display the countdown timer
        st.subheader("Days Left Until Maintenance")
        st.write(f"There are **{max(days_left, 0)}** days left until your next maintenance.")
        
        # Set a fixed progress (15%) to show bar is filled
        progress = 15  # Fixed value of 15% progress
        
        # Show the progress bar with the fixed 15%
        st.progress(progress)
        
        # Show a calendar with the maintenance date highlighted
        st.subheader("Maintenance Calendar")
        
        # Get the current month and year for the calendar
        month_calendar = calendar.month_name[maintenance_date.month]  # Get month name
        st.write(f"**{month_calendar} {maintenance_date.year}**")
        
        # Calendar setup
        month = maintenance_date.month
        year = maintenance_date.year
        cal = calendar.monthcalendar(year, month)
        
        # Create the calendar grid
        calendar_grid = "Mo Tu We Th Fr Sa Su\n"
        for week in cal:
            week_str = ""
            for day in week:
                if day == 0:
                    week_str += "   "  # Empty spaces for the days of the week outside the current month
                else:
                    if day == maintenance_date.day:
                        week_str += f"**{day:2}** "  # Highlight the maintenance date
                    else:
                        week_str += f"{day:2} "  # Regular date formatting
            calendar_grid += week_str + "\n"

        # Display the calendar grid
        st.text(calendar_grid)

        # Optionally, display a simple progress indicator for the maintenance date
        st.markdown(f"### Maintenance Date: {maintenance_date.strftime('%B %d, %Y')}")

    elif option == "Request Upgrade" and role == "Employee":
        st.title("Request Laptop Upgrade or Accessory")
        upgrade_type = st.selectbox("What would you like to request?", ["RAM Upgrade", "Storage Upgrade", "Laptop Stand", "External Mouse"])
        reason = st.text_area("Why do you need this?")
        if st.button("Submit Request"):
            # Create a ticket for the upgrade request
            ticket = {
                "employee_id": st.session_state.get('employee_id'),
                "subject": f"{upgrade_type} Request",
                "details": reason,
                "category": "Upgrade Request",
                "status": "Open",
                "priority": "Medium",
                "created_at": time.time(),
            }
            # Insert into the tickets collection
            tickets_collection.insert_one(ticket)
            st.success(f"Your request for a {upgrade_type} has been submitted as a ticket for admin review.")

    elif option == "Onboarding/Offboarding":
        st.title("Employee Management")
        
        # Select onboarding or offboarding
        page = st.selectbox("Choose an Option", ["Onboarding", "Offboarding"])

        if page == "Onboarding":
            onboarding_page()  # Call the onboarding logic

        elif page == "Laptop Allocation":
            offboarding_page()

        elif page == "Offboarding":
            offboarding_page() 

    # Logout button (optional)
    if st.sidebar.button("Logout"):
        st.session_state["authenticated"] = False
        st.rerun()  # Rerun to show the login page again
