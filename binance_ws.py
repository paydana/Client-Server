'''
    Asynchronus Binance Websocket Server
    Author: Mo Sharieff
    Date: 12-27-2018

    This script will act as a client and a server in which it streams
    raw websocket data from Binance, formats the data, and outputs
    it as its own websocket server.
'''

import websockets
import asyncio
import json
import requests
import logging
import time
import datetime


#logging.basicConfig(level=print)

# Timer functions and variables

curr_time = lambda: datetime.datetime.fromtimestamp(int(time.time())).strftime('%m-%d-%Y %H:%M:%S')
dt = lambda x, y, n: (y - x) / n

tPing = tPong = tStart = tEnd = time.time()

# Parameters

ohlc = ['1m','3m','5m','15m','30m','1h','2h','4h','6h','8h','12h','1d','3d','1w','1M']
depth = [5,10,20]
ping = 3
hours = 23

# Binance server url

ws_url = 'wss://stream.binance.com:9443'
rs_url = 'https://www.binance.com/api/v1/'

# Function which builds your sending url

url_build = lambda y, tag: '{}/ws/{}'.format(ws_url, y.lower()) if tag == 'single' else '{}/stream?streams={}'.format(ws_url, '/'.join(y))

# Functions for all websocket streams

sstream = {'aggTrade':lambda symbol: '{}@aggTrade'.format(symbol.lower()),
           'trade':lambda symbol: '{}@trade'.format(symbol.lower()),
           'klines':lambda symbol, interval: '{}@kline_{}'.format(symbol.lower(), interval),
           'miniTick':lambda symbol, all_t: '{}@miniTicker'.format(symbol.lower()) if all_t == False else '!miniTicker@arr',
           'ticker':lambda symbol, all_t: '{}@ticker'.format(symbol.lower()) if all_t == False else '!ticker@arr',
           'book':lambda symbol, level: '{}@depth'.format(symbol.lower()) if level == 'update' else '{}@depth{}'.format(symbol.lower(), level)}

# Function to import REST data

def get_data(datatype):
    if datatype == 'ticks':
        url = rs_url + 'exchangeInfo'
        r = requests.get(url)
        if r.status_code == 200:
            return [i['symbol'] for i in r.json()['symbols']]

# Function which builds your final websocket url

def build_msg():
    ticks = get_data('ticks')
    ticks = ticks

    klines = [sstream['klines'](i, '1m') for i in ticks]
    book = [sstream['book'](i, 20) for i in ticks]
    trade = [sstream['trade'](i) for i in ticks]

    msg = book
    
    return url_build(msg, 'multi')

# Parses data and sends it to appropriate channel (* Link Server Script here)
# -----------------------------------------------------------------------------------------
async def parse_data(data):
    data = json.loads(data)
    print(' Time: {} | {}\n'.format(curr_time(), data))

    # Link To Server


# -----------------------------------------------------------------------------------------

# Main websocket client function (recieves exchange data)

async def exchange_client(loop, timest):

    tStart, tEnd, tPing, tPong = timest

    send_url = build_msg()

    txx = time.time()
    tyy = txx
    cy = 0
    
    async with websockets.connect(send_url) as ws:
        while True:
            msg = await ws.recv()
            await parse_data(msg)

            # Time check to send response pong and refresh socket if shut down

            if dt(tPing, tPong, 60) >= ping + 0.2:
                ut = await ws.pong()
                print(' Time: {} | Pong Sent: {}'.format(curr_time(), ut))
                tPing = tPong

            if dt(tStart, tEnd, pow(60,2)*24) >= hours:
                print(' Time: {} | Time to refresh socket...........'.format(curr_time()))
                tStart = tEnd
                break

            tPong = time.time()
            tEnd = time.time()
  
# Main loop function

def run_socket():
    while True:
        tPing = time.time()
        tPong = tPing

        tStart = tPing
        tEnd = tPing

        print(' Time: {} | Socket connecting..........'.format(curr_time()))

        loop = asyncio.get_event_loop()
        loop.run_until_complete(exchange_client(loop, (tStart, tEnd, tPing, tPong)))

        print(' Time: {} | Socket is rebooting..............'.format(curr_time()))
        time.sleep(4)
        run_socket()

# Runs entire program

if __name__ == '__main__':
    run_socket()


