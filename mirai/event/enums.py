from enum import Enum

class ExternalEventTypes(Enum):
    BotOnlineEvent = "BotOnlineEvent"
    BotOfflineEventActive = "BotOfflineEventActive"
    BotOfflineEventForce = "BotOfflineEventForce"
    BotOfflineEventDropped = "BotOfflineEventDropped"
    BotReloginEvent = "BotReloginEvent"
    BotGroupPermissionChangeEvent = "BotGroupPermissionChangeEvent"
    BotMuteEvent = "BotMuteEvent"
    BotUnmuteEvent = "BotUnmuteEvent"
    BotJoinGroupEvent = "BotJoinGroupEvent"
    BotLeaveEventActive = "BotLeaveEventActive"
    BotLeaveEventKick = "BotLeaveEventKick"

    GroupRecallEvent = "GroupRecallEvent"
    FriendRecallEvent = "FriendRecallEvent"

    GroupNameChangeEvent = "GroupNameChangeEvent"
    GroupEntranceAnnouncementChangeEvent = "GroupEntranceAnnouncementChangeEvent"
    GroupMuteAllEvent = "GroupMuteAllEvent"

    # 群设置被修改事件
    GroupAllowAnonymousChatEvent = "GroupAllowAnonymousChatEvent" # 群设置 是否允许匿名聊天 被修改
    GroupAllowConfessTalkEvent = "GroupAllowConfessTalkEvent" # 坦白说
    GroupAllowMemberInviteEvent = "GroupAllowMemberInviteEvent" # 邀请进群

    # 群事件(被 Bot 监听到的, 为"被动事件", 其中 Bot 身份为第三方.)
    MemberJoinEvent = "MemberJoinEvent"
    MemberLeaveEventKick = "MemberLeaveEventKick"
    MemberLeaveEventQuit = "MemberLeaveEventQuit"
    MemberCardChangeEvent = "MemberCardChangeEvent"
    MemberSpecialTitleChangeEvent = "MemberSpecialTitleChangeEvent"
    MemberPermissionChangeEvent = "MemberPermissionChangeEvent"
    MemberMuteEvent = "MemberMuteEvent"
    MemberUnmuteEvent = "MemberUnmuteEvent"

    NewFriendRequestEvent = "NewFriendRequestEvent"
    MemberJoinRequestEvent = "MemberJoinRequestEvent"

    # python-mirai 自己提供的事件
    UnexceptedException = "UnexceptedException"

class NewFriendRequestResponseOperate(Enum):
    accept = 0
    refuse = 1
    refuse_and_blacklist = 2

class MemberJoinRequestResponseOperate(Enum):
    accept = 0
    refuse = 1
    ignore = 2
    refuse_and_blacklist = 3
    ignore_and_blacklist = 4
