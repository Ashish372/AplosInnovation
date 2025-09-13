"""
Inventory Restocking Recommendation System

This system analyzes inventory levels, sales data, and shipment times to provide
intelligent restocking recommendations for warehouse management.

Based on the ontology diagram, this system considers:
- Current stock levels vs. thresholds
- Sales velocity from the last 30 days
- Average shipment times from warehouses to customers
"""

import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
import string
from typing import List, Tuple, Dict
import json

class RestockingSystem:
    def __init__(self, db_path: str = "inventory.db"):
        """Initialize the restocking system with database connection."""
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.setup_database()
        
    def setup_database(self):
        """Create database tables based on the ontology schema."""
        cursor = self.conn.cursor()
        
        # Customer table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS customer (
                customer_id TEXT PRIMARY KEY,
                customer_name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                registration_date DATE NOT NULL
            )
        ''')
        
        # Product table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS product (
                product_id TEXT PRIMARY KEY,
                product_name TEXT NOT NULL,
                product_category TEXT NOT NULL,
                unit_price DECIMAL(10,2) NOT NULL
            )
        ''')
        
        # Warehouse table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS warehouse (
                warehouse_id TEXT PRIMARY KEY,
                warehouse_name TEXT NOT NULL,
                location TEXT NOT NULL,
                capacity INTEGER NOT NULL
            )
        ''')
        
        # Carrier table - with CHECK constraint for service_level enum
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS carrier (
                carrier_id TEXT PRIMARY KEY,
                service_level TEXT NOT NULL CHECK (service_level IN ('Standard', 'Express', 'Overnight')),
                avg_delivery_time INTEGER NOT NULL
            )
        ''')
        
        # Order table - with CHECK constraint for order_status enum
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                order_id TEXT PRIMARY KEY,
                customer_id TEXT NOT NULL,
                product_id TEXT NOT NULL,
                order_date DATE NOT NULL,
                order_status TEXT NOT NULL CHECK (order_status IN ('Pending', 'Shipped', 'Delivered', 'Canceled')),
                quantity INTEGER NOT NULL,
                FOREIGN KEY (customer_id) REFERENCES customer(customer_id),
                FOREIGN KEY (product_id) REFERENCES product(product_id)
            )
        ''')
        
        # Inventory table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS inventory (
                product_id TEXT NOT NULL,
                warehouse_id TEXT NOT NULL,
                stock_quantity INTEGER NOT NULL,
                reserved_quantity INTEGER NOT NULL,
                last_updated TIMESTAMP NOT NULL,
                PRIMARY KEY (product_id, warehouse_id),
                FOREIGN KEY (product_id) REFERENCES product(product_id),
                FOREIGN KEY (warehouse_id) REFERENCES warehouse(warehouse_id)
            )
        ''')
        
        # Shipment table - with CHECK constraint for shipment_status enum
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS shipment (
                shipment_id TEXT PRIMARY KEY,
                order_id TEXT NOT NULL,
                warehouse_id TEXT NOT NULL,
                carrier_id TEXT NOT NULL,
                service_level TEXT NOT NULL CHECK (service_level IN ('Standard', 'Express', 'Overnight')),
                shipment_status TEXT NOT NULL CHECK (shipment_status IN ('In Transit', 'Delivered', 'Delayed')),
                ship_date DATE NOT NULL,
                estimated_delivery DATE NOT NULL,
                actual_delivery DATE,
                tracking_number TEXT UNIQUE NOT NULL,
                FOREIGN KEY (order_id) REFERENCES orders(order_id),
                FOREIGN KEY (warehouse_id) REFERENCES warehouse(warehouse_id),
                FOREIGN KEY (carrier_id) REFERENCES carrier(carrier_id)
            )
        ''')
        
        self.conn.commit()
        
    def generate_dummy_data(self):
        """Generate dummy data for all tables (200 rows where applicable)."""
        print("Generating dummy data...")
        
        # Generate Customers (50 customers)
        customers = []
        for i in range(50):
            customer_id = f"C{str(i+1).zfill(3)}"
            customer_name = f"Customer {customer_id}"
            email = f"customer{i+1}@example.com"
            reg_date = datetime.now() - timedelta(days=random.randint(30, 365))
            customers.append((customer_id, customer_name, email, reg_date.date()))
        
        cursor = self.conn.cursor()
        cursor.executemany(
            "INSERT OR REPLACE INTO customer VALUES (?, ?, ?, ?)", customers
        )
        
        # Generate Products (30 products)
        products = []
        categories = ['Electronics', 'Clothing', 'Books', 'Home & Garden', 'Sports', 'Toys']
        for i in range(30):
            product_id = f"P{str(i+1).zfill(3)}"
            product_name = f"Product {product_id}"
            category = random.choice(categories)
            unit_price = round(random.uniform(10.0, 500.0), 2)
            products.append((product_id, product_name, category, unit_price))
        
        cursor.executemany(
            "INSERT OR REPLACE INTO product VALUES (?, ?, ?, ?)", products
        )
        
        # Generate Warehouses (10 warehouses)
        warehouses = []
        locations = ['New York', 'Los Angeles', 'Chicago', 'Houston', 'Phoenix', 
                    'Philadelphia', 'San Antonio', 'San Diego', 'Dallas', 'San Jose']
        for i in range(10):
            warehouse_id = f"W{str(i+1).zfill(2)}"
            warehouse_name = f"Warehouse {warehouse_id}"
            location = locations[i]
            capacity = random.randint(1000, 10000)
            warehouses.append((warehouse_id, warehouse_name, location, capacity))
        
        cursor.executemany(
            "INSERT OR REPLACE INTO warehouse VALUES (?, ?, ?, ?)", warehouses
        )
        
        # Generate Carriers (3 carriers) - Standardized delivery times across all carriers
        carriers = [
            ('CarrierA', 'Express', 2),
            ('CarrierA', 'Standard', 5),
            ('CarrierA', 'Overnight', 1),
            ('CarrierB', 'Express', 2),
            ('CarrierB', 'Standard', 5),
            ('CarrierB', 'Overnight', 1),
            ('CarrierC', 'Express', 2),
            ('CarrierC', 'Standard', 5),
            ('CarrierC', 'Overnight', 1)
        ]
        
        cursor.executemany(
            "INSERT OR REPLACE INTO carrier VALUES (?, ?, ?)", carriers
        )
        
        # Generate Orders (200 orders)
        orders = []
        order_statuses = ['Pending', 'Shipped', 'Delivered', 'Canceled']
        
        for i in range(200):
            order_id = f"O{str(i+1).zfill(4)}"
            customer_id = f"C{str(random.randint(1, 50)).zfill(3)}"
            product_id = f"P{str(random.randint(1, 30)).zfill(3)}"
            order_date = datetime.now() - timedelta(days=random.randint(0, 60))
            status = random.choice(order_statuses)
            quantity = random.randint(1, 10)
            orders.append((order_id, customer_id, product_id, order_date.date(), status, quantity))
        
        cursor.executemany(
            "INSERT OR REPLACE INTO orders VALUES (?, ?, ?, ?, ?, ?)", orders
        )
        
        # Generate Inventory (all product-warehouse combinations)
        inventory = []
        for p in range(1, 31):  # 30 products
            for w in range(1, 11):  # 10 warehouses
                product_id = f"P{str(p).zfill(3)}"
                warehouse_id = f"W{str(w).zfill(2)}"
                stock_quantity = random.randint(0, 500)
                reserved_quantity = random.randint(0, min(50, stock_quantity))
                last_updated = datetime.now()
                inventory.append((product_id, warehouse_id, stock_quantity, 
                                reserved_quantity, last_updated))
        
        cursor.executemany(
            "INSERT OR REPLACE INTO inventory VALUES (?, ?, ?, ?, ?)", inventory
        )
        
        # Generate Shipments (for shipped/delivered orders)
        shipped_orders = cursor.execute(
            "SELECT order_id FROM orders WHERE order_status IN ('Shipped', 'Delivered')"
        ).fetchall()
        
        # Define service levels and their weights for more balanced distribution
        service_levels = ['Express', 'Standard', 'Overnight']
        service_weights = [0.3, 0.5, 0.2]  # 30% Express, 50% Standard, 20% Overnight
        
        shipments = []
        for i, (order_id,) in enumerate(shipped_orders):
            shipment_id = f"S{str(i+1).zfill(4)}"
            warehouse_id = f"W{str(random.randint(1, 10)).zfill(2)}"
            
            # Select service level with weighted distribution
            service_level = random.choices(service_levels, weights=service_weights)[0]
            
            # Get available carriers for this service level
            carrier_options = cursor.execute(
                "SELECT carrier_id, avg_delivery_time FROM carrier WHERE service_level = ?",
                (service_level,)
            ).fetchall()
            
            if carrier_options:
                selected_carrier = random.choice(carrier_options)
                carrier_id = selected_carrier[0]
                base_delivery_time = selected_carrier[1]
            else:
                # Fallback - shouldn't happen with our setup, but just in case
                carrier_id = random.choice(['CarrierA', 'CarrierB', 'CarrierC'])
                base_delivery_time = 3
            
            status = random.choice(['In Transit', 'Delivered', 'Delayed'])
            ship_date = datetime.now() - timedelta(days=random.randint(1, 30))
            
            # Add realistic variability with more conservative estimates
            # Carriers typically promise slightly longer times to ensure on-time delivery
            buffer_days = random.choice([0, 1, 1, 2])  # Usually 1-2 day buffer, sometimes none
            estimated_delivery_days = base_delivery_time + buffer_days
            
            # Actual delivery has some variability but is generally close to carrier's capability
            actual_delivery_variance = random.randint(-1, 2)  # Usually on time or 1-2 days late
            actual_delivery_days = base_delivery_time + actual_delivery_variance
            actual_delivery_days = max(1, actual_delivery_days)  # Minimum 1 day
            
            est_delivery = ship_date + timedelta(days=estimated_delivery_days)
            actual_delivery = None
            if status == 'Delivered':
                actual_delivery = ship_date + timedelta(days=actual_delivery_days)
            tracking_number = f"TRK{random.randint(100000, 999999)}"
            
            shipments.append((shipment_id, order_id, warehouse_id, carrier_id,
                            service_level, status, ship_date.date(), est_delivery.date(),
                            actual_delivery.date() if actual_delivery else None,
                            tracking_number))
        
        cursor.executemany(
            "INSERT OR REPLACE INTO shipment VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            shipments
        )
        
        self.conn.commit()
        print("Dummy data generated successfully!")
        
    def calculate_sales_velocity(self, days: int = 30) -> Dict[Tuple[str, str], float]:
        """Calculate sales velocity (units sold per day) for each product-warehouse combination."""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        query = '''
            SELECT 
                o.product_id,
                s.warehouse_id,
                SUM(o.quantity) as total_sold
            FROM orders o
            JOIN shipment s ON o.order_id = s.order_id
            WHERE o.order_date >= ? AND o.order_status IN ('Shipped', 'Delivered')
            GROUP BY o.product_id, s.warehouse_id
        '''
        
        cursor = self.conn.cursor()
        results = cursor.execute(query, (cutoff_date.date(),)).fetchall()
        
        velocity = {}
        for product_id, warehouse_id, total_sold in results:
            velocity[(product_id, warehouse_id)] = total_sold / days
            
        return velocity
    
    def get_average_shipment_time(self) -> Dict[str, float]:
        """Calculate average shipment time from each warehouse to customers."""
        query = '''
            SELECT 
                warehouse_id,
                AVG(julianday(actual_delivery) - julianday(ship_date)) as avg_days
            FROM shipment 
            WHERE actual_delivery IS NOT NULL
            GROUP BY warehouse_id
        '''
        
        cursor = self.conn.cursor()
        results = cursor.execute(query).fetchall()
        
        shipment_times = {}
        for warehouse_id, avg_days in results:
            shipment_times[warehouse_id] = avg_days if avg_days else 5.0  # Default 5 days
            
        return shipment_times
    
    def get_current_inventory(self) -> Dict[Tuple[str, str], Dict]:
        """Get current inventory levels for all product-warehouse combinations."""
        query = '''
            SELECT 
                product_id,
                warehouse_id,
                stock_quantity,
                reserved_quantity
            FROM inventory
        '''
        
        cursor = self.conn.cursor()
        results = cursor.execute(query).fetchall()
        
        inventory = {}
        for product_id, warehouse_id, stock_qty, reserved_qty in results:
            available_qty = stock_qty - reserved_qty
            inventory[(product_id, warehouse_id)] = {
                'stock_quantity': stock_qty,
                'reserved_quantity': reserved_qty,
                'available_quantity': available_qty
            }
            
        return inventory
    
    def calculate_restock_recommendations(self, 
                                       safety_stock_days: int = 14,
                                       restock_threshold_days: int = 7) -> List[Dict]:
        """
        Calculate restocking recommendations based on:
        - Current stock levels
        - Sales velocity (last 30 days)
        - Average shipment times
        - Safety stock requirements
        """
        print("Calculating restock recommendations...")
        
        # Get required data
        sales_velocity = self.calculate_sales_velocity()
        shipment_times = self.get_average_shipment_time()
        current_inventory = self.get_current_inventory()
        
        recommendations = []
        
        for (product_id, warehouse_id), inventory_data in current_inventory.items():
            available_qty = inventory_data['available_quantity']
            
            # Get sales velocity for this product-warehouse combination
            velocity = sales_velocity.get((product_id, warehouse_id), 0.1)  # Default low velocity
            
            # Get average shipment time for this warehouse
            avg_shipment_time = shipment_times.get(warehouse_id, 5.0)  # Default 5 days
            
            # Calculate required stock levels
            # Safety stock = velocity * safety_stock_days
            safety_stock = velocity * safety_stock_days
            
            # Reorder point = velocity * (shipment_time + restock_threshold_days)
            reorder_point = velocity * (avg_shipment_time + restock_threshold_days)
            
            # Check if restock is needed
            if available_qty <= reorder_point:
                # Calculate recommended restock quantity
                # Target stock = safety stock + velocity * replenishment_period
                replenishment_period = 30  # Plan for 30 days
                target_stock = safety_stock + (velocity * replenishment_period)
                
                recommended_qty = max(1, int(target_stock - available_qty))
                
                recommendations.append({
                    'product_id': product_id,
                    'warehouse_id': warehouse_id,
                    'recommended_restock_quantity': recommended_qty,
                    'current_available_stock': available_qty,
                    'sales_velocity_per_day': round(velocity, 2),
                    'avg_shipment_time_days': round(avg_shipment_time, 1),
                    'reorder_point': round(reorder_point, 1),
                    'safety_stock': round(safety_stock, 1),
                    'target_stock': round(target_stock, 1),
                    'urgency_score': round((reorder_point - available_qty) / reorder_point * 100, 1)
                })
        
        # Sort by urgency score (highest first)
        recommendations.sort(key=lambda x: x['urgency_score'], reverse=True)
        
        return recommendations
    
    def generate_restock_report(self) -> str:
        """Generate a comprehensive restocking report."""
        recommendations = self.calculate_restock_recommendations()
        
        report = []
        report.append("=" * 80)
        report.append("INVENTORY RESTOCKING RECOMMENDATIONS REPORT")
        report.append("=" * 80)
        report.append(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Total recommendations: {len(recommendations)}")
        report.append("")
        
        if not recommendations:
            report.append("No restocking needed at this time.")
            return "\n".join(report)
        
        report.append("TOP PRIORITY RESTOCKS:")
        report.append("-" * 50)
        
        for i, rec in enumerate(recommendations[:10], 1):  # Top 10
            report.append(f"{i:2d}. Product: {rec['product_id']} | Warehouse: {rec['warehouse_id']}")
            report.append(f"    Recommended Quantity: {rec['recommended_restock_quantity']:,}")
            report.append(f"    Current Stock: {rec['current_available_stock']}")
            report.append(f"    Urgency Score: {rec['urgency_score']}%")
            report.append(f"    Sales Velocity: {rec['sales_velocity_per_day']}/day")
            report.append("")
        
        report.append("\nSUMMARY BY WAREHOUSE:")
        report.append("-" * 30)
        
        warehouse_summary = {}
        for rec in recommendations:
            wid = rec['warehouse_id']
            if wid not in warehouse_summary:
                warehouse_summary[wid] = {'count': 0, 'total_qty': 0}
            warehouse_summary[wid]['count'] += 1
            warehouse_summary[wid]['total_qty'] += rec['recommended_restock_quantity']
        
        for warehouse_id, summary in warehouse_summary.items():
            report.append(f"{warehouse_id}: {summary['count']} products, {summary['total_qty']:,} total units")
        
        return "\n".join(report)
    
    def export_recommendations_csv(self, filepath: str = "restock_recommendations.csv"):
        """Export recommendations to CSV file."""
        recommendations = self.calculate_restock_recommendations()
        
        if not recommendations:
            print("No recommendations to export.")
            return
        
        df = pd.DataFrame(recommendations)
        df.to_csv(filepath, index=False)
        print(f"Recommendations exported to {filepath}")
    
    def close(self):
        """Close database connection."""
        self.conn.close()

def main():
    """Main function to run the restocking system."""
    print("Inventory Restocking Recommendation System")
    print("=" * 50)
    
    # Initialize system
    system = RestockingSystem()
    
    try:
        # Generate dummy data
        system.generate_dummy_data()
        
        # Generate and display report
        report = system.generate_restock_report()
        print(report)
        
        # Export to CSV
        system.export_recommendations_csv()
        
        # Also save detailed recommendations as JSON
        recommendations = system.calculate_restock_recommendations()
        with open('detailed_recommendations.json', 'w') as f:
            json.dump(recommendations, f, indent=2)
        print("Detailed recommendations saved to detailed_recommendations.json")
        
    finally:
        system.close()

if __name__ == "__main__":
    main()