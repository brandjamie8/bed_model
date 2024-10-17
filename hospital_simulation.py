import streamlit as st
import simpy
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

st.set_page_config(page_title='Hospital Bed Simulation', layout='wide')

# Streamlit App Title
st.title('Hospital Bed Simulation')

st.write("""
This simulation models hospital bed occupancy over time, considering different patient types,
arrival rates, lengths of stay, bed management policies, and patients not meeting criteria to reside (NMCTR).
""")

# Sidebar Parameters
st.sidebar.header('Simulation Parameters')

# Simulation time
SIMULATION_TIME = st.sidebar.number_input('Simulation Time (days)', min_value=1, value=365)

# Number of beds
NUM_BEDS = st.sidebar.number_input('Total Number of Beds', min_value=1, value=100)

# Patient Types
patient_types = ['Medical', 'Surgical']

# Arrival rates
st.sidebar.subheader('Patient Arrival Rates (per day)')
ARRIVAL_RATES = {}
for p_type in patient_types:
    ARRIVAL_RATES[p_type] = st.sidebar.number_input(f'{p_type} Patients', min_value=0.0, value=5.0)

# Mean Lengths of Stay
st.sidebar.subheader('Mean Lengths of Stay (days)')
MEAN_LOS = {}
for p_type in patient_types:
    MEAN_LOS[p_type] = st.sidebar.number_input(f'{p_type} Patients', min_value=0.1, value=7.0)

# Patient Complexity Factors
st.sidebar.subheader('Patient Complexity Factors')
COMPLEXITY_FACTORS = {}
for p_type in patient_types:
    COMPLEXITY_FACTORS[p_type] = st.sidebar.slider(f'{p_type} Patients', min_value=0.5, max_value=2.0, value=1.0)

# Bed Boarding
ENABLE_BED_BOARDING = st.sidebar.checkbox('Enable Bed Boarding', value=True)
EXTRA_BED_RATIO = st.sidebar.number_input('Extra Beds per N Beds', min_value=1, value=5)

# NMCR Parameters
st.sidebar.header('Not Meeting Criteria to Reside (NMCR) Parameters')

# Proportion of patients experiencing NMCR delays
NMCR_PROPORTION = st.sidebar.slider('Proportion of Patients with NMCR Delays (%)', min_value=0, max_value=100, value=20)

# Reasons for NMCR Delays
st.sidebar.subheader('NMCR Delay Reasons Proportions (%)')
NMCR_INTERNAL_PROPORTION = st.sidebar.slider('Internal Reasons', min_value=0, max_value=100, value=50)
NMCR_EXTERNAL_PROPORTION = 100 - NMCR_INTERNAL_PROPORTION  # External reasons proportion

# Average Additional Delays
st.sidebar.subheader('Average Additional Delays (days)')
NMCR_INTERNAL_DELAY = st.sidebar.number_input('Internal Reasons Delay', min_value=0.1, value=2.0)
NMCR_EXTERNAL_DELAY = st.sidebar.number_input('External Reasons Delay', min_value=0.1, value=5.0)

# Seed for reproducibility
np.random.seed(42)

# Simulation Code
def run_simulation():
    class Hospital:
        def __init__(self, env, num_beds):
            self.env = env
            self.num_beds = num_beds
            self.occupied_beds = 0
            self.extra_beds = 0  # Number of extra beds available due to bed boarding
            self.total_beds = num_beds
            self.bed_capacity = num_beds  # Initial bed capacity
            self.beds = simpy.PriorityResource(env, capacity=num_beds + (num_beds // EXTRA_BED_RATIO))
            self.occupancy = []
            self.times = []
            self.env.process(self.monitor_occupancy())
            self.patients = []  # List to store patient data

        def monitor_occupancy(self):
            while True:
                # Record occupancy at each time step
                self.record_occupancy()
                yield self.env.timeout(1)

        def admit_patient(self, patient_id, p_type, length_of_stay):
            arrival_time = self.env.now

            # Determine if patient will have NMCR delay
            has_nmcr_delay = np.random.rand() < (NMCR_PROPORTION / 100)
            if has_nmcr_delay:
                # Determine reason for NMCR delay
                reason = 'Internal' if np.random.rand() < (NMCR_INTERNAL_PROPORTION / 100) else 'External'
                # Add additional delay based on reason
                if reason == 'Internal':
                    additional_delay = np.random.exponential(NMCR_INTERNAL_DELAY)
                else:
                    additional_delay = np.random.exponential(NMCR_EXTERNAL_DELAY)
                total_length_of_stay = length_of_stay + additional_delay
            else:
                total_length_of_stay = length_of_stay

            # Determine priority (normal beds have higher priority than extra beds)
            if self.occupied_beds < self.num_beds:
                priority = 0  # Normal bed
            else:
                if ENABLE_BED_BOARDING and self.occupied_beds < (self.num_beds + self.num_beds // EXTRA_BED_RATIO):
                    priority = 1  # Extra bed
                else:
                    priority = 2  # Wait until a bed is available

            with self.beds.request(priority=priority) as request:
                yield request
                self.occupied_beds += 1
                # Record occupancy when patient occupies a bed
                self.record_occupancy()
                yield self.env.timeout(total_length_of_stay)
                self.occupied_beds -= 1
                # Record occupancy when patient leaves
                self.record_occupancy()

            # Collect patient data
            discharge_time = self.env.now
            self.patients.append({
                'Patient ID': patient_id,
                'Type': p_type,
                'Arrival Time': arrival_time,
                'Length of Stay': length_of_stay,
                'NMCR Delay': total_length_of_stay - length_of_stay if has_nmcr_delay else 0,
                'Total LOS': total_length_of_stay,
                'Discharge Time': discharge_time,
                'NMCR Reason': reason if has_nmcr_delay else None
            })

        def record_occupancy(self):
            self.occupancy.append(self.occupied_beds)
            self.times.append(self.env.now)

    def patient_generator(env, hospital):
        patient_id = 0
        while env.now < SIMULATION_TIME:
            # Determine patient type based on arrival rates
            total_rate = sum(ARRIVAL_RATES.values())
            if total_rate == 0:
                break
            inter_arrival_time = np.random.exponential(1 / total_rate)
            yield env.timeout(inter_arrival_time)
            p_type = np.random.choice(
                patient_types,
                p=[ARRIVAL_RATES[p] / total_rate for p in patient_types]
            )
            length_of_stay = np.random.exponential(MEAN_LOS[p_type]) * COMPLEXITY_FACTORS[p_type]
            env.process(hospital.admit_patient(patient_id, p_type, length_of_stay))
            patient_id += 1

    # Set up the simulation environment
    env = simpy.Environment()
    hospital = Hospital(env, NUM_BEDS)

    # Start the patient arrival process
    env.process(patient_generator(env, hospital))

    # Run the simulation
    env.run(until=SIMULATION_TIME)

    return hospital.times, hospital.occupancy, hospital.patients

# Run the simulation
times, occupancy, patient_data = run_simulation()

# Prepare DataFrame for analysis
data = pd.DataFrame({'Time': times, 'Occupancy': occupancy})
patients_df = pd.DataFrame(patient_data)

# Plot bed occupancy over time
st.subheader('Bed Occupancy Over Time')
fig, ax = plt.subplots(figsize=(12, 6))
ax.step(data['Time'], data['Occupancy'], where='post')
ax.set_xlabel('Time (days)')
ax.set_ylabel('Number of Occupied Beds')
ax.set_title('Hospital Bed Occupancy Over Time')
ax.grid(True)
st.pyplot(fig)

# Statistics
average_occupancy = np.mean(occupancy)
max_occupancy = np.max(occupancy)
overflow_events = sum(np.array(occupancy) > NUM_BEDS)

st.subheader('Simulation Statistics')
col1, col2, col3 = st.columns(3)
col1.metric('Average Occupancy', f'{average_occupancy:.2f} beds')
col2.metric('Maximum Occupancy', f'{max_occupancy} beds')
col3.metric('Overflow Events', f'{overflow_events} times')

# NMCR Analysis
st.subheader('Not Meeting Criteria to Reside (NMCR) Analysis')

# NMCR Summary
total_patients = len(patients_df)
nmcr_patients = patients_df[patients_df['NMCR Delay'] > 0]
nmcr_count = len(nmcr_patients)
nmcr_internal = nmcr_patients[nmcr_patients['NMCR Reason'] == 'Internal']
nmcr_external = nmcr_patients[nmcr_patients['NMCR Reason'] == 'External']

col1, col2, col3 = st.columns(3)
col1.metric('Total Patients', f'{total_patients}')
col2.metric('Patients with NMCR Delays', f'{nmcr_count} ({(nmcr_count/total_patients)*100:.1f}%)')
col3.metric('Average NMCR Delay', f'{nmcr_patients["NMCR Delay"].mean():.2f} days')

# NMCR Reasons Breakdown
st.write('**NMCR Delay Reasons Breakdown:**')
col1, col2 = st.columns(2)
col1.metric('Internal Reasons', f'{len(nmcr_internal)} patients')
col2.metric('External Reasons', f'{len(nmcr_external)} patients')

# NMCR Delay Distribution
st.write('**NMCR Delay Distribution:**')
fig2, ax2 = plt.subplots(figsize=(8, 4))
ax2.hist(nmcr_patients['NMCR Delay'], bins=30, alpha=0.7, color='orange')
ax2.set_xlabel('NMCR Delay (days)')
ax2.set_ylabel('Number of Patients')
ax2.set_title('Distribution of NMCR Delays')
st.pyplot(fig2)

# Additional Information
st.write("""
*Use the sidebar to adjust the simulation parameters, including the NMCR settings. The NMCR analysis above provides insights into how NMCR delays impact bed occupancy and patient flow.*
""")
