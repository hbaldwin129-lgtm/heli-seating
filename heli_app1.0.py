import streamlit as st
import itertools
from xhtml2pdf import pisa
import io
import datetime

# --- 1. Helicopter Properties ---
HELICOPTER_SEATS = {
    'Front_Left':        {'arm': 40, 'legroom': 'high', 'adjacent_to': ['Rear_Far_Left']},
    'Front_Right':       {'arm': 40, 'legroom': 'high', 'adjacent_to': ['Rear_Far_Right']},
    'Rear_Far_Left':     {'arm': 80, 'legroom': 'med',  'adjacent_to': ['Front_Left', 'Rear_Center_Left']},
    'Rear_Center_Left':  {'arm': 80, 'legroom': 'low',  'adjacent_to': ['Rear_Far_Left', 'Rear_Center_Right']},
    'Rear_Center_Right': {'arm': 80, 'legroom': 'low',  'adjacent_to': ['Rear_Center_Left', 'Rear_Far_Right']},
    'Rear_Far_Right':    {'arm': 80, 'legroom': 'med',  'adjacent_to': ['Front_Right', 'Rear_Center_Right']}
}

MAX_WEIGHT = 1200
CG_LIMITS  = (60.0, 75.0)


# --- 2. Calculation Functions ---
def calculate_cg(arrangement):
    total_weight = sum(p['weight'] for p in arrangement)
    total_moment = sum(p['weight'] * HELICOPTER_SEATS[s]['arm']
                       for p, s in zip(arrangement, HELICOPTER_SEATS.keys()))
    return total_moment / total_weight if total_weight > 0 else 0

def score_arrangement(arrangement):
    score = 0
    seat_names = list(HELICOPTER_SEATS.keys())
    for i, passenger in enumerate(arrangement):
        seat = seat_names[i]
        for adj_seat in HELICOPTER_SEATS[seat]['adjacent_to']:
            adj_idx = seat_names.index(adj_seat)
            if adj_idx < len(arrangement):
                if passenger['group'] == arrangement[adj_idx]['group']:
                    score += 20
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


# --- 3. PDF Generation ---
def create_pdf(arrangement, total_weight, cg, cruise_ship, pilot_name, call_sign, flight_time):

    passenger_rows = ""
    for i, p in enumerate(arrangement):
        note = "F" if i == 4 else ("FP" if i == 5 else "")
        passenger_rows += (
            f'<tr>'
            f'<td style="text-align:center;font-weight:bold">{i+1}</td>'
            f'<td style="text-align:center;font-size:6.5pt">{p["group"]}</td>'
            f'<td colspan="2" style="text-align:center">{p["name"]}</td>'
            f'<td style="text-align:right;font-weight:bold">{p["weight"]}</td>'
            f'<td style="text-align:center">{note}</td>'
            f'</tr>'
        )
    for i in range(len(arrangement), 6):
        passenger_rows += (
            f'<tr>'
            f'<td style="text-align:center;font-weight:bold">{i+1}</td>'
            f'<td style=""></td>'
            f'<td colspan="2" style=""></td>'
            f'<td style=""></td>'
            f'<td style=""></td>'
            f'</tr>'
        )

    html = (
        '<!DOCTYPE html>'
        '<html><head><style>'
        '@page { size: 99mm 93mm; margin: 3mm; }'
        'body { font-family: Arial, sans-serif; margin: 0; padding: 0; }'
        'table { width: 93mm; border: 1.5pt solid black; border-collapse: collapse; table-layout: fixed; }'
        'td { border: 0.5pt solid black; padding: 0.5pt 2pt; font-size: 7.5pt; height: 11pt; vertical-align: middle; overflow: hidden; white-space: nowrap; }'
        '</style></head>'
        '<body><table>'
        '<colgroup>'
        '<col style="width:7mm">'
        '<col style="width:11mm">'
        '<col style="width:9mm">'
        '<col style="width:38mm">'
        '<col style="width:17mm">'
        '<col style="width:11mm">'
        '</colgroup>'
        # Row 1: H130 | call_sign | TIME | flight_time | MENDY | F
        '<tr>'
        f'<td style="font-size:6.5pt">H130</td>'
        f'<td style="font-weight:bold">{call_sign}</td>'
        f'<td style="font-size:6.5pt">TIME</td>'
        f'<td style="font-weight:bold;text-align:center">{flight_time}</td>'
        f'<td style="font-size:6.5pt;text-align:center">MENDY</td>'
        f'<td style="font-size:6.5pt;text-align:center">F</td>'
        '</tr>'
        # Row 2: PILOT | pilot_name | 150 | 50
        '<tr>'
        f'<td style="font-size:6.5pt">PILOT</td>'
        f'<td colspan="3" style="font-weight:bold">{pilot_name}</td>'
        f'<td style="text-align:right;font-weight:bold">150</td>'
        f'<td style="text-align:center;font-weight:bold">50</td>'
        '</tr>'
        # Row 3: PASSENGER NAMES | WEIGHT+10
        '<tr>'
        '<td colspan="4" style="font-size:6.5pt;font-weight:bold">PASSENGER NAMES</td>'
        '<td colspan="2" style="font-size:6.5pt;font-weight:bold;text-align:center">WEIGHT+10</td>'
        '</tr>'
        + passenger_rows +
        # Aft Cargo
        '<tr>'
        '<td style="text-align:center;font-weight:bold">S</td>'
        '<td style="font-size:6.5pt">SIDE</td>'
        '<td colspan="2" style="text-align:center;font-weight:bold">Aft Cargo</td>'
        '<td style="text-align:right;font-weight:bold">0</td>'
        '<td></td>'
        '</tr>'
        # FRONT/BACK
        '<tr>'
        '<td colspan="2" style="font-size:6.5pt;font-weight:bold">FRONT/BACK</td>'
        '<td style="text-align:center;font-weight:bold">427</td>'
        f'<td style="text-align:center;font-weight:bold">{cg:.1f}</td>'
        f'<td colspan="2" style="text-align:center;font-weight:bold">{total_weight}</td>'
        '</tr>'
        # SHIP
        '<tr>'
        '<td style="font-size:6.5pt">SHIP</td>'
        f'<td colspan="2" style="font-weight:bold">{cruise_ship}</td>'
        '<td style="font-size:6.5pt;text-align:center">TOTAL</td>'
        '<td style="text-align:center;font-weight:bold">5159</td>'
        '<td style="text-align:center;font-weight:bold">OK</td>'
        '</tr>'
        # HOGE
        '<tr>'
        '<td colspan="3" style="font-size:6.5pt">HOGE at Max Gross at:</td>'
        '<td colspan="3" style="text-align:center;font-weight:bold">#N/A feet</td>'
        '</tr>'
        '</table></body></html>'
    )

    pdf_buffer = io.BytesIO()
    pisa_status = pisa.CreatePDF(html, dest=pdf_buffer)
    if pisa_status.err:
        return b"Error generating PDF"
    return pdf_buffer.getvalue()


# --- 4. Streamlit UI ---
st.set_page_config(page_title="Heli-Seating Optimizer", layout="wide")
st.title("🚁 Helicopter Weight & Balance Optimizer")
st.write("Enter passenger details below to calculate the safest and most comfortable seating arrangement.")

st.subheader("Flight Information")
col1, col2, col3, col4 = st.columns(4)
cruise_ship = col1.text_input("Cruise Ship Name",       value="N. Bliss")
pilot_name  = col2.text_input("Pilot Name",              value="Michelle Manger")
call_sign   = col3.text_input("Aircraft Call Sign",      value="09T")
flight_time = col4.text_input("Flight Time (e.g., 9A)",  value="9A")
flight_date = st.date_input("Flight Date", datetime.date.today())

if 'passengers' not in st.session_state:
    st.session_state.passengers = [
        {'name': 'Meejin Kim',          'weight': 133, 'group': 1},
        {'name': 'Meeok Kim',           'weight': 135, 'group': 1},
        {'name': 'Mike Wilson',         'weight': 210, 'group': 2},
        {'name': 'Lena Wilson',         'weight': 190, 'group': 2},
        {'name': 'Erik Van Buggenhout', 'weight': 219, 'group': 3},
        {'name': 'Evelien Verbaewen',   'weight': 208, 'group': 3},
    ]

with st.form("passenger_form"):
    st.subheader("Passenger Manifest")
    c1, c2, c3 = st.columns(3)
    c1.write("**Name**"); c2.write("**Weight (lbs)**"); c3.write("**Group ID**")

    updated_passengers = []
    for i, p in enumerate(st.session_state.passengers):
        c1, c2, c3 = st.columns(3)
        name   = c1.text_input(  f"Name {i+1}",  value=p['name'],   label_visibility="collapsed")
        weight = c2.number_input(f"Weight {i+1}", value=p['weight'], min_value=1, label_visibility="collapsed")
        group  = c3.number_input(f"Group {i+1}",  value=p['group'],  min_value=1, label_visibility="collapsed")
        updated_passengers.append({'name': name, 'weight': weight, 'group': group})

    submitted = st.form_submit_button("Optimize Seating")

if submitted:
    st.session_state.passengers = updated_passengers
    st.session_state.run_optimization = True

if st.session_state.get('run_optimization', False):
    st.write("### Flight Summary")
    st.write(
        f"**Date:** {flight_date.strftime('%Y-%m-%d')} | **Time:** {flight_time or 'N/A'} | "
        f"**Ship:** {cruise_ship or 'N/A'} | **Pilot:** {pilot_name or 'N/A'} | "
        f"**Call Sign:** {call_sign or 'N/A'}"
    )

    total_weight = sum(p['weight'] for p in st.session_state.passengers)
    st.write(f"**Total Passenger Weight:** {total_weight} lbs (Max: {MAX_WEIGHT} lbs)")
    st.divider()

    result, score = optimize_seating(st.session_state.passengers)

    if isinstance(result, str):
        st.error(result)
    else:
        st.success(f"Optimal Seating Found! (Score: {score:.2f})")
        result_cg = calculate_cg(result)
        st.info(f"**Center of Gravity:** {result_cg:.2f} inches from datum")

        st.subheader("Seat Assignments")
        for seat, passenger in zip(HELICOPTER_SEATS.keys(), result):
            st.write(
                f"🚁 **{seat.replace('_', ' ')}**: {passenger['name']} "
                f"*(Group {passenger['group']}, {passenger['weight']} lbs)*"
            )

        st.divider()

        pdf_file = create_pdf(result, total_weight, result_cg, cruise_ship, pilot_name, call_sign, flight_time)
        pdf_filename = f"{flight_time.strip() or '0000'}_{call_sign.strip() or 'UNKNOWN'}_{flight_date.strftime('%Y-%m-%d')}.pdf"

        st.download_button(
            label="📄 Download Manifest as PDF",
            data=pdf_file,
            file_name=pdf_filename,
            mime="application/pdf"
        )