"""Actual HTTP integration test: two authenticated services, conditional PUT, re-read."""
import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from agentic_portfolio.http_integration import Endpoint, synchronize

class TestLiveHttpIntegration(unittest.TestCase):
    def test_observe_write_and_reverify_over_http(self):
        truth={'sku':'SKU-A','title':'Device','description':'Device description',
               'price':'100.00','currency':'USD','availability':'in stock',
               'image_url':'/assets/a.jpg'}
        state={'channel':[dict(truth,price='119.00')], 'version':1,
               'puts':0}
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):
                return
            def auth(self):
                return self.headers.get('Authorization') == 'Bearer local-test-token'
            def respond(self,status,body,etag=None):
                raw=json.dumps(body).encode()
                self.send_response(status)
                self.send_header('Content-Type','application/json')
                self.send_header('Content-Length',str(len(raw)))
                if etag:
                    self.send_header('ETag',etag)
                self.end_headers()
                self.wfile.write(raw)
            def do_GET(self):
                if not self.auth():
                    return self.respond(401,{'error':'unauthorized'})
                if self.path=='/catalog':
                    return self.respond(200,[truth])
                if self.path=='/channel':
                    return self.respond(200,state['channel'],str(state['version']))
                self.respond(404,{'error':'not found'})
            def do_PUT(self):
                if not self.auth():
                    return self.respond(401,{'error':'unauthorized'})
                if self.path!='/channel':
                    return self.respond(404,{'error':'not found'})
                if self.headers.get('If-Match') != str(state['version']):
                    return self.respond(412,{'error':'stale revision'})
                length=int(self.headers.get('Content-Length',0))
                update=json.loads(self.rfile.read(length))
                if not isinstance(update.get('products'),list):
                    return self.respond(400,{'error':'invalid payload'})
                state['channel']=update['products']
                state['version']+=1
                state['puts']+=1
                self.respond(200,{'updated':True},str(state['version']))

        server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True)
        thread.start()
        try:
            base='http://127.0.0.1:'+str(server.server_port)
            catalog=Endpoint(base+'/catalog','local-test-token')
            channel=Endpoint(base+'/channel','local-test-token')
            observed=synchronize(catalog,channel,writeback=False)
            self.assertEqual(observed['before']['status'],'REVIEW_REQUIRED')
            self.assertFalse(observed['writeback_performed'])
            self.assertEqual(state['puts'],0)
            result=synchronize(catalog,channel,writeback=True)
            self.assertEqual(result['before']['findings'][0]['field'],'price')
            self.assertTrue(result['writeback_performed'])
            self.assertTrue(result['verified'])
            self.assertEqual(result['after']['findings'],[])
            self.assertEqual(state['puts'],1)
            self.assertEqual(state['channel'][0]['price'],'100.00')
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)

if __name__=='__main__':
    unittest.main()
