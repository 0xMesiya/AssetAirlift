from web3 import Web3
import os

w3 = Web3()

def create_wallet():
    account = w3.eth.account.create(os.urandom(32))

    address = account.address
    private_key = account.key.hex()
    
    return address, private_key