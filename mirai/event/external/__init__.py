from pydantic import BaseModel, Field
from mirai.event import ExternalEvent
from mirai.event.enums import ExternalEventTypes as EventType
from mirai.entities.group import Permission, Group, Member
from mirai.entities.friend import Friend
import typing as T
from datetime import datetime

class BotOnlineEvent(ExternalEvent):
    type: EventType = EventType.BotOnlineEvent
    qq: int

class BotOfflineEventActive(ExternalEvent):
    type: EventType = EventType.BotOfflineEventActive
    qq: int

class BotOfflineEventForce(ExternalEvent):
    type: EventType = EventType.BotOfflineEventForce
    qq: int

class BotOfflineEventDropped(ExternalEvent):
    type: EventType = EventType.BotOfflineEventDropped
    qq: int

class BotReloginEvent(ExternalEvent):
    type: EventType = EventType.BotReloginEvent
    qq: int

class BotGroupPermissionChangeEvent(ExternalEvent):
    type: EventType = EventType.BotGroupPermissionChangeEvent
    origin: Permission
    current: Permission
    group: Group

class BotMuteEvent(ExternalEvent):
    type: EventType = EventType.BotMuteEvent
    durationSeconds: int
    operator: T.Optional[Member]

class BotUnmuteEvent(ExternalEvent):
    type: EventType = EventType.BotUnmuteEvent
    operator: T.Optional[Member]

class BotJoinGroupEvent(ExternalEvent):
    type: EventType = EventType.BotJoinGroupEvent
    group: Group

class GroupRecallEvent(ExternalEvent):
    type: EventType = EventType.GroupRecallEvent
    authorId: int
    messageId: int
    time: datetime
    group: Group
    operator: T.Optional[Member]

class FriendRecallEvent(ExternalEvent):
    type: EventType = EventType.FriendRecallEvent
    authorId: int
    messageId: int
    time: int
    operator: int

class GroupNameChangeEvent(ExternalEvent):
    type: EventType = EventType.GroupNameChangeEvent
    origin: str
    current: str
    group: Group
    operator: T.Optional[Member]

class GroupEntranceAnnouncementChangeEvent(ExternalEvent):
    type: EventType = EventType.GroupEntranceAnnouncementChangeEvent
    origin: str
    current: str
    group: Group
    operator: T.Optional[Member]

class GroupMuteAllEvent(ExternalEvent):
    type: EventType = EventType.GroupMuteAllEvent
    origin: bool
    current: bool
    group: Group
    operator: T.Optional[Member]

class GroupAllowAnonymousChatEvent(ExternalEvent):
    type: EventType = EventType.GroupAllowAnonymousChatEvent
    origin: bool
    current: bool
    group: Group
    operator: T.Optional[Member]

class GroupAllowConfessTalkEvent(ExternalEvent):
    type: EventType = EventType.GroupAllowAnonymousChatEvent
    origin: bool
    current: bool
    group: Group
    isByBot: bool

class GroupAllowMemberInviteEvent(ExternalEvent):
    type: EventType = EventType.GroupAllowMemberInviteEvent
    origin: bool
    current: bool
    group: Group
    operator: T.Optional[Member]

class MemberJoinEvent(ExternalEvent):
    type: EventType = EventType.MemberJoinEvent
    member: Member

class MemberLeaveEventKick(ExternalEvent):
    type: EventType = EventType.MemberLeaveEventKick
    member: Member
    operator: T.Optional[Member]

class MemberLeaveEventQuit(ExternalEvent):
    type: EventType = EventType.MemberLeaveEventQuit
    member: Member

class MemberCardChangeEvent(ExternalEvent):
    type: EventType = EventType.MemberCardChangeEvent
    origin: str
    current: str
    member: Member
    operator: T.Optional[Member]

class MemberSpecialTitleChangeEvent(ExternalEvent):
    type: EventType = EventType.MemberSpecialTitleChangeEvent
    origin: str
    current: str
    member: Member

class MemberPermissionChangeEvent(ExternalEvent):
    type: EventType = EventType.MemberPermissionChangeEvent
    origin: str
    current: str
    member: Member

class MemberMuteEvent(ExternalEvent):
    type: EventType = EventType.MemberMuteEvent
    durationSeconds: int
    member: Member
    operator: T.Optional[Member]

class MemberUnmuteEvent(ExternalEvent):
    type: EventType = EventType.MemberUnmuteEvent
    member: Member
    operator: T.Optional[Member]

class BotLeaveEventActive(ExternalEvent):
    type: EventType = EventType.BotLeaveEventActive
    group: Group

class BotLeaveEventKick(ExternalEvent):
    type: EventType = EventType.BotLeaveEventKick
    group: Group

class NewFriendRequestEvent(ExternalEvent):
    type: EventType = EventType.NewFriendRequestEvent
    requestId: int = Field(..., alias="eventId")
    supplicant: int = Field(..., alias="fromId") # 即请求方 QQ
    sourceGroup: T.Optional[int] = Field(..., alias="groupId")
    nickname: str = Field(..., alias="nick")

class MemberJoinRequestEvent(ExternalEvent):
    type: EventType = EventType.MemberJoinRequestEvent
    requestId: int = Field(..., alias="eventId")
    supplicant: int = Field(..., alias="fromId") # 即请求方 QQ
    groupId: T.Optional[int] = Field(..., alias="groupId")
    groupName: str = Field(..., alias="groupName")
    nickname: str = Field(..., alias="nick")
