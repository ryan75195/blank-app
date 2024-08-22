import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Set page configuration and title
st.set_page_config(page_title="Saucin' Lashes Booking System", layout="centered")
st.title("Saucin' Beauty")
st.subheader("Book your appointment here.")

# Google Sheets connection setup
def connect_to_gsheets(sheet_name):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    credentials = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
    client = gspread.authorize(credentials)
    sheet = client.open(sheet_name).sheet1
    return sheet

# Establish connection to your Google Sheet
sheet = connect_to_gsheets("Saucin Books")

# Load existing bookings
def load_existing_bookings(sheet):
    bookings = sheet.get_all_records()
    df = pd.DataFrame(bookings)
    df['Date'] = pd.to_datetime(df['Date'])
    df['Time'] = pd.to_datetime(df['Time'], format='%H:%M:%S').dt.time
    return df

# Fetch existing bookings from Google Sheets
existing_bookings = load_existing_bookings(sheet)

# Service selection
st.header("1. Select Your Service")
# Define services for each category
services = {
    "Eyelashes": {
        "Classic Lashes": 50,
        "Volume Lashes": 75,
        "Hybrid Lashes": 65,
        "Infill": 25,
    },
    "Massages": {
        "Swedish Massage": 60,
        "Deep Tissue Massage": 80,
        "Hot Stone Massage": 90,
        "Aromatherapy Massage": 70,
    }
}

# Dropdown menu to select category
category_selected = st.selectbox("Choose a category:", list(services.keys()))

# Display the services in the selected category using st.radio
st.write(f"### Available {category_selected} Services")
service_selected = st.radio(
    "Choose your service:",
    options=[f"{service} - ${price}" for service, price in services[category_selected].items()],
)

# Extract the selected service and price
selected_service_name = service_selected.split(" - $")[0]
service_price = services[category_selected][selected_service_name]

# Display the selected service and total price
st.write(f"### You selected: {selected_service_name}")
st.write(f"**Price:** ${service_price}")

# Date and time selection
st.header("2. Select Date and Time")
date_selected = st.date_input("Choose your date", datetime.now())

# Filter out unavailable time slots with a maximum of 4 slots per day
def get_available_time_slots(date_selected, existing_bookings):
    booked_slots = existing_bookings[(existing_bookings['Date'] == date_selected)]

    # Initialize the time slots: 9 AM, 11 AM, 1 PM, 3 PM
    all_slots = [datetime.combine(date_selected, datetime.strptime(f"{hour:02d}:00", "%H:%M").time()) for hour in [9, 11, 13, 15]]
    
    # Remove slots that are already booked
    for _, booking in booked_slots.iterrows():
        booked_time = datetime.combine(date_selected, booking['Time'])
        for slot in all_slots:
            if slot.time() == booked_time.time():
                all_slots.remove(slot)
                break

    # Format the remaining slots for display
    available_slots = [slot.strftime('%H:%M') for slot in all_slots]
    
    return available_slots

available_slots = get_available_time_slots(date_selected, existing_bookings)
if available_slots:
    time_selected = st.selectbox("Choose your time", available_slots)
else:
    st.error("No available slots on this date. Please choose another date.")

# User details
st.header("3. Enter Your Information")
with st.form("booking_form"):
    name = st.text_input("Name", placeholder="Enter your full name")
    email = st.text_input("Email", placeholder="Enter your email")
    phone = st.text_input("Phone Number", placeholder="Enter your phone number")

    # Confirm button
    submitted = st.form_submit_button("Confirm Booking")

    if submitted:
        if name and email and phone and time_selected:
            booking_details = {
                "Name": name,
                "Email": email,
                "Phone": phone,
                "Service": selected_service_name,
                "Date": date_selected.strftime('%Y-%m-%d'),
                "Time": time_selected,
                "Price": f"${service_price}"
            }
            st.success("🎉 Booking Confirmed!")
            st.write("Your booking details:")
            st.write(pd.DataFrame([booking_details]))
            
            # Append booking details to Google Sheets
            try:
                sheet.append_row(list(booking_details.values()))
            except Exception as e:
                st.error(f"Failed to submit booking. Please try again.")
        else:
            st.error("Please fill in all the details to confirm your booking.")
