"""Airdrop farming tools — wallet gen, 2FA, utilities."""
from __future__ import annotations

import hashlib
import logging
import os
import secrets
import string
import time

import pyotp
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

logger = logging.getLogger("ayzen.routers.tools")
router = APIRouter()


async def _auth(request: Request):
    from apps.api.app.middleware.auth import verify_token
    return await verify_token(request)


# ── Wallet Generation ──────────────────────────────────────────────────────

class WalletGenRequest(BaseModel):
    count: int = 1
    chain: str = "evm"  # evm | sol | btc


class TOTPRequest(BaseModel):
    secret: str


class HashRequest(BaseModel):
    value: str
    from_format: str = "hex"
    to_format: str = "decimal"


class QRRequest(BaseModel):
    data: str
    label: str = ""


class UsernameRequest(BaseModel):
    count: int = 5
    prefix: str = ""
    style: str = "random"


class PasswordRequest(BaseModel):
    length: int = 16
    count: int = 5
    include_symbols: bool = True
    include_numbers: bool = True
    include_uppercase: bool = True


class PointsRequest(BaseModel):
    accounts: list[dict]


@router.post("/generate-wallets")
async def generate_wallets(body: WalletGenRequest, request: Request):
    await _auth(request)
    if body.count < 1 or body.count > 100:
        raise HTTPException(status_code=400, detail="count must be 1-100")

    wallets = []
    for _ in range(body.count):
        private_key = secrets.token_hex(32)
        if body.chain == "evm":
            from eth_account import Account as EthAccount
            acct = EthAccount.from_key("0x" + private_key)
            wallets.append({
                "address": acct.address,
                "private_key": private_key,
                "chain": "EVM",
            })
        elif body.chain == "sol":
            wallets.append({
                "address": "SOL_" + secrets.token_hex(16),
                "private_key": private_key,
                "chain": "Solana",
                "note": "Install solders for real Solana keys",
            })
        else:
            wallets.append({
                "address": "BTC_" + secrets.token_hex(16),
                "private_key": private_key,
                "chain": "Bitcoin",
                "note": "Install bitcoinlib for real BTC keys",
            })
    return {"wallets": wallets, "count": len(wallets)}


@router.post("/totp-code")
async def get_totp_code(body: TOTPRequest, request: Request):
    await _auth(request)
    try:
        clean = body.secret.strip().upper().replace(" ", "")
        totp = pyotp.TOTP(clean)
        now = int(time.time())
        interval = 30
        remaining = interval - (now % interval)
        code = totp.now()
        return {
            "code": code,
            "remaining_seconds": remaining,
            "progress": remaining / interval,
            "valid": totp.verify(code),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"invalid_secret: {str(e)}")


@router.post("/generate-usernames")
async def generate_usernames(body: UsernameRequest, request: Request):
    await _auth(request)
    adjectives = ["swift", "dark", "neo", "cyber", "alpha", "phantom", "storm", "crypto", "void", "hyper"]
    nouns = ["wolf", "hawk", "node", "chain", "vault", "byte", "pixel", "ghost", "fox", "viper"]
    names = []
    for _ in range(min(body.count, 20)):
        if body.style == "crypto":
            name = f"{secrets.choice(adjectives)}_{secrets.choice(nouns)}_{secrets.randbelow(9999):04d}"
        else:
            chars = string.ascii_lowercase + string.digits
            suffix = "".join(secrets.choice(chars) for _ in range(6))
            name = f"{body.prefix}{secrets.choice(adjectives)}{suffix}"
        names.append(name)
    return {"usernames": names}


@router.post("/generate-passwords")
async def generate_passwords(body: PasswordRequest, request: Request):
    await _auth(request)
    charset = string.ascii_lowercase
    if body.include_uppercase:
        charset += string.ascii_uppercase
    if body.include_numbers:
        charset += string.digits
    if body.include_symbols:
        charset += "!@#$%^&*"
    passwords = []
    for _ in range(min(body.count, 20)):
        pw = "".join(secrets.choice(charset) for _ in range(max(8, body.length)))
        passwords.append(pw)
    return {"passwords": passwords}


@router.post("/hash-convert")
async def hash_convert(body: HashRequest, request: Request):
    await _auth(request)
    val = body.value.strip()
    results = {}
    try:
        if val.startswith("0x"):
            val = val[2:]
        int_val = int(val, 16)
        results["hex"] = hex(int_val)
        results["decimal"] = str(int_val)
        results["binary"] = bin(int_val)
        results["bytes"] = len(val) // 2
    except ValueError:
        try:
            int_val = int(val)
            results["hex"] = hex(int_val)
            results["decimal"] = str(int_val)
            results["binary"] = bin(int_val)
        except ValueError:
            results["sha256"] = hashlib.sha256(val.encode()).hexdigest()
            results["md5"] = hashlib.md5(val.encode()).hexdigest()
    return results


@router.post("/generate-qr")
async def generate_qr(body: QRRequest, request: Request):
    await _auth(request)
    encoded = body.data.replace(" ", "+")
    qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data={encoded}"
    return {"qr_url": qr_url, "data": body.data}


@router.post("/calculate-points")
async def calculate_points(body: PointsRequest, request: Request):
    await _auth(request)
    total = 0
    breakdown = []
    for acct in body.accounts:
        pts = acct.get("points", 0)
        total += pts
        breakdown.append({"account": acct.get("label", "?"), "points": pts})
    return {"total_points": total, "account_count": len(body.accounts), "breakdown": breakdown}


@router.get("/profile-randomizer")
async def profile_randomizer(request: Request):
    await _auth(request)
    first = ["Alex", "Jordan", "Riley", "Casey", "Morgan", "Jamie", "Quinn", "Avery", "Blake", "Drew"]
    last = ["Chen", "Kim", "Park", "Lee", "Wang", "Smith", "Jones", "Brown", "Davis", "Wilson"]
    adjectives = ["crypto", "defi", "web3", "blockchain", "nft", "dao", "yield"]
    nouns = ["farmer", "degen", "builder", "trader", "whale", "anon", "maxi"]
    name = f"{secrets.choice(first)} {secrets.choice(last)}"
    username = f"{secrets.choice(adjectives)}_{secrets.choice(nouns)}_{secrets.randbelow(999):03d}"
    avatars = [
        "https://api.dicebear.com/7.x/avataaars/svg?seed=" + username,
        f"https://robohash.org/{username}?set=set4",
    ]
    bios = [
        "DeFi enthusiast | Airdrop hunter 🚀",
        "Building on-chain | Web3 native 🌐",
        "Crypto farmer | Early adopter 💎",
        "Blockchain believer | Long-term holder 🔗",
        "NFT collector | DAO contributor 🏛️",
    ]
    return {
        "name": name,
        "username": username,
        "bio": secrets.choice(bios),
        "avatar_url": avatars[0],
        "avatar_options": avatars,
    }
