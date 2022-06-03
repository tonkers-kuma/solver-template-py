from src.util.schema import (
    SettledBatchAuctionModel,
    InteractionData,
    BigInt
)
from decimal import Decimal
from web3 import Web3
import json
from eth_abi import encode_single, encode_abi

url = 'https://rpc.xdaichain.com'
w3 = Web3(Web3.HTTPProvider(url))


def solve(batch) -> SettledBatchAuctionModel:
    vault_raw = open('./contracts/artifacts/Vault.json')

    vault_abi = json.load(vault_raw)["abi"]

    print(f'yearn solver')
    interaction_data = []
    prices = {}
    for order in batch.orders:
        print(type(order.buy_token))
        buy_token = w3.eth.contract(address=Web3.toChecksumAddress(order.buy_token.value), abi=vault_abi)
        sell_token = w3.eth.contract(address=Web3.toChecksumAddress(order.sell_token.value), abi=vault_abi)
        sell_amount = int(order.sell_amount)

        if "yVault" in buy_token.functions.name().call() and buy_token.functions.token().call() == sell_token.address:
            # order to sell underlying for yv
            pps = buy_token.functions.pricePerShare().call()
            dec = buy_token.functions.decimals().call()
            buy_amount = int(sell_amount * (10 ** dec) / pps)

            approve_data = InteractionData(
                target=sell_token.address,
                value=0,
                call_data=sell_token.encodeABI(fn_name="approve", args=[buy_token.address, sell_amount])
            )

            deposit_data = InteractionData(
                target=buy_token.address,
                value=0,
                call_data=buy_token.encodeABI(fn_name="deposit", args=[sell_amount])
            )
            interaction_data.append(approve_data)
            interaction_data.append(deposit_data)

        elif "yVault" in sell_token.functions.name().call() and sell_token.functions.token().call() == buy_token.address:
            # order to sell yv for underlying
            pps = sell_token.functions.pricePerShare().call()
            dec = sell_token.functions.decimals().call()
            print(pps)
            buy_amount = int(sell_amount * pps / (10 ** dec))

            withdraw_data = InteractionData(
                target=sell_token.address,
                value=0,
                call_data=sell_token.encodeABI(fn_name="withdraw", args=[sell_amount])
            )
            interaction_data.append(withdraw_data)

        else:
            # no yv involved
            continue
        print(f'{type(buy_amount)} {type(sell_amount)} ')
        order.execute(buy_amount_value=buy_amount, sell_amount_value=sell_amount, xrate_tol=Decimal(5))
        print(buy_amount)

        prices[order.sell_token] = sell_amount
        prices[order.buy_token] = buy_amount
        print(batch)
        print(prices)

    return SettledBatchAuctionModel(
        ref_token=batch.ref_token.value,
        orders={order.order_id: order.as_dict() for order in batch.orders if order.is_executed()},
        prices={key.value: str(value) for key, value in prices.items()},
        amms={},
        interaction_data=interaction_data
    )
