import typing as T
from enum import Enum
from .base import MessageComponentTypes
from mirai.entities.friend import Friend
from mirai.entities.group import Group, Member
from pydantic import BaseModel
from .chain import MessageChain

class MessageItemType(Enum):
    FriendMessage = "FriendMessage"
    GroupMessage = "GroupMessage"
    TempMessage = "TempMessage"
    BotMessage = "BotMessage"

class FriendMessage(BaseModel):
    type: MessageItemType = "FriendMessage"
    messageChain: T.Optional[MessageChain]
    sender: Friend

    def toString(self):
        if self.messageChain:
            return self.messageChain.toString()

class GroupMessage(BaseModel):
    type: MessageItemType = "GroupMessage"
    messageChain: T.Optional[MessageChain]
    sender: Member

    def toString(self):
        if self.messageChain:
            return self.messageChain.toString()

class TempMessage(BaseModel):
    type: MessageItemType = "TempMessage"
    messageChain: T.Optional[MessageChain]
    sender: Member

    def toString(self):
        if self.messageChain:
            return self.messageChain.toString()

class BotMessage(BaseModel):
    type: MessageItemType = 'BotMessage'
    messageId: int

MessageTypes = {
    "GroupMessage": GroupMessage,
    "FriendMessage": FriendMessage,
    "TempMessage": TempMessage
}