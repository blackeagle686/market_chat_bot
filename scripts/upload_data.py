import argparse
import os
import shutil
import pandas as pd
from database import SessionLocal, Category, Product, init_db


COLUMN_MAP = {
    "name": ["Product Name", "Name", "product", "item", "product_name", "Product Name (Brand)"],
    "price": ["Price (EGP)", "Price", "Unit Price", "price_egp", "price"],
    "category": ["Category", "Section", "Group", "category", "category_name", "Unnamed: 4"],
    "partition": ["Partition", "Subcategory", "partition", "partition_name"],
    "variant": ["Variant", "Variant Name", "variant", "option", "Brand"],
    "category_description": ["Category Description", "Category Details", "Description", "category_description"],
    "category_image": ["Image URL", "Category Image", "Image", "image_url"]
}


def normalize_columns(columns):
    normalized = {col.strip(): col.strip() for col in columns}
    return normalizedUU


def find_column(df_columns, names):
    for name in names:
        if name in df_columns:
            return name
        lower = name.lower()
        for col in df_columns:
            if col.lower() == lower:
                return col
    return None


def map_columns(df):
    mapped = {}
    for key, names in COLUMN_MAP.items():
        col = find_column(df.columns, names)
        if col:
            mapped[key] = col
    return mapped


def load_excel(excel_file, sheet_name=None):
    df_or_dict = pd.read_excel(excel_file, sheet_name=sheet_name)
    if isinstance(df_or_dict, dict):
        # Multiple sheets, pick the first one
        sheet_names = list(df_or_dict.keys())
        print(f"Multiple sheets found: {sheet_names}. Using the first sheet: '{sheet_names[0]}'")
        return df_or_dict[sheet_names[0]]
    return df_or_dict


def get_value(row, mapped_columns, key, default=""):
    col = mapped_columns.get(key)
    if col is None:
        return default
    value = row.get(col)
    if pd.isna(value):
        return default
    return value


def create_category(db, name, description=None, image_url=None):
    category = db.query(Category).filter(Category.name == name).first()
    if category:
        updated = False
        if description and not category.description:
            category.description = description
            updated = True
        if image_url and not category.image_url:
            category.image_url = image_url
            updated = True
        if updated:
            db.add(category)
        return category

    category = Category(name=name, description=description, image_url=image_url)
    db.add(category)
    db.flush()
    return category


def create_product(db, mapped_columns, row, category_id, image_url=None):
    product_name = str(get_value(row, mapped_columns, "name", "")).strip()
    if not product_name:
        return None

    price_raw = get_value(row, mapped_columns, "price", 0)
    try:
        price = float(price_raw)
    except (TypeError, ValueError):
        price = 0.0

    variant = str(get_value(row, mapped_columns, "variant", "")).strip()
    partition = str(get_value(row, mapped_columns, "partition", "")).strip()

    existing = db.query(Product).filter(
        Product.name == product_name,
        Product.variant == variant,
        Product.category_id == category_id
    ).first()

    if existing:
        existing.price = price
        existing.partition = partition
        if image_url:
            existing.image_url = image_url
        db.add(existing)
        return existing

    product = Product(
        name=product_name,
        price=price,
        variant=variant,
        partition=partition,
        category_id=category_id,
        image_url=image_url
    )
    db.add(product)
    return product


def upload_data(excel_file, sheet_name=None):
    if not os.path.exists(excel_file):
        raise FileNotFoundError(f"Excel file not found: {excel_file}")

    init_db()
    db = SessionLocal()
    try:
        df = load_excel(excel_file, sheet_name=sheet_name)
        df.columns = [str(c).strip() for c in df.columns]
        mapped_columns = map_columns(df)

        print(f"Loaded {len(df)} rows from '{excel_file}'.")
        print(f"Available columns: {list(df.columns)}")
        print("Mapped columns:")
        for key, col in mapped_columns.items():
            print(f"  {key}: {col}")

        if "name" not in mapped_columns or "price" not in mapped_columns or "category" not in mapped_columns:
            print("Column mapping failed. Please check your Excel file has columns similar to:")
            for key, names in COLUMN_MAP.items():
                print(f"  {key}: {names}")
            raise ValueError(
                "Required columns are missing. Expected at least: Product Name, Price, Category."
            )

        # Show sample data for debugging
        print("\nSample data (first 5 rows):")
        for i in range(min(5, len(df))):
            row = df.iloc[i]
            print(f"Row {i+1}:")
            for key, col in mapped_columns.items():
                value = get_value(row, mapped_columns, key, "")
                print(f"  {key}: '{value}'")
            print()

        categories_cache = {}
        created_categories = 0
        created_products = 0
        updated_products = 0

        # Directory for product images
        image_source_dir = os.path.join("market_image", "New folder")
        image_target_dir = os.path.join("static", "uploads")
        os.makedirs(image_target_dir, exist_ok=True)

        # Get and sort all images numerically
        all_images = []
        if os.path.exists(image_source_dir):
            import re
            def natural_sort_key(s):
                return [int(text) if text.isdigit() else text.lower() for text in re.split('([0-9]+)', s)]
            
            all_images = [f for f in os.listdir(image_source_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
            all_images.sort(key=natural_sort_key)
            print(f"Found {len(all_images)} images. Mapping them sequentially to products.")

        for index, row in df.iterrows():
            product_name = str(get_value(row, mapped_columns, "name", "")).strip()
            product_image_url = None
            
            # Simple sequential mapping: product at index matches image at index
            if index < len(all_images):
                image_filename = all_images[index]
                source_path = os.path.join(image_source_dir, image_filename)
                
                # Copy image to static/uploads
                target_filename = f"product_{index + 1}_{image_filename}"
                target_path = os.path.join(image_target_dir, target_filename)
                shutil.copy2(source_path, target_path)
                product_image_url = f"/static/uploads/{target_filename}"
                # print(f"  Mapped row {index+1} -> {image_filename}")

            category_name = str(get_value(row, mapped_columns, "category", "")).strip()
            if not category_name:
                # If no category specified, try to infer from partition or set default
                partition = str(get_value(row, mapped_columns, "partition", "")).strip()
                if partition:
                    category_name = f"Partition {partition}"
                else:
                    category_name = "General"  # Default category

            if not category_name:
                print(f"Skipping row {index+1}: no category found")
                continue

            if category_name in categories_cache:
                category = categories_cache[category_name]
            else:
                description = get_value(row, mapped_columns, "category_description", None)
                image_url = get_value(row, mapped_columns, "category_image", None)
                existing_cat = db.query(Category).filter(Category.name == category_name).first()
                is_new_category = existing_cat is None
                category = create_category(db, category_name, description, image_url)
                db.flush()
                categories_cache[category_name] = category
                if is_new_category:
                    created_categories += 1

            existing_count = db.query(Product).filter(
                Product.name == str(get_value(row, mapped_columns, "name", "")).strip(),
                Product.variant == str(get_value(row, mapped_columns, "variant", "")).strip(),
                Product.category_id == category.id
            ).count()

            product = create_product(db, mapped_columns, row, category.id, image_url=product_image_url)
            if product is None:
                continue

            if existing_count:
                updated_products += 1
            else:
                created_products += 1

        db.commit()
        print(f"Categories created/updated: {len(categories_cache)}")
        print(f"Products created: {created_products}")
        print(f"Products updated: {updated_products}")
        print("Upload completed successfully.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Upload data from an Excel file to the market database.")
    parser.add_argument(
        "excel_file",
        nargs="?",
        default="data_set.xlsx",
        help="Path to the Excel file to upload (default: data_set.xlsx)"
    )
    parser.add_argument(
        "--sheet",
        default=None,
        help="Sheet name or index to read from the Excel workbook"
    )
    args = parser.parse_args()

    try:
        upload_data(args.excel_file, args.sheet)
    except Exception as exc:
        print(f"Error: {exc}")
        raise
