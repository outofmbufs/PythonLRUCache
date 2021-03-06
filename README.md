# Python LRU Cache

This is a python class implementing a generalized LRU cache, leveraging
the guts of the functools `@lru_cache` decorator to provide a cache with
three methods:

* A way to manually enter something into the cache (`encache` or via `__setitem__`).
* A way to obtain something from the cache (`__getitem__`), raising an
exception (`KeyError`) on a cache miss.
* A way to test for something being in the cache (`__contains__`).


It does this by tricking `@lru_cache` into doing all the work while
still not reaching into the internals of that function.

## Examples

```
c = ManualLRUCache()
c.encache('a', 1)
c['foo'] = 17             # same as encache('foo', 17)

'a' in c --> True
'b' in c --> False
'foo' in c --> True

c['a'] --> 1
c['b'] --> raises KeyError
c['foo'] --> 17

```
