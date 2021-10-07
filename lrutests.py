import threading
import queue
import unittest
import random
from lrucache import ManualLRUCache


class TestMethods(unittest.TestCase):

    testvals = (('a', 1), ('b', 2), ('c', 3), ('d', 4), ('e', 5))

    # helper function. Builds the cache.
    # NOTE: Tests rely on knowing this puts the items into the cache
    # in order (i.e., callers know the LRU corresponds to kvs)
    def makecache(self, kvs):
        c = ManualLRUCache(cachesize=len(kvs))
        for k, v in kvs:
            c.encache(k, v)
        return c

    def test_CC1(self):
        c = self.makecache(self.testvals)
        # all should be in the cache
        for k, v in self.testvals:
            self.assertTrue(k in c)
            self.assertEqual(c[k], v)

    def test_CC2(self):
        c = self.makecache(self.testvals)

        # add another kv, kicking out the first (oldest)
        kx, vx = object(), 'whatever'
        c.encache(kx, vx)

        # now the first one should be gone
        k0, v0 = self.testvals[0]
        self.assertFalse(k0 in c)

        # the rest should all be in there
        for k, v in self.testvals[1:]:
            self.assertTrue(k in c)
            self.assertEqual(c[k], v)

        # and the newest one should be in there
        self.assertTrue(kx in c)
        self.assertEqual(c[kx], vx)

    def test_CC3(self):
        c = self.makecache(self.testvals)

        # use the first one, so it is no longer the oldest
        k0, v0 = self.testvals[0]
        self.assertEqual(c[k0], v0)

        # add another kv, which will kick out the SECOND one
        kx, vx = object(), 'whatever'
        c.encache(kx, vx)

        self.assertTrue(k0 in c)     # first one still in there
        k1, v1 = self.testvals[1]
        self.assertFalse(k1 in c)    # second should be gone
        for k, v in self.testvals[2:]:
            self.assertTrue(k in c)
            self.assertEqual(c[k], v)

        # and that new one should still be in there
        self.assertTrue(kx in c)
        self.assertEqual(c[kx], vx)

    def test_CC4(self):
        vsize = 500
        cachesizes = [vsize * 2, vsize + 1, vsize, vsize - 1, vsize - 10,
                      vsize // 2, vsize // 7, vsize // 10]

        for keyfmt in (None, "key:{}", "irrelevantly{}longtestkey"):
            kvs = [(keyfmt.format(i) if keyfmt else i,
                    "value:{}".format(i))
                   for i in range(vsize)]
            for cachesize in cachesizes:
                c = ManualLRUCache(cachesize=cachesize)

                # run all the k,v pairs through the cache, such that
                # the last "cachesize" elements in kvs will be the LRU
                # elements in the cache.
                for k, v in kvs:
                    c.encache(k, v)

                # now randomly access key/value pairs and manually
                # track the LRU behavior and see if it matches
                # XXX: This is really a test of @lru_cache and it might
                #      be arguable that strict adherence to cachesize
                #      isn't part of the spec (but this tests for it)
                for i in range(cachesize * 10):
                    nth = random.randrange(vsize)
                    k, v = kvs[nth]
                    kvs.remove((k, v))
                    kvs.append((k, v))
                    c.encache(k, v)
                    self.assertEqual(v, c[k])

                # after all that, the last 'cachesize' elements of kvs
                # should all be in the cache - which may be ALL of the kvs
                # if the cache is larger.
                for i, kv in enumerate(kvs[::-1]):
                    k, v = kv
                    if i < cachesize:
                        self.assertEqual(c[k], v)
                    else:
                        # XXX this tests that any beyond the 'cachesize'
                        #     are not in the cache, but is that really
                        #     part of the @lru_cache interface? Is
                        #     cachesize a suggestion or a guarantee???
                        self.assertFalse(k in c)

    def test_threading(self):
        # an attempt to demonstrate that all this works
        # correctly with multiple threads; obviously, there's
        # no certainty this would expose real race conditions

        failures = queue.Queue()   # threads will send bad news here

        def basher(c, k, nx):
            for i in range(nx):
                c.encache((k, i), (k, i))
                # there's no guarantee it stays in there, it could
                # get bounced out from other threads, but the key
                # (no pun intended) point here is that if it IS in there
                # to make sure it has the right value
                try:
                    kx, ix = c[(k, i)]
                except KeyError:
                    pass
                else:
                    if kx != k or ix != i:
                        failures.put((k, i, kx, ix))
                        break

        # numbers determined somewhat arbitrarily
        nthreads = 50
        nx = 20000
        cachesize = 17
        kvs = [(object(), None) for i in range(cachesize)]
        c = self.makecache(kvs)

        threads = [threading.Thread(target=basher, args=(c, i, nx))
                   for i in range(nthreads)]

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        self.assertTrue(failures.empty())


if __name__ == "__main__":
    unittest.main()
