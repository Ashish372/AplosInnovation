"""
Supply Chain Analytics Module (Headless - saves visualizations without showing)

This module provides comprehensive analytics and insights with automatic file saving:
1. Calculate average delivery time per carrier
2. Identify top 5 best-selling products in the last quarter
3. Create visualizations showing inventory shortages per warehouse
4. Generate actionable supply chain optimization insights
"""

import sqlite3
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import json

class SupplyChainAnalytics:
    def __init__(self, db_path: str = "inventory.db"):
        """Initialize the supply chain analytics system."""
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        
    def calculate_carrier_delivery_performance(self) -> pd.DataFrame:
        """Calculate average delivery time for shipments per carrier."""
        query = '''
            SELECT
                s.carrier_id,
                s.service_level,
                COUNT(s.shipment_id) as total_shipments,
                AVG(
                    julianday(s.actual_delivery) - julianday(s.ship_date)
                ) as avg_delivery_days,
                MIN(
                    julianday(s.actual_delivery) - julianday(s.ship_date)
                ) as min_delivery_days,
                MAX(
                    julianday(s.actual_delivery) - julianday(s.ship_date)
                ) as max_delivery_days,
                AVG(
                    julianday(s.actual_delivery) - julianday(s.estimated_delivery)
                ) as avg_delay_days,
                COUNT(CASE WHEN s.actual_delivery <= s.estimated_delivery THEN 1 END) * 100.0 / COUNT(*) as on_time_percentage
            FROM shipment s
            WHERE s.actual_delivery IS NOT NULL
            GROUP BY s.carrier_id, s.service_level
            ORDER BY s.carrier_id, s.service_level
        '''
        
        df = pd.read_sql_query(query, self.conn)
        
        # Round numerical values for better display
        numerical_cols = ['avg_delivery_days', 'min_delivery_days', 'max_delivery_days', 
                         'avg_delay_days', 'on_time_percentage']
        for col in numerical_cols:
            if col in df.columns:
                df[col] = df[col].round(2)
        
        return df
    
    def identify_top_selling_products(self, days: int = 90) -> pd.DataFrame:
        """Identify top 5 best-selling products in the last quarter (90 days)."""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        query = '''
            SELECT 
                p.product_id,
                p.product_name,
                p.product_category,
                p.unit_price,
                SUM(o.quantity) as total_units_sold,
                COUNT(DISTINCT o.order_id) as total_orders,
                SUM(o.quantity * p.unit_price) as total_revenue,
                AVG(o.quantity) as avg_order_quantity,
                COUNT(DISTINCT o.customer_id) as unique_customers
            FROM product p
            JOIN orders o ON p.product_id = o.product_id
            WHERE o.order_date >= ? 
                AND o.order_status IN ('Shipped', 'Delivered')
            GROUP BY p.product_id, p.product_name, p.product_category, p.unit_price
            ORDER BY total_units_sold DESC
            LIMIT 5
        '''
        
        df = pd.read_sql_query(query, self.conn, params=(cutoff_date.date(),))
        
        # Round numerical values
        df['total_revenue'] = df['total_revenue'].round(2)
        df['avg_order_quantity'] = df['avg_order_quantity'].round(2)
        df['unit_price'] = df['unit_price'].round(2)
        
        return df
    
    def analyze_inventory_shortages(self) -> pd.DataFrame:
        """Analyze inventory shortages per warehouse based on demand trends."""
        query = '''
            WITH demand_analysis AS (
                SELECT 
                    o.product_id,
                    s.warehouse_id,
                    COUNT(*) as order_frequency,
                    SUM(o.quantity) as total_demand_30days,
                    AVG(o.quantity) as avg_demand_per_order,
                    SUM(o.quantity) / 30.0 as daily_demand_rate
                FROM orders o
                JOIN shipment s ON o.order_id = s.order_id
                WHERE o.order_date >= date('now', '-30 days')
                    AND o.order_status IN ('Shipped', 'Delivered')
                GROUP BY o.product_id, s.warehouse_id
            ),
            current_inventory AS (
                SELECT 
                    i.product_id,
                    i.warehouse_id,
                    i.stock_quantity,
                    i.reserved_quantity,
                    (i.stock_quantity - i.reserved_quantity) as available_stock
                FROM inventory i
            )
            SELECT 
                w.warehouse_id,
                w.warehouse_name,
                w.location,
                ci.product_id,
                p.product_name,
                p.product_category,
                ci.available_stock,
                COALESCE(da.daily_demand_rate, 0.1) as daily_demand_rate,
                COALESCE(da.total_demand_30days, 0) as demand_last_30days,
                CASE
                    WHEN ci.available_stock = 0 THEN 0
                    WHEN COALESCE(da.daily_demand_rate, 0.1) > 0
                    THEN ci.available_stock / COALESCE(da.daily_demand_rate, 0.1)
                    ELSE 999
                END as days_of_stock,
                CASE 
                    WHEN ci.available_stock = 0 THEN 'OUT_OF_STOCK'
                    WHEN ci.available_stock / COALESCE(da.daily_demand_rate, 0.1) < 7 THEN 'CRITICAL'
                    WHEN ci.available_stock / COALESCE(da.daily_demand_rate, 0.1) < 14 THEN 'LOW'
                    ELSE 'ADEQUATE'
                END as stock_status
            FROM warehouse w
            CROSS JOIN current_inventory ci
            LEFT JOIN demand_analysis da ON ci.product_id = da.product_id 
                AND ci.warehouse_id = da.warehouse_id
            LEFT JOIN product p ON ci.product_id = p.product_id
            WHERE ci.warehouse_id = w.warehouse_id
            ORDER BY w.warehouse_id, 
                CASE stock_status 
                    WHEN 'OUT_OF_STOCK' THEN 1 
                    WHEN 'CRITICAL' THEN 2 
                    WHEN 'LOW' THEN 3 
                    ELSE 4 
                END,
                da.daily_demand_rate DESC
        '''
        
        df = pd.read_sql_query(query, self.conn)
        
        # Round numerical values
        df['daily_demand_rate'] = df['daily_demand_rate'].round(3)
        df['days_of_stock'] = df['days_of_stock'].round(1)
        
        return df
    
    def create_all_visualizations(self):
        """Create all visualizations and save them to files."""
        print("📊 Creating carrier performance visualization...")
        carrier_df = self.calculate_carrier_delivery_performance()
        
        fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(20, 6))
        fig.suptitle('Carrier Performance Analysis', fontsize=16, fontweight='bold')
        
        # Define colors for service levels
        service_level_colors = {'Express': '#ff7f0e', 'Standard': '#2ca02c', 'Overnight': '#d62728'}
        
        # 1. Delivery Days Range (Min-Max) by Carrier
        carrier_stats = carrier_df.groupby('carrier_id').agg({
            'avg_delivery_days': 'mean',
            'min_delivery_days': 'min',
            'max_delivery_days': 'max'
        }).reset_index()
        
        x_pos = np.arange(len(carrier_stats))
        bars1 = ax1.bar(x_pos, carrier_stats['avg_delivery_days'],
                       color=['#1f77b4', '#ff7f0e', '#2ca02c'], alpha=0.7, label='Average')
        
        ax1.set_title('Average Delivery Days by Carrier')
        ax1.set_ylabel('Delivery Days')
        ax1.set_xlabel('Carrier')
        ax1.set_xticks(x_pos)
        ax1.set_xticklabels(carrier_stats['carrier_id'])
        ax1.grid(axis='y', alpha=0.3)
        
        # Add value labels
        for i, (bar, avg_days) in enumerate(zip(bars1, carrier_stats['avg_delivery_days'])):
            ax1.text(bar.get_x() + bar.get_width()/2., avg_days + 0.2,
                    f'{avg_days:.1f}', ha='center', va='bottom', fontweight='bold')
        
        # 2. Service Level Count by Carrier - Grouped Bar Chart
        service_counts = carrier_df.groupby(['carrier_id', 'service_level'])['total_shipments'].sum().reset_index()
        service_pivot = service_counts.pivot(index='carrier_id', columns='service_level', values='total_shipments').fillna(0)
        
        # Ensure all service levels are represented
        for service in ['Express', 'Standard', 'Overnight']:
            if service not in service_pivot.columns:
                service_pivot[service] = 0
        
        # Reorder columns to match service levels
        service_pivot = service_pivot[['Express', 'Standard', 'Overnight']]
        
        x_carrier = np.arange(len(service_pivot.index))
        width = 0.25
        
        for i, service in enumerate(['Express', 'Standard', 'Overnight']):
            counts = service_pivot[service].values
            bars = ax2.bar(x_carrier + i*width, counts, width,
                          label=service, color=service_level_colors[service])
            
            # Add value labels on bars
            for bar, count in zip(bars, counts):
                if count > 0:
                    ax2.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 0.2,
                            f'{int(count)}', ha='center', va='bottom', fontweight='bold')
        
        ax2.set_title('Service Level Shipment Count by Carrier')
        ax2.set_ylabel('Number of Shipments')
        ax2.set_xlabel('Carrier')
        ax2.set_xticks(x_carrier + width)
        ax2.set_xticklabels(service_pivot.index)
        ax2.legend()
        ax2.grid(axis='y', alpha=0.3)
        
        # 3. On-Time Delivery Percentage by Carrier
        carrier_ontime = carrier_df.groupby('carrier_id')['on_time_percentage'].mean().reset_index()
        bars3 = ax3.bar(carrier_ontime['carrier_id'], carrier_ontime['on_time_percentage'],
                       color=['#1f77b4', '#ff7f0e', '#2ca02c'], alpha=0.8)
        
        ax3.set_title('On-Time Delivery Percentage by Carrier')
        ax3.set_ylabel('On-Time Delivery %')
        ax3.set_xlabel('Carrier')
        ax3.set_ylim(0, 100)
        ax3.grid(axis='y', alpha=0.3)
        
        # Add value labels and percentage formatting
        for bar, percentage in zip(bars3, carrier_ontime['on_time_percentage']):
            ax3.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 1,
                    f'{percentage:.1f}%', ha='center', va='bottom', fontweight='bold')
        
        # Add horizontal reference lines for performance benchmarks
        ax3.axhline(y=95, color='green', linestyle='--', alpha=0.7, label='Excellent (95%+)')
        ax3.axhline(y=80, color='orange', linestyle='--', alpha=0.7, label='Good (80%+)')
        ax3.axhline(y=60, color='red', linestyle='--', alpha=0.7, label='Poor (<60%)')
        ax3.legend(loc='upper right', fontsize=8)
        
        plt.tight_layout()
        plt.savefig('carrier_performance_analysis.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        print("📊 Creating top products visualization...")
        products_df = self.identify_top_selling_products()
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
        fig.suptitle('Top 5 Best-Selling Products (Last 90 Days)', fontsize=16, fontweight='bold')
        
        # Define color palette for product categories
        category_colors = {
            'Electronics': '#1f77b4',      # Blue
            'Clothing': '#ff7f0e',         # Orange
            'Books': '#2ca02c',            # Green
            'Home & Garden': '#d62728',    # Red
            'Sports': '#9467bd',           # Purple
            'Toys': '#8c564b',             # Brown
            'Food & Beverage': '#e377c2',  # Pink
            'Health & Beauty': '#7f7f7f',  # Gray
            'Automotive': '#bcbd22',       # Olive
            'Office Supplies': '#17becf'   # Cyan
        }
        
        # Get colors for each product based on category
        product_colors = [category_colors.get(category, '#1f77b4') for category in products_df['product_category']]
        
        # 1. Units Sold
        bars1 = ax1.barh(products_df['product_name'], products_df['total_units_sold'],
                        color=product_colors, alpha=0.8)
        ax1.set_title('Total Units Sold')
        ax1.set_xlabel('Units')
        for i, bar in enumerate(bars1):
            width = bar.get_width()
            ax1.text(width + 0.5, bar.get_y() + bar.get_height()/2.,
                    f'{int(width)}', ha='left', va='center')
        
        # 2. Revenue Generated
        bars2 = ax2.barh(products_df['product_name'], products_df['total_revenue'],
                        color=product_colors, alpha=0.8)
        ax2.set_title('Total Revenue Generated')
        ax2.set_xlabel('Revenue ($)')
        for i, bar in enumerate(bars2):
            width = bar.get_width()
            ax2.text(width + 10, bar.get_y() + bar.get_height()/2.,
                    f'${width:.0f}', ha='left', va='center')
        
        # Add category legend
        unique_categories = products_df['product_category'].unique()
        legend_handles = [plt.Rectangle((0,0),1,1, color=category_colors.get(cat, '#1f77b4'), alpha=0.8)
                         for cat in unique_categories]
        fig.legend(legend_handles, unique_categories, loc='upper center', bbox_to_anchor=(0.5, 0.02),
                  ncol=len(unique_categories), fontsize=10, title='Product Categories')
        
        # Adjust layout to make room for legend
        plt.subplots_adjust(bottom=0.15)
        
        plt.tight_layout()
        plt.savefig('top_products_analysis.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        print("📊 Creating inventory shortage visualization...")
        shortage_df = self.analyze_inventory_shortages()
        
        # Create summary by warehouse and status
        shortage_summary = shortage_df.groupby(['warehouse_name', 'stock_status']).size().reset_index(name='count')
        shortage_pivot = shortage_summary.pivot(index='warehouse_name', columns='stock_status', values='count').fillna(0)
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
        fig.suptitle('Inventory Shortage Analysis by Warehouse', fontsize=16, fontweight='bold')
        
        # 1. Stacked bar chart of stock status by warehouse
        colors = {'OUT_OF_STOCK': '#d62728', 'CRITICAL': '#ff7f0e', 'LOW': '#ffbb78', 'ADEQUATE': '#2ca02c'}
        shortage_pivot.plot(kind='bar', stacked=True, ax=ax1,
                           color=[colors.get(col, '#1f77b4') for col in shortage_pivot.columns])
        ax1.set_title('Stock Status Distribution by Warehouse')
        ax1.set_ylabel('Number of Products')
        ax1.set_xlabel('Warehouse')
        ax1.legend(title='Stock Status')
        ax1.tick_params(axis='x', rotation=45)
        
        # 2. Products in Shortage by Warehouse (table format)
        ax2.axis('off')
        ax2.set_title('Products in Shortage by Warehouse', fontweight='bold', pad=20)
        
        # Get shortage items (OUT_OF_STOCK, CRITICAL, LOW)
        shortage_items = shortage_df[shortage_df['stock_status'].isin(['OUT_OF_STOCK', 'CRITICAL', 'LOW'])]
        
        if len(shortage_items) > 0:
            # Group by warehouse and create text summary - use same order as bar chart
            y_pos = 0.95
            # Use the same warehouse order as the bar chart (shortage_pivot.index)
            warehouse_order = shortage_pivot.index.tolist()
            shortage_warehouses = shortage_items['warehouse_name'].unique()
            
            # Only include warehouses that have shortages, but in the same order as the chart
            ordered_shortage_warehouses = [w for w in warehouse_order if w in shortage_warehouses]
            
            for warehouse in ordered_shortage_warehouses:
                warehouse_shortages = shortage_items[shortage_items['warehouse_name'] == warehouse]
                
                # Warehouse header - better aligned
                ax2.text(0.02, y_pos, f"📦 {warehouse}:", fontweight='bold', fontsize=12,
                        transform=ax2.transAxes, color='#2c3e50')
                y_pos -= 0.08
                
                # Check if this warehouse has any shortages
                has_shortages = False
                
                # List products by status with better formatting
                for status in ['OUT_OF_STOCK', 'CRITICAL', 'LOW']:
                    status_items = warehouse_shortages[warehouse_shortages['stock_status'] == status]
                    if len(status_items) > 0:
                        has_shortages = True
                        status_color = colors.get(status, '#000000')
                        status_display = status.replace('_', ' ')
                        ax2.text(0.06, y_pos, f"⚠️ {status_display}:", fontweight='bold',
                                color=status_color, fontsize=10, transform=ax2.transAxes)
                        y_pos -= 0.06
                        
                        for _, item in status_items.iterrows():
                            stock_info = f"({int(item['available_stock'])} units)"
                            ax2.text(0.10, y_pos, f"• {item['product_name']} {stock_info}",
                                    fontsize=9, transform=ax2.transAxes, color='#34495e')
                            y_pos -= 0.045
                        y_pos -= 0.02
                
                # If no shortages for this warehouse, show "No shortages"
                if not has_shortages:
                    ax2.text(0.06, y_pos, "✅ No shortages", fontsize=10,
                            transform=ax2.transAxes, color='#27ae60')
                    y_pos -= 0.06
                
                y_pos -= 0.04  # Extra space between warehouses
                
                if y_pos < 0.1:  # Stop if we're running out of space
                    break
        else:
            ax2.text(0.5, 0.5, 'No products in shortage status',
                    ha='center', va='center', fontsize=12, transform=ax2.transAxes)
        
        plt.tight_layout()
        plt.savefig('inventory_shortage_analysis.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        return carrier_df, products_df, shortage_df
    
    def generate_supply_chain_insights_report(self) -> str:
        """Generate comprehensive supply chain optimization insights report."""
        print("🔍 Generating Supply Chain Analytics Report...")
        
        # Get all analytics data and create visualizations
        carrier_df, products_df, shortage_df = self.create_all_visualizations()
        
        # Calculate key metrics
        total_revenue = products_df['total_revenue'].sum()
        avg_delivery_time = carrier_df['avg_delivery_days'].mean()
        critical_shortages = len(shortage_df[shortage_df['stock_status'].isin(['OUT_OF_STOCK', 'CRITICAL'])])
        
        # Find best overall carrier (average performance across all service levels)
        carrier_avg_performance = carrier_df.groupby('carrier_id')['on_time_percentage'].mean()
        best_carrier = carrier_avg_performance.idxmax()
        
        report = []
        report.append("=" * 80)
        report.append("SUPPLY CHAIN OPTIMIZATION INSIGHTS REPORT")
        report.append("=" * 80)
        report.append(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # Executive Summary
        report.append("📋 EXECUTIVE SUMMARY")
        report.append("-" * 30)
        report.append(f"• Total revenue from top 5 products: ${total_revenue:,.2f}")
        report.append(f"• Average delivery time per carrier: {avg_delivery_time:.1f} days")
        report.append(f"• Critical inventory shortages identified: {critical_shortages} items")
        report.append(f"• Best performing carrier: {best_carrier}")
        report.append("")
        
        # Carrier Performance Analysis - Organized by Carrier
        report.append("🚚 CARRIER PERFORMANCE ANALYSIS")
        report.append("-" * 40)
        
        for carrier in sorted(carrier_df['carrier_id'].unique()):
            carrier_data = carrier_df[carrier_df['carrier_id'] == carrier]
            report.append(f"• {carrier}:")
            
            # Show performance for each service level this carrier handles
            for _, row in carrier_data.iterrows():
                report.append(f"  - {row['service_level']}: {row['avg_delivery_days']:.1f} days avg, {row['on_time_percentage']:.1f}% on-time, {row['total_shipments']} shipments")
            
            # Calculate overall average for this carrier
            avg_delivery = carrier_data['avg_delivery_days'].mean()
            avg_ontime = carrier_data['on_time_percentage'].mean()
            total_shipments = carrier_data['total_shipments'].sum()
            report.append(f"  → Overall Average: {avg_delivery:.1f} days, {avg_ontime:.1f}% on-time, {total_shipments} total shipments")
            report.append("")
        
        # Top Products Analysis
        report.append("🏆 TOP 5 BEST-SELLING PRODUCTS (Last 90 Days)")
        report.append("-" * 50)
        for i, (_, row) in enumerate(products_df.iterrows(), 1):
            report.append(f"{i}. {row['product_name']} ({row['product_category']})")
            report.append(f"   - Units sold: {row['total_units_sold']:,}")
            report.append(f"   - Revenue: ${row['total_revenue']:,.2f}")
            report.append(f"   - Unique customers: {row['unique_customers']}")
        report.append("")
        
        # Inventory Shortage Analysis
        report.append("⚠️  INVENTORY SHORTAGE ANALYSIS")
        report.append("-" * 35)
        
        # Group by warehouse
        shortage_by_warehouse = shortage_df.groupby(['warehouse_name', 'stock_status']).size().unstack(fill_value=0)
        
        for warehouse in shortage_by_warehouse.index:
            report.append(f"• {warehouse}:")
            if 'OUT_OF_STOCK' in shortage_by_warehouse.columns:
                out_of_stock = shortage_by_warehouse.loc[warehouse, 'OUT_OF_STOCK']
                if out_of_stock > 0:
                    report.append(f"  - Out of stock: {out_of_stock} products")
            if 'CRITICAL' in shortage_by_warehouse.columns:
                critical = shortage_by_warehouse.loc[warehouse, 'CRITICAL']
                if critical > 0:
                    report.append(f"  - Critical (< 7 days): {critical} products")
            if 'LOW' in shortage_by_warehouse.columns:
                low = shortage_by_warehouse.loc[warehouse, 'LOW']
                if low > 0:
                    report.append(f"  - Low stock (< 14 days): {low} products")
        report.append("")
        
        # Key Recommendations
        report.append("💡 KEY RECOMMENDATIONS")
        report.append("-" * 25)
        
        # Carrier recommendations - use overall carrier averages for consistency
        carrier_avg_performance = carrier_df.groupby('carrier_id')['on_time_percentage'].mean()
        worst_carrier_id = carrier_avg_performance.idxmin()
        worst_carrier_performance = carrier_avg_performance.min()
        best_carrier_performance = carrier_avg_performance.max()
        
        report.append("🚚 Carrier Optimization:")
        report.append(f"• Consider renegotiating with {worst_carrier_id} (lowest on-time: {worst_carrier_performance:.1f}%)")
        report.append(f"• Leverage {best_carrier} for critical deliveries (best on-time: {best_carrier_performance:.1f}%)")
        
        # Product recommendations
        report.append(f"\n🏆 Product Focus:")
        report.append(f"• Consider expanding {products_df['product_category'].mode()[0]} category")
        
        # Inventory recommendations
        critical_warehouses = shortage_df[shortage_df['stock_status'] == 'OUT_OF_STOCK']['warehouse_name'].unique()
        if len(critical_warehouses) > 0:
            report.append(f"\n⚠️  Urgent Inventory Actions:")
            for warehouse in critical_warehouses[:3]:  # Top 3 most critical
                report.append(f"• Immediate restocking required for {warehouse}")
        
        report.append(f"\n📊 VISUALIZATION FILES CREATED:")
        report.append("-" * 35)
        report.append("• carrier_performance_analysis.png")
        report.append("• top_products_analysis.png") 
        report.append("• inventory_shortage_analysis.png")
        
        return "\n".join(report)
    
    def export_analytics_data(self):
        """Export all analytics data to files."""
        # Export carrier performance
        carrier_df = self.calculate_carrier_delivery_performance()
        carrier_df.to_csv('carrier_performance_data.csv', index=False)
        
        # Export top products
        products_df = self.identify_top_selling_products()
        products_df.to_csv('top_products_data.csv', index=False)
        
        # Export inventory analysis
        inventory_df = self.analyze_inventory_shortages()
        inventory_df.to_csv('inventory_shortage_data.csv', index=False)
        
        print("📁 Analytics data exported:")
        print("  - carrier_performance_data.csv")
        print("  - top_products_data.csv")
        print("  - inventory_shortage_data.csv")
    
    def close(self):
        """Close database connection."""
        self.conn.close()

def main():
    """Main function to run supply chain analytics."""
    print("🏭 Supply Chain Optimization Analytics (Headless Mode)")
    print("=" * 60)
    
    # Initialize analytics system
    analytics = SupplyChainAnalytics()
    
    try:
        # Generate comprehensive report
        report = analytics.generate_supply_chain_insights_report()
        print(report)
        
        # Export data
        analytics.export_analytics_data()
        
        # Save report to file with UTF-8 encoding to handle emojis
        with open('supply_chain_insights_report.txt', 'w', encoding='utf-8') as f:
            f.write(report)
        print("\n📄 Full report saved to: supply_chain_insights_report.txt")
        
    finally:
        analytics.close()

if __name__ == "__main__":
    main()