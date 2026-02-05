/usr/bin/env python3
"""
Helper script to make a user an admin
Run this script to promote an existing user to admin status
"""

import os
import sys

# Add the project directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db, User

def make_user_admin(email):
    """Make a user admin by their email"""
    with app.app_context():
        user = User.query.filter_by(email=email).first()
        
        if not user:
            print(f"❌ User with email '{email}' not found!")
            print("\n📋 Available users:")
            all_users = User.query.all()
            if all_users:
                for u in all_users:
                    status = "👑 Admin" if u.is_admin else "👤 User"
                    print(f"  - {u.username} ({u.email}) - {status}")
            else:
                print("  No users found in database")
            return False
        
        if user.is_admin:
            print(f"⚠️  {user.username} is already an admin!")
            return False
        
        user.is_admin = True
        db.session.commit()
        
        print(f"✅ SUCCESS! {user.username} ({user.email}) is now an ADMIN!")
        print("\n🎉 You can now access:")
        print("   - /admin - User Management")
        print("   - /admin_dashboard - Admin Dashboard")
        print("\n💡 These links will appear in the side menu when you click the crown icon.")
        return True

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python make_admin.py <email>")
        print("\nExample: python make_admin.py praharshini@example.com")
        print("\n📋 First, let's see what users exist:")
        
        with app.app_context():
            users = User.query.all()
            if users:
                print("\nAvailable users:")
                for user in users:
                    status = "👑 Admin" if user.is_admin else "👤 User"
                    print(f"  - {user.username} ({user.email}) - {status}")
                email = input("\nEnter email to make admin: ").strip()
                if email:
                    make_user_admin(email)
            else:
                print("❌ No users found! Please create an account first.")
    else:
        email = sys.argv[1]
        make_user_admin(email)
