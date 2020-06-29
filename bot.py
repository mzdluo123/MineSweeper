import pyximport

pyximport.install()
from mirai import Mirai, Plain, At, Group, Member, Image, Friend, FriendMessage, GroupMessage, TempMessage
from mirai.event.message.models import MessageItemType
from config import mirai_api_http_locate, authKey, qq
from minesweeper import MineSweeper,GameState
from typing import Dict
from io import BytesIO
from time import time, sleep
from threading import Thread
import signal


app = Mirai(f"mirai://{mirai_api_http_locate}?authKey={authKey}&qq={qq}", websocket=True)
running = True
in_gaming_list: Dict[int, MineSweeper] = {}

HELP = """
欢迎游玩扫雷小游戏
输入 【m 开始】 即可开始游戏
输入 【m 中级或高级】 即可开始不同难度游戏
输入 【m 自定义 长 宽 雷数】 即可开始自定义游戏
使用 【m d 位置1 位置2】 来挖开多个方快
使用 【m t 位置1 位置2】 来标记多个方块
使用 【m show】 来重新查看游戏盘
使用 【m help】 来查看帮助
使用 【m exit】 退出游戏
项目地址 https://github.com/mzdluo123/MineSweeper
"""


def clean_thread():
    while running:
        for k, v in in_gaming_list.items():
            if time() - v.start_time > 15 * 60:
                del in_gaming_list[k]
        sleep(2)


async def send_msg(target, msg: list, user, msg_type):
    if msg_type is MessageItemType.GroupMessage:
        msg.insert(0, At(user.id))
        await app.sendGroupMessage(target, msg)
        return
    if msg_type is MessageItemType.FriendMessage:
        await app.sendFriendMessage(target, msg)
        return
    if msg_type is MessageItemType.TempMessage:
        await app.sendTempMessage(target, user, msg)


async def send_panel(app: Mirai, group: Group, member: Member, msg_type):
    byte_io = BytesIO()
    in_gaming_list[member.id].draw_panel().save(byte_io, format="jpeg")
    byte_io.flush()
    await send_msg(group, [Image.fromIO(byte_io)], member, msg_type)
    byte_io.close()


async def send_game_over(app: Mirai, group: Group, member: Member, msg_type):
    minesweeper = in_gaming_list[member.id]
    if minesweeper.state == GameState.WIN:
        await send_msg(group, [Plain(
            f"恭喜你赢了，再来一次吧！耗时{time() - minesweeper.start_time}秒 操作了{minesweeper.actions}次")], member, msg_type)
    if minesweeper.state == GameState.FAIL:
        await send_msg(group, [Plain(
            f"太可惜了，就差一点点，再来一次吧！耗时{time() - minesweeper.start_time}秒 操作了{minesweeper.actions}次")], member, msg_type)
    del in_gaming_list[member.id]


@app.receiver("FriendMessage")
async def friend_handel(app: Mirai, friend: Friend, message: FriendMessage):
    plain: Plain = message.messageChain.getFirstComponent(Plain)
    await msg_handel(friend, plain, friend, MessageItemType.FriendMessage)


@app.receiver("TempMessage")
async def tm_handel(app: Mirai, group: Group, member: Member, message: TempMessage):
    plain: Plain = message.messageChain.getFirstComponent(Plain)
    await msg_handel(group, plain, member, MessageItemType.TempMessage)


@app.receiver("GroupMessage")
async def gm_handel(app: Mirai, group: Group, member: Member, message: GroupMessage):
    plain: Plain = message.messageChain.getFirstComponent(Plain)
    await msg_handel(group, plain, member, MessageItemType.GroupMessage)


async def new_game(source, user, msg_type, row: int, column: int, mines: int):
    if user.id in in_gaming_list:
        await send_msg(source, [Plain("你已经在游戏中了")], user, msg_type)
        return
    in_gaming_list[user.id] = MineSweeper(row, column, mines)
    await send_panel(app, source, user, msg_type)


async def msg_handel(source, plain, user, msg_type):
    if plain is None:
        return
    if plain.text == "扫雷":
        await send_msg(source, [Plain(HELP)], user, msg_type)
    if len(plain.text) > 2 and plain.text[:1] == "m":
        commands = plain.text.split(" ")
        if commands[1] == "开始":
            await new_game(source, user, msg_type, 10, 10, 10)
        if commands[1] == "中级":
            await new_game(source, user, msg_type, 16, 16, 40)
        if commands[1] == "高级":
            await new_game(source, user, msg_type, 20, 20, 90)

        if commands[1] == "自定义" and len(commands) == 5:
            try:
                await new_game(source, user, msg_type, int(commands[2]), int(commands[3]), int(commands[4]))
            except ValueError as e:
                await send_msg(source, [Plain(f"错误 {e}")], user, msg_type)
        if commands[1] == "help":
            await send_msg(source, [Plain(HELP)], user, msg_type)

        # 以下命令只有在游戏中才可以使用
        if user.id not in in_gaming_list:
            return
        if commands[1] == "show":
            await send_panel(app, source, user, msg_type)

        if commands[1] == "exit":
            if user.id in in_gaming_list:
                await send_msg(source, [Plain("退出成功")], user, msg_type)
                del in_gaming_list[user.id]
            else:
                await send_msg(source, [Plain("请输入 m 开始 开始游戏")], user, msg_type)
        # 命令长度大于3才可以使用
        if len(commands) < 3:
            return
        if commands[1] == "d":
            try:
                for i in range(2, len(commands)):
                    location = MineSweeper.parse_input(commands[i])
                    in_gaming_list[user.id].mine(location[0], location[1])
                    if in_gaming_list[user.id].state != GameState.GAMING:
                        print("break!")
                        break
            except ValueError as e:
                await send_msg(source, [Plain(f"错误: {e}")], user, msg_type)
            await send_panel(app, source, user, msg_type)
            if in_gaming_list[user.id].state != GameState.GAMING:
                await send_game_over(app, source, user, msg_type)

        if commands[1] == "t":
            try:
                for i in range(2, len(commands)):
                    location = MineSweeper.parse_input(commands[i])
                    in_gaming_list[user.id].tag(location[0], location[1])
                await send_panel(app, source, user, msg_type)
            except ValueError as e:
                await send_msg(source, [Plain(f"错误: {e}")], user, msg_type)


def my_exit():
    global running
    running = False
    exit()


if __name__ == "__main__":
    Thread(target=clean_thread).start()
    signal.signal(signal.SIGINT, my_exit)
    signal.signal(signal.SIGTERM, my_exit)
    app.run()
