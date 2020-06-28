# MineSweeper
Mirai群内的扫雷小游戏

在任意群内发送`扫雷`可查看菜单

# 部署

clone项目，新建config.py，填入以下内容
```python
qq = qq号
authKey = "你得key"
mirai_api_http_locate = "地址:端口/"
```
输入以下命令启动
```
docker build . --rm -t minesweeper
docker run --rm -it -v 当前路径:/data minesweeper
```
