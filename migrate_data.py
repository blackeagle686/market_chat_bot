import pandas as pd
from database import SessionLocal, Category, Product, init_db
import os

def migrate():
    # Initialize database
    init_db()
    
    db = SessionLocal()
    
    # Read Excel file
    excel_file = "market_data.xlsx"
    if not os.path.exists(excel_file):
        print(f"Error: {excel_file} not found.")
        return

    try:
        df = pd.read_excel(excel_file)
        print(f"Read {len(df)} rows from {excel_file}")
        
        # Clean column names (strip whitespace)
        df.columns = [c.strip() for c in df.columns]
        
        # Expected columns: Product Name, Price (EGP), Category, Partition, Variant
        # Mapping if column names are slightly different
        col_map = {
            "Product Name": "name",
            "Price (EGP)": "price",
            "Category": "category",
            "Partition": "partition",
            "Variant": "variant"
        }
        
        # Find unique categories
        if "Category" in df.columns:
            categories = df["Category"].dropna().unique()
            for cat_name in categories:
                # Check if category exists
                cat = db.query(Category).filter(Category.name == cat_name).first()
                if not cat:
                    cat = Category(name=cat_name)
                    db.add(cat)
            db.commit()
            print(f"Added {len(categories)} categories.")

        # Add products
        for _, row in df.iterrows():
            cat_name = row.get("Category")
            cat = db.query(Category).filter(Category.name == cat_name).first()
            
            product = Product(
                name=str(row.get("Product Name", "Unknown")),
                price=float(row.get("Price (EGP)", 0)),
                partition=str(row.get("Partition", "")),
                variant=str(row.get("Variant", "")),
                category_id=cat.id if cat else None
            )
            db.add(product)
            
        db.commit()
        print("Migration completed successfully.")
        
    except Exception as e:
        print(f"Error during migration: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    migrate()
