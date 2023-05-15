Plana Bot
=========

A Simple QQ Bot.

客户端
---------

目前仅支持 go-cqhttp 的反向 ws 连接, 且上报消息需要设置为 array 类型.

启动
-------

确保你已经正确设置并启动了 go-cqhttp , 启动 Plana 只需要以下几行代码:

.. code-block:: python

    from plana import Plana

    bot = Plana()
    bot.run()

插件
--------

插件可以用来扩展 Plana 的功能, 要编写一个新的插件, 只需要在 plugins 目录下新建一个 py 文件或 module ,
编写一个继承自 `plana.Plugin` 的类, Plana 会在启动时自动寻找并加载插件.

支持
----------

下面列出了目前已经支持的功能.

支持的事件
~~~~~~~~~~~~~~~~

支持捕获来自 go-cqhttp 的事件

=============== ==========
Event           Comment
=============== ==========
group_message   群消息
private_message 私聊消息
=============== ==========

支持的操作
~~~~~~~~~~~~~~~~

支持与 go-cqhttp 进行交互

===================== ================
Action                Comment
===================== ================
send_group_message    发送群消息
send_private_message  发送私聊消息
get_login_info        获取登录用户的信息
get_group_member_info 获取群成员信息
===================== ================

消息操作
~~~~~~~~~~~~~~~~

指消息对象上可以使用的操作

========== ====================
Action     Comment
========== ====================
at_bot     当前消息有没有 at 自己
plain_text 消息中的纯文本部分
reply      快速回复
========== ====================
