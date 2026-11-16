#!/usr/bin/env python3
import json
import sys
import time
import urllib.error
import urllib.request


class T3Client:
    def __init__(self, config):
        self.url = config['url']
        self.token = config['token']
        self.session = None
        self.sequence = 0
        self.request('initialize', {
            'protocolVersion': '2025-06-18',
            'capabilities': {},
            'clientInfo': {'name': 'sync-personal', 'version': '1'},
        })
        self.request('notifications/initialized')

    def request(self, method, params=None):
        headers = {
            'Authorization': 'Bearer ' + self.token,
            'Content-Type': 'application/json',
            'Accept': 'application/json, text/event-stream',
            'MCP-Protocol-Version': '2025-06-18',
        }
        if self.session:
            headers['MCP-Session-Id'] = self.session
        payload = {'jsonrpc': '2.0', 'method': method}
        if params is not None:
            payload['params'] = params
        if not method.startswith('notifications/'):
            self.sequence += 1
            payload['id'] = self.sequence
        req = urllib.request.Request(self.url, json.dumps(payload).encode(), headers)
        with urllib.request.urlopen(req, timeout=15) as response:
            self.session = response.headers.get('MCP-Session-Id', self.session)
            raw = response.read().decode()
            content_type = response.headers.get('Content-Type', '')
        if 'id' not in payload:
            return None
        if 'text/event-stream' in content_type:
            messages = [json.loads(line[5:].strip()) for line in raw.splitlines()
                        if line.startswith('data:')]
            result = next(m for m in messages if m.get('id') == payload['id'])
        else:
            result = json.loads(raw)
        if 'error' in result:
            raise RuntimeError(str(result['error']))
        return result['result']

    def tool(self, name, arguments):
        result = self.request('tools/call', {'name': name, 'arguments': arguments})
        if result.get('isError'):
            raise RuntimeError(str(result.get('content', name + ' failed')))
        if 'structuredContent' in result:
            return result['structuredContent']
        text = '\n'.join(part['text'] for part in result.get('content', [])
                         if part.get('type') == 'text')
        return json.loads(text)

    def pages(self, name, arguments, key):
        cursor = 0
        while True:
            page = self.tool(name, {**arguments, 'cursor': cursor, 'limit': 100})
            yield from page[key]
            cursor = page.get('nextCursor')
            if cursor is None:
                break

    def blockers(self):
        # Thread listing defaults to the caller's project. Walk every project,
        # including child agents, so work elsewhere in Personal also blocks shutdown.
        projects = list(self.pages('t3_project_list', {}, 'projects'))
        active = ['running', 'starting', 'preparing', 'queued', 'waiting']
        threads = []
        for project in projects:
            threads.extend(self.pages('t3_thread_list', {
                'projectId': project['id'], 'statuses': active, 'includeSubagents': True,
            }, 'threads'))
        return threads


def main():
    with open(sys.argv[1]) as source:
        config = json.load(source)
    client = T3Client(config)
    identity = client.tool('t3_environment_read', {})
    if identity['environmentId'] != '7f48cfa2-f9e9-4493-be0b-f3478e469f31':
        raise SystemExit('Refusing to sync: MCP endpoint is not Personal.')
    started = time.monotonic()
    quiet = 0
    previous = None
    last_log = -30
    while time.monotonic() - started < 3600:
        try:
            threads = client.blockers()
        except (urllib.error.URLError, TimeoutError, ValueError, RuntimeError) as error:
            # Never mistake an unavailable server or denied tool call for idle.
            print('T3 status check failed: ' + str(error), flush=True)
            quiet = 0
            time.sleep(1)
            continue
        quiet = 0 if threads else quiet + 1
        if quiet >= 4:
            print('T3 reports no active threads; idle check complete.', flush=True)
            return
        elapsed = int(time.monotonic() - started)
        signature = tuple(sorted((t['threadId'], t.get('activityRunStatus') or t.get('status'),
                                  t.get('title', '')) for t in threads))
        if signature != previous or elapsed - last_log >= 30:
            detail = '; '.join('%s %s [%s]' % (tid, title, status)
                               for tid, status, title in signature) or 'confirming idle'
            print('%ds waiting: %s' % (elapsed, detail), flush=True)
            previous, last_log = signature, elapsed
        time.sleep(1)
    raise SystemExit('T3 did not become idle within one hour. Personal was not stopped.')


if __name__ == '__main__':
    main()
