import datetime
from dotenv import load_dotenv
import os

timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
filename = f'output_{timestamp}.txt'

load_dotenv()

wallet_from = os.getenv("ADDRESS")
wallet_priv_key = os.getenv("PRIVATE_KEY")

def check_wallet_info():
    if not wallet_from or not wallet_priv_key:
        raise ValueError("Both ADDRESS and PRIVATE_KEY must be defined in the .env file")