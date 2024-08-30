#!/usr/bin/env python3
'''A module to interact with Redis for caching and storing data.
'''

import uuid
import redis
from functools import wraps
from typing import Any, Callable, Union


def track_calls(method: Callable) -> Callable:
    '''Keeps track of how many times a method in the Cache class is called.
    '''
    @wraps(method)
    def wrapper(self, *args, **kwargs) -> Any:
        '''Increments the call count before calling the original method.
        '''
        if isinstance(self._redis_instance, redis.Redis):
            self._redis_instance.incr(method.__qualname__)
        return method(self, *args, **kwargs)
    return wrapper


def log_call_details(method: Callable) -> Callable:
    '''Logs the input and output of a method in the Cache class.
    '''
    @wraps(method)
    def wrapper(self, *args, **kwargs) -> Any:
        '''Stores method arguments and output before returning the result.
        '''
        input_key = f'{method.__qualname__}:inputs'
        output_key = f'{method.__qualname__}:outputs'
        if isinstance(self._redis_instance, redis.Redis):
            self._redis_instance.rpush(input_key, str(args))
        result = method(self, *args, **kwargs)
        if isinstance(self._redis_instance, redis.Redis):
            self._redis_instance.rpush(output_key, result)
        return result
    return wrapper


def display_call_history(fn: Callable) -> None:
    '''Displays the history of calls made to a method in the Cache class.
    '''
    if not fn or not hasattr(fn, '__self__'):
        return
    redis_instance = getattr(fn.__self__, '_redis_instance', None)
    if not isinstance(redis_instance, redis.Redis):
        return
    method_name = fn.__qualname__
    input_key = f'{method_name}:inputs'
    output_key = f'{method_name}:outputs'
    call_count = 0
    if redis_instance.exists(method_name):
        call_count = int(redis_instance.get(method_name))
    print(f'{method_name} was called {call_count} times:')
    inputs = redis_instance.lrange(input_key, 0, -1)
    outputs = redis_instance.lrange(output_key, 0, -1)
    for inp, outp in zip(inputs, outputs):
        print(f'{method_name}(*{inp.decode("utf-8")}) -> {outp}')


class Cache:
    '''A class for caching and storing data in Redis.
    '''
    def __init__(self) -> None:
        '''Initializes a new Cache object.
        '''
        self._redis_instance = redis.Redis()
        self._redis_instance.flushdb(True)

    @log_call_details
    @track_calls
    def save(self, data: Union[str, bytes, int, float]) -> str:
        '''Stores data in Redis and returns a unique key.
        '''
        key = str(uuid.uuid4())
        self._redis_instance.set(key, data)
        return key

    def retrieve(
            self,
            key: str,
            transform: Callable = None,
            ) -> Union[str, bytes, int, float]:
        '''Fetches data from Redis by key and applies an optional transform.
        '''
        value = self._redis_instance.get(key)
        return transform(value) if transform else value

    def retrieve_str(self, key: str) -> str:
        '''Fetches a string value from Redis.
        '''
        return self.retrieve(key, lambda x: x.decode('utf-8'))

    def retrieve_int(self, key: str) -> int:
        '''Fetches an integer value from Redis.
        '''
        return self.retrieve(key, lambda x: int(x))

