import threading
import queue
import unittest
from lrucache import ManualLRUCache, ThreadSafeManualLRUCache


class TestMethods(unittest.TestCase):

    testvals = (('a', 1), ('b', 2), ('c', 3), ('d', 4), ('e', 5))

    # helper function. Builds the cache, tests that everything
    # got cached. NOTE: Tests rely on knowing this puts the
    # items into the cache in order (i.e., callers know the LRU)
    def makecache(self, cls, kvs=None):
        if kvs is None:
            kvs = self.testvals

        c = cls(cachesize=len(kvs))
        for k, v in kvs:
            c.encache(k, v)

        # all should be in the cache
        for k, v in kvs:
            self.assertTrue(k in c)
            self.assertEqual(c[k], v)

        return c

    def test_LC1(self, cls=ManualLRUCache):
        c = self.makecache(cls)    # the tests are implicit in makecache

    def test_LC2(self, cls=ManualLRUCache):
        c = self.makecache(cls)

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

    def test_LC3(self, cls=ManualLRUCache):
        c = self.makecache(cls)

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

    # the same tests with the threadsafe versions
    def test_TS1(self):
        with self.subTest(cls="ThreadSafe"):
            self.test_LC1(cls=ThreadSafeManualLRUCache)

    def test_TS2(self):
        with self.subTest(cls="ThreadSafe"):
            self.test_LC2(cls=ThreadSafeManualLRUCache)

    def test_TS3(self):
        with self.subTest(cls="ThreadSafe"):
            self.test_LC3(cls=ThreadSafeManualLRUCache)

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
        nthreads = 20
        nx = 20000
        cachesize = 17
        kvs = [(object(), None) for i in range(cachesize)]
        c = self.makecache(ThreadSafeManualLRUCache, kvs=kvs)

        threads = [threading.Thread(target=basher, args=(c, i, nx))
                   for i in range(nthreads)]

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        self.assertTrue(failures.empty())


if __name__ == "__main__":
    unittest.main()
