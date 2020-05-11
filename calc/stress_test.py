import random
import aiohttp
import asyncio
import argparse
import time, re


class Generator:
    operations = ["+", "-", "*", "/"]

    def __init__(self):
        self.res = ''

    def generate_valid(self, s='0'):
        need_exit = random.randint(0, 8)
        if need_exit == 0:
            self._res = s
            return
        a = random.randint(0, 9999999)
        b = random.randint(0, 10)
        op = random.randint(0, 3)
        if op == 3 and a == 0:  # protect division by zero
            a = 1
        s = '%s%s%s' % ('(%s)' % s if b == 10 else s, self.operations[op], a)
        self.generate_valid(s)

    def generate_invalid(self, s=''):
        full_operations = [')', '(']
        full_operations.extend(self.operations)
        c = random.randint(0, 8)
        need_exit = random.randint(0, 8)
        if need_exit == 0:
            self._res = s
            return
        if c == 0:
            a = random.randint(0, 9999999)
            s += str(a)
        else:
            op_index = random.randint(0, 5)
            s += full_operations[op_index]
        self.generate_invalid(s)

    def get(self):
        return self._res


url = 'http://localhost.ru:8000'


async def send_post(expression):
    session = aiohttp.ClientSession()
    ret = await session.post('%s/calculate' % url, data='{"expression":"%s"}' % expression)
    await session.close()
    ret_json = await ret.json()
    if 'ret' in ret_json:
        pid = ret_json['ret']
        print('\nPOST ret pid = %s\n' % pid)
        return pid
    else:
        print('\nPOST result isn\'t pid: %s\n' % await ret.text())
        assert False


async def get(pid):
    session = aiohttp.ClientSession()
    ret = await session.get("%s/result?id=%s" % (url, pid))
    ret_json = await ret.json()
    print('\nGET ret = %s\n' % ret_json['ret'])
    await session.close()
    return ret_json['ret']


async def process_func(expression, is_valid):
    pid = await send_post(expression)
    if not pid:
        print('\nadd calc task for %s expression %s failed!\n' % ('valid' if is_valid else 'invalid', expression))
        return
    res = await get(pid)
    if res == 'processing soon...':
        time.sleep(30)
        res = await get(pid)
        try:
            eval_res = eval(expression)
            assert eval_res == res
        except:
            if is_valid:
                print('\nexception: res = %s is_valid = %s\n' % (res, is_valid))
            assert is_valid == False
    elif res == 'not found':
        print('\ncalculation task for %s expression = %s with pid = %s was aborted\n' % (
        'valid' if is_valid else 'invalid', expression, pid))
    else:
        if re.match('^[0-9]+$', str(res)):
            print('\n OK result =%s for task with expression %s with pid = %s\n' % (res, expression, pid))
        elif res.startswith('ERROR:'):
            assert is_valid != True
        else:
            print('\nunexpected result =%s for task with expression %s with pid = %s\n' % (res, expression, pid))


async def calculation_task(expression, is_valid):
    await process_func(expression, is_valid)


async def test_it(url_str, process_num=200):
    global url
    url = url_str
    generator = Generator()
    tasks_list = []
    for i in range(process_num):
        generator.generate_valid()
        expression = generator.get()
        tasks_list.append(asyncio.create_task(calculation_task(expression, True)))

    for i in range(process_num):
        generator.generate_invalid()
        expression = generator.get()
        tasks_list.append(asyncio.create_task(calculation_task(expression, False)))

    await asyncio.gather(*tasks_list)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Start stress test.')
    parser.add_argument('--process_num', metavar='N', type=int, default=200,
                        help='count of post requests to server with valid & invalid expressions')
    parser.add_argument('--url', metavar='url', type=str, default='http://localhost.ru:8000',
                        help='count of post requests to server with valid & invalid expressions')
    args = parser.parse_args()
    process_num = args.process_num
    url = args.url
    start_time = time.monotonic()
    print('Start stress testing with process_num = %s on %s' % (process_num, url))
    asyncio.get_event_loop().run_until_complete(test_it(url, process_num))
    run_time = time.monotonic() - start_time
    print('\ntime executed: %s\n' % run_time)
