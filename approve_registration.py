"""Local-only manual approval. Usage: python approve_registration.py [list | approve ID]"""
import getpass
import os
import sys
from pathlib import Path

os.chdir(Path(__file__).resolve().parent)
import auth
import registration_requests


def main():
    args = sys.argv[1:]
    pending = [row for row in registration_requests.list_requests() if row["status"] == "pending"]
    if args == ["list"]:
        for row in pending:
            print(f'{row["username"]}\t{row["email"]}\t{row["requested_at"]}')
        if not pending:
            print("No pending requests")
        return 0
    if len(args) != 2 or args[0] != "approve":
        print("Usage: python approve_registration.py list | approve ID")
        return 2
    username = args[1]
    row = next((item for item in pending if item["username"] == username), None)
    if row is None:
        print("No pending request for that ID")
        return 1
    print(f'Approve ID: {username}; email for manual delivery: {row["email"]}')
    password = getpass.getpass("New password to send manually: ")
    if len(password) < 8 or password != getpass.getpass("Confirm password: "):
        print("Passwords must match and contain at least 8 characters")
        return 1
    result = auth.register_user(username, password)
    if not result["ok"]:
        print(result["error"])
        return 1
    registration_requests.mark_approved(username)
    print(f'Account created for {username}. Send the password to {row["email"]} manually.')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
