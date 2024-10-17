import streamlit as st
import numpy as np

st.set_page_config(page_title='Occupancy and LOS Analysis', layout='wide')

st.title('Occupancy and Length of Stay Analysis')

st.write("""
On this page, you can set a target occupancy rate and find out what the ideal average length of stay (LOS)
would be to maintain this occupancy.
""")

st.write("""
Additionally, you'll see the number of discharges per week this translates to.
""")

# Sidebar Parameters
st.sidebar.header('Occupancy Analysis Parameters')

# Number of beds
NUM_BEDS = st.sidebar.number_input('Total Number of Beds', min_value=1, value=100)

# Patient Types
patient_types = ['Medical', 'Surgical']

# Arrival rates
st.sidebar.subheader('Patient Arrival Rates (per day)')
ARRIVAL_RATES = {}
total_arrival_rate = 0
for p_type in patient_types:
    ARRIVAL_RATES[p_type] = st.sidebar.number_input(f'{p_type} Patients', min_value=0.0, value=5.0)
    total_arrival_rate += ARRIVAL_RATES[p_type]

if total_arrival_rate == 0:
    st.warning('Total arrival rate must be greater than 0.')
    st.stop()

# Target Occupancy Rate
st.sidebar.subheader('Target Occupancy Rate')
target_occupancy_rate = st.sidebar.slider('Occupancy Rate (%)', min_value=1, max_value=100, value=85)

# Calculations
# Convert occupancy rate to a fraction
occupancy_fraction = target_occupancy_rate / 100

# Ideal Average LOS
ideal_average_los = (occupancy_fraction * NUM_BEDS) / total_arrival_rate

# Number of Discharges per Week
# In steady state, discharges per week = arrivals per week
discharges_per_week = total_arrival_rate * 7

# Display Results
st.subheader('Results')
col1, col2 = st.columns(2)
col1.metric('Ideal Average LOS', f'{ideal_average_los:.2f} days')
col2.metric('Discharges per Week', f'{discharges_per_week:.2f} patients')

st.write("""
**Interpretation:**
- To maintain a target occupancy rate of **{0}%** with **{1}** beds and a total arrival rate of **{2:.2f} patients/day**, 
the ideal average length of stay should be **{3:.2f} days**.
- This translates to approximately **{4:.2f} discharges per week**.
""".format(
    target_occupancy_rate, NUM_BEDS, total_arrival_rate, ideal_average_los, discharges_per_week
))

# Option to adjust LOS per patient type
st.subheader('Adjust Length of Stay per Patient Type')

st.write("""
You can adjust the lengths of stay for each patient type to achieve the ideal average LOS calculated above.
""")

# Current Mean LOS
st.write('**Current Mean LOS per Patient Type:**')
current_mean_los = {}
for p_type in patient_types:
    current_mean_los[p_type] = st.number_input(f'{p_type} Patients Mean LOS (days)', min_value=0.1, value=7.0)

# Calculate weighted average LOS
total_arrivals = sum(ARRIVAL_RATES.values())
weighted_average_los = sum([ARRIVAL_RATES[p] * current_mean_los[p] for p in patient_types]) / total_arrivals

st.write(f'**Current Weighted Average LOS:** {weighted_average_los:.2f} days')

# Suggest adjustments if needed
if abs(weighted_average_los - ideal_average_los) > 0.01:
    st.write("""
    **Suggested Adjustments:**
    To achieve the ideal average LOS, consider adjusting the lengths of stay as follows.
    """)
    # Proportionally adjust LOS to match ideal average LOS
    adjustment_factor = ideal_average_los / weighted_average_los
    adjusted_los = {p: current_mean_los[p] * adjustment_factor for p in patient_types}

    for p_type in patient_types:
        st.write(f'- **{p_type} Patients:** Adjust LOS to **{adjusted_los[p_type]:.2f} days**')

else:
    st.write('The current lengths of stay align with the ideal average LOS.')

# Visualizing LOS Distribution
st.subheader('Visualizing Length of Stay Distribution')

import matplotlib.pyplot as plt

# Generate LOS distributions
fig, ax = plt.subplots(figsize=(8, 4))

for p_type in patient_types:
    los_values = np.random.exponential(current_mean_los[p_type], 1000)
    ax.hist(los_values, bins=50, alpha=0.5, label=f'{p_type} LOS')

ax.axvline(ideal_average_los, color='red', linestyle='--', label='Ideal Average LOS')
ax.set_xlabel('Length of Stay (days)')
ax.set_ylabel('Frequency')
ax.set_title('Length of Stay Distributions')
ax.legend()
st.pyplot(fig)
