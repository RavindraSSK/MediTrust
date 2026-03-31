def send_reset_code_email(email: str, code: str) -> None:
  
    print("\n" + "=" * 60)
    print("MediTrust Password Reset")
    print(f"To: {email}")
    print(f"Reset code: {code}")
    print("This code expires in 10 minutes.")
    print("=" * 60 + "\n")