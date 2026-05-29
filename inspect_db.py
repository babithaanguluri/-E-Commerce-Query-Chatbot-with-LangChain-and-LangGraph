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
    
    # 2. Print table schema/structures
    print("Database Table Structures (Schema):")
    print("-" * 60)
    for table in tables:
        print(f"Table: {table.upper()}")
        cursor.execute(f"PRAGMA table_info({table});")
        columns = cursor.fetchall()
        for col in columns:
            col_id, col_name, col_type, not_null, default_val, is_pk = col
            pk_mark = " [PRIMARY KEY]" if is_pk else ""
            nn_mark = " NOT NULL" if not_null else ""
            print(f"  - {col_name:<20} ({col_type}){pk_mark}{nn_mark}")
        
        # Check for foreign keys
        cursor.execute(f"PRAGMA foreign_key_list({table});")
        fkeys = cursor.fetchall()
        for fk in fkeys:
            fk_id, seq, to_table, from_col, to_col, on_update, on_delete, match = fk
            print(f"  * Foreign Key: {from_col} -> {to_table}({to_col})")
        print("-" * 60)
    
    # 3. Print row counts
    print("\nTable Row Counts:")
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
