import pymongo
import pandas as pd

# MongoDB Client Setup (ensure you connect correctly to your MongoDB instance)
client = pymongo.MongoClient("mongodb://localhost:27017/")  # Adjust the URL if necessary
db = client["lapmatrix"]  # Replace with your database name
tickets_collection = db["tickets"]  # Replace with your collection name

def get_tickets():
    """Fetch all tickets from MongoDB."""
    tickets = tickets_collection.find()  # Fetch all tickets from the collection
    # Convert tickets to a pandas DataFrame
    return pd.DataFrame(list(tickets))  # Use list() to convert cursor to a list

def filter_tickets(status=None, priority=None):
    """Filters tickets based on status and priority."""
    df = get_tickets()
    if status != 'All' and status:
        df = df[df['status'] == status]
    if priority != 'All' and priority:
        df = df[df['priority'] == priority]
    return df

def update_ticket(ticket_id, status, priority, details):
    """Updates the ticket's status, priority, and details."""
    ticket_data = tickets_collection.find_one({"_id": ticket_id})  # Find ticket by ID
    if ticket_data:
        tickets_collection.update_one(
            {"_id": ticket_id},  # Match ticket by ID
            {"$set": {
                "status": status,
                "priority": priority,
                "details": details
            }}
        )
        print(f"Ticket {ticket_id} updated successfully!")
    else:
        print(f"Ticket with ID {ticket_id} not found.")

# Example usage of update_ticket function
ticket_id = 'some_ticket_id'  # Replace with an actual ticket ID from your database
new_status = "Closed"
new_priority = "High"
new_details = "Resolved issue with laptop reservation system."

update_ticket(ticket_id, new_status, new_priority, new_details)
