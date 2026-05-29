import sqlite3

def inspect_database():
    conn = sqlite3.connect("ecommerce.db")
    cursor = conn.cursor()
    
    print("=" * 60)
    print("           E-COMMERCE DATABASE INSPECTOR")
    print("=" * 60)
    
    # 1. List all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]
    print(f"Found Tables: {', '.join(tables)}\n")
    
    # 2. Print row counts
    print("Table Row Counts:")
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f" - {table:<12}: {count} records")
    print("-" * 60)
    
    # 3. Print latest orders
    print("Latest 3 Orders:")
    cursor.execute("SELECT order_id, customer_id, product_id, status, created_at FROM orders ORDER BY created_at DESC LIMIT 3;")
    for row in cursor.fetchall():
        print(f" - Order {row[0]}: Customer {row[1]} | Product {row[2]} | Status: {row[3]:<10} | Created: {row[4]}")
    print("-" * 60)
    
    # 4. Print all returns (to verify inserts)
    print("All Return Records (Returns Table):")
    cursor.execute("SELECT return_id, order_id, status, reason, refund_amount FROM returns ORDER BY return_id DESC;")
    returns = cursor.fetchall()
    if not returns:
        print(" (No return records found)")
    for row in returns:
        print(f" - Return {row[0]}: Order {row[1]} | Status: {row[2]:<10} | Reason: {row[3]:<20} | Refund: ${row[4]}")
    print("=" * 60)
    
    conn.close()

if __name__ == "__main__":
    inspect_database()
