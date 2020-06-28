class NetworkError(Exception):
    pass

class Cancelled(Exception):
    pass

class UnknownTarget(Exception):
    pass

class UnknownEvent(Exception):
    pass

class LoginException(Exception):
    "你忘记在mirai-console登录就这种错误."
    pass

class AuthenticateError(Exception):
    pass

class InvaildSession(Exception):
    pass

class ValidatedSession(Exception):
    "一般来讲 这种情况出现时需要刷新session"

class UnknownReceiverTarget(Exception):
    pass

class CallDevelopers(Exception):
    '还愣着干啥?开ISSUE啊!'
    pass

class NonEnabledError(Exception):
    pass

class BotMutedError(Exception):
    pass

class TooLargeMessageError(Exception):
    pass