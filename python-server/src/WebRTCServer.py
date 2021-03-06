import uuid
import json
import asyncio
import platform
import cv2
import fractions
import time

from aiohttp import web
from aiohttp_index import IndexMiddleware
from threading import Thread

from aiortc.codecs import get_capabilities
from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack
from aiortc.contrib.media import MediaPlayer

from av import VideoFrame
from queue import Queue

from src.utils.Logger import default_logger as logger


class WebRTCServer:

    class CameraPreview(VideoStreamTrack):

        kind = 'video'

        def __init__(self, max_size=3):
            super().__init__()
            self.__frame_queue = Queue()
            self.__last_frame = None
            self.__max_size = max_size
            self.__start = -1

        def add_frame(self, frame):
            if self.__frame_queue.qsize() > self.__max_size:
                self.__frame_queue.get()
            self.__frame_queue.put(frame)

        async def recv(self):
            av_frame = None
            try:
                super_frame = await super().recv() # TODO
                if self.__frame_queue.qsize() == 0:
                    if self.__last_frame is None:
                        av_frame = super_frame
                    else:
                        av_frame = self.__last_frame
                else:
                    frame = self.__frame_queue.get()

                    if self.__start == -1:
                        self.__start = time.time()

                    av_frame = VideoFrame.from_ndarray(frame, format="bgr24")
                    av_frame.pts = super_frame.pts#time.time() - self.__start
                    av_frame.time_base = super_frame.time_base#fractions.Fraction(1, 1000)
            except Exception as e:
                print(e)

            self.__last_frame = av_frame
            return av_frame

    def __init__(self, port=80, ip='localhost', resolution='640x480'):
        self.on_new_message_listener = None
        self.__is_running = False
        self.__camera_preview = WebRTCServer.CameraPreview()
        self.__pcs = set()
        self.__channels = set()
        self.__request_id_channels = {}
        self.__port = port
        self.__ip = ip
        self.__resolution = resolution
        self.__app = web.Application(middlewares=[IndexMiddleware()])
        self.__app.router.add_post('/offer', self.offer)
        self.__app.router.add_static('/', path=str('../public/'))
        self.__loop = None
        self.__site = None

    def add_frame_to_queue(self, frame):
        self.__camera_preview.add_frame(frame)

    def is_running(self):
        return self.__is_running

    def start(self):
        async def runner():
            app_runner = web.AppRunner(self.__app)
            await app_runner.setup()
            self.__site = web.TCPSite(app_runner, self.__ip, self.__port)
            await self.__site.start()

        def thread():
            self.__loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.__loop)
            self.__loop.run_until_complete(runner())
            self.__is_running = True
            self.__loop.run_forever()

        thread = Thread(target=thread, daemon=True)
        thread.start()
        logger.info('WebRTC server started %s:%d' % (self.__ip, self.__port))

    def stop(self):
        logger.debug('Closing WebRTC server...')
        if self.__site is not None and self.__loop is not None:
            async def stop():
                future = asyncio.run_coroutine_threadsafe(self.on_shutdown(), self.__loop)
                future.result()
                self.__loop.stop()
                self.__site = None
                self.__loop = None
                self.__is_running = False

            loop = asyncio.new_event_loop()
            loop.run_until_complete(stop())

    def send_to_all(self, message):
        if not self.__is_running:
            return

        message = {
            'payload': message
        }
        message = json.dumps(message)

        async def task():
            for channel in self.__channels:
                if channel.readyState == 'open':
                    channel.send(message)
                    logger.trace('Message sent to channel %s: %s' % (channel.id, message))
        asyncio.run_coroutine_threadsafe(task(), self.__loop)

    def send_to_request_id(self, message, request_id=None):
        if not self.__is_running or request_id is None:
            return

        message = {
            'request_id': request_id,
            'payload': message
        }
        message = json.dumps(message)

        async def task():
            if request_id in self.__request_id_channels:
                channel = self.__request_id_channels[request_id]
                if channel.readyState == 'open':
                    channel.send(message)
                    logger.trace('Message sent to channel %s: %s' % (channel.id, message))
                    self.__request_id_channels.pop(request_id)
        asyncio.run_coroutine_threadsafe(task(), self.__loop)

    async def offer(self, request):
        params = await request.json()
        offer = RTCSessionDescription(
            sdp=params['sdp'],
            type=params['type'])

        pc = RTCPeerConnection()
        pc_id = 'PeerConnection(%s)' % uuid.uuid4()
        self.__pcs.add(pc)
        logger.debug('%s: created for %s' % (pc_id, request.remote))

        @pc.on('datachannel')
        def on_datachannel(channel):
            logger.debug('%s: Data channel established (%s)' % (pc_id, channel.id))
            self.__channels.add(channel)
            @channel.on('message')
            def on_message(message):
                logger.trace('Message received from %s: %s' % (pc_id, message))
                try:
                    parsed_message = json.loads(message)
                    request_id = parsed_message['request_id'] if ('request_id' in parsed_message.keys()) else None
                    if request_id is not None:
                        self.__request_id_channels[request_id] = channel

                    if parsed_message and self.on_new_message_listener is not None:
                        self.on_new_message_listener(parsed_message, request_id)
                except ValueError:
                    logger.warn('Invalid message received from %s: %s' % (pc_id, message))

        @pc.on('iceconnectionstatechange')
        async def on_iceconnectionstatechange():
            logger.debug('%s: ICE connection state is %s' % (pc_id, pc.iceConnectionState))
            if pc.iceConnectionState == 'failed':
                await pc.close()
                logger.debug('%s: ICE connection discarded with state %s' % (pc_id, pc.iceConnectionState))
                self.__pcs.discard(pc)

        # player = MediaPlayer('src/test_video.mp4', options={'framerate': '30', 'video_size': '1920x1080'})
        await pc.setRemoteDescription(offer)
        for t in pc.getTransceivers():
            # pc.addTrack(player.video)
            pc.addTrack(self.__camera_preview)

        answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)

        return web.Response(
            content_type='application/json',
            text=json.dumps({
                'sdp': pc.localDescription.sdp,
                'type': pc.localDescription.type
            }))

    async def on_shutdown(self):
        # close peer connections
        coros = [pc.close() for pc in self.__pcs]
        await asyncio.gather(*coros)
        self.__pcs.clear()
        logger.info('WebRTC server closed')
