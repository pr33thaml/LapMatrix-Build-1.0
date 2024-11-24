# login.py

import streamlit as st
from pymongo import MongoClient

# MongoDB connection
client = MongoClient("mongodb://localhost:27017/")
db = client["lapmatrix"]
employees_collection = db["employees"]

# Function to authenticate users and fetch their role
def authenticate(email, password):
    user = employees_collection.find_one({"email": email, "password": password})
    if user:
        return user["role"]
    return None

def login_page():
    email = st.text_input("Email", placeholder="Enter your email")
    password = st.text_input("Password", placeholder="Enter your password", type="password")

    if st.button("Login"):
        role = authenticate(email, password)
        if role:
            st.session_state["authenticated"] = True
            st.session_state["role"] = role
            st.rerun()
        else:
            st.error("Invalid email or password.")
