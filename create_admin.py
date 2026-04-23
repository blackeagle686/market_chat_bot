from database import SessionLocal, User, init_db
import sys

def create_admin(username, password):
    # Ensure tables are created
    init_db()
    
    db = SessionLocal()
    try:
        # Check if user already exists
        existing_user = db.query(User).filter(User.username == username).first()
        if existing_user:
            print(f"User '{username}' already exists. Updating password...")
            existing_user.password = password
        else:
            new_user = User(username=username, password=password)
            db.add(new_user)
            print(f"Created new admin user: {username}")
        
        db.commit()
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python create_admin.py <username> <password>")
        print("Example: python create_admin.py admin admin123")
    else:
        create_admin(sys.argv[1], sys.argv[2])
