import requests
import json

config = json.load(open('../config.json'))
redis_config = json.load(open('config.json'))

def redis_get(url):
    r = requests.get(os.path.join('http://127.0.0.1:5000', url),
                     auth=('daniel', redis_config['redis_auth_key']))
    return r

def redis_put(url, json):
    r = requests.put(os.path.join('http://127.0.0.1:5000', url),
                     auth=('daniel', redis_config['redis_auth_key']),
                     json=json)
    return r

# pop (empty[*], items[*])
# push (empty[*], items[*])
# list (empty[*], items[*])
# size (empty[], items[])
# len (empty[], items[])
# ping (empty[], items[])
# requeue (empty[], items[])
# complete (empty[], items[])
# timeout (no items running[], items running[])
def main():
    print("push test")
    for i in range(3):
        if redis_put('queue/test/push', {'payload': i}).status_code != 200:
            print("push error at {}".format(i))

    print("list test")
    r = redis_get('queue/test/list')
    if r.status_code != 200:
        print("list test error")
    print(r.text)

    print("pop test")
    r = redis_get('/queue/test/pop')
    if r.status_code != 200:
        print("pop error")
    print(r.text)

    print("list test 2")
    r = redis_get('queue/test/list')
    if r.status_code != 200:
        print("list test 2 error")
    print(r.text)

    print("empty pop test")
    for i in range(3):
        if redis_get('/queue/test/pop').status_code not in [200, 404]:
            print("pop error at {}".format(i))

    print("empty list test")
    r = redis_get('queue/test/list')
    if r.status_code not in [200, 404]:
        print("empty list test")
    print(r.text)

if __name__ == "__main__":
    main()