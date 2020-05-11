import asyncio
from unittest import TestCase
from main import app
from calc import parse_expression
from fastapi.testclient import TestClient
import re
from main import startup_event

client = TestClient(app)


class TestCalc(TestCase):
    def setUp(self):
        self.pid = 0

    def inc_pid(self):
        self.pid += 1

    def test_valid_expressions(self):
        valid_exprs = ['(1 + 2 + 3 +4) / (9 * 6 + 9) - 10 + 4/10',
                       '12 + (1 + 2 + 3 +4) / (8 - 9 * 6 + 9) - 10 + 80/10 - 90/10',
                       '12+((1+2+3+4)/(8-9*6+9)*19 +6)-10+7/78-((10-7)/8)+8/(8+7)',
                       '(((8+12)))',
                       '(9 + (1 + 2))',
                       '(((9)))',
                       '9']
        for expr in valid_exprs:
            res, err = parse_expression(expr, self.pid, 0)
            self.assertEqual(res, eval(expr))
            self.assertEqual(err, None, 'expression = %s res = %s' % (expr, res))
            self.inc_pid()

    def test_invalid_expressions(self):
        invalid_exprs = ['',
                         '(1',
                         '1)',
                         '(1 + 2 + 3 +4) / (9 * 6 + 9) - 10 + 4/100)',
                         '((1 + 2 + 3 +4) / (9 * 6 + 9) - 10 + 4/100',
                         '1 + 2 *4) / 9',
                         'x + y - 9',
                         'func() + 9',
                         '()',
                         'hgg',
                         '14/0',
                         '114 + (12/(8-8)) * 14'
                         ]
        for expr in invalid_exprs:
            res, err = parse_expression(expr, self.pid, 0)
            self.assertEqual(res, None, 'expression = %s res = %s err = %s' % (expr, res, err))
            self.assertNotEqual(err, None)
            self.inc_pid()


class TestMain(TestCase):
    # input: string with math expression, containing () /* +- and integers(not supporting floats and float delimiter)
    # start parsing and calculating math expression
    def setUp(self):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(startup_event())

    def send_post(self, expr_str):
        response = client.post(
            "/calculate",
            json={"expression": expr_str}
        )
        return response

    def get(self, pid):
        response = client.get("/result?id=%s" % pid)
        return response

    def test_invalid_expression(self):
        # invalid expression
        invalid_exprs = ['',
                         '(1',
                         '1)',
                         '(1 + 2 + 3 +4) / (9 * 6 + 9) - 10 + 4/100)',
                         '((1 + 2 + 3 +4) / (9 * 6 + 9) - 10 + 4/100',
                         '1 + 2 *4) / 9',
                         'x + y - 9',
                         'func() + 9',
                         '()',
                         'hgg',
                         '14/0',
                         '114 + (12/(8-8)) * 14'
                         ]
        for invalid_expr in invalid_exprs:
            ret = self.send_post(invalid_expr)
            assert ret.status_code == 200
            self.assertTrue(re.match('{"ret":[0-9]+,"status":"ok"}', ret.text) != None)

    def test_correct_work(self):
        # correct expression
        valid_exprs = ['(1 + 2 + 3 +4) / (9 * 6 + 9) - 10 + 4/10',
                       '12 + (1 + 2 + 3 +4) / (8 - 9 * 6 + 9) - 10 + 80/10 - 90/10',
                       '12+((1+2+3+4)/(8-9*6+9)*19 +6)-10+7/78-((10-7)/8)+8/(8+7)',
                       '(((8+12)))',
                       '(9 + (1 + ]2))',
                       '(((0)))',
                       '0']
        for valid_expr in valid_exprs:
            ret = self.send_post(valid_expr)
            assert ret.status_code == 200
            self.assertTrue(re.match('{"ret":[0-9]+,"status":"ok"}', ret.text) != None)
            pid = int(ret.json()['ret'])

            print('\nstart process with pid = %s\n' % pid)

            ret = self.get(pid)
            self.assertEqual(ret.text, '{"ret":"processing soon...","status":"ok"}')

            ret = self.get(22200)
            self.assertEqual(ret.text, '{"ret":"not found","status":"Nok"}')
