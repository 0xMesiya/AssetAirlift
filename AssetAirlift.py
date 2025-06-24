import asyncio

import Config
import Helpers
from AssetsHelper import getHoldings, init_nonce, migrateHoldings, setWalletTo
from CreateWallet import create_wallet


async def main():

    # Create wallet and get address and private key
    address, private_key = create_wallet()
    setWalletTo(address)

    # Write details to file
    with open(Config.filename, "w") as f:
        f.write(f"{Helpers.prettyPrintSection('DETAILS')}\n")
        f.write(f"FROM: {Config.wallet_from}\n")
        f.write(f"TO: {address}\n")
        f.write(f"\n{Helpers.prettyPrintSection('NEW WALLET')}\n")
        f.write(f"ADDRESS: {address}\n")
        f.write(f"PRIVATE KEY: {private_key}\n")

    # Get all erc20, erc721 & erc1155 tokens in from wallet & write details to file
    holdings = getHoldings(Config.wallet_from)

    # Migrate all erc20, erc721, erc1155 & Avax to new wallet
    await init_nonce()
    await migrateHoldings(holdings)



if __name__ == "__main__":
    Config.check_wallet_info()
    asyncio.run(main())