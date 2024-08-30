"""
This is a carpooling script that takes in a list of people and their respective locations and returns the optimal carpooling plan.
"""

#%% Libraries
import pandas as pd # Data manipulation and importing
import geopy, geopy.distance # Geocoding and address manipulation https://geopy.readthedocs.io/en/stable/
import folium # Map creation https://python-visualization.github.io/folium/latest/getting_started.html
import os # File manipulation


# Import data
if os.path.exists('drivers_private.txt') and os.path.exists('passengers_private.txt'):
    drivers = pd.read_csv('drivers_private.txt', delimiter='\t')
    passengers = pd.read_csv('passengers_private.txt', delimiter='\t')
else:
    drivers = pd.read_csv('drivers.txt')
    passengers = pd.read_csv('passengers.txt')

for person in [drivers, passengers]:
    person.columns = [col.strip() for col in person.columns]
    for col in person.columns:
        person[col] = person[col].apply(lambda x: x.strip() if isinstance(x, str) else x)

print("================================== Drivers ==================================")
print(drivers)
print("================================== Passengers ==================================")
print(passengers)

#%%
## ----------------------- YOU CAN EDIT BELOW THESE LINES ----------------------- ##
## ---------------------- TO MATCH YOUR DATA AND PREFERENCES -------------------- ##

## Assign the columns to the appropriate variables
# Drivers
driver_first_name = drivers['First Name']
driver_last_name = drivers['Last Name']
driver_spots = drivers['Spots available']
driver_address = drivers['Address']
# Passengers
passenger_first_name = passengers['First Name']
passenger_last_name = passengers['Last Name']
passenger_address = passengers['Address']
# Travel Destination
# carpool_destination = "41-53 Church St, Cowes VIC 3922" # CYC The Island
carpool_destination = "CYC The Island, Cowes VIC 3922" # CYC The Island


## ----------------------- YOU CAN EDIT ABOVE THESE LINES ----------------------- ##

#%%
## Geocoding
geolocator = geopy.Nominatim(user_agent="GoogleV3")
geo_destination = geolocator.geocode(carpool_destination, timeout=10)
print(carpool_destination + "\n" + str(geo_destination))
print(type(geo_destination), geo_destination.address)


#%%
## Define Classes
class Person:
    def __init__(self, first_name, last_name, address):
        self.first_name = first_name
        self.last_name = last_name
        self.address = address
        self.geo_location = geolocator.geocode(address, timeout=10)
        print(f"{self.first_name} {self.last_name}\t{self.geo_location}")
    
class Driver(Person):
    def __init__(self, first_name, last_name, address, spots):
        super().__init__(first_name, last_name, address)
        self.spots = int(spots)
        self.passengers: list[Person] = []
        self.shortest_distance: None | list[Person] = None
    
    def min_distance(self, geo_destination) -> float:
        """Calculate the distance to the destination."""
        dist, self.shortest_distance = Driver.min_distance_lists([self], self.passengers, geo_destination)
        return dist
        
    @staticmethod
    def min_distance_lists(assigned_passengers: list[Person], unassigned_passengers: list[Person], destination) -> tuple[float, list[Person]]:
        """Calculate the minimum distance between assigned passengers."""
        min_distance: tuple[float | None, list[Person]] = (None, [])
        
        if len(unassigned_passengers) == 0:
            return (sum([geopy.distance.distance(assigned_passengers[i].geo_location[1:], assigned_passengers[i+1].geo_location[1:]).kilometers
                        for i in range(len(assigned_passengers) - 1)
                       ] + [geopy.distance.distance(assigned_passengers[-1].geo_location[1:], destination[1:]).kilometers
                    ]), 
                    assigned_passengers.copy())
        else:
            for i in range(len(unassigned_passengers)):
                # Recursively call to find the minimum distance
                assigned_passengers.append(unassigned_passengers[i])
                dist, passengers = Driver.min_distance_lists(assigned_passengers, unassigned_passengers[:i] + unassigned_passengers[i+1:], destination)
                if min_distance[0] is None or dist < min_distance[0]:
                    min_distance = (dist, passengers)
                assigned_passengers.pop()
        return min_distance
        

def assign_passengers(available_drivers: list[Driver], passengers: list[Person]) -> tuple[float, dict[Driver, list[Person]]]:
    """Recursive function call that only updates the best combination if it is better than the previous best combination."""
    if len(passengers) == 0:
        return sum([driver.min_distance(geo_destination) for driver in available_drivers]), {driver: driver.shortest_distance for driver in available_drivers}
    else:
        # Add a passenger to a driver.
        min_snapshot: dict[Driver, list[Person]] = {}
        min_dist = None    
        for i, driver in enumerate(available_drivers):
            if len(driver.passengers) < driver.spots:
                for j, passenger in enumerate(passengers):
                    driver.passengers.append(passenger)
                    dist, snapshot = assign_passengers(available_drivers, passengers[:j] + passengers[j+1:])
                    driver.passengers.pop()
                    if min_dist is None or dist < min_dist:
                        min_dist = dist
                        min_snapshot = snapshot
        return min_dist, min_snapshot
        
# Create objects
drivers = [Driver(driver_first_name[i], driver_last_name[i], driver_address[i], driver_spots[i]) for i in range(len(driver_first_name))]
passengers = [Person(passenger_first_name[i], passenger_last_name[i], passenger_address[i]) for i in range(len(passenger_first_name))]
    
# Assign passengers
min_dist, snapshot = assign_passengers(drivers, passengers)        
print(min_dist, snapshot)

#%% # Show this on a map
m = folium.Map(location=[-38.375, 145.215], zoom_start=10)

colors = ["red", "blue", "green", "purple", "orange", "darkred", "lightred", "beige", "darkblue", "darkgreen", "cadetblue", "darkpurple", "pink", "lightblue", "lightgreen", "gray", "black", "lightgray"]

for j, driver in enumerate(snapshot):
    folium.Marker(driver.geo_location[1:][0], popup=f"{driver.first_name} {driver.last_name}").add_to(m)
    for i, passenger in enumerate(snapshot[driver]):
        folium.Marker(passenger.geo_location[1:][0], popup=f"{passenger.first_name} {passenger.last_name}").add_to(m)
        if i == 0:
            # Start at driver home
            folium.PolyLine([driver.geo_location[1:][0], passenger.geo_location[1:][0]], color=colors[j]).add_to(m)
        else:
            # Otherwise connect the passengers
            folium.PolyLine([snapshot[driver][i-1].geo_location[1:][0], passenger.geo_location[1:][0]], color=colors[j]).add_to(m)
    # Finally connect the last passenger to the destination        
    folium.PolyLine([snapshot[driver][-1].geo_location[1:][0], geo_destination[1:][0]], color=colors[j]).add_to(m)

display(m)
m.save("output.html")

## Save to output.txt
# %%
