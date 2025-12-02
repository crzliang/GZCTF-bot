# gzctf-bot

通过直接使用SQL语句查询数据库的数据；**因此这项服务不推荐使用公网服务器进行部署**

## 功能

- 指令查询
  - /help 帮助
  - /rank 查询总排行榜
  - /rank-XX 查询指定年级（两位数字前缀，如 25 表示 2025）的排行榜
- 自动播报（默认开启，管理员可以关闭）
  - 一血、二血、三血
  - 新题目开放、提示更新、公告
  - 开关命令：/open、/close

## docker-compose 部署运行:

复制目录下的docker-compose-example.yml文件的内容到本地，重命名为docker-compose.yml，注意要**配置好环境变量**

我是使用napcat作为qq的客户端，所以在yml文件中也带上了napcat的配置。如果你习惯使用其他的客户端，请自行配置。

启动命令

```
docker compose up -d
```
