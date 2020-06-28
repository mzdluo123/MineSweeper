import asyncio
import inspect
import os
import random
import re
import traceback
import typing as T
from collections import namedtuple
from enum import Enum

import aiohttp

from . import exceptions
from .logger import Protocol


def assertOperatorSuccess(result, raise_exception=False, return_as_is=False):
  if not result:
    if raise_exception:
      raise exceptions.InvaildSession("this method returned None, as sessionkey invaild...")
    else:
      return None
  if "code" in result:
    if not raise_exception:
      return result['code'] == 0
    else:
      if result['code'] != 0:
        print(result)
        raise {
          1: exceptions.AuthenticateError, # 这种情况需要检查Authkey, 可能还是连错了.
          2: exceptions.LoginException, # 嗯...你是不是忘记在mirai-console登录了?...算了 自动重连.
          3: exceptions.InvaildSession, # 这种情况会自动重连.
          4: exceptions.ValidatedSession, # 啊 smjb错误... 也会自动重连
          5: exceptions.UnknownReceiverTarget, # 业务代码错误.
          10: PermissionError, # 一般业务代码错误, 自行亦会
          20: exceptions.BotMutedError, # 机器人被禁言
          30: exceptions.TooLargeMessageError,
          400: exceptions.CallDevelopers # 发生这个错误...你就给我提个ISSUE
        }[result['code']](f"""invaild stdin: { {
          1: "wrong auth key",
          2: "unknown qq account",
          3: "invaild session key",
          4: "disabled session key",
          5: "unknown receiver target",
          10: "permission denied",
          20: "bot account has been muted",
          30: "mirai backend cannot deal with so large message",
          400: "wrong arguments"
        }[result['code']] }""")
      else:
        if return_as_is:
          return result
        else:
          return True
  if return_as_is:
    return result
  return False

class ImageType(Enum):
  Friend = "friend"
  Group = "group"

Parameter = namedtuple("Parameter", ["name", "annotation", "default"])

TRACEBACKED = os.urandom(32)

ImageRegex = {
  "group": r"({(?<=\{)([0-9A-Z]{8})\-([0-9A-Z]{4})-([0-9A-Z]{4})-([0-9A-Z]{4})-([0-9A-Z]{12})(?=\})}\..{5}",
  "friend": r"(?<=/)([0-9a-z]{8})\-([0-9a-z]{4})-([0-9a-z]{4})-([0-9a-z]{4})-([0-9a-z]{12})"
}

_windows_device_files = (
  "CON",
  "AUX",
  "COM1",
  "COM2",
  "COM3",
  "COM4",
  "LPT1",
  "LPT2",
  "LPT3",
  "PRN",
  "NUL",
)
_filename_ascii_strip_re = re.compile(r"[^A-Za-z0-9_.-]")

def getMatchedString(regex_result):
  if regex_result:
    return regex_result.string[slice(*regex_result.span())]

def findKey(mapping, value):
  try:
    index = list(mapping.values()).index(value)
  except ValueError:
    return "Unknown"
  return list(mapping.keys())[index]

def raiser(error):
  raise error

def printer(val):
  print(val)
  return val

def justdo(call, val):
  print(call())
  return val

def randomNumberString():
  return str(random.choice(range(100000000, 9999999999)))

def randomRangedNumberString(length_range=(9,)):
  length = random.choice(length_range)
  return random.choice(range(10**(length - 1), int("9"*(length))))

def protocol_log(func):
  async def wrapper(*args, **kwargs):
    try:
      result = await func(*args, **kwargs)
      Protocol.info(f"protocol method {func.__name__} was called")
      return result
    except Exception as e:
      Protocol.error(f"protocol method {func.__name__} raised a error: {e.__class__.__name__}")
      raise e
  return wrapper

def secure_filename(filename):
  if isinstance(filename, str):
    from unicodedata import normalize

    filename = normalize("NFKD", filename).encode("ascii", "ignore")
    filename = filename.decode("ascii")

  for sep in os.path.sep, os.path.altsep:
    if sep:
      filename = filename.replace(sep, " ")

  filename = \
    str(_filename_ascii_strip_re.sub("", "_".join(filename.split()))).strip("._")

  if (
    os.name == "nt" and filename and \
    filename.split(".")[0].upper() in _windows_device_files
  ):
    filename = "_" + filename

  return filename

def edge_case_handler(func):
  async def wrapper(self, *args, **kwargs):
    retry_times = 0
    while retry_times <= 5:
      retry_times += 1
      try:
        return await func(self, *args, **kwargs)
      except exceptions.AuthenticateError:
        Protocol.error("invaild authkey, please check your input.")
        exit(1)
      except exceptions.LoginException:
        Protocol.error("there is not such qq in headless client, we will try again after 5 seconds.")
        await asyncio.sleep(5)
        if func.__name__ != "verify":
          await self.verify()
        continue
      except (exceptions.InvaildSession, exceptions.ValidatedSession):
        Protocol.error("a unexpected session error, we will deal with it.")
        await self.enable_session()
      except aiohttp.client_exceptions.ClientError:
        Protocol.error(f"cannot connect to the headless client, will retry after 5 seconds.")
        await asyncio.sleep(5)
        continue
      except exceptions.CallDevelopers:
        Protocol.error("emmm, please contect me at github.")
        exit(-1)
      except:
        raise
    else:
      Protocol.error("we retried many times, but it doesn't send a success message to us...")
  wrapper.__name__ = func.__name__
  return wrapper

def throw_error_if_not_enable(func):
  def wrapper(self, *args, **kwargs):
    if not self.enabled:
      raise exceptions.NonEnabledError(
        f"you mustn't use any methods in MiraiProtocol...,\
      if you want to access '{func.__name__}' before `app.run()`\
      , use 'Subroutine'."
      )
    return func(self, *args, **kwargs)
  wrapper.__name__ = func.__name__
  wrapper.__annotations__ = func.__annotations__
  return wrapper

def if_error_print_arg(func):
  def wrapper(*args, **kwargs):
    try:
      return func(*args, **kwargs)
    except:
      print(args, kwargs)
      traceback.print_exc()
  return wrapper

def argument_signature(callable_target) -> T.List[Parameter]:
    return [
        Parameter(
            name=name,
            annotation=param.annotation if param.annotation != inspect._empty else None,
            default=param.default if param.default != inspect._empty else None
        )
        for name, param in dict(inspect.signature(callable_target).parameters).items()
    ]
