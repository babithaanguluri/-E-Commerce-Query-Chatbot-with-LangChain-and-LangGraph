from langchain_community.utilities.sql_database import SQLDatabase
from langchain_core.tools import tool

# Connect to the SQLite database
db = SQLDatabase.from_uri("sqlite:///ecommerce.db")

@tool
def execute_sql_query(query: str) -> str:
    """Execute a SQL query against the ecommerce database and return the result.
    
    The database has 4 tables:
    - customers(customer_id, name, email)
    - products(product_id, name, category, price, stock, rating)
    - orders(order_id, customer_id, product_id, quantity, status, created_at, estimated_delivery_date, tracking_number)
    - returns(return_id, order_id, status, reason, refund_amount)
    
    Use this tool to look up order status, product availability, return status, customer history, etc.
    Always use proper SQL syntax for SQLite.
    """
    try:
        return db.run(query)
    except Exception as e:
        return f"Error executing query: {e}"
