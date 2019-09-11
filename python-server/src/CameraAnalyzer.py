import cv2
import time
import numpy as np
from copy import deepcopy
from threading import Thread, Lock
from src.Logger import Logger
from src.FPS import FPS


class CameraAnalyzer:

    def __init__(self, on_new_frame_target_fps=0, logger=None):
        self.on_new_frame_listener = None
        self.__logger = logger
        self.__stats = {}
        self.__lock = Lock()

        # Thread
        self.__terminate = False
        self.__stopped = True
        self.__analyzer = Thread(target=self.read_from_camera)
        self.__analyzer.start()

        # FPS control
        self.__fps = FPS()
        self.__target_fps = -1
        self.__next_frame_ms = -1
        self.__on_new_frame_next_ms = -1
        self.__on_new_frame_target_fps = on_new_frame_target_fps

    def start(self):
        if not self.__stopped:
            self.__log('Camera service is already running', Logger.LogLevel.INFO)
        else:
            self.__log('Camera service started', Logger.LogLevel.INFO)
            self.__stopped = False

    def stop(self):
        if self.__stopped:
            self.__log('Camera service is already stopped', Logger.LogLevel.INFO)
        else:
            self.__log('Camera service stopped', Logger.LogLevel.INFO)
            self.__stopped = True

    def close(self):
        self.__log('Closing camera service...', Logger.LogLevel.DEBUG)
        self.__terminate = True
        self.__analyzer.join()
        self.__log('Camera service closed', Logger.LogLevel.DEBUG)

    def get_available_cameras(self):
        index = 0
        arr = []
        while True:
            cap = cv2.VideoCapture(index)
            if not cap.read()[0]:
                break
            else:
                arr.append(index)
            cap.release()
            index += 1
        return arr

    def read_from_camera(self):
        cap = cv2.VideoCapture(0)
        self.__target_fps = cap.get(cv2.CAP_PROP_FPS)

        while not self.__terminate:
            if not self.__stopped:

                # Read frame
                t0 = time.time()
                ret, frame = cap.read()

                if ret == False:
                    raise Exception('TODO: No more frames !')

                # Process frame
                t1 = time.time()
                self.__process_frame(frame)

                # Wait time to sync frame
                t2 = time.time()
                self.__sync_frame(1. / self.__target_fps)

                # Frame Listenner
                t3 = time.time()
                self.__on_new_frame_skip(ret, frame)

                # Stats
                t4 = time.time()
                self.__set_stats(t1 - t0, t2 - t1, t3 - t2, t4 - t3)

                self.__fps.update()
            else:
                time.sleep(.05)

    def __set_stats(self, t_read, t_process, t_sync, t_listener):
        """ Thread safe """
        with self.__lock:
            self.__stats['t_read']     = t_read
            self.__stats['t_process']  = t_process
            self.__stats['t_sync']     = t_sync
            self.__stats['t_listener'] = t_listener
            self.__stats['fps']        = self.__fps.average
            self.__stats['target_fps'] = self.__target_fps

    def get_stats(self):
        """ Thread safe """
        with self.__lock:
            return deepcopy(self.__stats)

    def __on_new_frame_skip(self, ret, frame):
        """
        if __on_new_frame_target_fps <= 0, then just call on_new_frame_listener with every frame
        otherwise, call on_new_frame_listener according to the target fps in __on_new_frame_target_fps
        as close as possible
        """
        if self.on_new_frame_listener is None:
            return

        self.__on_new_frame_target_fps = 10
        if self.__on_new_frame_target_fps <= 0:
            self.on_new_frame_listener(ret, frame)
            return

        if self.__on_new_frame_next_ms < 0:
            self.__on_new_frame_next_ms = time.time()
            self.on_new_frame_listener(ret, frame)
            return

        if (self.__on_new_frame_next_ms - time.time()) < 0:
            self.__on_new_frame_next_ms += 1. / self.__on_new_frame_target_fps
            self.on_new_frame_listener(ret, frame)

    def __sync_frame(self, target_ms):
        if self.__next_frame_ms < 0:
            self.__next_frame_ms = time.time()
        else:
            self.__next_frame_ms += target_ms
            wait = self.__next_frame_ms - time.time()
            if wait > 0:
                time.sleep(wait)

    def __process_frame(self, frame):
        pass

    def __log(self, msg, level):
        if self.__logger is not None:
            self.__logger.log(msg, level)