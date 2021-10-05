# The MIT License (MIT)
#
# Copyright (c) 2021 Neil Webber
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

from functools import lru_cache
import threading

# @lru_cache contains an LRU cache implementation but doesn't expose it,
# which is unfortunate in cases where a more general interface would be
# useful. As a simple example, there might be an algorithm policy decision
# based on whether something expensive to compute is currently in cache.
# There could also be more complex decisions about *what* results to
# cache (e.g., doing LRU but only on a subset of results).
#
# This class exposes a manual LRU cache with the following methods:
#
#      encache     : put something into the cache (bumping the LRU item out)
#      __getitem__ : retrieve something from the cache, or raise KeyError
#      __contains__: test for something being in the cache
#
# It does this by a clever ("brutish"?) hack to trick @lru_cache into
# doing the bulk of the work. A key/value pair is entered into the
# lru_cache by having this function:
#
#      @lru_cache
#      def value_from_key(key):
#          return value
#
# which returns a value for a key and can be decorated by @lru_cache to
# get that key/value pair cached. But how does value_from_key know what
# the value is? It's passed "under the covers" (out of sight from lru_cache)
# via an object attribute! Yeehah!
#
# NOTE: THE SIMPLEST/FASTEST IMPLEMENTATION OF THIS IS NOT THREAD SAFE.
#       See the ThreadSafe... subclass after this for a version with locking.
#
# XXX: Is there a simpler/better way to leverage the lru_cache code to
# create an LRU cache where entries can be manually added to it?
#


class ManualLRUCache:

    def __init__(self, cachesize=100):
        self.__keyval = (object(), 'NO-MATCH')   # won't match any user key

        # the magic function that (ab)uses lru_cache to do the work
        @lru_cache(maxsize=cachesize)
        def value_from_key(key):
            k, v = self.__keyval
            if key == k:
                return v     # most importantly, this makes lru_cache cache it
            raise KeyError(key)

        self._value_from_key = value_from_key

    def encache(self, key, value):
        """Force something into the cache. NOT THREAD SAFE."""
        # Need to pass the value to _value_from_key... this way!
        self.__keyval = (key, value)
        # this shouldn't ever KeyError, but it can if invoked
        # in multithreading without locks. Fail gracefully...
        try:
            self._value_from_key(key)            # puts it in the lru_cache
        except KeyError:
            pass

    def __getitem__(self, key):
        # If lru_cache has this key, it will return the value.
        # Otherwise, this will invoke value_from_key which will
        # raise KeyError (because the key won't match __keyval).
        # This is how "return it if it is in the LRU cache" works.
        # See __contains__ for another way to understand this.
        return self._value_from_key(key)

    def __contains__(self, key):
        # See __getitem__ for another way to understand this.
        try:
            _ = self[key]
        except KeyError:
            return False
        else:
            return True


# same but with locking for thread safety
class ThreadSafeManualLRUCache(ManualLRUCache):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__lock = threading.Lock()

    def encache(self, key, value):
        with self.__lock:
            super().encache(key, value)

    def __getitem__(self, key):
        with self.__lock:
            return super().__getitem__(key)

    # don't have to override __contains__ because __getitem__ lock suffices
