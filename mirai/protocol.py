import json
import re
import threading
import traceback
import typing as T
from datetime import timedelta
from pathlib import Path
from uuid import UUID

import pydantic

from mirai.entities.friend import Friend
from mirai.entities.group import (Group, GroupSetting, Member,
                                  MemberChangeableSetting)
from mirai.event import ExternalEvent
from mirai.event import external as eem
from mirai.event.enums import (
    NewFriendRequestResponseOperate,
    MemberJoinRequestResponseOperate
)
from mirai.event.message import components
from mirai.event.message.base import BaseMessageComponent
from mirai.event.message.chain import MessageChain
from mirai.event.message.models import (BotMessage, FriendMessage,
                                        GroupMessage, MessageTypes)
from mirai.image import InternalImage
from mirai.logger import Protocol as ProtocolLogger
from mirai.misc import (ImageRegex, ImageType, assertOperatorSuccess,
                        edge_case_handler, getMatchedString, printer,
                        protocol_log, raiser, throw_error_if_not_enable)
from mirai.network import fetch

# 与 mirai 的 Command 部分将由 mirai.command 模块进行魔法支持,
# 并尽量的兼容 mirai-console 的内部机制.

class MiraiProtocol:
    qq: int
    baseurl: str
    session_key: str
    auth_key: str

    @protocol_log
    @edge_case_handler
    async def auth(self):
        return assertOperatorSuccess(
            await fetch.http_post(f"{self.baseurl}/auth", {
                "authKey": self.auth_key
            }
        ), raise_exception=True, return_as_is=True)

    @protocol_log
    @edge_case_handler
    async def verify(self):
        return assertOperatorSuccess(
            await fetch.http_post(f"{self.baseurl}/verify", {
                "sessionKey": self.session_key,
                "qq": self.qq
            }
        ), raise_exception=True, return_as_is=True)

    @throw_error_if_not_enable
    @protocol_log
    @edge_case_handler
    async def release(self):
        return assertOperatorSuccess(
            await fetch.http_post(f"{self.baseurl}/release", {
                "sessionKey": self.session_key,
                "qq": self.qq
            }
        ), raise_exception=True)

    @throw_error_if_not_enable
    @edge_case_handler
    async def getConfig(self) -> dict:
        return assertOperatorSuccess(
            await fetch.http_get(f"{self.baseurl}/config", {
                "sessionKey": self.session_key
            }
        ), raise_exception=True, return_as_is=True)

    @throw_error_if_not_enable
    @edge_case_handler
    async def setConfig(self,
        cacheSize=None,
        enableWebsocket=None
    ):
        return assertOperatorSuccess(
            await fetch.http_post(f"{self.baseurl}/config", {
                "sessionKey": self.session_key,
                **({
                    "cacheSize": cacheSize
                } if cacheSize else {}),
                **({
                    "enableWebsocket": enableWebsocket
                } if enableWebsocket else {})
            }
        ), raise_exception=True, return_as_is=True)

    @throw_error_if_not_enable
    @protocol_log
    @edge_case_handler
    async def sendFriendMessage(self,
        friend: T.Union[Friend, int],
        message: T.Union[
            MessageChain,
            BaseMessageComponent,
            T.List[T.Union[BaseMessageComponent, InternalImage]],
            str
        ]
    ) -> BotMessage:
        return BotMessage.parse_obj(assertOperatorSuccess(
            await fetch.http_post(f"{self.baseurl}/sendFriendMessage", {
                "sessionKey": self.session_key,
                "target": self.handleTargetAsFriend(friend),
                "messageChain": await self.handleMessageAsFriend(message)
            }
        ), raise_exception=True, return_as_is=True))

    @throw_error_if_not_enable
    @protocol_log
    @edge_case_handler
    async def sendGroupMessage(self,
        group: T.Union[Group, int],
        message: T.Union[
            MessageChain,
            BaseMessageComponent,
            T.List[T.Union[BaseMessageComponent, InternalImage]],
            str
        ],
        quoteSource: T.Union[int, components.Source]=None
    ) -> BotMessage:
        return BotMessage.parse_obj(assertOperatorSuccess(
            await fetch.http_post(f"{self.baseurl}/sendGroupMessage", {
                "sessionKey": self.session_key,
                "target": self.handleTargetAsGroup(group),
                "messageChain": await self.handleMessageAsGroup(message),
                **({"quote": quoteSource.id \
                    if isinstance(quoteSource, components.Source) else quoteSource}\
                if quoteSource else {})
            }
        ), raise_exception=True, return_as_is=True))

    @throw_error_if_not_enable
    @protocol_log
    @edge_case_handler
    async def sendTempMessage(self,
        group: T.Union[Group, int],
        member: T.Union[Member, int],
        message: T.Union[
            MessageChain,
            BaseMessageComponent,
            T.List[T.Union[BaseMessageComponent, InternalImage]],
            str
        ],
        quoteSource: T.Union[int, components.Source]=None
    ) -> BotMessage:
        return BotMessage.parse_obj(assertOperatorSuccess(
            await fetch.http_post(f"{self.baseurl}/sendTempMessage", {
                "sessionKey": self.session_key,
                "qq": (member.id if isinstance(member, Member) else member),
                "group": (group.id if isinstance(group, Group) else group),
                "messageChain": await self.handleMessageForTempMessage(message),
                **({"quote": quoteSource.id \
                    if isinstance(quoteSource, components.Source) else quoteSource}\
                if quoteSource else {})
            }
        ), raise_exception=True, return_as_is=True))

    @throw_error_if_not_enable
    @protocol_log
    @edge_case_handler
    async def revokeMessage(self, source: T.Union[components.Source, BotMessage, int]):
        return assertOperatorSuccess(await fetch.http_post(f"{self.baseurl}/recall", {
            "sessionKey": self.session_key,
            "target": source if isinstance(source, int) else source.id \
                if isinstance(source, components.Source) else source.messageId\
                if isinstance(source, BotMessage) else\
                    raiser(TypeError("invaild message source"))
        }), raise_exception=True)

    @throw_error_if_not_enable
    @protocol_log
    @edge_case_handler
    async def groupList(self) -> T.List[Group]:
        return [Group.parse_obj(group_info) \
            for group_info in await fetch.http_get(f"{self.baseurl}/groupList", {
                "sessionKey": self.session_key
            })
        ]

    @throw_error_if_not_enable
    @protocol_log
    @edge_case_handler
    async def friendList(self) -> T.List[Friend]:
        return [Friend.parse_obj(friend_info) \
            for friend_info in await fetch.http_get(f"{self.baseurl}/friendList", {
                "sessionKey": self.session_key
            })
        ]

    @throw_error_if_not_enable
    @protocol_log
    @edge_case_handler
    async def memberList(self, target: int) -> T.List[Member]:
        return [Member.parse_obj(member_info) \
            for member_info in await fetch.http_get(f"{self.baseurl}/memberList", {
                "sessionKey": self.session_key,
                "target": target
            })
        ]

    @throw_error_if_not_enable
    @protocol_log
    @edge_case_handler
    async def groupMemberNumber(self, target: int) -> int:
        return len(await self.memberList(target)) + 1

    @throw_error_if_not_enable
    @protocol_log
    @edge_case_handler
    async def uploadImage(self, type: T.Union[str, ImageType], image: InternalImage):
        post_result = json.loads(await fetch.upload(f"{self.baseurl}/uploadImage", image.render(), {
            "sessionKey": self.session_key,
            "type": type if isinstance(type, str) else type.value
        }))
        return components.Image(**post_result)

    @protocol_log
    @edge_case_handler
    async def sendCommand(self, command, *args):
        return assertOperatorSuccess(await fetch.http_post(f"{self.baseurl}/command/send", {
            "authKey": self.auth_key,
            "name": command,
            "args": args
        }), raise_exception=True, return_as_is=True)

    @throw_error_if_not_enable
    @edge_case_handler
    async def fetchMessage(self, count: int) -> T.List[T.Union[FriendMessage, GroupMessage, ExternalEvent]]:
        from mirai.event.external.enums import ExternalEvents
        result = assertOperatorSuccess(
            await fetch.http_get(f"{self.baseurl}/fetchMessage", {
                "sessionKey": self.session_key,
                "count": count
            }
        ), raise_exception=True, return_as_is=True)['data']
        # 因为重新生成一个开销太大, 所以就直接在原数据内进行遍历替换
        try:
            for index in range(len(result)):
                # 判断当前项是否为 Message
                if result[index]['type'] in MessageTypes:
                    if 'messageChain' in result[index]: 
                        result[index]['messageChain'] = MessageChain.parse_obj(result[index]['messageChain'])

                    result[index] = \
                        MessageTypes[result[index]['type']].parse_obj(result[index])

                elif hasattr(ExternalEvents, result[index]['type']):
                    # 判断当前项为 Event
                    result[index] = \
                        ExternalEvents[result[index]['type']].value.parse_obj(result[index])
        except pydantic.ValidationError:
            ProtocolLogger.error(f"parse failed: {result}")
            traceback.print_exc()
            raise
        return result

    @protocol_log
    @edge_case_handler
    async def getManagers(self):
        return assertOperatorSuccess(await fetch.http_get(f"{self.baseurl}/managers"))

    @throw_error_if_not_enable
    @protocol_log
    @edge_case_handler
    async def messageFromId(self, sourceId: T.Union[components.Source, components.Quote, int]):
        if isinstance(sourceId, (components.Source, components.Quote)):
            sourceId = sourceId.id

        result = assertOperatorSuccess(await fetch.http_get(f"{self.baseurl}/messageFromId", {
            "sessionKey": self.session_key,
            "id": sourceId
        }), raise_exception=True, return_as_is=True)

        if result['type'] in MessageTypes:
            if "messageChain" in result:
                result['messageChain'] = MessageChain.custom_parse(result['messageChain'])

            return MessageTypes[result['type']].parse_obj(result)
        else:
            raise TypeError(f"unknown message, not found type.")

    @throw_error_if_not_enable
    @protocol_log
    @edge_case_handler
    async def muteAll(self, group: T.Union[Group, int]) -> bool:
        return assertOperatorSuccess(
            await fetch.http_post(f"{self.baseurl}/muteAll", {
                "sessionKey": self.session_key,
                "target": self.handleTargetAsGroup(group)
            }
        ), raise_exception=True)

    @throw_error_if_not_enable
    @protocol_log
    @edge_case_handler
    async def unmuteAll(self, group: T.Union[Group, int]) -> bool:
        return assertOperatorSuccess(
            await fetch.http_post(f"{self.baseurl}/unmuteAll", {
                "sessionKey": self.session_key,
                "target": self.handleTargetAsGroup(group)
            }
        ), raise_exception=True)

    @throw_error_if_not_enable
    @protocol_log
    @edge_case_handler
    async def memberInfo(self,
        group: T.Union[Group, int],
        member: T.Union[Member, int]
    ):
        return MemberChangeableSetting.parse_obj(assertOperatorSuccess(
            await fetch.http_get(f"{self.baseurl}/memberInfo", {
                "sessionKey": self.session_key,
                "target": self.handleTargetAsGroup(group),
                "memberId": self.handleTargetAsMember(member)
            }
        ), raise_exception=True, return_as_is=True))

    @throw_error_if_not_enable
    @protocol_log
    @edge_case_handler
    async def botMemberInfo(self,
        group: T.Union[Group, int]
    ):
        return await self.memberInfo(group, self.qq)

    @throw_error_if_not_enable
    @protocol_log
    @edge_case_handler
    async def changeMemberInfo(self,
        group: T.Union[Group, int],
        member: T.Union[Member, int],
        setting: MemberChangeableSetting
    ) -> bool:
        return assertOperatorSuccess(
            await fetch.http_post(f"{self.baseurl}/memberInfo", {
                "sessionKey": self.session_key,
                "target": self.handleTargetAsGroup(group),
                "memberId": self.handleTargetAsMember(member),
                "info": json.loads(setting.json())
            }
        ), raise_exception=True)

    @throw_error_if_not_enable
    @protocol_log
    @edge_case_handler
    async def groupConfig(self, group: T.Union[Group, int]) -> GroupSetting:
        return GroupSetting.parse_obj(
            await fetch.http_get(f"{self.baseurl}/groupConfig", {
                "sessionKey": self.session_key,
                "target": self.handleTargetAsGroup(group)
            })
        )

    @throw_error_if_not_enable
    @protocol_log
    @edge_case_handler
    async def changeGroupConfig(self,
        group: T.Union[Group, int],
        config: GroupSetting
    ) -> bool:
        return assertOperatorSuccess(
            await fetch.http_post(f"{self.baseurl}/groupConfig", {
                "sessionKey": self.session_key,
                "target": self.handleTargetAsGroup(group),
                "config": json.loads(config.json())
            }
        ), raise_exception=True)

    @throw_error_if_not_enable
    @protocol_log
    @edge_case_handler
    async def mute(self,
        group: T.Union[Group, int],
        member: T.Union[Member, int],
        time: T.Union[timedelta, int]
    ):
        if isinstance(time, timedelta):
            time = int(time.total_seconds())
        time = min(86400 * 30, max(60, time))
        return assertOperatorSuccess(
            await fetch.http_post(f"{self.baseurl}/mute", {
                "sessionKey": self.session_key,
                "target": self.handleTargetAsGroup(group),
                "memberId": self.handleTargetAsMember(member),
                "time": time
            }
        ), raise_exception=True)

    @throw_error_if_not_enable
    @protocol_log
    @edge_case_handler
    async def unmute(self,
        group: T.Union[Group, int],
        member: T.Union[Member, int]
    ):
        return assertOperatorSuccess(
            await fetch.http_post(f"{self.baseurl}/unmute", {
                "sessionKey": self.session_key,
                "target": self.handleTargetAsGroup(group),
                "memberId": self.handleTargetAsMember(member),
            }
        ), raise_exception=True)

    @throw_error_if_not_enable
    @protocol_log
    @edge_case_handler
    async def kick(self,
        group: T.Union[Group, int],
        member: T.Union[Member, int],
        kickMessage: T.Optional[str] = None
    ):
        return assertOperatorSuccess(
            await fetch.http_post(f"{self.baseurl}/kick", {
                "sessionKey": self.session_key,
                "target": self.handleTargetAsGroup(group),
                "memberId": self.handleTargetAsMember(member),
                **({
                    "msg": kickMessage
                } if kickMessage else {})
            }
        ), raise_exception=True)

    @throw_error_if_not_enable
    @protocol_log
    @edge_case_handler
    async def quitGroup(self,
        group: T.Union[Group, int]
    ):
        return assertOperatorSuccess(
            await fetch.http_post(f"{self.baseurl}/quit", {
                "sessionKey": self.session_key,
                "target": self.handleTargetAsGroup(group)
            }
        ), raise_exception=True) 
      
    @throw_error_if_not_enable
    @protocol_log
    @edge_case_handler
    async def respondRequest(self,
        request: T.Union[
            eem.NewFriendRequestEvent,
            eem.MemberJoinRequestEvent
        ],
        operate: T.Union[
            NewFriendRequestResponseOperate,
            MemberJoinRequestResponseOperate,
            int
        ],
        message: T.Optional[str] = ""
    ):
        """回应请求, 请求指 `添加好友请求` 或 `申请加群请求`."""
        if isinstance(request, eem.NewFriendRequestEvent):
            if not isinstance(operate, (NewFriendRequestResponseOperate, int)):
                raise TypeError(f"unknown operate: {operate}")
            operate = (operate.value if isinstance(operate, NewFriendRequestResponseOperate) else operate)
            return assertOperatorSuccess(await fetch.http_post(f"{self.baseurl}/resp/newFriendRequestEvent", {
                "sessionKey": self.session_key,
                "eventId": request.requestId,
                "fromId": request.supplicant,
                "groupId": request.sourceGroup,
                "operate": operate,
                "message": message
            }), raise_exception=True)
        elif isinstance(request, eem.MemberJoinRequestEvent):
            if not isinstance(operate, (MemberJoinRequestResponseOperate, int)):
                raise TypeError(f"unknown operate: {operate}")
            operate = (operate.value if isinstance(operate, MemberJoinRequestResponseOperate) else operate)
            return assertOperatorSuccess(await fetch.http_post(f"{self.baseurl}/resp/memberJoinRequestEvent", {
                "sessionKey": self.session_key,
                "eventId": request.requestId,
                "fromId": request.supplicant,
                "groupId": request.sourceGroup,
                "operate": operate,
                "message": message
            }), raise_exception=True)
        else:
            raise TypeError(f"unknown request: {request}")

    async def handleMessageAsGroup(
        self,
        message: T.Union[
            MessageChain,
            BaseMessageComponent,
            T.List[T.Union[BaseMessageComponent, InternalImage]],
            str
        ]):
        if isinstance(message, MessageChain):
            return json.loads(message.json())
        elif isinstance(message, BaseMessageComponent):
            return [json.loads(message.json())]
        elif isinstance(message, (tuple, list)):
            result = []
            for i in message:
                if isinstance(i, InternalImage):
                    result.append({
                        "type": "Image" if not i.flash else "FlashImage",
                        "imageId": (await self.handleInternalImageAsGroup(i)).asGroupImage()
                    })
                elif isinstance(i, components.Image):
                    result.append({
                        "type": "Image",
                        "imageId": i.asGroupImage()
                    })
                elif isinstance(i, components.FlashImage):
                    result.append({
                        "type": "FlashImage",
                        "imageId": i.asGroupImage()
                    })
                else:
                    result.append(json.loads(i.json()))
            return result
        elif isinstance(message, str):
            return [json.loads(components.Plain(text=message).json())]
        else:
            raise raiser(ValueError("invaild message."))

    async def handleMessageAsFriend(
        self,
        message: T.Union[
            MessageChain,
            BaseMessageComponent,
            T.List[BaseMessageComponent],
            str
        ]):
        if isinstance(message, MessageChain):
            return json.loads(message.json())
        elif isinstance(message, BaseMessageComponent):
            return [json.loads(message.json())]
        elif isinstance(message, (tuple, list)):
            result = []
            for i in message:
                if isinstance(i, InternalImage):
                    result.append({
                        "type": "Image" if not i.flash else "FlashImage",
                        "imageId": (await self.handleInternalImageAsFriend(i)).asFriendImage()
                    })
                elif isinstance(i, components.Image):
                    result.append({
                        "type": "Image" if not i.flash else "FlashImage",
                        "imageId": i.asFriendImage()
                    })
                else:
                    result.append(json.loads(i.json()))
            return result
        elif isinstance(message, str):
            return [json.loads(components.Plain(text=message).json())]
        else:
            raise raiser(ValueError("invaild message."))

    async def handleMessageForTempMessage(
        self, 
        message: T.Union[
            MessageChain,
            BaseMessageComponent,
            T.List[BaseMessageComponent],
            str
        ]):
        if isinstance(message, MessageChain):
            return json.loads(message.json())
        elif isinstance(message, BaseMessageComponent):
            return [json.loads(message.json())]
        elif isinstance(message, (tuple, list)):
            result = []
            for i in message:
                if isinstance(i, InternalImage):
                    result.append({
                        "type": "Image" if not i.flash else "FlashImage",
                        "imageId": (await self.handleInternalImageForTempMessage(i)).asFriendImage()
                    })
                elif isinstance(i, components.Image):
                    result.append({
                        "type": "Image" if not i.flash else "FlashImage",
                        "imageId": i.asFriendImage()
                    })
                else:
                    result.append(json.loads(i.json()))
            return result
        elif isinstance(message, str):
            return [json.loads(components.Plain(text=message).json())]
        else:
            raise raiser(ValueError("invaild message."))

    def handleTargetAsGroup(self, target: T.Union[Group, int]):
        return target if isinstance(target, int) else \
            target.id if isinstance(target, Group) else \
                raiser(ValueError("invaild target as group."))

    def handleTargetAsFriend(self, target: T.Union[Friend, int]):
        return target if isinstance(target, int) else \
            target.id if isinstance(target, Friend) else \
                raiser(ValueError("invaild target as a friend obj."))

    def handleTargetAsMember(self, target: T.Union[Member, int]):
        return target if isinstance(target, int) else \
            target.id if isinstance(target, Member) else \
                raiser(ValueError("invaild target as a member obj."))

    async def handleInternalImageAsGroup(self, image: InternalImage):
        return await self.uploadImage("group", image)

    async def handleInternalImageAsFriend(self, image: InternalImage):
        return await self.uploadImage("friend", image)

    async def handleInternalImageForTempMessage(self, image: InternalImage):
        return await self.uploadImage("temp", image)
