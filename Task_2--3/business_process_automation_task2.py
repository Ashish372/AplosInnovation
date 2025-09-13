"""
Demonstration script showing all capabilities of the Restocking System
"""

from restocking_system import RestockingSystem
import json

def main():
    print("🏪 INVENTORY RESTOCKING SYSTEM DEMONSTRATION")
    print("=" * 60)
    
    system = RestockingSystem()
    
    try:
        print("\n📊 Generating comprehensive dummy data...")
        print("- 50 customers")
        print("- 30 products across 6 categories") 
        print("- 10 warehouses in different locations")
        print("- 3 shipping carriers")
        print("- 200 orders over 60 days")
        print("- 300 inventory records (30 products × 10 warehouses)")
        
        system.generate_dummy_data()
        print("✅ Data generation complete!")
        
        print("\n🧮 Analyzing sales data and calculating recommendations...")
        recommendations = system.calculate_restock_recommendations()
        
        print(f"📈 Found {len(recommendations)} products requiring restocking")
        
        print("\n🎯 CORE RECOMMENDATIONS:")
        print("-" * 50)
        print("product_id | warehouse_id | recommended_quantity")
        print("-" * 50)
        
        for rec in recommendations:
            print(f"{rec['product_id']:>10} | {rec['warehouse_id']:>12} | {rec['recommended_restock_quantity']:>17}")
        
        if recommendations:
            print(f"\n📊 DETAILED ANALYSIS OF TOP RECOMMENDATION:")
            print("-" * 50)
            top_rec = recommendations[0]
            print(f"Product: {top_rec['product_id']}")
            print(f"Warehouse: {top_rec['warehouse_id']}")
            print(f"Current Available Stock: {top_rec['current_available_stock']}")
            print(f"Sales Velocity: {top_rec['sales_velocity_per_day']:.2f} units/day")
            print(f"Avg Shipment Time: {top_rec['avg_shipment_time_days']:.1f} days")
            print(f"Reorder Point: {top_rec['reorder_point']:.1f} units")
            print(f"Safety Stock: {top_rec['safety_stock']:.1f} units")
            print(f"Target Stock: {top_rec['target_stock']:.1f} units")
            print(f"Urgency Score: {top_rec['urgency_score']:.1f}%")
            print(f"Recommended Restock: {top_rec['recommended_restock_quantity']} units")
        
        print(f"\n💾 Exporting results...")
        system.export_recommendations_csv()
        
        with open('detailed_recommendations.json', 'w') as f:
            json.dump(recommendations, f, indent=2)
        
        print("✅ Files created:")
        print("  - restock_recommendations.csv")
        print("  - detailed_recommendations.json")
        print("  - inventory.db (SQLite database)")
        
        print(f"\n📋 ALGORITHM SUMMARY:")
        print("-" * 30)
        print("• Sales velocity calculated from last 30 days")
        print("• Shipment times averaged per warehouse")
        print("• Reorder point = velocity × (shipment_time + 7 days)")
        print("• Safety stock = velocity × 14 days") 
        print("• Target stock = safety_stock + velocity × 30 days")
        print("• Recommendations sorted by urgency score")
        
        print(f"\n🎉 Restocking system demonstration complete!")
        
    finally:
        system.close()

if __name__ == "__main__":
    main()