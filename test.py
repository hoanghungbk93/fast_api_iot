import requests
import time

# Define the start and end coordinates
start_location = {"latitude": 40.7128, "longitude": -74.0060}  # Example: New York City
end_location = {"latitude": 34.0522, "longitude": -118.2437}  # Example: Los Angeles

# Define the number of steps and the delay between updates
steps = 100
delay = 5  # seconds

# Calculate the step increments
lat_step = (end_location["latitude"] - start_location["latitude"]) / steps
lon_step = (end_location["longitude"] - start_location["longitude"]) / steps

# URL of the FastAPI endpoint
url = "http://fast.itmf.com.vn/gps/update"

# Simulate the movement
while True:
    # Forward direction
    for step in range(steps + 1):
        current_location = {
            "latitude": start_location["latitude"] + step * lat_step,
            "longitude": start_location["longitude"] + step * lon_step,
        }
        
        # Send the location update to the backend
        response = requests.post(url, json=current_location)
        
        if response.status_code == 200:
            print(f"Location updated: {current_location}")
        else:
            print(f"Failed to update location: {response.status_code}")
        
        # Wait for the specified delay
        time.sleep(delay)
    
    # Reverse direction
    for step in range(steps, -1, -1):
        current_location = {
            "latitude": start_location["latitude"] + step * lat_step,
            "longitude": start_location["longitude"] + step * lon_step,
        }
        
        # Send the location update to the backend
        response = requests.post(url, json=current_location)
        
        if response.status_code == 200:
            print(f"Location updated: {current_location}")
        else:
            print(f"Failed to update location: {response.status_code}")
        
        # Wait for the specified delay
        time.sleep(delay)