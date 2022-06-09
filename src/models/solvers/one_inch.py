from src.util.schema import (
    InteractionData,
)
from web3 import Web3
import json
from typing import List
import os
from dotenv import load_dotenv
import requests
from web3.contract import Contract
import logging

router_raw = open('./contracts/artifacts/AggregationRouterV4.json')
router_abi = json.load(router_raw)["abi"]

settlement_address = "0x9008D19f58AAbD9eD0D60971565AA8510560ab41"

load_dotenv()
chain_id = os.environ['CHAIN_ID']
apiBaseUrl = 'https://api.1inch.io/v4.0/' + chain_id

aggregation_router_v4 = "0x1111111254fb6c44bAC0beD2854e76F90643097d"

def solve(token_in: Contract, amount_in: int, token_out: Contract, w3) -> (List[InteractionData], int):
    params = {
        "fromTokenAddress": token_in.address,
        "toTokenAddress": token_out.address,
        "amount": amount_in
    }
    print(params)

    # request quote
    r = requests.get(apiBaseUrl + "/quote", params=params)
    print(r.json())
    est_amount_out = int(r.json()["toTokenAmount"])

    router = w3.eth.contract(address=Web3.toChecksumAddress(aggregation_router_v4), abi=router_abi)
    approve_data = InteractionData(
        target=token_in.address,
        value=0,
        call_data=token_in.encodeABI(fn_name="approve", args=[router.address, amount_in])
    )

    # struct SwapDescription {
    #     IERC20 srcToken;
    #     IERC20 dstToken;
    #     address payable srcReceiver;
    #     address payable dstReceiver;
    #     uint256 amount;
    #     uint256 minReturnAmount;
    #     uint256 flags;
    #     bytes permit;
    # }

    # function swap(
    #     IAggregationExecutor caller,
    #     SwapDescription calldata desc,
    #     bytes calldata data
    # )

    swap_description = (
        token_in.address,
        token_out.address,
        settlement_address,
        settlement_address,
        amount_in,
        0,
        0,
        b'0x0'
    )

    swap_data = InteractionData(
        target=router.address,
        value=0,
        call_data=router.encodeABI(fn_name="swap", args=[settlement_address, swap_description, b'0x0'])
    )

    return ([approve_data, swap_data], est_amount_out)
