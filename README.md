# MineSweeper
Mirai群内的扫雷小游戏

在任意群内或私聊，临时消息发送`扫雷`可查看菜单

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
如需后台运行请使用
```
docker run --rm -it -d -v 当前路径:/data minesweeper
```


还有一个没啥用的cython优化版，请切换到cython分支。比master分支稍快一些
