from mirai import Mirai, Plain, At, GroupMessage, Group, Member, Image
from config import mirai_api_http_locate, authKey, qq
from minesweeper import MineSweeper, GameState
from typing import Dict
from io import BytesIO
from time import time, sleep
from threading import Thread
import signal

app = Mirai(f"mirai://{mirai_api_http_locate}?authKey={authKey}&qq={qq}", websocket=True)
running = True
in_gaming_list: Dict[int, MineSweeper] = {}


def clean_thread():
    while running:
        for k, v in in_gaming_list.items():
            if time() - v.start_time > 10 * 60:
                del in_gaming_list[k]
        sleep(2)


async def send_panel(app: Mirai, group: Group, member: Member):
    byte_io = BytesIO()
    in_gaming_list[member.id].draw_panel().save(byte_io, format="jpeg")
    byte_io.flush()
    await app.sendGroupMessage(group, [At(member.id),
                                       Image.fromIO(byte_io)])
    byte_io.close()


async def send_game_over(app: Mirai, group: Group, member: Member):
    minesweeper = in_gaming_list[member.id]
    if minesweeper.state == GameState.WIN:
        await app.sendGroupMessage(group, [At(member.id), Plain("恭喜你赢了，再来一次吧！")])
    if minesweeper.state == GameState.FAIL:
        await app.sendGroupMessage(group, [At(member.id), Plain("太可惜了，就差一点点，再来一次吧！")])
    del in_gaming_list[member.id]


@app.receiver("GroupMessage")
async def event_gm(app: Mirai, group: Group, member: Member, message: GroupMessage):
    plain: Plain = message.messageChain.getFirstComponent(Plain)
    if plain is None:
        return
    if plain.text == "扫雷":
        await app.sendGroupMessage(group, [Plain("""欢迎游玩扫雷小游戏
        输入 【m 开始】 即可开始游戏
        使用 【m d】 位置1 位置2 来挖开多个方快
        使用 【m t】 位置1 位置2 来标记多个方块
        使用 【m show】 来重新查看游戏盘
        使用 【m exit】 退出游戏""")])
    if len(plain.text) > 2 and plain.text[:1] == "m":
        commands = plain.text.split(" ")
        if commands[1] == "开始":
            if member.id in in_gaming_list:
                await app.sendGroupMessage(group, [At(member.id), Plain("你已经在游戏中了")])
                return
            in_gaming_list[member.id] = MineSweeper(10, 10, 10)
            await send_panel(app, group, member)
        if member.id not in in_gaming_list:
            return
        if commands[1] == "show":
            await send_panel(app, group, member)

        if commands[1] == "exit":
            if member.id in in_gaming_list:
                await app.sendGroupMessage(group, [At(member.id), Plain("退出成功")])
                del in_gaming_list[member.id]
            else:
                await app.sendGroupMessage(group, [At(member.id), Plain("请输入 m 开始 开始游戏")])

        if len(commands) < 3:
            return
        if commands[1] == "d":
            try:
                for i in range(2, len(commands)):
                    location = MineSweeper.parse_input(commands[i])
                    in_gaming_list[member.id].mine(location[0], location[1])
                    if in_gaming_list[member.id].state != GameState.GAMING:
                        break
            except ValueError as e:
                await app.sendGroupMessage(group, [Plain(f"错误: {e}")])
            await send_panel(app, group, member)
            if in_gaming_list[member.id].state != GameState.GAMING:
                await send_game_over(app, group, member)

        if commands[1] == "t":
            try:
                for i in range(2, len(commands)):
                    location = MineSweeper.parse_input(commands[i])
                    in_gaming_list[member.id].tag(location[0], location[1])
                await send_panel(app, group, member)
            except ValueError as e:
                await app.sendGroupMessage(group, [Plain(f"错误: {e}")])


def my_exit():
    global running
    running = False
    exit()


if __name__ == "__main__":
    Thread(target=clean_thread).start()
    signal.signal(signal.SIGINT, my_exit)
    signal.signal(signal.SIGTERM, my_exit)
    app.run()
