"""Gas Tracker — live gas prices for 25+ EVM and non-EVM mainnets."""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

import httpx
from fastapi import APIRouter

logger = logging.getLogger("ayzen.routers.gas")
router = APIRouter()

# In-memory cache
_cache: dict[str, Any] = {}
_cache_ts: float = 0.0
_CACHE_TTL = 30  # seconds

NETWORKS = [
    {"name": "Ethereum",      "symbol": "ETH", "rpc": "https://eth.llamarpc.com",                  "chain_id": 1},
    {"name": "Arbitrum One",  "symbol": "ETH", "rpc": "https://arb1.arbitrum.io/rpc",              "chain_id": 42161},
    {"name": "Optimism",      "symbol": "ETH", "rpc": "https://mainnet.optimism.io",               "chain_id": 10},
    {"name": "Base",          "symbol": "ETH", "rpc": "https://mainnet.base.org",                  "chain_id": 8453},
    {"name": "Polygon",       "symbol": "MATIC","rpc": "https://polygon-rpc.com",                  "chain_id": 137},
    {"name": "BNB Chain",     "symbol": "BNB", "rpc": "https://bsc-dataseed.binance.org",           "chain_id": 56},
    {"name": "Avalanche",     "symbol": "AVAX","rpc": "https://api.avax.network/ext/bc/C/rpc",     "chain_id": 43114},
    {"name": "Fantom",        "symbol": "FTM", "rpc": "https://rpc.ftm.tools",                     "chain_id": 250},
    {"name": "zkSync Era",    "symbol": "ETH", "rpc": "https://mainnet.era.zksync.io",             "chain_id": 324},
    {"name": "Scroll",        "symbol": "ETH", "rpc": "https://rpc.scroll.io",                     "chain_id": 534352},
    {"name": "Linea",         "symbol": "ETH", "rpc": "https://rpc.linea.build",                   "chain_id": 59144},
    {"name": "Mantle",        "symbol": "MNT", "rpc": "https://rpc.mantle.xyz",                    "chain_id": 5000},
    {"name": "Blast",         "symbol": "ETH", "rpc": "https://rpc.blast.io",                      "chain_id": 81457},
    {"name": "Zora",          "symbol": "ETH", "rpc": "https://rpc.zora.energy",                   "chain_id": 7777777},
    {"name": "Mode",          "symbol": "ETH", "rpc": "https://mainnet.mode.network",              "chain_id": 34443},
    {"name": "Manta Pacific", "symbol": "ETH", "rpc": "https://pacific-rpc.manta.network/http",   "chain_id": 169},
    {"name": "Taiko",         "symbol": "ETH", "rpc": "https://rpc.mainnet.taiko.xyz",             "chain_id": 167000},
    {"name": "Berachain",     "symbol": "BERA","rpc": "https://rpc.berachain.com",                 "chain_id": 80084},
    {"name": "Sonic",         "symbol": "S",   "rpc": "https://rpc.soniclabs.com",                 "chain_id": 146},
    {"name": "Sei Network",   "symbol": "SEI", "rpc": "https://evm-rpc.sei-apis.com",              "chain_id": 1329},
    {"name": "Abstract",      "symbol": "ETH", "rpc": "https://api.mainnet.abs.xyz",               "chain_id": 2741},
    {"name": "Unichain",      "symbol": "ETH", "rpc": "https://mainnet.unichain.org",              "chain_id": 130},
    {"name": "Starknet",      "symbol": "ETH", "rpc": None, "static": {"slow": 0.001, "standard": 0.001, "fast": 0.001}},
    {"name": "Injective",     "symbol": "INJ", "rpc": None, "static": {"slow": 0.0002, "standard": 0.0005, "fast": 0.001}},
    {"name": "MegaETH",       "symbol": "ETH", "rpc": None, "coming_soon": True},
]


async def _eth_gas_price(client: httpx.AsyncClient, rpc: str) -> float | None:
    """Call eth_gasPrice on a given RPC, return gwei float."""
    try:
        resp = await client.post(
            rpc,
            json={"jsonrpc": "2.0", "method": "eth_gasPrice", "params": [], "id": 1},
            timeout=5.0,
        )
        data = resp.json()
        hex_val = data.get("result", "0x0")
        wei = int(hex_val, 16)
        return round(wei / 1e9, 4)  # gwei
    except Exception:
        return None


async def _eth_price_usd() -> float:
    """Fetch ETH price from CoinGecko (fallback 3000 if fails)."""
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(
                "https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd",
                timeout=5.0,
            )
            return r.json()["ethereum"]["usd"]
    except Exception:
        return 3000.0


def _gwei_to_usd(gwei: float, eth_price: float) -> float:
    """Estimate USD cost for a 21000 gas transfer."""
    eth_cost = (gwei * 21000) / 1e9
    return round(eth_cost * eth_price, 6)


def _gas_color(gwei: float) -> str:
    if gwei < 5:
        return "green"
    if gwei < 30:
        return "yellow"
    return "red"


async def _noop() -> None:
    return None


async def _fetch_all() -> list[dict]:
    eth_price = await _eth_price_usd()
    results = []

    async with httpx.AsyncClient() as client:
        tasks = []
        for net in NETWORKS:
            if net.get("coming_soon") or net.get("static") or not net.get("rpc"):
                tasks.append(_noop())
            else:
                tasks.append(_eth_gas_price(client, net["rpc"]))

        prices = await asyncio.gather(*tasks, return_exceptions=True)

    now_ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    for i, net in enumerate(NETWORKS):
        if net.get("coming_soon"):
            results.append({
                "name": net["name"], "symbol": net["symbol"],
                "coming_soon": True, "updated_at": now_ts,
            })
            continue

        if net.get("static"):
            s = net["static"]
            results.append({
                "name": net["name"], "symbol": net["symbol"],
                "slow_gwei": s["slow"], "standard_gwei": s["standard"], "fast_gwei": s["fast"],
                "usd_slow": _gwei_to_usd(s["slow"], eth_price),
                "usd_standard": _gwei_to_usd(s["standard"], eth_price),
                "usd_fast": _gwei_to_usd(s["fast"], eth_price),
                "color": _gas_color(s["standard"]),
                "updated_at": now_ts,
            })
            continue

        gwei = prices[i]
        if isinstance(gwei, Exception) or gwei is None:
            results.append({"name": net["name"], "symbol": net["symbol"], "error": True, "updated_at": now_ts})
            continue

        slow = round(gwei * 0.8, 4)
        fast = round(gwei * 1.5, 4)
        results.append({
            "name": net["name"], "symbol": net["symbol"],
            "slow_gwei": slow, "standard_gwei": gwei, "fast_gwei": fast,
            "usd_slow": _gwei_to_usd(slow, eth_price),
            "usd_standard": _gwei_to_usd(gwei, eth_price),
            "usd_fast": _gwei_to_usd(fast, eth_price),
            "color": _gas_color(gwei),
            "updated_at": now_ts,
        })

    return results


@router.get("/")
async def get_gas_prices() -> dict:
    global _cache, _cache_ts
    now = time.time()
    if _cache and (now - _cache_ts) < _CACHE_TTL:
        return {"data": _cache, "cached": True, "ttl": int(_CACHE_TTL - (now - _cache_ts))}
    data = await _fetch_all()
    _cache = data
    _cache_ts = now
    return {"data": data, "cached": False, "ttl": _CACHE_TTL}
