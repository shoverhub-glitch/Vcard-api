import asyncio
import sys
import os
import argparse
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
from config import get_settings
from utils.auth import get_password_hash

settings = get_settings()


async def create_admin_user(email: str, password: str):
    print("=" * 50)
    print("WCard Admin User Creator")
    print("=" * 50)
    
    client = AsyncIOMotorClient(settings.mongodb_url)
    db = client[settings.database_name]
    users_collection = db["users"]
    
    print(f"\nConnecting to: {settings.mongodb_url}")
    print(f"Database: {settings.database_name}")
    
    existing_user = await users_collection.find_one({"email": email})
    if existing_user:
        print(f"\n[X] User with email '{email}' already exists!")
        client.close()
        return
    
    hashed_password = get_password_hash(password)
    
    user_doc = {
        "email": email,
        "hashed_password": hashed_password,
        "role": "admin",
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    
    result = await users_collection.insert_one(user_doc)
    
    print(f"\n[OK] Admin user created successfully!")
    print(f"  Email: {email}")
    print(f"  Role: admin")
    print(f"  ID: {result.inserted_id}")
    
    client.close()
    
    print("\n" + "=" * 50)
    print("You can now login at /admin with these credentials")
    print("=" * 50)


async def list_users():
    print("=" * 50)
    print("WCard Users List")
    print("=" * 50)
    
    client = AsyncIOMotorClient(settings.mongodb_url)
    db = client[settings.database_name]
    users_collection = db["users"]
    
    users = []
    async for user in users_collection.find({}):
        users.append({
            "id": str(user["_id"]),
            "email": user["email"],
            "role": user["role"],
            "is_active": user.get("is_active", True),
            "created_at": user["created_at"].strftime("%Y-%m-%d %H:%M:%S") if user.get("created_at") else "N/A",
        })
    
    if not users:
        print("\nNo users found in the database.")
    else:
        print(f"\nFound {len(users)} user(s):\n")
        for user in users:
            print(f"  ID: {user['id']}")
            print(f"  Email: {user['email']}")
            print(f"  Role: {user['role']}")
            print(f"  Active: {'Yes' if user['is_active'] else 'No'}")
            print(f"  Created: {user['created_at']}")
            print()
    
    client.close()


async def delete_user(email: str):
    print("=" * 50)
    print("WCard Delete User")
    print("=" * 50)
    
    client = AsyncIOMotorClient(settings.mongodb_url)
    db = client[settings.database_name]
    users_collection = db["users"]
    
    result = await users_collection.delete_one({"email": email})
    
    if result.deleted_count > 0:
        print(f"\n[OK] User '{email}' deleted successfully!")
    else:
        print(f"\n[X] User '{email}' not found.")
    
    client.close()


def main():
    parser = argparse.ArgumentParser(description="WCard Admin User Management")
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    create_parser = subparsers.add_parser("create", help="Create admin user")
    create_parser.add_argument("--email", "-e", required=True, help="Admin email")
    create_parser.add_argument("--password", "-p", required=True, help="Admin password")
    
    list_parser = subparsers.add_parser("list", help="List all users")
    
    delete_parser = subparsers.add_parser("delete", help="Delete user")
    delete_parser.add_argument("--email", "-e", required=True, help="User email to delete")
    
    args = parser.parse_args()
    
    if args.command == "create":
        asyncio.run(create_admin_user(args.email, args.password))
    elif args.command == "list":
        asyncio.run(list_users())
    elif args.command == "delete":
        asyncio.run(delete_user(args.email))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
