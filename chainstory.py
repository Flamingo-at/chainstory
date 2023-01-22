import time
import asyncio
import aiohttp
import datetime

from web3.auto import w3
from loguru import logger
from aiohttp import ClientSession
from random import choice, randint
from aiohttp_proxy import ProxyConnector
from eth_account.messages import encode_defunct
from pyuseragents import random as random_useragent


def random_tor_proxy():
    proxy_auth = str(randint(1, 0x7fffffff)) + ':' + \
        str(randint(1, 0x7fffffff))
    proxies = f'socks5://{proxy_auth}@localhost:' + str(choice([9150]))
    return(proxies)


async def get_connector():
    connector = ProxyConnector.from_url(random_tor_proxy())
    return(connector)


def create_wallet():
    account = w3.eth.account.create()
    return(str(account.address), str(account.privateKey.hex()))


def create_signature(private_key: str, nonce: str):
    message = encode_defunct(text=nonce)
    signed_message = w3.eth.account.sign_message(message, private_key)
    return(signed_message.signature.hex())


async def worker(q: asyncio.Queue):
    while True:
        try:
            async with aiohttp.ClientSession(
                connector=await get_connector(),
                headers={'user-agent': random_useragent()}
            ) as client:

                address, private_key = create_wallet()

                emails = await q.get()
                email, password = emails.split(":")

                logger.info('Connection wallet')
                response = await client.post('https://www.chainstory.xyz/_vercel/insights/view',
                                             json={
                                                 "o": f"https://www.chainstory.xyz/{address}#",
                                                 "ts": str(round(time.time(), 3)).replace('.', '')
                                             })
                if await response.text() != "OK":
                    raise Exception()

                response = await client.get('https://app.dynamic.xyz/api/v0/sdk/728972b8-7312-4da6-9f84-c1bf07594782/nonce')
                nonce = (await response.json())['nonce']

                issued = str(datetime.datetime.utcnow()).replace(' ', 'T')[:-3]
                expiration = str(datetime.datetime.utcnow() 
                    + datetime.timedelta(hours=+1)).replace(' ', 'T')[:-3]

                message = f"www.chainstory.xyz wants you to sign in with your Ethereum account:\n{address}\n\nTo claim your ChainStory page, please sign this message to verify you are the owner of this address.\n\nURI: https://www.chainstory.xyz/{address}#\nVersion: 1\nChain ID: 1\nNonce: {nonce}\nIssued At: {issued}Z\nExpiration Time: {expiration}Z\nRequest ID: 728972b8-7312-4da6-9f84-c1bf07594782"

                logger.info('Verify signature')
                signature = create_signature(private_key, message)

                response = await client.post('https://app.dynamic.xyz/api/v0/sdk/728972b8-7312-4da6-9f84-c1bf07594782/verify',
                                             json={
                                                 "signedMessage": signature,
                                                 "messageToSign": message,
                                                 "publicWalletAddress": address,
                                                 "chain": "EVM",
                                                 "walletName": "MetaMask",
                                                 "walletProvider": "browserExtension"
                                             })
                authorization = (await response.json())['jwt']

                logger.info('Get NFT')
                response = await client.get(f'https://www.chainstory.xyz/api/claimpage?authToken={authorization}'
                                            f'&pageAddress={address}&emailAddress={email}')

                if str((await response.json())['msg']) != "Successfully claimed page!":
                    logger.error((await response.json())['msg'])
                    raise Exception()

        except:
            with open('error.txt', 'a', encoding='utf-8') as file:
                file.write(f'{emails}\n')
            logger.error('Error\n')

        else:
            with open('registered.txt', 'a', encoding='utf-8') as file:
                file.write(f'{emails}:{address}:{private_key}\n')
            logger.success('Successfully\n')

        finally:
            await asyncio.sleep(delay)


async def main():
    with open("emails.txt", "r") as accounts:
        accounts = accounts.read().strip().split("\n")

        q = asyncio.Queue()

        for account in list(accounts):
            q.put_nowait(account)

    tasks = [asyncio.create_task(worker(q)) for _ in range(threads)]
    await asyncio.gather(*tasks)


if __name__ == '__main__':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    print("Bot Chainstory @flamingoat\n")

    delay = int(input('Delay(sec): '))
    threads = int(input('Threads: '))

    asyncio.run(main())