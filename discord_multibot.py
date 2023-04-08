# ░█▀▄░▀█▀░█▀▀░█▀▀░█▀█░█▀▄░█▀▄░░░█▄█░█░█░█░░░▀█▀░▀█▀░█▀▄░█▀█░▀█▀
# ░█░█░░█░░▀▀█░█░░░█░█░█▀▄░█░█░░░█░█░█░█░█░░░░█░░░█░░█▀▄░█░█░░█░
# ░▀▀░░▀▀▀░▀▀▀░▀▀▀░▀▀▀░▀░▀░▀▀░░░░▀░▀░▀▀▀░▀▀▀░░▀░░▀▀▀░▀▀░░▀▀▀░░▀░

################################################################################
# originally forked from
# https://github.com/verata-veritatis/discord-coingecko-price-bot
#
# rebuilt & refactored with <3 by:
# flim.eth
#
# questions? reach out
# twitter.com/0xflim
# 0xflim@pm.me
#
# if this is helpful to you, please consider donating:
# 0x8d6fc57487ade3738c2baf3437b63d35420db74d (or flim.eth)
################################################################################
import asyncio
import requests
import tokens  # gitignore dictionary, holds Discord API tokens & attributes
import time
import ssl
import json
import math
from bs4 import BeautifulSoup
from urllib.request import Request, urlopen
from discord import Activity, ActivityType, Client, Intents, errors
from discord.ext import tasks
from datetime import datetime as dt

# https://discordpy.readthedocs.io/en/stable/faq.html#what-does-blocking-mean


################################################################################
# I keep a gitignore file (tokens.py) which contains a simple dictionary:
#
# Values represent Discord API tokens
# Token info here: https://discord.com/developers/docs/topics/oauth2#bots
#
# Keys represent a list of attributes including for example coingecko market id:
# ex. --> https://www.coingecko.com/en/coins/<id>.
#
# I store them both in lists here:
################################################################################
bot_tokens = list(tokens.tokens_dict.keys())
attributes = list(tokens.tokens_dict.values())
################################################################################

print("\n---------- V6 flim's Discord Multibot ----------\n")

################################################################################
# API & response code sanity check; also create list of tickers
################################################################################
print(f"{str(dt.utcnow())[:-7]} | Checking CoinGecko & Opensea for market IDs.")
tickers = []
status_code = 0

# synchronous startup
for i in range(len(bot_tokens)):
    if attributes[i][1] == "opensea":
        r = requests.get(
            f"https://api.opensea.io/api/v1/collection/{attributes[i][0]}/"
        )
        token_name = r.json()["collection"]["primary_asset_contracts"][0][
            "symbol"
        ].upper()
        status_code = r.status_code
    elif attributes[i][1] == "larvalabs":
        r = requests.get(f"https://cryptopunks.app/")
        token_name = attributes[i][0].upper()
        status_code = r.status_code
    elif attributes[i][1] == "tofunft":
        hdr = {"User-Agent": "Mozilla/5.0"}
        site = f"https://tofunft.com/collection/{attributes[i][0]}/items"
        context = ssl._create_unverified_context()
        r = Request(site, headers=hdr)
        page = urlopen(r, context=context)
        token_name = attributes[i][2].title()
        status_code = page.getcode()
    elif attributes[i][1] == "dopexapi":
        r = requests.get(f"https://api.dopex.io/api/v2/ssov")
        token_name = attributes[i][0].upper()
        status_code = r.status_code
    elif attributes[i][1] == "beaconchain":
        r = requests.get(f"https://beaconcha.in/validator/{attributes[i][0]}")
        token_name = attributes[i][2].upper()
        status_code = r.status_code
    elif attributes[i][0] == "gas":
        r = requests.get(
            "https://api.etherscan.io/api"
            "?module=gastracker"
            "&action=gasoracle"
            f"&apikey={attributes[i][2]}"
        )
        token_name = attributes[i][0].upper()
        status_code = r.status_code
    elif attributes[i][1] == "defillama":
        r = requests.get(f"https://api.llama.fi/{attributes[i][2]}/{attributes[i][0]}")
        token_name = attributes[i][2].upper()
        status_code = r.status_code
    else:
        r = requests.get(f"https://api.coingecko.com/api/v3/coins/{attributes[i][0]}")
        status_code = r.status_code
        if status_code > 400:
            print(r.status_code)
            print(
                f"{str(dt.utcnow())[:-7]} | Error {status_code}."
                + f" Could not find {attributes[i][0]}. Exiting...\n"
            )
            if status_code == 429:
                print(f"{str(dt.utcnow())[:-7]} | Waiting 60 seconds before exit...")
                time.sleep(60)
            exit()
        token_name = r.json()["symbol"].upper()
    time.sleep(2)  # protect against rate limiting
    tickers.append(token_name)
    print(f"{str(dt.utcnow())[:-7]} | Found {token_name}/{attributes[i][3].upper()}.")


################################################################################
# Start clients and set intents.
################################################################################
print(f"\n{str(dt.utcnow())[:-7]} | Starting Discord bot army of {len(bot_tokens)}.")
clients = []

for i in range(len(bot_tokens)):
    clients.append(Client(intents=Intents.default()))

client = clients[i]

# update April 2023 per FAQ:
# https://discordpy.readthedocs.io/en/stable/faq.html#general
# It is highly discouraged to use Client.change_presence() or API calls
#   in on_ready as this event may be called many times while running, not just once
#   I should refactor this out of my code
#   seem like this is a good approach
#   https://github.com/cleot/CoinGecko-Discord-Bot/blob/main/main.py
# I'm stubborn and trying to get it working with all my existing call logic


@client.event
async def on_ready():
    print(f"\n{str(dt.utcnow())[:-7]} | Multibot is running.\n")
    await asyncio.sleep(0.5)
    for i in range(len(clients)):
        for guild in clients[i].guilds:
            print(
                f"{str(dt.utcnow())[:-7]} | {clients[i].user} has connected to {guild.name}."
            )
            await asyncio.sleep(0.1)
    print("\n")
    refresh_data.start()


@tasks.loop(seconds=float(10))
async def refresh_data():
    for i in range(len(clients)):
        nick, name = await get_data(i)
        await asyncio.sleep(3)
        if nick == "":
            await asyncio.sleep(5)
            pass
        else:
            for guild in clients[i].guilds:
                await guild.me.edit(nick=nick)
                await clients[i].change_presence(
                    activity=Activity(
                        name=name,
                        type=ActivityType.watching,
                    )
                )


async def get_data(i):
    errored_guilds = []
    try:
        # pick which operation / API
        async with asyncio.timeout(10):
            if attributes[i][1] == "opensea":
                r = requests.get(
                    f"https://api.opensea.io/api/v1/collection/{attributes[i][0]}/stats"
                )
                status_code = r.status_code
            elif attributes[i][1] == "defillama":
                r = requests.get(
                    f"https://api.llama.fi/{attributes[i][2]}/{attributes[i][0]}"
                )
                status_code = r.status_code
            elif attributes[i][1] == "larvalabs":
                # r = requests.get(f"https://www.larvalabs.com/cryptopunks")
                r = requests.get(f"https://cryptopunks.app/")
                status_code = r.status_code
            elif attributes[i][1] == "beaconchain":
                r = requests.get(f"https://beaconcha.in/validator/{attributes[i][0]}")
                status_code = r.status_code
            elif attributes[i][1] == "tofunft":
                site = f"https://tofunft.com/collection/{attributes[i][0]}/items"
                r = Request(site, headers=hdr)
                page = urlopen(r, context=context)
                status_code = page.getcode()
            elif attributes[i][1] == "dopexapi":
                r = requests.get(f"https://api.dopex.io/api/v2/ssov")
                status_code = r.status_code
            elif attributes[i][1] == "etherscan":
                r = requests.get(
                    "https://api.etherscan.io/api"
                    "?module=gastracke"
                    "r&action=gasorac"
                    f"le&apikey={attributes[i][2]}"
                )
                fastGas = int(r.json()["result"]["FastGasPrice"])
                rawSuggestedBase = r.json()["result"]["suggestBaseFee"]
                suggestedBase = math.floor(float(r.json()["result"]["suggestBaseFee"]))

                # convert gwei to wei
                fastGasWei = fastGas * 1e9

                # get priority fees
                fastPriority = fastGas % suggestedBase
            else:
                r = requests.get(
                    f"https://api.coingecko.com/api/v3/coins/{attributes[i][0]}"
                )
                status_code = r.status_code

            # handle for different use cases
            if attributes[i][2] == "market_cap":
                price = round(
                    float(r.json()["market_data"][attributes[i][2]][attributes[i][3]])
                    / 1000000,
                    2,
                )
                fdv = round(
                    float(
                        r.json()["market_data"]["fully_diluted_valuation"][
                            attributes[i][3]
                        ]
                    )
                    / 1000000,
                    2,
                )
            elif attributes[i][1] == "defillama":
                # tvl = r.json()
                tvl = round(float(r.json()) / 1000000, 2)
            elif attributes[i][1] == "opensea":
                floor_price = r.json()["stats"][attributes[i][2]]
                pctchng = r.json()["stats"]["seven_day_average_price"]
            elif attributes[i][1] == "larvalabs":
                soup = BeautifulSoup(r.content, "html.parser")
                punk_stats = soup.findAll("div", attrs={"class": "col-md-4 punk-stat"})
                floor = punk_stats[0].b
                split = floor.string.split(" ETH ")
                eth_floor = "Ξ" + split[0]
                usd_floor = split[1].lstrip("(").rstrip(" USD)")
            elif attributes[i][1] == "beaconchain":
                soup = BeautifulSoup(r.content, "html.parser")
                blocks = soup.find("span", attrs={"id": "blockCount"})
                block_stats = blocks.attrs["title"].split("Blocks (")[1]
                b_prop = block_stats.split(", ")[0].split(": ")
                b_miss = block_stats.split(", ")[1].split(": ")
                b_orph = block_stats.split(", ")[2].split(": ")
                b_sche = block_stats.split(", ")[3].split(": ")

                attestations = soup.find("span", attrs={"id": "attestationCount"})
                attestation_stats = attestations.attrs["title"].split(
                    "Attestation Assignments ("
                )[1]
                a_exec = attestation_stats.split(", ")[0].split(": ")
                a_miss = attestation_stats.split(", ")[1].split(": ")
                a_orph = attestation_stats.split(", ")[2].split(": ")
            elif attributes[i][1] == "tofunft":
                soup = BeautifulSoup(page, "html.parser")
                script = soup.find(id="__NEXT_DATA__").string
                json_data = json.loads(script)
                floor_dict = json_data["props"]["pageProps"]["data"]["contract"][
                    "stats"
                ]["market_floor_price"]

                vol = round(
                    float(
                        json_data["props"]["pageProps"]["data"]["contract"]["stats"][
                            "market_vol"
                        ]
                    ),
                    2,
                )
                floor = floor_dict.pop("0x0000000000000000000000000000000000000000")
            elif attributes[i][1] == "dopexapi":
                r = r.json()["42161"]
                tvl_dict = {}
                tokens = [attributes[i][0].upper()]
                # for all tokens in token list, get all active SSOVs & sum tvl by token
                for t in tokens:
                    # reset tvl varible with each new token
                    tvl = 0
                    # iterate thru SSOVs to find active SSOVs which match current token
                    for ssov in r:
                        for key, value in ssov.items():
                            if (
                                ssov["retired"] == False
                                and ssov["underlyingSymbol"] == t
                            ):
                                # add tvl to cumulative tvl for given token & format to float
                                tvl += float(ssov["tvl"]) / 1000000
                                break
                    # add the token and tvl key value pair to the tvl dict
                    tvl_dict.update({t: tvl})
                # per witherblock these values should be added to Dopex API, but not yet
                # epoch = attributes[i][4]
                # epoch_month = attributes[i][5]
            elif attributes[i][1] == "etherscan":
                r2 = requests.get(
                    "https://api.etherscan.io/api"
                    "?module=gastracker"
                    "&action=gasestimate"
                    f"&gasprice={str(round(fastGasWei))}"
                    f"&apikey={attributes[i][2]}"
                )

                fastGasTime = r2.json()["result"]
                status_code = r2.status_code
            else:
                price = r.json()["market_data"][attributes[i][2]][attributes[i][3]]
                pctchng = r.json()["market_data"][
                    "price_change_percentage_24h_in_currency"
                ][attributes[i][3]]
            # print status code & bot number
            print(f"{str(dt.utcnow())[:-7]} | Discord bot: {i+1} of {len(bot_tokens)}.")
            print(f"{str(dt.utcnow())[:-7]} | response status code: {status_code}.")

            # console printing logic
            consolePrint = ""
            if attributes[i][2] == "market_cap":
                consolePrint = (
                    f"{str(dt.utcnow())[:-7]} | {tickers[i]} Mcap: ${price:,}m.\n"
                    f"{str(dt.utcnow())[:-7]} | JONES FDV: ${fdv:,}m.\n"
                )
            elif attributes[i][1] == "defillama":
                consolePrint = f"{str(dt.utcnow())[:-7]} | {attributes[i][0]} {tickers[i]}: ${tvl:,}m.\n"
            elif attributes[i][1] == "opensea":
                consolePrint = (
                    f"{str(dt.utcnow())[:-7]} | {tickers[i]} floor price: Ξ{floor_price}.\n"
                    f"{str(dt.utcnow())[:-7]} | {tickers[i]} 7d avg. price: Ξ{round(pctchng,2)}.\n"
                )
            elif attributes[i][3] == "btc":
                consolePrint = (
                    f"{str(dt.utcnow())[:-7]} | {tickers[i]}/{attributes[i][3].upper()}: ₿{price:,}.\n"
                    f"{str(dt.utcnow())[:-7]} | {tickers[i]} 24hr % change: {round(pctchng,2)}%.\n"
                )
            elif attributes[i][1] == "larvalabs":
                consolePrint = (
                    f"{str(dt.utcnow())[:-7]} | {tickers[i]} floor: {eth_floor}.\n"
                    f"{str(dt.utcnow())[:-7]} | {tickers[i]} floor: {usd_floor}.\n"
                )
            elif attributes[i][1] == "beaconchain":
                consolePrint = (
                    f"{str(dt.utcnow())[:-7]} | blocks: {block_stats}.\n"
                    f"{str(dt.utcnow())[:-7]} | attestations: {attestation_stats}.\n"
                )
            elif attributes[i][1] == "tofunft":
                consolePrint = (
                    f"{str(dt.utcnow())[:-7]} | {tickers[i]} floor: Ξ{floor}.\n"
                    f"{str(dt.utcnow())[:-7]} | {tickers[i]} volume: Ξ{vol}.\n"
                )
            elif attributes[i][1] == "dopexapi":
                consolePrint = (
                    f"{str(dt.utcnow())[:-7]} | {tickers[i]} SSOV tvl: ${round(tvl_dict[tickers[i]],2):,}m\n"
                    # f"{str(dt.utcnow())[:-7]} | {tickers[i]} epoch: {epoch} | {epoch_month}.\n"
                )
            elif attributes[i][1] == "etherscan":
                consolePrint = (
                    f"{str(dt.utcnow())[:-7]} | status code: {r.status_code}.\n"
                    f"{str(dt.utcnow())[:-7]} | suggested base fee: {suggestedBase}.\n"
                    f"{str(dt.utcnow())[:-7]} | fast gas: {fastGas}.\n"
                    f"{str(dt.utcnow())[:-7]} | fast gas wei : {fastGasWei}.\n"
                    f"{str(dt.utcnow())[:-7]} | fast priority: {fastPriority}.\n"
                    f"{str(dt.utcnow())[:-7]} | fast gas confirmation in seconds: {fastGasTime}.\n"
                )
            else:
                consolePrint = (
                    f"{str(dt.utcnow())[:-7]} | {tickers[i]} price: ${price:,}.\n"
                    f"{str(dt.utcnow())[:-7]} | {tickers[i]} 24hr % change: {round(pctchng,2)}%.\n"
                )
            print(consolePrint)

            for guild in clients[i].guilds:
                try:

                    # handle different logic for bot nicknaming & data display
                    if attributes[i][3] == "btc":
                        nick = f"{tickers[i]}/{attributes[i][3].upper()} ₿{round(float(price), 4)}"
                    elif attributes[i][1] == "defillama":
                        nick = f"{tickers[i]} ${tvl:,}m"
                    elif attributes[i][2] == "market_cap":
                        nick = f"MCAP ${price:,}m"
                    elif attributes[i][1] == "opensea":
                        nick = f"{tickers[i]} Ξ{round(floor_price,2):,}"
                    elif attributes[i][1] == "larvalabs":
                        nick = f"{tickers[i]} {eth_floor}"
                    elif attributes[i][1] == "beaconchain":
                        nick = f"{tickers[i].lower()} blocks: {b_prop[1]}"
                    elif attributes[i][1] == "tofunft":
                        nick = f"{tickers[i]}: Ξ{floor}"
                    elif attributes[i][1] == "dopexapi":
                        nick = f"{tickers[i]} ${round(tvl_dict[tickers[i]],2):,}m"
                    elif attributes[i][1] == "etherscan":
                        nick = f"{fastGas:,} gwei ~{fastGasTime} sec"
                    elif price < 1:
                        nick = f"{tickers[i]} ${round(price,4):,}"
                    else:
                        nick = f"{tickers[i]} ${round(price,2):,}"
                    # handle different logic for bot activity
                    if attributes[i][2] == "market_cap":
                        name = f"FDV: ${round(fdv,2):,}m"
                    elif attributes[i][1] == "opensea":
                        name = f"7d avg.: Ξ{round(pctchng,2)}"
                    elif attributes[i][1] == "larvalabs":
                        name = f"in USD: {usd_floor}"
                    elif attributes[i][1] == "beaconchain":
                        name = f"attestations: {a_exec[1]}"
                    elif attributes[i][1] == "tofunft":
                        name = f"Volume: Ξ{vol}"
                    elif attributes[i][1] == "defillama":
                        name = f"Vaults"
                    elif attributes[i][1] == "dopexapi":
                        name = f"Current Epoch"
                    elif attributes[i][1] == "etherscan":
                        name = f"Base: {suggestedBase} Priority: {fastPriority}"
                    else:
                        name = f"24h: {round(pctchng,2)}%"
                except errors.Forbidden:
                    if guild not in errored_guilds:
                        print(
                            f"{str(dt.utcnow())[:-7]} | {guild}:{guild.id} hasn't set "
                            "nickname permissions for the bot!"
                        )
                    errored_guilds.append(guild)
                    nick, name = ""
                    break
                except Exception as e:
                    print(
                        f"{str(dt.utcnow())[:-7]} | Unknown error within update: {e}."
                    )
                    nick, name = ""
    except ValueError as e:
        print(f"{str(dt.utcnow())[:-7]} | ValueError: {e}.")
        nick, name = ""
    except TypeError as e:
        print(f"{str(dt.utcnow())[:-7]} | TypeError: {e}.")
        nick, name = ""
    except OSError as e:
        print(f"{str(dt.utcnow())[:-7]} | OSError: {e}.")
        nick, name = ""
    except Exception as e:
        print(f"{dt.utcnow()} | Unknown error outside update: {e}.")
        nick, name = ""
    finally:
        return nick, name


################################################################################
# Run the clients forever
################################################################################
loop = asyncio.new_event_loop()
t = []
for i in range(len(clients)):
    t.append(loop.create_task(clients[i].start(bot_tokens[i])))
    print(t[i])
loop.run_forever()
################################################################################
