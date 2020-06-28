# MineSweeper
Mirai群内的扫雷小游戏

在任意群内发送`扫雷`可查看菜单

# 部署

clone项目修改config.py，然后输入
```
docker build . --rm -t minesweeper
docker run --rm -it -v 当前路径:/data minesweeper
```
