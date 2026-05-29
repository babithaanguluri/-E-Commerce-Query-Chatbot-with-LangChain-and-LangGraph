import sqlite3
from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
import random
from datetime import datetime, timedelta
from faker import Faker

Base = declarative_base()

class Customer(Base):
    __tablename__ = 'customers'
    customer_id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    
    orders = relationship("Order", back_populates="customer")

class Product(Base):
    __tablename__ = 'products'
    product_id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    category = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    stock = Column(Integer, nullable=False)
    rating = Column(Float, nullable=False)

class Order(Base):
    __tablename__ = 'orders'
    order_id = Column(String, primary_key=True)
    customer_id = Column(String, ForeignKey('customers.customer_id'), nullable=False)
    product_id = Column(String, ForeignKey('products.product_id'), nullable=False)
    quantity = Column(Integer, nullable=False)
    status = Column(String, nullable=False) # 'processing', 'shipped', 'delivered', 'cancelled'
    created_at = Column(DateTime, nullable=False)
    estimated_delivery_date = Column(DateTime, nullable=True)
    tracking_number = Column(String, nullable=True)

    customer = relationship("Customer", back_populates="orders")
    product = relationship("Product")
    returns = relationship("Return", back_populates="order")

class Return(Base):
    __tablename__ = 'returns'
    return_id = Column(String, primary_key=True)
    order_id = Column(String, ForeignKey('orders.order_id'), nullable=False)
    status = Column(String, nullable=False) # 'pending', 'approved', 'rejected'
    reason = Column(String, nullable=True)
    refund_amount = Column(Float, nullable=True)

    order = relationship("Order", back_populates="returns")

def seed_database():
    engine = create_engine('sqlite:///ecommerce.db')
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    Faker.seed(42)
    random.seed(42)
    fake = Faker()

    # 1. Create Customers (e.g., 30)
    customers = []
    for i in range(1, 31):
        c = Customer(
            customer_id=f"C{1000 + i}",
            name=fake.name(),
            email=fake.email()
        )
        customers.append(c)
    session.add_all(customers)

    # 2. Create Products (e.g., 20)
    # Requirement: At least 5 products must have zero stock.
    products = []
    categories = ['Electronics', 'Clothing', 'Home', 'Books', 'Toys']
    for i in range(1, 21):
        stock_count = 0 if i <= 5 else random.randint(10, 100)
        p = Product(
            product_id=f"P{1000 + i}",
            name=fake.word().capitalize() + " " + random.choice(['Widget', 'Gadget', 'Thingamajig', 'Item']),
            category=random.choice(categories),
            price=round(random.uniform(10.0, 500.0), 2),
            stock=stock_count,
            rating=round(random.uniform(1.0, 5.0), 1)
        )
        products.append(p)
    session.add_all(products)
    
    # 3. Create Orders (e.g., 100)
    # Requirement: At least 10 customers must have multiple orders.
    orders = []
    multi_order_customers = customers[:12] # Guarantee 12 customers have multiple
    
    order_counter = 1
    
    # Give multiple orders to the first 12 customers
    for c in multi_order_customers:
        num_orders = random.randint(2, 5)
        for _ in range(num_orders):
            product = random.choice(products)
            status = random.choice(['processing', 'shipped', 'delivered', 'cancelled'])
            
            created_at = fake.date_time_between(start_date='-1y', end_date='now')
            est_del_date = created_at + timedelta(days=random.randint(3, 10))
            tracking_num = fake.uuid4()[:8].upper() if status in ['shipped', 'delivered'] else None
            
            o = Order(
                order_id=f"O{1000 + order_counter}",
                customer_id=c.customer_id,
                product_id=product.product_id,
                quantity=random.randint(1, 3),
                status=status,
                created_at=created_at,
                estimated_delivery_date=est_del_date,
                tracking_number=tracking_num
            )
            orders.append(o)
            order_counter += 1

    # Give single orders to some other customers
    for c in customers[12:]:
        if random.choice([True, False]): # 50% chance to have an order
            product = random.choice(products)
            status = random.choice(['processing', 'shipped', 'delivered', 'cancelled'])
            
            created_at = fake.date_time_between(start_date='-1y', end_date='now')
            est_del_date = created_at + timedelta(days=random.randint(3, 10))
            tracking_num = fake.uuid4()[:8].upper() if status in ['shipped', 'delivered'] else None
            
            o = Order(
                order_id=f"O{1000 + order_counter}",
                customer_id=c.customer_id,
                product_id=product.product_id,
                quantity=random.randint(1, 3),
                status=status,
                created_at=created_at,
                estimated_delivery_date=est_del_date,
                tracking_number=tracking_num
            )
            orders.append(o)
            order_counter += 1
            
    session.add_all(orders)

    # 4. Create Returns
    # Requirement: return must be linked to an order that has a delivered status.
    returns = []
    delivered_orders = [o for o in orders if o.status == 'delivered']
    
    # Create returns with deterministic statuses to guarantee representation
    statuses = ['approved', 'pending', 'rejected', 'approved', 'pending']
    return_counter = 1
    for i, o in enumerate(delivered_orders):
        if i < len(statuses) or random.random() < 0.3:
            status = statuses[i] if i < len(statuses) else random.choice(['pending', 'approved', 'rejected'])
            refund_amount = None
            if status == 'approved':
                refund_amount = round(o.quantity * next(p.price for p in products if p.product_id == o.product_id), 2)
            
            r = Return(
                return_id=f"R{1000 + return_counter}",
                order_id=o.order_id,
                status=status,
                reason=random.choice(['Defective', 'Changed Mind', 'Wrong Item']),
                refund_amount=refund_amount
            )
            returns.append(r)
            return_counter += 1
            
    session.add_all(returns)
    session.commit()

    print(f"Database seeded successfully!")
    print(f"Customers: {session.query(Customer).count()}")
    print(f"Products: {session.query(Product).count()}")
    print(f"Orders: {session.query(Order).count()}")
    print(f"Returns: {session.query(Return).count()}")

if __name__ == "__main__":
    seed_database()
