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


class ManualLRUCache:

    # STYLE NOTE: This class was nested because it is intimately tied
    #             together with value_from_key() created/decorated
    #             in ManualLRUCache.__init__ and used by encache.
    #
    # A 'Smuggle' allows passing a key and "smuggling in" an optional value.
    # The point is that the value is hidden from @lru_cache via the
    # implementation of dunder hash/eq methods here.  This is how the value
    # is passed *in* to value_from_key as decorated with @lru_cache, so
    # that value_from_key can return a value (from a key) causing
    # the lru_cache code to encache the key/value pair.

    class _Smuggle:
        __slots__ = ['__key', 'smuggledvalue']

        def __init__(self, key):
            self.__key = key

        # enforce read-only on key; this is really not necessary because
        # _Smuggle is a private class here but do it anyway.
        @property
        def key(self):
            return self.__key

        # note that this ignores any smuggled value
        def __hash__(self):
            return hash(self.key)

        # note that this ignores any smuggled value
        def __eq__(self, other):
            return self.key == other.key

    def __init__(self, cachesize=100):

        # This is the magic function that (ab)uses lru_cache to do the work.
        # NOTE: has to be created/decorated at init time (vs class method)
        # so that each cache has its own @lru_cache internals, including
        # having its own maxsize (cachesize) as specified.
        @lru_cache(maxsize=cachesize)
        def __value_from_key(smg):
            try:
                return smg.smuggledvalue   # only works if coming from encache
            except AttributeError as e:
                raise KeyError(smg.key) from e

        self._value_from_key = __value_from_key

    def encache(self, key, value):
        """Force something into the cache."""
        # Need to pass the value to _value_from_key... this way!
        smg = self._Smuggle(key)
        smg.smuggledvalue = value
        self._value_from_key(smg)

    def __getitem__(self, key):
        # If lru_cache has this key, it will return the value
        # (instead of invoking _value_from_key). Otherwise,
        # _value_from_key will raise KeyError (because there is
        # no smuggled value, only the key). This is how "return it if
        # it is in the LRU cache" works.
        # See __contains__ for another way to understand this.
        return self._value_from_key(self._Smuggle(key))

    def __contains__(self, key):
        # See __getitem__ for another way to understand this.
        try:
            _ = self[key]
        except KeyError:
            return False
        return True
