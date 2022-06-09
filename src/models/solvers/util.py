import json
from web3 import Web3
from enum import Enum
from typing import Dict
from web3.contract import Contract
import logging

# add more as we support
class SolverType(Enum):
    GENERIC = "generic"
    YEARN_VAULT = "vault wrapper"
    CURVE_LP = "curve lp"
    BALANCER_LP = "balancer lp"


# logic for determining type of solver to use and which direction
def classify(token_in: Contract, token_out: Contract) -> (SolverType, bool):
    type = (SolverType.GENERIC, False)
    try:
        token_in_name = token_in.functions.name().call()
        token_out_name = token_out.functions.name().call()
        print(f'in:{token_in_name} out:{token_out_name}')
        if "yVault" in token_out_name and token_out.functions.token().call() == token_in.address:
            type = (SolverType.YEARN_VAULT, True)
        elif "yVault" in token_in_name and token_in.functions.token().call() == token_out.address:
            type = (SolverType.YEARN_VAULT, False)
        elif "Curve.fi" in token_out_name and "Curve.fi" not in token_in_name:
            type = (SolverType.CURVE_LP, True)
        elif "Curve.fi" in token_in_name and "Curve.fi" not in token_out_name:
            type = (SolverType.CURVE_LP, False)
        else:
            type = (SolverType.GENERIC, False)
    except Exception as e:
        logging.error(f'e')
    finally:
        return type


# makes sure that news additions to the price vector are scaled correctly to avoid breaking existing ratios
def append_scaled(t1, p1, t2, p2, prices: Dict[str, int]):
    if t1 in prices and t2 not in prices:
        existing_price = prices[t1]
        scale = existing_price / p1
        prices[t2] = p2 * scale
    elif t2 in prices and t1 not in prices:
        existing_price = prices[t2]
        scale = existing_price / p2
        prices[t1] = p1 * scale
    else:
        prices[t1] = p1
        prices[t2] = p2
