from asynctest import TestCase
from main import *
from fastapi.testclient import TestClient
client = TestClient(app)


class TestDomain(TestCase):
    def test_is_valid(self):
        domain = Domain('ya.ru')
        self.assertTrue(domain.is_valid())

        domain._domain = 'funbox.ru'
        self.assertTrue(domain.is_valid())

        for domain_name in ['666$$==', '**', '---', 'iuy_0']:
            domain._domain = domain_name
            domain._set_is_valid()
            self.assertFalse(domain.is_valid())

        for domain_name in [666, -10, 0, 'iuy-miu']:
            domain._domain = domain_name
            domain._set_is_valid()
            self.assertFalse(domain.is_valid())

    def test_visit(self):
        visit_time = (int)(time.time())
        domain = Domain('ya.ru')
        domain.visit(visit_time)
        self.assertTrue(domain._max_visited == visit_time)
        self.assertTrue(domain._min_visited == visit_time)

        visit_time2 = (int)(time.time())
        domain.visit(visit_time2)
        self.assertTrue(domain._max_visited == visit_time2)
        self.assertTrue(domain._min_visited == visit_time)

    def test_filter(self):
        domain = Domain('ya.ru', 44)
        domain.visit(0)
        self.assertTrue(domain.filter(0, 55))

        domain._max_visited = 78
        self.assertFalse(domain.filter(0, 55))

        domain._min_visited = 22
        domain._max_visited = 44
        self.assertFalse(domain.filter(0, 33))
        self.assertTrue(domain.filter(0, 45))
        self.assertFalse(domain.filter(33, 37))
        self.assertTrue(domain.filter(20, 45))
        self.assertFalse(domain.filter(0, 22))
        self.assertFalse(domain.filter(44, 88))


    def test_equal(self):
        domain1 = Domain('ya.ru', 88)
        domain2 = Domain('ya.ru', 88)
        self.assertTrue(domain1 == domain2)

        # diff _max_visisted
        domain2.visit(99)
        self.assertFalse(domain1 == domain2)

        # diff _min_visited
        domain2._max_visited = domain1._max_visited
        domain2._min_visited = 33
        self.assertFalse(domain1 == domain2)

        #diff domain name
        domain2._max_visited = domain1._max_visited
        domain2._min_visited = domain1._min_visited
        domain2._domain = 'stackoverflow.com'
        self.assertFalse(domain1 == domain2)

        # all fields are equal again
        domain2._domain = domain1._domain
        self.assertTrue(domain1 == domain2)


class TestMain(TestCase):
    async def setUp(self):
        await startup_event()
        # select test db
        db = await get_redis().select(1)
        #flush test database
        await get_redis().flushdb()
        # set test data
        await self.set_test_data_to_redis()

        # check any data in redis exists
        all_known_domains = await get_all_known_domains()
        self.assertTrue(all_known_domains.__len__() > 0)

    async def tearDown(self):
        await release_lock()

    async def set_test_data_to_redis(self):
        domains = ['ya.ru',
                    'stackoverflow.com',
                    'hh.ru',
                    'habr.com'
                  ]
        await sync_with_redis(domains)

    async def get_domains_from_redis(self, change_func = None):
        all_known_domains = await get_all_known_domains()
        domains = []
        for domain_name in all_known_domains:
            domain = Domain(domain_name.decode('utf-8'))
            await domain.parse_data_from_redis()
            if change_func:
                change_func(domain)
            domains.append(domain)
        return domains

    # input: list of domains
    # need save domains with updating max or min visited timestamp in redis if domain exists soon
    async def test_sync_with_redis(self):
        def visit(domain):
            domain.visit((int)(time.time()))

        all_known_domains_before = await get_all_known_domains()
        #before test: get domain state from redis
        domain_states_before = await self.get_domains_from_redis() #(visit)

        #empty domains list
        domains = []
        await  sync_with_redis(domains)

        #check nothing changes
        all_known_domains = await get_all_known_domains()
        self.assertTrue(all_known_domains.__len__() == all_known_domains_before.__len__())
        self.assertTrue(set(all_known_domains) == set(all_known_domains_before))

        domain_states_after = await self.get_domains_from_redis()

        self.assertTrue(domain_states_after.__len__() == domain_states_before.__len__())
        self.assertTrue(domain_states_after == domain_states_before)

        #invalid domains
        domains = ['gjfdfhg', '000000', '****', 'correct.com']
        await sync_with_redis(domains)

        domain_states_after = await self.get_domains_from_redis()

        #check add only correct domain
        self.assertTrue(domain_states_after.__len__() == domain_states_before.__len__() + 1)
        self.assertFalse(domain_states_after == domain_states_before)

        #invalid data types
        domains = [-1, None, 'correct.com']
        await sync_with_redis(domains)

        domain_states_after = await self.get_domains_from_redis()

        # check add only correct domain
        self.assertTrue(domain_states_after.__len__() == domain_states_before.__len__() + 1)
        self.assertFalse(domain_states_after == domain_states_before)

        #ok domains
        domains = ['google.com', 'vk.com', 'correct.com']
        await sync_with_redis(domains)

        domain_states_after = await self.get_domains_from_redis()

        # check + 2 new, 1 updated
        self.assertTrue(domain_states_after.__len__() == domain_states_before.__len__() + 3)
        self.assertFalse(domain_states_after == domain_states_before)

    # input: timestamps from to
    # need return a list of uniq visited domains in [from, to] saved in redis
    async def test_query_domains_from_redis(self):

        # zero from, to
        from_ts = 0
        to_ts = 0
        ret = await query_domains_from_redis(from_ts, to_ts)
        self.assertTrue(ret.__len__() == 0)

        # negative from, to
        from_ts = -5
        to_ts = -8
        ret = await query_domains_from_redis(from_ts, to_ts)
        self.assertTrue(ret.__len__() == 0)

        # to > from => need replace to & from
        from_ts = int(time.time())
        to_ts = 0
        ret = await query_domains_from_redis(from_ts, to_ts)
        self.assertTrue(ret.__len__() > 0)

        # from == to
        from_ts = int(time.time())
        to_ts = int(time.time())
        ret = await query_domains_from_redis(from_ts, to_ts)
        self.assertTrue(ret.__len__() == 0)

        # from > to
        from_ts = 0
        to_ts = int(time.time())
        ret = await query_domains_from_redis(from_ts, to_ts)
        self.assertTrue(ret.__len__() > 0)



    # input: links list
    # save a list uniq visited domains to redis with current timestamp
    def test_send_post(self):
        def send_post(links):
            response = client.post(
                "/visited_links",
                json={"links": links},
            )
            return response

        # empty links list
        links = []
        ret = send_post(links)
        assert ret.status_code == 200
        self.assertTrue(ret.text == '{"status":"ok"}')

        # invalid links
        links = ['linkkkkk', '****', '34', '^^', '-1']
        ret = send_post(links)
        assert ret.status_code == 200
        self.assertTrue(ret.text == '{"status":"Nok"}')

        # invalid data types
        links = [-7, -8, 10]
        ret = send_post(links)
        assert ret.status_code == 200
        self.assertTrue(ret.text == '{"status":"Nok"}')

        # correct data
        links = ["foobar.com/bass?a=1",
                      "https://ya.ru",
                      "https://ya.ru?q=123",
                      "funbox.ru",
                      "https://stackoverflow.com/questions/11828270/how-to-exit-the-vim-editor"]
        ret = send_post(links)
        assert ret.status_code == 200
        self.assertTrue(ret.text == '{"status":"ok"}')

    def test_visited_domains(self):
        # get all domains - maximum time range (0, curr_time)
        curr_time = int(time.time())
        response = client.get("/visited_domains?from=0&to=%s" % curr_time)
        assert response.status_code == 200
        self.assertTrue('domains' in response.json() and len(response.json()['domains']) > 0)
        #assert response.json() == '{"domains":["stackoverflow.com","hh.ru","habr.com","ya.ru"],"status":"ok"}'

        #without from
        response = client.get("/visited_domains?to=123456")
        assert response.status_code == 200
        self.assertFalse('domains' in response.json() and len(response.json()['domains']) > 0)

        #without to
        response = client.get("/visited_domains?from=0")
        assert response.status_code == 200
        self.assertFalse('domains' in response.json() and len(response.json()['domains']) > 0)

        #without params
        response = client.get("/visited_domains")
        assert response.status_code == 200
        self.assertFalse('domains' in response.json() and len(response.json()['domains']) > 0)

