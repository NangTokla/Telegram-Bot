import os
import json
import asyncio
import uvicorn
from fastapi import FastAPI
from mcstatus import JavaServer
from time import sleep
from telegram import Bot

if ("config.json" in os.listdir(os.getcwd())):
    with open("config.json", "r") as file:
        config: dict = json.load(file)
else:
    config: dict = {
        "server": {
            "server_ip_addr": os.getenv("server_ip_addr"),
            "server_ip_port": os.getenv("server_ip_port")
        },
        "bot": {
            "token": os.getenv("bot_token"),
            "chat_id": os.getenv("chat_id"),
        }
    }
print(config)

server_data: dict = config.get("server")
bot_data: dict = config.get("bot")

bot: Bot = Bot(
    bot_data.get("token")
)
web_app: FastAPI = FastAPI()
# home page of web app
@web_app.api_route(
    "/",
    methods=[
        "GET",
        "HEAD",
        "POST",
        "OPTIONS"
    ]
)
async def keep_alive():
    return {"status": "Running.."}

# get the server status
# ex. each players in the server
#     if the server is online or offline
def get_server_status(
    server_ip_addr: str,
    server_ip_port: int
) -> dict:
    server = JavaServer.lookup(
        f"{server_ip_addr}:{server_ip_port}"
    )
    data = server.status()
    result: dict = {
        "state": "online" if type(data.motd.raw) == str else "offline",
        "players": [
            player.name for player in data.players.sample
        ] if data.players.sample else []
    }
    return result

# handle the player broadcasting
async def handle_player_broadcast(
    temp_player_list: list,
    live_player_list: list
) -> None:
    # check if there's player that left
    for player in temp_player_list:
        if player not in live_player_list:
            temp_player_list.remove(player)
            await broadcast_players(player, False)
    # check if there's player joining
    for player in live_player_list:
        if player not in temp_player_list:
            temp_player_list.append(player)
            await broadcast_players(player, True)

# make the bot send a message
async def send_msg(msg: str):
    await bot.send_message(
        chat_id=bot_data.get("chat_id"),
        text=msg
    )

# broadcast the message of the server state acordingly
async def broadcast_state(server_status: str) -> None:
    if (server_status == "online"):
        msg: str = "The server is currenly online🟢\nJoin now at SuckMyPP.aternos.me"
    else:
        msg: str = "The server is closed🔴"
    await send_msg(
        msg=msg
    )

# broadcast players state
async def broadcast_players(player_name: str, state: bool) -> None:
    if (state):
        keyword: str = "Joined"
    else:
        keyword: str = "Left"
    await send_msg(
        msg=f"[INFO]: {player_name} {keyword} the server"
    )

# main loop (handle everything)
async def bot_loop() -> None:
    last_state: str = "offline"
    players_list: list = []
    while True:
        # sleep (for performance)
        await asyncio.sleep(2.5)
        # errror handling
        try:
            current_status: dict = get_server_status(
                server_data.get("server_ip_addr"),
                server_data.get("server_ip_port")
            )
        except:
            continue
        # handle player broadcasting
        # ex. playername Joined the server
        if (
            last_state == "online" and
            (
                len(players_list) !=
                len(current_status.get("players"))
            )
        ):
            await handle_player_broadcast(
                players_list,
                current_status.get("players")
            )
        if (last_state == "offline"): players_list.clear()

        # check for changes in the server state
        # broadcast if there's changes
        current_state: str = current_status.get("state")
        if (current_state == last_state): continue
        await broadcast_state(current_state)
        last_state = current_state

async def web_loop() -> None:
    asyncio.create_task(bot_loop()) # bot loop
    port = 6000
    config_uvicorn = uvicorn.Config(
        app=web_app, 
        host="0.0.0.0",
        port=port
    )
    server = uvicorn.Server(config=config_uvicorn)
    await server.serve()

if __name__ == "__main__":
    asyncio.run(web_loop())
