import argparse

from pymongo import MongoClient


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", required=True)
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--root-user", required=True)
    parser.add_argument("--root-password", required=True)
    parser.add_argument("--db-name", required=True)
    parser.add_argument("--app-user", required=True)
    parser.add_argument("--app-password", required=True)
    args = parser.parse_args()

    client = MongoClient(
        host=args.host,
        port=args.port,
        username=args.root_user,
        password=args.root_password,
        authSource="admin",
        serverSelectionTimeoutMS=10000,
    )
    client.admin.command("ping")

    db = client[args.db_name]
    roles = [
        {"role": "readWrite", "db": args.db_name},
        {"role": "dbAdmin", "db": args.db_name},
        {"role": "userAdmin", "db": args.db_name},
    ]
    existing = db.command("usersInfo", args.app_user).get("users", [])
    if existing:
        db.command("updateUser", args.app_user, pwd=args.app_password, roles=roles)
    else:
        db.command("createUser", args.app_user, pwd=args.app_password, roles=roles)

    db["__bootstrap__"].update_one(
        {"_id": "init"},
        {"$set": {"created_by": "Codex", "db": args.db_name}},
        upsert=True,
    )
    print(f"OK {args.db_name} {args.app_user}")


if __name__ == "__main__":
    main()
