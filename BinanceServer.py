import websockets
import asyncio
import json
import requests
import time
import datetime

loop = asyncio.get_event_loop()

# Timer functions and variables

tPing = tPong = tStart = tEnd = time.time()

curr_time = lambda: datetime.datetime.fromtimestamp(int(time.time())).strftime('%m-%d-%Y %H:%M:%S')
dt = lambda x, y, n: (y - x) / n
du = lambda x, y, n: '{0:.3f}'.format((y - x) / n)

ohlc = ['1m','3m','5m','15m','30m','1h','2h','4h','6h','8h','12h','1d','3d','1w','1M']
depth = [5,10,20]
ping = 3
hours = 23

ws_url = 'wss://stream.binance.com:9443'
rs_url = 'https://www.binance.com/api/v1/'

url_build = lambda y, tag: '{}/ws/{}'.format(ws_url, y[0].lower()) if tag == 'single' else '{}/stream?streams={}'.format(ws_url, '/'.join(y))

sstream = {'aggTrade':lambda symbol: '{}@aggTrade'.format(symbol.lower()),
           'trade':lambda symbol: '{}@trade'.format(symbol.lower()),
           'klines':lambda symbol, interval: '{}@kline_{}'.format(symbol.lower(), interval),
           'miniTick':lambda symbol, all_t: '{}@miniTicker'.format(symbol.lower()) if all_t == False else '!miniTicker@arr',
           'ticker':lambda symbol, all_t: '{}@ticker'.format(symbol.lower()) if all_t == False else '!ticker@arr',
           'book':lambda symbol, level: '{}@depth'.format(symbol.lower()) if level == 'update' else '{}@depth{}'.format(symbol.lower(), level)}

def get_data(datatype):
    if datatype == 'ticks':
        url = rs_url + 'exchangeInfo'
        r = requests.get(url)
        if r.status_code == 200:
            return [i['symbol'] for i in r.json()['symbols']]


def stream(tag, ticks):
    if tag == 'klines':
        return [sstream['klines'](i, ticks[1]) for i in ticks[0]]
    elif tag == 'book':
        return [sstream['book'](i, ticks[1]) for i in ticks[0]]
    elif tag == 'trade':
        return [sstream['trade'](i) for i in ticks[0]]
    elif tag == 'ticker':
        return sstream['ticker'](None, True) 
    else:
        return [sstream['aggTrade'](i) for i in ticks[0]]


def build_msg(tagger):
    ticks = get_data('ticks')
    msg = stream(tagger[0],[ticks,tagger[1]])
    return url_build(msg, 'multi') if tagger[0] != 'ticker' else url_build(msg, 'single')


async def parse_data(conn, data, tagger, dx):
    data = json.loads(data)
    #msg = ' Timestamp: {} | Tag: {} | Run(mins): {} | {}\n'.format(curr_time(), tagger[0], dx, data)
    #print('sending')
    message = {'Tag':tagger[0],'Data':data}
    await conn.send(json.dumps(message))

async def exchange_client(conn, timest, tagger):

    a = b = time.time()

    tPing, tPong = timest

    send_url = build_msg(tagger)

    async with websockets.connect(send_url) as ws:
        while True:
            msg = await ws.recv()
            dx = du(a, b, 60)
            await parse_data(conn, msg, tagger, dx)

            if dt(tPing, tPong, 60) >= ping + 0.2:
                ut = await ws.pong()
                await ws.send(json.dumps({'E':int(time.time()),'e':'pong'}))
                print(' Time: {} | Pong Sent: {}'.format(curr_time(), ut))
                tPing = time.time()

            b = time.time()
            tPong = time.time()


async def start(websocket, path):

    tasks = [loop.create_task(exchange_client(websocket,count,['klines','1m'])),
             loop.create_task(exchange_client(websocket,count,['book',5])),
             loop.create_task(exchange_client(websocket,count,['trade',None])),
             loop.create_task(exchange_client(websocket,count,['ticker',[True, True]])),
             loop.create_task(exchange_client(websocket,count,['aggTrade',None]))]             

    await asyncio.wait(tasks)


if __name__ == '__main__':

    start_server = websockets.serve(start, '127.0.0.1', 5678)
    
    while True:
        count = [tPing, tPong]
                           
        loop.run_until_complete(start_server)
        loop.run_forever()

        if dt(tStart, tEnd, pow(60,2)*24) >= hours:
            print(' Time: {} | Time to refresh socket...........'.format(curr_time()))
            time.sleep(5)

            for task in asyncio.Task.all_tasks():
                task.cancel()

            loop = asyncio.get_event_loop()
            tStart = tEnd = tPing = tPong = time.time()
            tagger = [tPing, tPong]
            
        tEnd = time.time()
  

