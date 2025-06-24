import asyncio
import copy
import glob
import json
from enum import Enum

import requests
from web3 import Web3
from web3.middleware import geth_poa_middleware

import Config
import Helpers

w3 = Web3(Web3.HTTPProvider("https://api.avax.network/ext/bc/C/rpc"))
w3.middleware_onion.inject(geth_poa_middleware, layer=0)

routescanUrl = "https://api.routescan.io"
getHoldingsForERCTypeUrl = "/v2/network/mainnet/evm/43114/address/{address}/erc{ercType}-holdings?ecosystem=avalanche&includedChainIds=43114%2C73772&count=true&limit=100"


def setWalletTo(address: str):
    global wallet_to
    wallet_to = address

nonce_lock = asyncio.Lock()
next_nonce = None

async def init_nonce():
    global next_nonce
    next_nonce = w3.eth.get_transaction_count(Config.wallet_from)

async def get_next_nonce():
    global next_nonce
    async with nonce_lock:
        if next_nonce is None:
            next_nonce = w3.eth.get_transaction_count(Config.wallet_from)
        nonce_to_use = next_nonce
        next_nonce += 1
        return nonce_to_use

# enums for ercType(20, 721, 1155)
class ERCType(Enum):
    ERC20 = 20
    ERC721 = 721
    ERC1155 = 1155


def loadABIs(): 
    erc_files = glob.glob("./abis/erc*.json")
    abis = {}
    for file in erc_files:
        with open(file) as f:
            key = file.split("\\")[-1].split(".")[0].upper()  # Capitalize the key
            abis[key] = json.load(f)
    return abis

def getHoldingsForERCType(address: str, ercType: ERCType):
    url = routescanUrl + getHoldingsForERCTypeUrl.format(address=address, ercType=ercType.value)
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        return None


# getHoldings for each ERC type and return a list of all holdings
def getHoldings(address: str):
    holdings = {}
    for ercType in ERCType:
        response = getHoldingsForERCType(address, ercType)
        if response is not None:
            if ercType.name in holdings:
                holdings[ercType.name].extend(response["items"])
            else:
                holdings[ercType.name] = response["items"]

    printErc20Holdings(holdings)
    printErc721Holdings(holdings)
    printErc1155Holdings(holdings)

    return holdings

def printErc20Holdings(holdings: dict):
    headers = ["tokenSymbol", "tokenName", "tokenQuantity", "tokenAddress"]

    erc20Holdings = copy.deepcopy(holdings)

    for item in erc20Holdings[ERCType.ERC20.name]:
        # each item has a quantity and a tokenDecimals. We need to convert the quantity to a decimal number
        item["tokenQuantity"] = "{:.2f}".format(int(item["tokenQuantity"]) / (10 ** item["tokenDecimals"]))

    printHoldings(erc20Holdings, ERCType.ERC20.name, headers)

def printErc721Holdings(holdings: dict):
    headers = ["collectionSymbol", "collectionName", "count", "tokenAddress"]
    erc721Counts = {}

    erc721Holdings = copy.deepcopy(holdings)

    for item in erc721Holdings[ERCType.ERC721.name]:
        tokenAddress = item["tokenAddress"]
        if tokenAddress in erc721Counts:
            erc721Counts[tokenAddress]["count"] += 1
        else:
            erc721Counts[tokenAddress] = item
            erc721Counts[tokenAddress]["count"] = 1

    erc721Holdings[ERCType.ERC721.name] = list(erc721Counts.values())
    printHoldings(erc721Holdings, ERCType.ERC721.name, headers)

def printErc1155Holdings(holdings: dict):
    headers = ["balance", "tokenId", "tokenAddress"]
    printHoldings(holdings, ERCType.ERC1155.name, headers)

def printHoldings(holdings: dict, ercType: str, headers: list):
    col_widths = [len(header) for header in headers]
    for item in holdings[ercType]:
        for i, header in enumerate(headers):
            col_widths[i] = max(col_widths[i], len(str(item[header])))

    row_format = "".join("{:<" + str(width+1) + "}" for width in col_widths)

    total_width = sum(col_widths)
    word = f'{ercType} HOLDINGS'
    line = Helpers.prettyPrintSection(word, total_width)

    with open(Config.filename, 'a') as f:
        f.write(f'\n\n{line}\n')

        f.write(row_format.format(*headers) + '\n')
        f.write('-' * sum(col_widths) + '\n')

        for item in holdings[ercType]:
            row = [str(item[header]) for header in headers]
            f.write(row_format.format(*row) + '\n')

    print(f'\n\n{line}')
    print(row_format.format(*headers))
    print('-' * sum(col_widths))

    for item in holdings[ercType]:
        row = [str(item[header]) for header in headers]
        print(row_format.format(*row))

async def migrateHoldings(holdings: dict):
    abis = loadABIs()

    loadedContracts = {}
    tasks = []
    for ercType in ERCType:
        for item in holdings[ercType.name]:
            contractAddress = item["tokenAddress"]
            if contractAddress not in loadedContracts:
                loadedContracts[contractAddress] = loadContract(abis, contractAddress, ercType.name)
            contract = loadedContracts[contractAddress]
            
            #send tokens
            args = argMappings(ercType)(item)
            tasks.append(sendHelper(ercType, contract, args))

    await asyncio.gather(*tasks, return_exceptions=True)

    # We've sent all tokens we need gas for - send native
    await sendNative()
            


def loadContract(abis, address, ERCType):
    contract = w3.eth.contract(address=address, abi=abis[ERCType])
    return contract


async def sendHelper(ERCType, contract, args = None):
    if (wallet_to is None):
        raise ValueError("wallet_to is not set")
    
    raw_tx = {
        "from": Config.wallet_from,
        "to": contract.address,
        "gasPrice": w3.eth.gas_price,
        "gas": 200000,
        "value": 0,
        "data": sendMapping(ERCType)(contract, args),
        "nonce": await get_next_nonce(),
        "chainId": 43114
    }

    signed_tx = w3.eth.account.sign_transaction(raw_tx, Config.wallet_priv_key)
    try:
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        print(f"Sent {ERCType.name} {args} to {wallet_to}")
        return tx_receipt
    except Exception as e:
        print(f"Failed to send {ERCType.name} {args} to {wallet_to}")
        print(e)
        return None

def getERC20Args(d):
    return [None]

def sendERC20(contract, args):
    balance = contract.functions.balanceOf(Config.wallet_from).call()
    return contract.encodeABI(fn_name='transfer', args=[wallet_to, balance])

def getERC721Args(d):
    return [int(d["tokenId"])]

def sendERC721(contract, args):
    tokenId = args[0]
    return contract.encodeABI(fn_name='transferFrom', args=[Config.wallet_from, wallet_to, tokenId])

def getERC1155Args(d):
    return [int(d["tokenId"]), int(d["balance"])]

def sendERC1155(contract, args):
    tokenId = args[0]
    quantity = args[1]
    return contract.encodeABI(fn_name='safeTransferFrom', args=[Config.wallet_from, wallet_to, tokenId, quantity, "0x"])

def sendMapping(ERCType):
    return {
        ERCType.ERC20: sendERC20,
        ERCType.ERC721: sendERC721,
        ERCType.ERC1155: sendERC1155
    }.get(ERCType, None)

def argMappings(ERCType):
    return {
        ERCType.ERC20: getERC20Args,
        ERCType.ERC721: getERC721Args,
        ERCType.ERC1155: getERC1155Args
    }.get(ERCType, None)



async def sendNative():
    if (wallet_to is None):
        raise ValueError("wallet_to is not set")
    
    balance = w3.eth.get_balance(Config.wallet_from)
    gasPrice = w3.eth.gas_price
    raw_tx = {
        "from": Config.wallet_from,
        "to": wallet_to,
        "gasPrice": gasPrice,
        "gas": 200000,
        "value": int(balance - (gasPrice*200000)),
        "nonce": await get_next_nonce(),
        "chainId": 43114
    }

    signed_tx = w3.eth.account.sign_transaction(raw_tx, Config.wallet_priv_key)

    try:
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        print(f"Sent {balance} AVAX to {wallet_to}")
        return tx_receipt
    except Exception as e:
        print(f"Failed to send AVAX to {wallet_to}")
        print(e)
        return None