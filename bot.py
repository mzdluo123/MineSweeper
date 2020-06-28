from mirai import Mirai, Plain, At, GroupMessage, Group, Member, Image
from config import mirai_api_http_locate, authKey, qq
from minesweeper import MineSweeper, GameState
from typing import Dict
from io import BytesIO

app = Mirai(f"mirai://{mirai_api_http_locate}?authKey={authKey}&qq={qq}")

in_gaming_list: Dict[int, MineSweeper] = {}


async def send_panel(app: Mirai, group: Group, member: Member):
    byte_io = BytesIO()
    in_gaming_list[member.id].draw_panel().save(byte_io)
    await app.sendGroupMessage(group, [At(member),
                                       Image.fromIO(byte_io)])


async def send_game_over(app: Mirai, group: Group, member: Member):
    minesweeper = in_gaming_list[member.id]
    if minesweeper.state == GameState.WIN:
        await app.sendGroupMessage(group, [At(member), Plain("恭喜你赢了，再来一次吧！")])
    if minesweeper.state == GameState.FAIL:
        await app.sendGroupMessage(group, [At(member), Plain("太可惜了，就差一点点，再来一次吧！")])
    del in_gaming_list[member.id]


@app.receiver("GroupMessage")
async def event_gm(app: Mirai, group: Group, member: Member, message: GroupMessage):
    plain: Plain = message.messageChain.getFirstComponent(Plain)
    if plain.text == "扫雷":
        await app.sendGroupMessage(group, [Plain("""欢迎游玩扫雷小游戏
        输入 m 开始 即可开始游戏
        使用 m d 位置 来挖开一个方快
        使用 m t 位置 来标记一个方块
        使用 m show 来重新查看游戏盘""")])
    if len(plain.text) > 2 and plain.text[:1] == "m":
        commands = plain.text.split(" ")
        if commands[1] == "开始":
            in_gaming_list[member.id] = MineSweeper(10, 10, 10)
            await send_panel(app, group, member)
        if member.id not in in_gaming_list:
            return
        if commands[1] == "show":
            await send_panel(app, group, member)

        if len(commands) != 3:
            return
        if commands[1] == "d":
            try:
                location = MineSweeper.parse_input(commands[2])
                in_gaming_list[member.id].mine(location[0], location[1])
                if in_gaming_list[member.id].state != GameState.GAMING:
                    await send_game_over(app, group, member)
                await send_panel(app, group, member)
            except Exception as e:
                await app.sendGroupMessage(group, [Plain(f"错误: {e}")])

        if commands[1] == "t":
            try:
                location = MineSweeper.parse_input(commands[2])
                in_gaming_list[member.id].tag(location[0], location[1])
                await send_panel(app, group, member)
            except Exception as e:
                await app.sendGroupMessage(group, [Plain(f"错误: {e}")])


if __name__ == "__main__":
    app.run()
