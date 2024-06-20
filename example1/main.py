"""Send decoded frames from N rtsp cameras to a single python multiprocess

If this program crashes / exits dirtily, remember to do "killall -9 python3"

Run with "python3 main.py"
"""
import logging, time
from valkka.core import *
from valkka.multiprocess.sync import EventGroup
from rgb import RGB24Process, event_fd_group_1  # from local file


class MyProcess(RGB24Process):
	# there is only one multiprocess receiving frame from ALL cameras,
	# so don't be surprised if there is one processor screaming 100% in your system
	# it is the processor that's hosting *this* process

	def preRun__(self):
		super().preRun__()
		import redis
		# import libraries that use multithreading
		# create instances from those libraries
		# self.redis_instance = etc
		self.frames_collection = {}
		self.redis_client = redis.StrictRedis(host="localhost", port=6379, db=1)

	def handleFrame__(self, frame, meta, cam_id):
		# please test first just with printing this debug message:
		self.logger.debug("handleFrame__ : rgb client got frame %s from slot %s", frame.shape, meta.slot)
		"""metadata has the following members:
		size 
		width
		height
		slot
		mstimestamp
		"""
		import cv2
		import json
		img = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
		image = f"/home/kamol/projects/valkka_sample/frames/{cam_id}/{meta.mstimestamp}.jpg"
		cv2.imwrite(image, img)

		# This code block somehow skipping several frames, which was saved to storage already but had not been push
		self.frames_collection[cam_id] = image
		if len(self.frames_collection) == 10:
			self.redis_client.rpush("camerasynchronizerviavalkka", json.dumps(self.frames_collection))
			self.frames_collection.clear()


class LiveStream:
	def __init__(self, shmem_buffers, shmem_name, address, slot, width, height):
		self.shmem_buffers = shmem_buffers
		self.shmem_name = shmem_name
		self.address = address
		self.slot = slot
		self.width = width
		self.height = height

		# reserve a unix event fd file descriptor for synchronization
		_, self.event = event_fd_group_1.reserve()
		# RBGShmem Filter
		self.shmem_filter = RGBShmemFrameFilter(self.shmem_name, self.shmem_buffers, self.width, self.height)
		# self.shmem_filter = BriefInfoFrameFilter(self.shmem_name)  # For Debugging
		self.shmem_filter.useFd(self.event)

		# SWS Filter
		self.sws_filter = SwScaleFrameFilter(f"sws_{self.shmem_name}", self.width, self.height, self.shmem_filter)
		# self.interval_filter = TimeIntervalFrameFilter("interval_filter", 0, self.sws_filter)

		# decoding part
		self.avthread = AVThread("avthread", self.sws_filter)
		self.av_in_filter = self.avthread.getFrameFilter()

		# define connection to camera
		self.ctx = LiveConnectionContext(LiveConnectionType_rtsp, self.address, self.slot, self.av_in_filter)

		self.avthread.startCall()
		self.avthread.decodingOnCall()

	def close(self):
		self.avthread.decodingOffCall()
		self.avthread.stopCall()
		self.event.release()  # release the unix event file descriptor


# multiprocesses are started before anything else!
p = MyProcess()
p.formatLogger(logging.DEBUG)  # if this is not set, loglevel.DEBUG logging won't show
p.ignoreSIGINT()
p.start()

cams = {
	1: "172.16.50.50",
	2: "172.16.50.54",
	3: "172.16.50.56",
	4: "172.16.50.57",
	5: "172.16.50.58",
	6: "172.16.50.59",
	7: "172.16.50.60",
	8: "172.16.50.62",
	9: "172.16.50.63",
	10: "172.16.50.64"
}

livethread = LiveThread("live")

livestreams = {}
for i, cam in cams.items():
	print(">", i, cam)
	livestreams[i] = LiveStream(  # NOTE: CREATES THE SHMEM SERVER
		shmem_buffers=10,
		shmem_name=f"{cam}",  # need to save frames into cams IPs folders, used in handleFrames as `client.name`
		address=f"rtsp://user:password@{cam}:554",
		slot=i,
		width=960,
		height=540
	)

# Start livethread
livethread.startCall()

# Register context to livethread
for livestream in livestreams.values():
	livethread.registerStreamCall(livestream.ctx)
	livethread.playStreamCall(livestream.ctx)
	# shmem_names.append(livestream.shmem_name)
	# THIS CALL CREATES THE SHMEM CLIENT:
	p.activateRGB24Client(
		# client side parameters must match server side:
		name=livestream.shmem_name,
		n_ringbuffer=livestream.shmem_buffers,
		width=livestream.width,
		height=livestream.height,
		# unix event fd sync primitive must match at SERVER and CLIENT sides:
		ipc_index=event_fd_group_1.asIndex(livestream.event)
	)

# while True:
# 	try:
# 		time.sleep(1)
# 	except KeyboardInterrupt:
# 		print("SIGTERM or CTRL-C: will exit asap")
# 		break
time.sleep(15)
livethread.stopCall()
p.stop()
