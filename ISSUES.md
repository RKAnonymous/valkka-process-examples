### FPS:

Maximum FPS rate 11.17 when setting **width=1920** and **height=1080**.
With decreased width/height numbers FPS is 20 on average.
Possible cause might be lack of hardware performance limit (hertz, CPU etc. which I have no enough deep knowledge)

### Synch saved and pushed frames:

Waiting for `frames_collection` to be full and then pushing the data to redis is skipping several frames.
Synchronization is needed exactly here, the frame has been saved to storage must be also written to the redis strictly
by that order

Here is a simple difference:

1st item of redis array

    {
        "172.16.50.54": "/frames/172.16.50.54/1718874411840.jpg",
        "172.16.50.57": "/frames/172.16.50.57/1718874411640.jpg",
        "172.16.50.63": "/frames/172.16.50.63/1718874411600.jpg",
        "172.16.50.59": "/frames/172.16.50.59/1718874411600.jpg",
        "172.16.50.62": "/frames/172.16.50.62/1718874411600.jpg",
        "172.16.50.60": "/frames/172.16.50.60/1718874411590.jpg",
        "172.16.50.56": "/frames/172.16.50.56/1718874411600.jpg",
        "172.16.50.64": "/frames/172.16.50.64/1718874411560.jpg",
        "172.16.50.50": "/frames/172.16.50.50/1718874411541.jpg",
        "172.16.50.58": "/frames/172.16.50.58/1718874411565.jpg"
    }


Frames in storage folder:
        
    172.16.50.50: 1.   1718874411541.jpg    <-                    

    172.16.50.54: 1.   1718874411524.jpg
                  2.   1718874411560.jpg
                  3.   1718874411600.jpg
                  4.   1718874411640.jpg
                  5.   1718874411720.jpg
                  6.   1718874411760.jpg
                  7.   1718874411800.jpg
                  8.   1718874411840.jpg    <-

    172.16.50.56: 1.   1718874411563.jpg
                  2.   1718874411600.jpg    <-
    
    172.16.50.63: 1.   1718874411531.jpg
                  2.   1718874411560.jpg
                  3.   1718874411600.jpg    <-
    
    172.16.50.64: 1.   1718874411541.jpg
                  2.   1718874411560.jpg
                  3.   1718874411600.jpg    <-

    etc.

Maybe my approach of gathering frames is not the right one. So, open to optimizations :)

## FPS rate with various parameters

### In Host machine

    +-------------------+-----------+------------+---------+
    |   shmem_buffers   |   width   |   height   |   FPS   |
    +-------------------+-----------+------------+---------+
    |      10           |   1920    |    1080    |   7.91  |
    +-------------------+-----------+------------+---------+
    |      100          |   1920    |    1080    |   10.8  |
    +-------------------+-----------+------------+---------+
    |      10           |   960     |    540     |   20.1  |
    +-------------------+-----------+------------+---------+
    |      100          |   960     |    540     |   20.1  |
    +-------------------+-----------+------------+---------+

Machine parameters

    Memory:           19.4 GiB
    Processor:        Intel® Core™ i5-9500 CPU @ 3.00GHz × 6
    Graphics:         NVIDIA GeForce GTX 1050 Ti/PCIe/SSE2 / NVIDIA Corporation GP107 [GeForce GTX 1050 Ti]
    Driver Version:   535.183.01
    CUDA Version:     12.2
    Disk Capacity:    233G
    OS:               Ubuntu 20.04.6 LTS
    OS Type:          64-bit


### In Docker container

    +-------------------+-----------+------------+---------+
    |   shmem_buffers   |   width   |   height   |   FPS   |
    +-------------------+-----------+------------+---------+
    |      100          |   1920    |    1080    |   12.5  |
    +-------------------+-----------+------------+---------+
    |      100          |   960     |     540    |   20.1  |
    +-------------------+-----------+------------+---------+


Machine parameters

    Memory:           64 Gb
    Processor:        11th Gen Intel(R) Core(TM) i7-11700K @ 3.60GHz × 16
    Graphics:         NVIDIA GeForce RTX 3090
    Driver Version:   535.54.03
    CUDA Version:     12.2
    Disk Capacity:    3.5T
    OS:               Ubuntu 20.04.6 LTS
    OS Type:          64-bit
    Docker version:   24.0.3
