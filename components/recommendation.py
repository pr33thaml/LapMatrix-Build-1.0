import numpy as np
import pandas as pd

# Load the data (Make sure the path is correct)
data = pd.read_csv('data/train_laptops.csv')  # Use relative path

# Clean the dataset by removing commas
data['Required CPU Speed (GHz)'] = data['Required CPU Speed (GHz)'].astype(str).str.replace(',', '').astype(float)
data['Required RAM (GB)'] = data['Required RAM (GB)'].astype(str).str.replace(',', '').astype(float)
data['Required Storage (GB)'] = data['Required Storage (GB)'].astype(str).str.replace(',', '').astype(float)

# Ensure that there are no non-numeric values
data['Required CPU Speed (GHz)'] = pd.to_numeric(data['Required CPU Speed (GHz)'], errors='coerce')
data['Required RAM (GB)'] = pd.to_numeric(data['Required RAM (GB)'], errors='coerce')
data['Required Storage (GB)'] = pd.to_numeric(data['Required Storage (GB)'], errors='coerce')

# Extract unique roles from the dataset
roles = data['Role'].unique().tolist()

# Create a list of laptops and a
laptops = data[['Recommended Laptop', 'Required CPU Speed (GHz)', 'Required RAM (GB)', 'Required Storage (GB)']].drop_duplicates()

# Function to get the closest laptop based on user input
def get_closest_laptop(cpu_speed, ram, storage):
    # Calculate the Euclidean distance to the desired specs
    data['distance'] = np.sqrt(
        (data['Required CPU Speed (GHz)'] - cpu_speed) ** 2 +
        (data['Required RAM (GB)'] - ram) ** 2 +
        (data['Required Storage (GB)'] - storage) ** 2
    )
    # Find the laptop with the minimum distance (i.e., closest match)
    closest_laptop = data.loc[data['distance'].idxmin()]
    return closest_laptop['Recommended Laptop']

# Expose the dataset and roles
def get_data():
    return data

def get_roles():
    return roles
