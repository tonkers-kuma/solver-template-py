from src.util.schema import (
    SettledBatchAuctionModel,
    InteractionData,
)
from decimal import Decimal
from web3 import Web3
from web3.contract import Contract
import json
from typing import List
from src.models.solvers import one_inch

curve_pool_raw = open('./contracts/artifacts/CurvePool.json')
curve_token_raw = open('./contracts/artifacts/CurveToken.json')
erc20_raw = open('./contracts/artifacts/CurveToken.json')

curve_pool_abi = json.load(curve_pool_raw)["abi"]
curve_token_abi = json.load(curve_token_raw)["abi"]
erc20_abi = json.load(erc20_raw)["abi"]

settlement_address = "0x9008d19f58aabd9ed0d60971565aa8510560ab41"


# only one direction for now (sell then lp)
def solve(token_in: Contract, amount_in, token_out: Contract, w3) -> (List[InteractionData], int):
    print(f'Using curve lp solver')

    interaction_data = []

    curve_token = w3.eth.contract(address=Web3.toChecksumAddress(token_out.address), abi=curve_token_abi)
    curve_pool = w3.eth.contract(address=Web3.toChecksumAddress(curve_token.functions.minter().call()),
                                 abi=curve_pool_abi)

    num_tokens = 0

    index_of_min = 0
    min = float('inf')

    # loop to find desired underlying token and index in the curve pool
    for i in range(0, 10):
        coin_address = ""
        try:
            coin_address = curve_pool.functions.coins(i).call()
        except:
            break
        # gracefully break here
        coin = w3.eth.contract(address=Web3.toChecksumAddress(coin_address), abi=erc20_abi)
        num_tokens = num_tokens + 1

        dec = coin.functions.decimals().call()
        balance = curve_pool.functions.balances(i).call()
        normalized_balance = balance * 10 ** (18 - dec)
        if normalized_balance < min:
            index_of_min = i
            min = normalized_balance
            underlying_token = coin

    # cow or dex to the underlying token
    interactions, amount_out = one_inch.solve(token_in, amount_in, underlying_token, w3)
    interaction_data += interactions

    # once we have the underlying token, we can lp
    # approve
    approve_data = InteractionData(
        target=token_in.address,
        value=0,
        call_data=token_in.encodeABI(fn_name="approve", args=[curve_pool.address, amount_in])
    )

    # for now just do single sided lp
    tokens = [0 for _ in range(0, num_tokens)]
    tokens[index_of_min] = amount_out
    print(type(amount_out))
    print(tokens)
    # lp in
    lp_data = InteractionData(
        target=curve_pool.address,
        value=0,
        call_data=curve_pool.encodeABI(fn_name="add_liquidity", args=[tokens, 0])
    )

    interaction_data += [approve_data, lp_data]

    est_token_out = curve_pool.functions.calc_token_amount(tokens, True).call()

    return (interaction_data, est_token_out)
