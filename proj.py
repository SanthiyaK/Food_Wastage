import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text

# -------------------------
#  Database Connection
# -------------------------
engine = create_engine("mysql+mysqlconnector://root:root%40123@localhost/food_wastage_db")

# -------------------------
#  App Configuration
# -------------------------
st.set_page_config(page_title="Food Wastage Portal", layout="wide")
st.title(" Food Wastage Management Portal")

# -------------------------
#  Sidebar Navigation
# -------------------------
menu = ["Dashboard", "CRUD Operations", "Filters", "Contact", "Analytics"]
choice = st.sidebar.selectbox("Menu", menu)

# -------------------------
#  Dashboard: Quick View
# -------------------------
if choice == "Dashboard":
    st.header(" Quick Dashboard Overview")
    
    with engine.connect() as conn:
        total_providers = pd.read_sql("SELECT COUNT(*) AS count FROM providers", conn).iloc[0,0]
        total_receivers = pd.read_sql("SELECT COUNT(*) AS count FROM receivers", conn).iloc[0,0]
        total_food = pd.read_sql("SELECT SUM(Quantity) AS total FROM food_listings", conn).iloc[0,0]
        total_claims = pd.read_sql("SELECT COUNT(*) AS total FROM claims", conn).iloc[0,0]
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Providers", total_providers)
    col2.metric("Total Receivers", total_receivers)
    col3.metric("Total Food Available", total_food)
    col4.metric("Total Claims", total_claims)

# -------------------------
#  CRUD Operations
# -------------------------
elif choice == "CRUD Operations":
    st.header("🛠 CRUD Operations")
    table_choice = st.selectbox("Select Table", ["providers", "receivers", "food_listings", "claims"])
    
    with engine.connect() as conn:
        df = pd.read_sql(f"SELECT * FROM {table_choice}", conn)
    
    st.subheader("Current Records")
    st.dataframe(df)
    
    st.subheader("Add / Update / Delete Records")
    
    if table_choice == "providers":
        name = st.text_input("Name")
        type_ = st.text_input("Type")
        address = st.text_input("Address")
        city = st.text_input("City")
        contact = st.text_input("Contact")
        action = st.radio("Action", ["Add", "Update", "Delete"])
        record_id = st.number_input("Record ID (for update/delete)", min_value=0, step=1)
        
        if st.button("Execute"):
            with engine.begin() as conn:
                if action == "Add":
                    conn.execute(text("""
                        INSERT INTO providers (Name, Type, Address, City, Contact)
                        VALUES (:name, :type, :address, :city, :contact)
                    """), {"name": name, "type": type_, "address": address, "city": city, "contact": contact})
                    st.success(" Provider added successfully!")
                
                elif action == "Update":
                    conn.execute(text("""
                        UPDATE providers
                        SET Name=:name, Type=:type, Address=:address, City=:city, Contact=:contact
                        WHERE Provider_ID=:id
                    """), {"name": name, "type": type_, "address": address, "city": city, "contact": contact, "id": record_id})
                    st.success(" Provider updated successfully!")
                
                elif action == "Delete":
                    conn.execute(text("DELETE FROM providers WHERE Provider_ID=:id"), {"id": record_id})
                    st.success(" Provider deleted successfully!")

    # Similar CRUD blocks can be added for receivers, food_listings, and claims

# -------------------------
#  Filters
# -------------------------
elif choice == "Filters":
    st.header(" Filter Food Donations")
    location = st.text_input("Location")
    provider = st.text_input("Provider Name")
    food_type = st.text_input("Food Type")
    
    query = """
        SELECT f.Food_ID, f.Food_Name, f.Quantity, f.Expiry_Date, f.Location,
               f.Food_Type, f.Meal_Type, p.Name AS Provider_Name, p.Contact
        FROM food_listings f
        JOIN providers p ON f.Provider_ID = p.Provider_ID
        WHERE 1=1
    """
    
    params = {}
    if location:
        query += " AND f.Location LIKE :location"
        params["location"] = f"%{location}%"
    if provider:
        query += " AND p.Name LIKE :provider"
        params["provider"] = f"%{provider}%"
    if food_type:
        query += " AND f.Food_Type LIKE :food_type"
        params["food_type"] = f"%{food_type}%"
    
    with engine.connect() as conn:
        filtered_food = pd.read_sql(text(query), conn, params=params)
    
    st.dataframe(filtered_food)

# -------------------------
#  Contact
# -------------------------
elif choice == "Contact":
    st.header(" Contact Providers / Receivers")
    contact_type = st.radio("Contact", ["Providers", "Receivers"])
    
    with engine.connect() as conn:
        if contact_type == "Providers":
            df = pd.read_sql("SELECT Name, Contact, City FROM providers", conn)
        else:
            df = pd.read_sql("SELECT Name, Contact, City FROM receivers", conn)
    
    st.dataframe(df)

# -------------------------
#  Analytics & Queries
# -------------------------
elif choice == "Analytics":
    st.header(" Analytics & Insights")
    
    queries = {
        "Providers per city": "SELECT City, COUNT(*) AS Provider_Count FROM providers GROUP BY City",
        "Receivers per city": "SELECT City, COUNT(*) AS Receiver_Count FROM receivers GROUP BY City",
        "Top provider type contributing food": """
            SELECT p.Type, SUM(f.Quantity) AS Total_Quantity
            FROM food_listings f
            JOIN providers p ON f.Provider_ID = p.Provider_ID
            GROUP BY p.Type
            ORDER BY Total_Quantity DESC LIMIT 5
        """,
        "Top receivers by claims": """
            SELECT r.Name, COUNT(c.Claim_ID) AS Claims_Count
            FROM claims c
            JOIN receivers r ON c.Receiver_ID = r.Receiver_ID
            GROUP BY r.Name
            ORDER BY Claims_Count DESC LIMIT 10
        """,
        "Total food available": "SELECT SUM(Quantity) AS Total_Food FROM food_listings",
        "City with most listings": """
            SELECT Location AS City, COUNT(*) AS Listings_Count
            FROM food_listings
            GROUP BY Location
            ORDER BY Listings_Count DESC LIMIT 1
        """,
        "Most common food types": """
            SELECT Food_Type, COUNT(*) AS Count
            FROM food_listings
            GROUP BY Food_Type
            ORDER BY Count DESC LIMIT 10
        """,
        "Claims per food item": """
            SELECT f.Food_Name, COUNT(c.Claim_ID) AS Claims_Count
            FROM claims c
            JOIN food_listings f ON c.Food_ID = f.Food_ID
            GROUP BY f.Food_Name
            ORDER BY Claims_Count DESC
        """,
        "Provider with highest successful claims": """
            SELECT p.Name, COUNT(c.Claim_ID) AS Successful_Claims
            FROM claims c
            JOIN food_listings f ON c.Food_ID = f.Food_ID
            JOIN providers p ON f.Provider_ID = p.Provider_ID
            WHERE c.Status = 'Completed'
            GROUP BY p.Name
            ORDER BY Successful_Claims DESC LIMIT 1
        """,
        "Percentage of claims by status": """
            SELECT Status, COUNT(*)*100.0/(SELECT COUNT(*) FROM claims) AS Percentage
            FROM claims
            GROUP BY Status
        """,
        "Average quantity claimed per receiver": """
            SELECT r.Name, AVG(f.Quantity) AS Avg_Quantity
            FROM claims c
            JOIN receivers r ON c.Receiver_ID = r.Receiver_ID
            JOIN food_listings f ON c.Food_ID = f.Food_ID
            GROUP BY r.Name
            ORDER BY Avg_Quantity DESC
        """,
        "Most claimed meal type": """
            SELECT f.Meal_Type, COUNT(c.Claim_ID) AS Count
            FROM claims c
            JOIN food_listings f ON c.Food_ID = f.Food_ID
            GROUP BY f.Meal_Type
            ORDER BY Count DESC
        """,
        "Total quantity donated by each provider": """
            SELECT p.Name, SUM(f.Quantity) AS Total_Donated
            FROM food_listings f
            JOIN providers p ON f.Provider_ID = p.Provider_ID
            GROUP BY p.Name
            ORDER BY Total_Donated DESC
        """
    }
    
    for title, q in queries.items():
        st.subheader(title)
        with engine.connect() as conn:
            df = pd.read_sql(q, conn)
        st.dataframe(df)
