import asyncio
import copy
import inspect
import traceback
from functools import partial, lru_cache
from async_lru import alru_cache
from typing import (
    Any, Awaitable, Callable, Dict, List, NamedTuple, Optional, Union)
from urllib import parse
from contextlib import AsyncExitStack, ExitStack

import pydantic
import aiohttp
import sys

from mirai.depend import Depend
from mirai.entities.friend import Friend
from mirai.entities.group import Group, Member
from mirai.event import ExternalEvent, ExternalEventTypes, InternalEvent
from mirai.event.message import MessageChain, components
from mirai.event.message.models import (
  FriendMessage, GroupMessage, TempMessage,
  MessageItemType, MessageTypes
)
from mirai.logger import (
  Event as EventLogger,
  Session as SessionLogger,
  Network as NetworkLogger
)
from mirai.misc import argument_signature, raiser, TRACEBACKED, printer
from mirai.network import fetch
from mirai.protocol import MiraiProtocol
from mirai.entities.builtins import ExecutorProtocol
from functools import lru_cache
from mirai import exceptions

class Mirai(MiraiProtocol):
  event: Dict[
    str, List[Callable[[Any], Awaitable]]
  ] = {}
  subroutines: List[Callable] = []
  lifecycle: Dict[str, List[Callable]] = {
    "start": [],
    "end": [],
    "around": []
  }
  useWebsocket = False
  listening_exceptions: List[Exception] = []

  extensite_config: Dict
  global_dependencies: List[Depend]
  global_middlewares: List

  def __init__(self,
    url: Optional[str] = None,

    host: Optional[str] = None,
    port: Optional[int] = None,
    authKey: Optional[str] = None,
    qq: Optional[int] = None,

    websocket: bool = False,
    extensite_config: dict = None,
    global_dependencies: List[Depend] = None,
    global_middlewares: List = None
  ):
    self.extensite_config = extensite_config or {}
    self.global_dependencies = global_dependencies or []
    self.global_middlewares = global_middlewares or []
    self.useWebsocket = websocket

    if url:
      urlinfo = parse.urlparse(url)
      if urlinfo:
        query_info = parse.parse_qs(urlinfo.query)
        if all([
          urlinfo.scheme == "mirai",
          urlinfo.path in ["/", "/ws"],

          "authKey" in query_info and query_info["authKey"],
          "qq" in query_info and query_info["qq"]
        ]):
          if urlinfo.path == "/ws":
            self.useWebsocket = True
          else:
            self.useWebsocket = websocket

          authKey = query_info["authKey"][0]

          self.baseurl = f"http://{urlinfo.netloc}"
          self.auth_key = authKey
          self.qq =  int(query_info["qq"][0])
        else:
          raise ValueError("invaild url: wrong format")
      else:
        raise ValueError("invaild url")
    else:
      if all([host, port, authKey, qq]):
        self.baseurl = f"http://{host}:{port}"
        self.auth_key = authKey
        self.qq = int(qq)
      else:
        raise ValueError("invaild arguments")

  async def enable_session(self):
    auth_response = await self.auth()
    if all([
      "code" in auth_response and auth_response['code'] == 0,
      "session" in auth_response and auth_response['session']
    ]):
      if "msg" in auth_response and auth_response['msg']:
        self.session_key = auth_response['msg']
      else:
        self.session_key = auth_response['session']

      await self.verify()
    else:
      if "code" in auth_response and auth_response['code'] == 1:
        raise ValueError("invaild authKey")
      else:
        raise ValueError('invaild args: unknown response')

    self.enabled = True
    return self

  def receiver(self,
      event_name,
      dependencies: List[Depend] = None,
      use_middlewares: List[Callable] = None
    ):
    event_name = self.getEventCurrentName(event_name)
    def receiver_warpper(func: Callable):
      if not inspect.iscoroutinefunction(func):
        raise TypeError("event body must be a coroutine function.")

      self.event.setdefault(event_name, [])
      self.event[event_name].append(ExecutorProtocol(
        callable=func,
        dependencies=(dependencies or []) + self.global_dependencies,
        middlewares=(use_middlewares or []) + self.global_middlewares
      ))
      return func
    return receiver_warpper

  async def message_polling(self, count=10):
    while True:
      await asyncio.sleep(0.5)

      try:
        result  = \
          await super().fetchMessage(count)
      except pydantic.ValidationError:
        continue
      last_length = len(result)
      latest_result = []
      while True:
        if last_length == count:
          latest_result = await super().fetchMessage(count)
          last_length = len(latest_result)
          result += latest_result
          continue
        break

      for message_index in range(len(result)):
        item = result[message_index]
        await self.queue.put(
          InternalEvent(
            name=self.getEventCurrentName(type(item)),
            body=item
          )
        )

  async def ws_message(self):
    async with aiohttp.ClientSession() as session:
      async with session.ws_connect(
        f"{self.baseurl}/message?sessionKey={self.session_key}"
      ) as ws_connection:
        while True:
          try:
            received_data = await ws_connection.receive_json()
          except TypeError:
            continue
          if received_data:
            NetworkLogger.debug("received", received_data)
            try:
              received_data['messageChain'] = MessageChain.parse_obj(received_data['messageChain'])
              received_data = MessageTypes[received_data['type']].parse_obj(received_data)
            except pydantic.ValidationError:
              SessionLogger.error(f"parse failed: {received_data}")
              traceback.print_exc()
            else:
              await self.queue.put(InternalEvent(
                name=self.getEventCurrentName(type(received_data)),
                body=received_data
              ))
  
  async def ws_event(self):
    from mirai.event.external.enums import ExternalEvents
    async with aiohttp.ClientSession() as session:
      async with session.ws_connect(
        f"{self.baseurl}/event?sessionKey={self.session_key}"
      ) as ws_connection:
        while True:
          try:
            received_data = await ws_connection.receive_json()
          except TypeError:
            continue
          if received_data:
            try:
              if hasattr(ExternalEvents, received_data['type']):
                  received_data = \
                    ExternalEvents[received_data['type']]\
                      .value\
                      .parse_obj(received_data)
              else:
                raise exceptions.UnknownEvent(f"a unknown event has been received, it's '{received_data['type']}'")
            except pydantic.ValidationError:
              SessionLogger.error(f"parse failed: {received_data}")
              traceback.print_exc()
            else:
              await self.queue.put(InternalEvent(
                name=self.getEventCurrentName(type(received_data)),
                body=received_data
              ))

  async def event_runner(self):
    while True:
      try:
        event_context: NamedTuple[InternalEvent] = await asyncio.wait_for(self.queue.get(), 3)
      except asyncio.TimeoutError:
        continue

      if event_context.name in self.registeredEventNames:
        EventLogger.info(f"handling a event: {event_context.name}")
        for event_body in list(self.event.values())\
              [self.registeredEventNames.index(event_context.name)]:
          if event_body:
            running_loop = asyncio.get_running_loop()
            running_loop.create_task(self.executor(event_body, event_context))

  @staticmethod
  def sort_middlewares(iterator):
    return {
      "async": [
        i for i in iterator if all([
          hasattr(i, "__aenter__"),
          hasattr(i, "__aexit__")
        ])
      ],
      "normal": [
        i for i in iterator if all([
          hasattr(i, "__enter__"),
          hasattr(i, "__exit__")
        ])
      ]
    }

  async def put_exception(self, event_context, exception):
    from mirai.event.builtins import UnexpectedException
    if event_context.name != "UnexpectedException":
      if exception.__class__ in self.listening_exceptions:
        EventLogger.error(f"threw a exception by {event_context.name}, Exception: {exception.__class__.__name__}, and it has been catched.")
      else:
        EventLogger.error(f"threw a exception by {event_context.name}, Exception: {exception.__class__.__name__}, and it hasn't been catched!")
        traceback.print_exc()
      await self.queue.put(InternalEvent(
        name="UnexpectedException",
        body=UnexpectedException(
          error=exception,
          event=event_context,
          application=self
        )
      ))
    else:
      EventLogger.critical(f"threw a exception in a exception handler by {event_context.name}, Exception: {exception.__class__.__name__}.")

  async def executor_with_middlewares(self,
    callable, raw_middlewares,
    event_context,
    lru_cache_sets=None
  ):
    middlewares = self.sort_middlewares(raw_middlewares)
    try:
      async with AsyncExitStack() as stack:
        for async_middleware in middlewares['async']:
          await stack.enter_async_context(async_middleware)
        for normal_middleware in middlewares['normal']:
          stack.enter_context(normal_middleware)
      
      result = await self.executor(
        ExecutorProtocol(
          callable=callable,
          dependencies=self.global_dependencies,
          middlewares=[]
        ),
        event_context,
        lru_cache_sets=lru_cache_sets
      )
      if result is TRACEBACKED:
        return TRACEBACKED
    except exceptions.Cancelled:
      return TRACEBACKED
    except (NameError, TypeError) as e:
      EventLogger.error(f"threw a exception by {event_context.name}, it's about Annotations Checker, please report to developer.")
      traceback.print_exc()
    except Exception as exception:
      if type(exception) not in self.listening_exceptions:
        EventLogger.error(f"threw a exception by {event_context.name} in a depend, and it's {exception}, body has been cancelled.")
        raise
      else:
        await self.put_exception(
          event_context,
          exception
        )
        return TRACEBACKED

  async def executor(self,
    executor_protocol: ExecutorProtocol,
    event_context,
    extra_parameter={},
    lru_cache_sets=None
  ):
    lru_cache_sets = lru_cache_sets or {}
    executor_protocol: ExecutorProtocol
    for depend in executor_protocol.dependencies:
      if not inspect.isclass(depend.func):
        depend_func = depend.func
      elif hasattr(depend.func, "__call__"):
        depend_func = depend.func.__call__
      else:
        raise TypeError("must be callable.")

      if depend_func in lru_cache_sets and depend.cache:
        depend_func = lru_cache_sets[depend_func]
      else:
        if depend.cache:
          original = depend_func
          if inspect.iscoroutinefunction(depend_func):
            depend_func = alru_cache(depend_func)
          else:
            depend_func = lru_cache(depend_func)
          lru_cache_sets[original] = depend_func

      result = await self.executor_with_middlewares(
        depend_func, depend.middlewares, event_context, lru_cache_sets
      )
      if result is TRACEBACKED:
        return TRACEBACKED

    ParamSignatures = argument_signature(executor_protocol.callable)
    PlaceAnnotation = self.get_annotations_mapping()
    CallParams = {}
    for name, annotation, default in ParamSignatures:
      if default:
        if isinstance(default, Depend):
          if not inspect.isclass(default.func):
            depend_func = default.func
          elif hasattr(default.func, "__call__"):
            depend_func = default.func.__call__
          else:
            raise TypeError("must be callable.")
          
          if depend_func in lru_cache_sets and default.cache:
            depend_func = lru_cache_sets[depend_func]
          else:
            if default.cache:
              original = depend_func
              if inspect.iscoroutinefunction(depend_func):
                depend_func = alru_cache(depend_func)
              else:
                depend_func = lru_cache(depend_func)
              lru_cache_sets[original] = depend_func

          CallParams[name] = await self.executor_with_middlewares(
            depend_func, default.middlewares, event_context, lru_cache_sets
          )
          continue
        else:
          raise RuntimeError("checked a unexpected default value.")
      else:
        if annotation in PlaceAnnotation:
          CallParams[name] = PlaceAnnotation[annotation](event_context)
          continue
        else:
          if name not in extra_parameter:
            raise RuntimeError(f"checked a unexpected annotation: {annotation}")
    
    try:
      async with AsyncExitStack() as stack:
        sorted_middlewares = self.sort_middlewares(executor_protocol.middlewares)
        for async_middleware in sorted_middlewares['async']:
          await stack.enter_async_context(async_middleware)
        for normal_middleware in sorted_middlewares['normal']:
          stack.enter_context(normal_middleware)

        return await self.run_func(executor_protocol.callable, **CallParams, **extra_parameter)
    except exceptions.Cancelled:
      return TRACEBACKED
    except Exception as e:
      await self.put_exception(event_context, e)
      return TRACEBACKED

  def getRestraintMapping(self):
    from mirai.event.external.enums import ExternalEvents
    return {
      Mirai: lambda k: True,
      GroupMessage: lambda k: k.__class__.__name__ == "GroupMessage",
      FriendMessage: lambda k: k.__class__.__name__ == "FriendMessage",
      TempMessage: lambda k: k.__class__.__name__ == "TempMessage",
      MessageChain: lambda k: k.__class__.__name__ in MessageTypes,
      components.Source: lambda k: k.__class__.__name__ in MessageTypes,
      Group: lambda k: k.__class__.__name__ in ["GroupMessage", "TempMessage"],
      Friend: lambda k: k.__class__.__name__ =="FriendMessage",
      Member: lambda k: k.__class__.__name__ in ["GroupMessage", "TempMessage"],
      "Sender": lambda k: k.__class__.__name__ in MessageTypes,
      "Type": lambda k: k.__class__.__name__,
      **({
        event_class.value: partial(
          (lambda a, b: a == b.__class__.__name__),
          copy.copy(event_name)
        )
        for event_name, event_class in \
          ExternalEvents.__members__.items()
      })
    }

  def checkEventBodyAnnotations(self):
    event_bodys: Dict[Callable, List[str]] = {}
    for event_name in self.event:
      event_body_list = self.event[event_name]
      for i in event_body_list:
        event_bodys.setdefault(i.callable, [])
        event_bodys[i.callable].append(event_name)
    
    restraint_mapping = self.getRestraintMapping()
    for func in event_bodys:
      self.checkFuncAnnotations(func)

  def getFuncRegisteredEvents(self, callable_target: Callable):
    result = []
    for event_name in self.event:
      if callable_target in [i.callable for i in self.event[event_name]]:
        result.append(event_name)
    return result

  def checkFuncAnnotations(self, callable_target: Callable):
    restraint_mapping = self.getRestraintMapping()
    registered_events = self.getFuncRegisteredEvents(callable_target)
    for name, annotation, default in argument_signature(callable_target):
      if not default:
        if not registered_events:
          raise ValueError(f"error in annotations checker: {callable_target} is invaild.")
        for event_name in registered_events:
          try:
            if not restraint_mapping[annotation](type(event_name, (object,), {})()):
              raise ValueError(f"error in annotations checker: {callable_target}.[{name}:{annotation}]: {event_name}")
          except KeyError:
            raise ValueError(f"error in annotations checker: {callable_target}.[{name}:{annotation}] is invaild.")
          except ValueError:
            raise

  def checkDependencies(self, depend_target: Depend):
    self.checkEventBodyAnnotations()
    for name, annotation, default in argument_signature(depend_target.func):
      if type(default) == Depend:
        self.checkDependencies(default)

  def checkEventDependencies(self):
    for event_name, event_bodys in self.event.items():
      for i in event_bodys:
        for depend in i.dependencies:
          if type(depend) != Depend:
            raise TypeError(f"error in dependencies checker: {i['func']}: {event_name}")
          else:
            self.checkDependencies(depend)

  def exception_handler(self, exception_class=None):
    from .event.builtins import UnexpectedException
    from mirai.event.external.enums import ExternalEvents
    def receiver_warpper(func: Callable):
      event_name = "UnexpectedException"

      if not inspect.iscoroutinefunction(func):
        raise TypeError("event body must be a coroutine function.")

      async def func_warpper_inout(context: UnexpectedException, *args, **kwargs):
        if type(context.error) == exception_class:
          return await func(context, *args, **kwargs)

      func_warpper_inout.__annotations__.update(func.__annotations__)

      self.event.setdefault(event_name, [])
      self.event[event_name].append(ExecutorProtocol(
        callable=func_warpper_inout,
        dependencies=self.global_dependencies,
        middlewares=self.global_middlewares
      ))
      
      if exception_class:
        if exception_class not in self.listening_exceptions:
          self.listening_exceptions.append(exception_class)
      return func
    return receiver_warpper

  def gen_event_anno(self):
    from mirai.event.external.enums import ExternalEvents

    def warpper(name, event_context):
      if name != event_context.name:
        raise ValueError("cannot look up a non-listened event.")
      return event_context.body
    return {
      event_class.value: partial(warpper, copy.copy(event_name))\
      for event_name, event_class in ExternalEvents.__members__.items()
    }

  def get_annotations_mapping(self):
    return {
      Mirai: lambda k: self,
      GroupMessage: lambda k: k.body \
        if self.getEventCurrentName(k.body) == "GroupMessage" else\
          raiser(ValueError("you cannot setting a unbind argument.")),
      FriendMessage: lambda k: k.body \
        if self.getEventCurrentName(k.body) == "FriendMessage" else\
          raiser(ValueError("you cannot setting a unbind argument.")),
      TempMessage: lambda k: k.body \
        if self.getEventCurrentName(k.body) == "TempMessage" else\
          raiser(ValueError("you cannot setting a unbind argument.")),
      MessageChain: lambda k: k.body.messageChain\
        if self.getEventCurrentName(k.body) in MessageTypes else\
          raiser(ValueError("MessageChain is not enable in this type of event.")),
      components.Source: lambda k: k.body.messageChain.getSource()\
        if self.getEventCurrentName(k.body) in MessageTypes else\
          raiser(TypeError("Source is not enable in this type of event.")),
      Group: lambda k: k.body.sender.group\
        if self.getEventCurrentName(k.body) in ["GroupMessage", "TempMessage"] else\
          raiser(ValueError("Group is not enable in this type of event.")),
      Friend: lambda k: k.body.sender\
        if self.getEventCurrentName(k.body) == "FriendMessage" else\
          raiser(ValueError("Friend is not enable in this type of event.")),
      Member: lambda k: k.body.sender\
        if self.getEventCurrentName(k.body) in ["GroupMessage", "TempMessage"] else\
          raiser(ValueError("Group is not enable in this type of event.")),
      "Sender": lambda k: k.body.sender\
        if self.getEventCurrentName(k.body) in MessageTypes else\
          raiser(ValueError("Sender is not enable in this type of event.")),
      "Type": lambda k: self.getEventCurrentName(k.body),
      **self.gen_event_anno()
    }

  def getEventCurrentName(self, event_value):
    from .event.builtins import UnexpectedException
    from mirai.event.external.enums import ExternalEvents
    if inspect.isclass(event_value) and issubclass(event_value, ExternalEvent): # subclass
      return event_value.__name__
    elif isinstance(event_value, ( # normal class
      UnexpectedException,
      GroupMessage,
      FriendMessage,
      TempMessage
    )):
      return event_value.__class__.__name__
    elif event_value in [ # message
      GroupMessage,
      FriendMessage,
      TempMessage
    ]:
      return event_value.__name__
    elif isinstance(event_value, ( # enum
      MessageItemType,
      ExternalEvents
    )):
      return event_value.name
    else:
      return event_value

  @property
  def registeredEventNames(self):
    return [self.getEventCurrentName(i) for i in self.event.keys()]

  def subroutine(self, func: Callable[["Mirai"], Any]):
    from .event.builtins import UnexpectedException
    async def warpper(app: "Mirai"):
      try:
        return await func(app)
      except Exception as e:
        await self.queue.put(InternalEvent(
          name="UnexpectedException",
          body=UnexpectedException(
            error=e,
            event=None,
            application=self
          )
        ))
    self.subroutines.append(warpper)
    return func

  async def checkWebsocket(self, force=False):
    return (await self.getConfig())["enableWebsocket"]

  @staticmethod
  async def run_func(func, *args, **kwargs):
    if inspect.iscoroutinefunction(func):
      await func(*args, **kwargs)
    else:
      func(*args, **kwargs)

  def onStage(self, stage_name):
    def warpper(func):
      self.lifecycle.setdefault(stage_name, [])
      self.lifecycle[stage_name].append(func)
      return func
    return warpper

  def include_others(self, *args: List["Mirai"]):
    for other in args:
      for event_name, items in other.event.items():
        if event_name in self.event:
          self.event[event_name] += items
        else:
          self.event[event_name] = items.copy()
      self.subroutines = other.subroutines
      for life_name, items in other.lifecycle:
        self.lifecycle.setdefault(life_name, [])
        self.lifecycle[life_name] += items
      self.listening_exceptions += other.listening_exceptions

  def run(self, loop=None, no_polling=False, no_forever=False):
    self.checkEventBodyAnnotations()
    self.checkEventDependencies()

    loop = loop or asyncio.get_event_loop()
    self.queue = asyncio.Queue(loop=loop)
    exit_signal = False
    loop.run_until_complete(self.enable_session())
    if not no_polling:
      # check ws status
      if self.useWebsocket:
        SessionLogger.info("event receive method: websocket")
      else:
        SessionLogger.info("event receive method: http polling")

      result = loop.run_until_complete(self.checkWebsocket())
      if not result: # we can use http, not ws.
        # should use http, but we can change it.
        if self.useWebsocket:
          SessionLogger.warning("catched wrong config: enableWebsocket=false, we will modify it.")
          loop.run_until_complete(self.setConfig(enableWebsocket=True))
          loop.create_task(self.ws_event())
          loop.create_task(self.ws_message())
        else:
          loop.create_task(self.message_polling())
      else: # we can use websocket, it's fine
        if self.useWebsocket:
          loop.create_task(self.ws_event())
          loop.create_task(self.ws_message())
        else:
          SessionLogger.warning("catched wrong config: enableWebsocket=true, we will modify it.")
          loop.run_until_complete(self.setConfig(enableWebsocket=False))
          loop.create_task(self.message_polling())
      loop.create_task(self.event_runner())
    
    if not no_forever:
      for i in self.subroutines:
        loop.create_task(i(self))

    try:
      for start_callable in self.lifecycle['start']:
        loop.run_until_complete(self.run_func(start_callable, self))

      for around_callable in self.lifecycle['around']:
        loop.run_until_complete(self.run_func(around_callable, self))

      loop.run_forever()
    except KeyboardInterrupt:
      SessionLogger.info("catched Ctrl-C, exiting..")
    except Exception as e:
      traceback.print_exc()
    finally:
      for around_callable in self.lifecycle['around']:
        loop.run_until_complete(self.run_func(around_callable, self))

      for end_callable in self.lifecycle['end']:
        loop.run_until_complete(self.run_func(end_callable, self))

      loop.run_until_complete(self.release())
