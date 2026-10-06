import json
import urllib.error
import urllib.request

base = 'http://127.0.0.1:59374'
state = json.load(urllib.request.urlopen(base + '/api/state'))
before = json.load(urllib.request.urlopen(base + '/api/journal'))['summary']
values = dict(state['values'])
values['pitch'] = -1
request = urllib.request.Request(
    base + '/api/apply', method='POST',
    data=json.dumps({'values': values, 'selection': state.get('selection', {'tube':'custom','screw':'custom','material':'unspecified'})}).encode(),
    headers={'Content-Type': 'application/json'},
)
try:
    urllib.request.urlopen(request)
    raise AssertionError('Invalid geometry accepted')
except urllib.error.HTTPError as error:
    assert error.code == 422, error.code
    assert not json.load(error)['ok']
after = json.load(urllib.request.urlopen(base + '/api/journal'))['summary']
assert before == after, (before, after)
print('Invalid apply rejected; journal unchanged')
