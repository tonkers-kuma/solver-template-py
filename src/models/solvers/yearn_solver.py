import logging

from src.util.schema import (
    SettledBatchAuctionModel,
    InteractionData,
)
from decimal import Decimal
from web3 import Web3
import json
import os
from dotenv import load_dotenv
from src.models.solvers import vault_wrapper, simple_cow, curve_lp, util

load_dotenv()
url = os.environ['NODE_URL']
w3 = Web3(Web3.HTTPProvider(url))

erc20_raw = open('./contracts/artifacts/ERC20.json')
erc20_abi = json.load(erc20_raw)["abi"]


def solve(batch) -> SettledBatchAuctionModel:
    interaction_data = []
    prices = {}
    for order in batch.orders:
        token_in = w3.eth.contract(address=Web3.toChecksumAddress(order.sell_token.value), abi=erc20_abi)
        token_out = w3.eth.contract(address=Web3.toChecksumAddress(order.buy_token.value), abi=erc20_abi)
        amount_in = int(order.sell_amount)

        data = []
        amount_out = 0

        solver_type, is_entering = util.classify(token_in, token_out)

        if util.SolverType.CURVE_LP == solver_type:
            data, amount_out = curve_lp.solve(token_in, amount_in, token_out, w3)
        elif util.SolverType.YEARN_VAULT == solver_type:
            # vault_wrapper.solve()
            logging.warning("not implemented ")
        else:
            # dex aggregator
            logging.warning("not implemented ")

        print(f'{solver_type}: \n{token_in.address} {amount_in} -->\n{token_out.address} {amount_out}')

        if amount_out > 0:
            interaction_data += data
            util.append_scaled(token_in.address, amount_in, token_out.address, amount_out, prices)
            order.execute(sell_amount_value=amount_in, buy_amount_value=amount_out)

    executed_orders = {order.order_id: order.as_dict() for order in batch.orders if order.is_executed()}
    print(f'executed orders: {executed_orders}')
    print(f'price vector: {prices}')
    print(f'interaction data: {interaction_data}')
    return SettledBatchAuctionModel(
        ref_token=batch.ref_token.value,
        orders=executed_orders,
        prices=prices,
        amms={},
        interaction_data=interaction_data)


[InteractionData(target='0x9C58BAcC331c9aa871AFD802DB6379a98e80CEdb', value='0',
                 call_data=b'0x095ea7b30000000000000000000000001111111254fb6c44bac0bed2854e76f90643097d000000000000000000000000000000000000000000000000002386f26fc10000'),
 InteractionData(target='0x1111111254fb6c44bAC0beD2854e76F90643097d', value='0',
                 call_data=b'0x7c0252000000000000000000000000009008d19f58aabd9ed0d60971565aa8510560ab41000000000000000000000000000000000000000000000000000000000000006000000000000000000000000000000000000000000000000000000000000001a00000000000000000000000009c58bacc331c9aa871afd802db6379a98e80cedb000000000000000000000000e91d153e0b41518a2ce8dd3d7944fa863463a97d0000000000000000000000009008d19f58aabd9ed0d60971565aa8510560ab410000000000000000000000009008d19f58aabd9ed0d60971565aa8510560ab41000000000000000000000000000000000000000000000000002386f26fc100000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000001000000000000000000000000000000000000000000000000000000000000000003307830000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000033078300000000000000000000000000000000000000000000000000000000000'),
 ('target', '0x9C58BAcC331c9aa871AFD802DB6379a98e80CEdb'), ('value', '0'), ('call_data',
                                                                            b'0x095ea7b30000000000000000000000007f90122bf0700f9e7e1f688fe926940e8839f353000000000000000000000000000000000000000000000000002386f26fc10000'),
 ('target', '0x7f90122BF0700F9E7e1F688fe926940E8839F353'), ('value', '0'), ('call_data',
                                                                            b'0x4515cef30000000000000000000000000000000000000000000000001a653fe89cb150b0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000')]
