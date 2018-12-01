import json
import os
import requests
import time

config = json.load(open('../config.json'))
redis_config = json.load(open('config.json'))

base_url = 'http://127.0.0.1:5000/'

def redis_get(url):
    r = requests.get(base_url + url.lstrip('/'),
                     auth=('daniel', redis_config['redis_auth_key']))
    return r

def redis_put(url, json=None):
    r = requests.put(base_url + url.lstrip('/'),
                     auth=('daniel', redis_config['redis_auth_key']),
                     json=json)
    return r

# Need to make true case check so I don't have
# to manually inspect output each time.
# pop (empty[*], items[*])
# push (empty[*], items[*])
# list (empty[*], items[*])
# size (empty[*], items[*])
# len (empty[*], items[*])
# ping (empty[*], items[*])
# requeue (empty[*], items[*])
# complete (empty[*], items[*])
# timeout (no items running[*], items running[*])
def main():
    print("empty timeout test: sleeping for {} seconds".format(redis_config['job_timeout'] + 30))
    time.sleep(redis_config['job_timeout'] + 30)

    print("push test")
    for i in range(3):
        if redis_put('queue/test/push', {'payload': i}).status_code != 200:
            print("push error at {}".format(i))

    print("list test")
    r = redis_get('queue/test/list')
    if r.status_code != 200:
        print("list test error")
    print(r.json())

    print("pop test")
    r = redis_get('/queue/test/pop')
    if r.status_code != 200:
        print("pop error")
    print(r.json())
    complete_test = r.json()['id']

    print("list test 2")
    r = redis_get('queue/test/list')
    if r.status_code != 200:
        print("list test 2 error")
    print(r.json())

    print("size test")
    r = redis_get('queue/test/size')
    if r.status_code != 200:
        print("size test error")
    print(r.json())

    print("len test")
    r = redis_get('queue/test/len')
    if r.status_code != 200:
        print("len test error")
    print(r.json())

    print("empty pop test")
    status = 200
    while status != 404:
        time.sleep(1)
        r = redis_get('/queue/test/pop')
        status = r.status_code
        if status not in [200, 404]:
            print("pop error at {}".format(i))

    print("empty list test")
    r = redis_get('queue/test/list')
    if r.status_code not in [200, 404]:
        print("empty list test failed")
    print(r.json())

    print("empty size test")
    r = redis_get('queue/test/size')
    if r.status_code not in [200]:
        print("empty size test failed")
    print(r.json())

    print("empty len test")
    r = redis_get('queue/test/len')
    if r.status_code != 200:
        print("empty len test error")
    print(r.json())

    print("complete test")
    r = redis_put('job/{}/complete'.format(complete_test))
    if r.status_code != 200:
        print("complete error")
    print(r.text)

    r = redis_get('queue/test/len')
    if r.status_code != 200:
        print("len error")
    print(r.json())

    r = redis_get('queue/test/size')
    if r.status_code != 200:
        print("len error")
    print(r.json())

    print("timeout test: sleeping for {} seconds".format(redis_config['job_timeout'] + 30))
    time.sleep(redis_config['job_timeout'] + 30)
    r = redis_get('queue/test/len')
    if r.status_code != 200:
        print("len error")
    print(r.json())

    r = redis_get('queue/test/size')
    if r.status_code != 200:
        print("len error")
    print(r.json())

    # ping, make sure it wasn't placed back on.
    # then empty with complete
    print("empty ping test")
    r = redis_put('job/1/ping')
    if r.status_code != 404:
        print("ping error")
    print(r.text)
    print("ping test: sleeping for {} seconds".format(redis_config['job_timeout']))

    print("list test")
    r = redis_get('queue/test/list')
    if r.status_code != 200:
        print("list test error")
    print(r.json())

    print("emptying queue")
    status = 200
    while status != 404:
        r = redis_get('/queue/test/pop')
        status = r.status_code
        if status not in [200, 404]:
            print("pop error at {}".format(i))
        else:
            if status == 200:
                redis_put('/job/{}/complete'.format(r.json()['id']))

    print("empty complete test")
    r = redis_get('queue/test/size')
    if r.status_code != 200:
        print("len error")
    print(r.json())

    r = redis_put('job/0/complete')
    if r.status_code != 404:
        print("empty complete error")
    print(r.text)

    print("empty ping test")
    r = redis_put('job/0/ping')
    if r.status_code != 404:
        print("empty ping error")
    print(r.text)

if __name__ == "__main__":
    main()