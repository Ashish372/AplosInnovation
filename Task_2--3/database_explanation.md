# What is inventory.db?

## Overview

`inventory.db` is a **SQLite database file** that serves as the core data storage for the Inventory Restocking Recommendation System. It contains all the structured data (randomly generated) needed to analyze inventory levels, sales patterns, and generate intelligent restocking recommendations.

## Database Schema

Based on the ontology diagram, the database contains 7 main tables:

### Core Business Entities

1. **`customer`** - Customer information
   - `customer_id` (Primary Key, Pattern: C001-C050)
   - `customer_name`
   - `email`
   - `registration_date`

2. **`product`** - Product catalog
   - `product_id` (Primary Key, Pattern: P001-P030)
   - `product_name`
   - `product_category`
   - `unit_price`

3. **`warehouse`** - Storage facilities
   - `warehouse_id` (Primary Key, Pattern: W01-W10)
   - `warehouse_name`
   - `location`
   - `capacity`

4. **`carrier`** - Shipping providers
   - `carrier_id` (Primary Key: CarrierA, CarrierB, CarrierC)
   - `carrier_name`
   - `service_level`
   - `avg_delivery_time`

### Transaction and Operational Tables

5. **`orders`** - Customer orders (200 records)
   - `order_id` (Primary Key, Pattern: O0001-O0200)
   - `customer_id` (Foreign Key)
   - `product_id` (Foreign Key)
   - `order_date`
   - `order_status`
   - `quantity`

6. **`inventory`** - Current stock levels (300 records: 30 products × 10 warehouses)
   - `product_id` (Foreign Key)
   - `warehouse_id` (Foreign Key)
   - `stock_quantity`
   - `reserved_quantity`
   - `last_updated`

7. **`shipment`** - Delivery tracking
   - `shipment_id` (Primary Key)
   - `order_id` (Foreign Key)
   - `warehouse_id` (Foreign Key)
   - `carrier_id` (Foreign Key)
   - `service_level` (Foreign Key)
   - `shipment_status`
   - `ship_date`
   - `estimated_delivery`
   - `actual_delivery`
   - `tracking_number`

## Data Generation

The database is populated with realistic dummy data:

- **50 customers** with valid email patterns
- **30 products** across 6 categories (Electronics, Clothing, Books, etc.)
- **10 warehouses** in major US cities
- **3 carriers** with different service levels
- **200 orders** spanning the last 60 days
- **300 inventory records** covering all product-warehouse combinations
- **Shipment records** for all shipped/delivered orders

## File Location and Size

- **Created**: Automatically when the restocking system runs
- **Contains**: ~500+ records across 7 tables
- **Used By**:
  - `restocking_system.py` (main system)
  - `business_insights_decision_making_task3.py` (analytics and visualizations)
  - `business_process_automation_task2.py` (demonstration)
