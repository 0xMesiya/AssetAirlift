# AssetAirlift
Easily migrate all ERC20, ERC721 &amp; ERC1155 tokens to a new wallet

AssetAirlift is a Python-based utility for managing and migrating Ethereum-based assets (ERC20, ERC721, and ERC1155 tokens) between wallets on the Avalanche network. It allows you to create a new wallet, fetch the holdings of an existing wallet, and migrate those holdings to a new wallet.

> I have tried to not use any non python native packages to avoid dependencies. Current implementation uses Web3, requests & dotenv.

# Installation
Before you can run this project, you need to install the required Python packages. This project uses pip, a package installer for Python. You can install these packages using the following command:
`pip install -r requirements.txt`

# Usage
Add the wallet you are migrating from to a `.env` file. Include the wallet address & private key.

```
ADDRESS=...
PRIVATE_KEY=...
```

Run the AssetAirlift.py script to start the process:

While in the base directory of the project run: `python AssetAirlift.py`

This will create a new wallet, fetch the holdings of the original wallet and migrate all ERC20, ERC721, ERC1155 and AVAX to the newly created wallet.
> New wallet details as well as all of the current holdings of the original wallet will be saved in `output_XXX.txt`

# Disclaimer
Please note that this project interacts with the Avalanche network and Ethereum assets. Be sure to understand the implications of these interactions before running the script.
It is the responsibility of the user to understand what this script is doing and no loss of assets will be at fault of the creator.
