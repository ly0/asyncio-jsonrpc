from asynciorpc.interface.register import register
from asynciorpc.runner import run

# put your implement codes to implements package
# import here and register as an asynciorpc

class TestClass:

    def test(self, a, b):
        import time
        time.sleep(10)
        return (1, a, b)

    def test2(self, a, b):
        return (1, a, b)

a = TestClass()
register(a.test, 'TestApi') # http://127.0.0.1:10080/dmall.ams.TestApi
register(a.test2, 'TestApi2') # http://127.0.0.1:10080/dmall.ams.TestApi2

run()
