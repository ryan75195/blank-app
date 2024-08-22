import os
from email.mime.multipart import MIMEMultipart
import smtplib
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from googleapiclient.discovery import build
from google.oauth2 import service_account
from email.mime.text import MIMEText
import base64

# Load secrets from environment variables
st.secrets["gcp_service_account"] = {
    "type": os.getenv("GCP_TYPE"),
    "project_id": os.getenv("GCP_PROJECT_ID"),
    "private_key_id": os.getenv("GCP_PRIVATE_KEY_ID"),
    "private_key": os.getenv("GCP_PRIVATE_KEY").replace('\\n', '\n'),
    "client_email": os.getenv("GCP_CLIENT_EMAIL"),
    "client_id": os.getenv("GCP_CLIENT_ID"),
    "auth_uri": os.getenv("GCP_AUTH_URI"),
    "token_uri": os.getenv("GCP_TOKEN_URI"),
    "auth_provider_x509_cert_url": os.getenv("GCP_AUTH_PROVIDER_CERT_URL"),
    "client_x509_cert_url": os.getenv("GCP_CLIENT_CERT_URL")
}

# Other secrets
sender_email = os.getenv("SENDER_EMAIL")
sender_password = os.getenv("SENDER_PASSWORD")

def send_email_gmail(sender_email, sender_password, recipient_email, subject, body):
    try:
        # Create the email message
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = recipient_email
        msg['Subject'] = subject
        
        # Attach the message body
        msg.attach(MIMEText(body, 'plain'))
        
        # Establish a secure session with Gmail's SMTP server
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()  # Upgrade the connection to a secure encrypted SSL/TLS connection
        server.login(sender_email, sender_password)  # Login to the email account
        
        # Send the email
        server.sendmail(sender_email, recipient_email, msg.as_string())
        server.quit()  # Terminate the SMTP session
        print(f"Email sent to {recipient_email}")
        
    except Exception as e:
        print(f"Failed to send email. Error: {e}")

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

    # Strip any leading quotes and convert Date and Time to proper formats
    df['Date'] = pd.to_datetime(df['Date'].str.strip("'")).dt.date  # Strip leading quotes and keep only the date
    df['Time'] = pd.to_datetime(df['Time'].str.strip("'"), format='%H:%M').dt.time  # Strip leading quotes and convert to time

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
    # Compare only the date parts
    booked_slots = existing_bookings[existing_bookings['Date'] == date_selected]

    # Initialize the time slots: 9 AM, 11 AM, 1 PM, 3 PM
    all_slots = [datetime.combine(date_selected, datetime.strptime(f"{hour:02d}:00", "%H:%M").time()) for hour in [9, 11, 13, 15]]

    # Remove slots that are already booked
    for _, booking in booked_slots.iterrows():
        booked_time = datetime.combine(date_selected, booking['Time'])
        if booked_time in all_slots:
            all_slots.remove(booked_time)

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
if 'booking_submitted' not in st.session_state:
    st.session_state.booking_submitted = False

if st.session_state.booking_submitted:
    st.write("✅ Your booking has already been confirmed. Please contact aimee@basecentral.net to cancel or reschedule.")
else:
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
                    st.session_state.booking_submitted = True
                    st.write("📧 A confirmation email will be sent to you shortly. Please contact saucinlashes@gmail.com to cancel or reschedule.")
                    body = f"""Hello {booking_details['Name']},

Your booking for {booking_details['Service']} on {booking_details['Date']} at {booking_details['Time']} has been confirmed.

Thank you for choosing Saucin' Lashes!

Best regards,
Saucin' Lashes Team"""

                    # Send confirmation email
                    send_email_gmail(sender_email, sender_password, email, "Booking Confirmation", body)
                except Exception as e:
                    st.error(f"Failed to submit booking. Please try again.")
            else:
                st.error("Please fill in all the details to confirm your booking.")
