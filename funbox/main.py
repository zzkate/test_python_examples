from typing import List
from fastapi import FastAPI, Query
from pydantic import BaseModel
import time
from urllib.parse import urlparse
import aioredis
import redis
import re

app = FastAPI()

class Data(BaseModel):
    links: List[str]

redis = None

def get_redis():
    global redis
    return redis

@app.on_event("startup")
async def startup_event():
    global redis
    redis = await aioredis.create_redis_pool('redis://localhost')
    db = await redis.select(0)

@app.on_event("shutdown")
async def release_lock():
	global redis
	redis.close()

class Domain:
    def __init__(self, domain, visited=0):
        self._domain = domain
        self._max_visited = 0
        self._min_visited = 0
        self._set_is_valid()
        self.visit(visited)

    def is_valid(self):
        return self._is_valid

    def _set_is_valid(self):
        if type(self._domain) != str:
            self._is_valid = False
            print('\ninvalid type=%s of domain name=%s\n' % (type(self._domain), self._domain))
            self._domain = ''
            return

        # match 1 character domain name or 2+ domain name
        chars_or_digit = '[A-Za-z0-9]'
        chars_only = '[A-Za-z]'
        pattern = re.compile('^(%s\.|%s%s{0,61}%s\.){1,3}%s{2,6}$' % (chars_or_digit, chars_or_digit, chars_or_digit, chars_or_digit, chars_only))
        self._is_valid = (bool)(pattern.match(self._domain))

    def visit(self, visited):
        # check initial values
        if self._max_visited == 0 or self._min_visited == 0:
            self._max_visited = visited
            self._min_visited = visited
            return

        if visited > self._max_visited:
            self._max_visited = visited

        if visited < self._min_visited:
            self._min_visited = visited

    async def parse_data_from_redis(self):
        if not self.is_valid():
            return
        val = await redis.hgetall(self._domain)
        if val.__len__() > 0:
            if b'max_visited' in val:
                self._max_visited = (int)(val[b'max_visited'])
            if b'min_visited' in val:
                self._min_visited = (int)(val[b'min_visited'])

    async def set_data_to_redis(self):
        if not self.is_valid():
            return
        domain = {'domain': self._domain, 'min_visited': self._min_visited, 'max_visited': self._max_visited}
        await redis.hmset_dict(self._domain, domain)
        print('add %s to redis' % domain)

    def filter(self, from_ts, to_ts):
        # swap from, to if needed
        if from_ts > to_ts:
            tmp = from_ts
            from_ts = to_ts
            to_ts = tmp

        # if visited only once _max_visited == _min_visited
        if (int)(self._max_visited) == (int)(self._min_visited):
            return (int(from_ts) <= int(self._max_visited) and int(to_ts) >= int(self._max_visited))

        return (int(self._max_visited) <= int(to_ts) and\
                int(from_ts) <= int(self._min_visited))

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self._domain == other._domain and\
                   self._max_visited == other._max_visited and\
                   self._min_visited == other._min_visited and\
                   self.__dict__ == other.__dict__
        else:
            return False

async def sync_with_redis(domains):
    '''
    :input: list of domains
    need save domains with updating max or min visited timestamp in redis if domain exists soon
    :return: None
    '''

    result = True
    # remove duplications
    domains = list(set(domains))

    for domain_name in domains:
        domain = Domain(domain_name)
        if domain.is_valid() == False:
            result = False
            continue
        await domain.parse_data_from_redis()
        domain.visit((int)(time.time()))
        await domain.set_data_to_redis()
    return result

async def get_all_known_domains():
    all_known_domains = []
    cur = b'0'  # set initial cursor to 0
    while cur:
        cur, all_known_domains = await redis.scan(cur, match='*') # key:*
        print("All known domains:", all_known_domains)
    return all_known_domains

async def query_domains_from_redis(from_ts:int, to_ts:int):
    '''
    :input: timestamps from to
    :return: list of uniq visited domains in [from, to] saved in redis
    '''

    result_domains = []
    if from_ts == None or \
       to_ts == None or \
       not isinstance(from_ts, (int)) or\
       not isinstance(to_ts, (int)) or \
       from_ts < 0 or\
       to_ts < 0 or\
       from_ts == to_ts:
       return []

    all_known_domains = await get_all_known_domains()

    for domain_name in all_known_domains:
        domain = Domain(domain_name.decode("utf-8"))
        await domain.parse_data_from_redis()

        if domain.filter(from_ts, to_ts):
            result_domains.append(domain_name)

    return result_domains

@app.post('/visited_links')
async def send_post(data: Data):
    '''
    :input: links list
    save a list uniq visited domains to redis with current timestamp
    :return: status ok or Nok
    '''

    #print(data)
    result = True
    domains = []
    for link in data.links:
        try:
            o = urlparse(link)
            domain_name = o.netloc
            if not domain_name: # and '.' in str(o.path):
                domain_name += o.path.split('/')[0]
            domains.append(domain_name)
        except:
            result = False
            print('\nproblems with link=%s paring\n' % link)
    result = result and await sync_with_redis(domains)
    if result:
        return {"status": "ok"}
    else:
        return {"status": "Nok"}

@app.get("/visited_domains")
async def visited_domains(q: str = Query(None, alias="from"), to: str = ''):
    '''
    :input: timestamps from, to
    :return: a list uniq visited domains in time interval [from, to]
    '''
    from_ts = 0
    if q:
        from_ts = q
        try:
            result_domains = await query_domains_from_redis(int(from_ts), int(to))
            return {
                "domains": result_domains,
                "status": "ok"
            }
        except:
            print('\nproblem with getting domains from redis\n')
            return {"status": "Nok"}
    else:
        return {"status": "Nok"}