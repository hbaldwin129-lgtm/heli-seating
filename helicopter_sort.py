import streamlit as st
import itertools
from fpdf import FPDF
import datetime

# --- 1. Helicopter Properties (Your Logic) ---
HELICOPTER_SEATS = {
    'Front_Left':  {'arm': 40, 'legroom': 'high',  'adjacent_to': ['Rear_Far_Left']},
    'Front_Right': {'arm': 40, 'legroom': 'high',  'adjacent_to': ['Rear_Far_Right']}, 
    'Rear_Far_Left':   {'arm': 80, 'legroom': 'med',   'adjacent_to': ['Front_Left', 'Rear_Center_Left']},
    'Rear_Center_Left': {'arm': 80, 'legroom': 'low',   'adjacent_to': ['Rear_Far_Left', 'Rear_Center_Right']},
    'Rear_Center_Right': {'arm': 80, 'legroom': 'low',   'adjacent_to': ['Rear_Center_Left', 'Rear_Far_Right']},
    'Rear_Far_Right':  {'arm': 80, 'legroom': 'med',   'adjacent_to': ['Front_Right', 'Rear_Center_Right']}
}

MAX_WEIGHT = 1200 
CG_LIMITS = (60.0, 75.0) 

# --- 2. Calculation Functions (Your Logic) ---
def calculate_cg(arrangement):
    total_weight = sum(p['weight'] for p in arrangement)
    total_moment = sum(p['weight'] * HELICOPTER_SEATS[s]['arm'] for p, s in zip(arrangement, HELICOPTER_SEATS.keys()))
    return total_moment / total_weight if total_weight > 0 else 0

def score_arrangement(arrangement):
    score = 0
    seat_names = list(HELICOPTER_SEATS.keys())
    
    for i, passenger in enumerate(arrangement):
        seat = seat_names[i]
        # Group Optimization
        adjacent_seats = HELICOPTER_SEATS[seat]['adjacent_to']
        for adj_seat in adjacent_seats:
            adj_idx = seat_names.index(adj_seat)
            if adj_idx < len(arrangement):
                if passenger['group'] == arrangement[adj_idx]['group']:
                    score += 20 

    # CG Optimization
    cg = calculate_cg(arrangement)
    ideal_cg = (CG_LIMITS[0] + CG_LIMITS[1]) / 2
    score -= abs(ideal_cg - cg) * 2 
    
    return score

def optimize_seating(passengers):
    if sum(p['weight'] for p in passengers) > MAX_WEIGHT:
        return "Error: Total weight exceeds helicopter limits.", None

    best_arrangement = None
    best_score = -float('inf')
    
    for arrangement in itertools.permutations(passengers):
        cg = calculate_cg(arrangement)
        if CG_LIMITS[0] <= cg <= CG_LIMITS[1]:
            current_score = score_arrangement(arrangement)
            if current_score > best_score:
                best_score = current_score
                best_arrangement = arrangement
                
    if best_arrangement is None:
        return "Error: Could not find a seating arrangement within safe Center of Gravity limits.", None
        
    return best_arrangement, best_score

def create_pdf(arrangement, score, cg, total_weight, cruise_ship, pilot_name, call_sign):
    pdf = FPDF()
    pdf.add_page()
    
    # Title
    pdf.set_font("helvetica", "B", 16)
    pdf.cell(0, 10, "Helicopter Flight Manifest", ln=True, align="C")
    pdf.ln(5) # Add a little space
    
    # NEW: Added Flight Info
    pdf.set_font("helvetica", "", 12)
    pdf.cell(0, 8, f"Cruise Ship: {cruise_ship if cruise_ship else 'N/A'}", ln=True)
    pdf.cell(0, 8, f"Pilot: {pilot_name if pilot_name else 'N/A'}", ln=True)
    pdf.cell(0, 8, f"Call Sign: {call_sign if call_sign else 'N/A'}", ln=True)
    pdf.ln(5) 

    # Flight Stats
    pdf.set_font("helvetica", "", 12)
    pdf.cell(0, 8, f"Total Weight: {total_weight} lbs", ln=True)
    pdf.cell(0, 8, f"Center of Gravity: {cg:.2f} inches from datum", ln=True)
    pdf.cell(0, 8, f"Optimization Score: {score:.2f}", ln=True)
    pdf.ln(10)
    
    # Seating Chart
    pdf.set_font("helvetica", "B", 14)
    pdf.cell(0, 10, "Seat Assignments:", ln=True)
    
    pdf.set_font("helvetica", "", 12)
    seat_names = list(HELICOPTER_SEATS.keys())
    for seat, passenger in zip(seat_names, arrangement):
        seat_label = seat.replace("_", " ")
        info = f"{seat_label}: {passenger['name']} ({passenger['weight']} lbs)"
        pdf.cell(0, 8, info, ln=True)
        
    # Output the PDF as bytes so Streamlit can download it
    return bytes(pdf.output())

# --- 3. The Webpage Interface (Streamlit) ---
st.set_page_config(page_title="Heli-Seating Optimizer", layout="wide")

st.title("🚁 Helicopter Weight & Balance Optimizer")
st.write("Enter passenger details below to calculate the safest and most comfortable seating arrangement.")

st.subheader("Flight Information")
col_flight1, col_flight2, col_flight3, col_flight4 = st.columns(4)
cruise_ship = col_flight1.text_input("Cruise Ship Name")
pilot_name = col_flight2.text_input("Pilot Name")
call_sign = col_flight3.text_input("Aircraft Call Sign")
flight_time = col_flight4.text_input("Flight Time (e.g., 1430)")

flight_date = st.date_input("Flight Date", datetime.date.today())

# Initialize a list in session state to hold passenger data if it doesn't exist
if 'passengers' not in st.session_state:
    st.session_state.passengers = [
        {'name': 'Alice', 'weight': 140, 'group': 1},
        {'name': 'Bob',   'weight': 210, 'group': 1},
        {'name': 'Charlie','weight': 180, 'group': 2},
        {'name': 'Dave',  'weight': 195, 'group': 2},
        {'name': 'Eve',   'weight': 120, 'group': 3},
        {'name': 'Frank', 'weight': 160, 'group': 3}
    ]

# Create a form for the user to edit passenger data
with st.form("passenger_form"):
    st.subheader("Passenger Manifest")
    
    # Create columns for layout
    cols = st.columns(3)
    cols[0].write("**Name**")
    cols[1].write("**Weight (lbs)**")
    cols[2].write("**Group ID**")
    
    updated_passengers = []
    
    for i, p in enumerate(st.session_state.passengers):
        col1, col2, col3 = st.columns(3)
        name = col1.text_input(f"Name {i+1}", value=p['name'], label_visibility="collapsed")
        weight = col2.number_input(f"Weight {i+1}", value=p['weight'], min_value=1, label_visibility="collapsed")
        group = col3.number_input(f"Group {i+1}", value=p['group'], min_value=1, label_visibility="collapsed")
        
        updated_passengers.append({'name': name, 'weight': weight, 'group': group})
        
    submitted = st.form_submit_button("Optimize Seating")

# When the button is clicked, update the session state flag
if submitted:
    st.session_state.passengers = updated_passengers
    st.session_state.run_optimization = True
    
# Display results if optimization has been triggered
if st.session_state.get('run_optimization', False):
    # Display Flight Information
    st.write("### Flight Summary")
    st.write(f"**Date:** {flight_date.strftime('%Y-%m-%d')} | **Time:** {flight_time if flight_time else 'N/A'} | **Cruise Ship:** {cruise_ship if cruise_ship else 'N/A'} | **Pilot:** {pilot_name if pilot_name else 'N/A'} | **Call Sign:** {call_sign if call_sign else 'N/A'}")

    # Calculate Total Weight using the saved state
    total_weight = sum(p['weight'] for p in st.session_state.passengers)
    st.write(f"**Total Passenger Weight:** {total_weight} lbs (Max: {MAX_WEIGHT} lbs)")
    
    st.divider()
    
    # Run the optimizer
    result, score = optimize_seating(st.session_state.passengers)
    
    if isinstance(result, str):
        st.error(result) # Shows error in a red box
    else:
        st.success(f"Optimal Seating Found! (Optimization Score: {score:.2f})")
        
        # Display results nicely
        result_cg = calculate_cg(result)
        st.info(f"**Calculated Center of Gravity:** {result_cg:.2f} inches from datum")
        
        # Create a visual table of the seating
        st.subheader("Seat Assignments")
        for seat, passenger in zip(HELICOPTER_SEATS.keys(), result):
            st.write(f"🚁 **{seat.replace('_', ' ')}**: {passenger['name']} *(Group {passenger['group']}, {passenger['weight']} lbs)*")
    
    # ... your existing code that prints the seats on screen ...
        
        st.divider() # Adds a nice visual line
        
        # Create the PDF file in memory
        pdf_file = create_pdf(result, score, result_cg, total_weight, cruise_ship, pilot_name, call_sign)
        
        # Format the file name: [military_time] [call_sign] [date].pdf
        formatted_time = flight_time.strip() if flight_time else "0000"
        safe_call_sign = call_sign.strip() if call_sign else "UNKNOWN"
        pdf_filename = f"{formatted_time} {safe_call_sign} {flight_date.strftime('%Y-%m-%d')}.pdf"
        
        # Create the download button
        st.download_button(
            label="📄 Download Manifest as PDF",
            data=pdf_file,
            file_name=pdf_filename,
            mime="application/pdf"
        )