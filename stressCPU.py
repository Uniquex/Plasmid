import schedule
import time
import os


def stressCPU():
    cmd = 'sudo stress --cpu 4 --vm 1 --vm-bytes 256M --timeout 3600s'
    os.system(cmd)

def stressCPU50():
    cmd = 'sudo stress --cpu 2 --timeout 6200s'
    os.system(cmd)


if __name__ == '__main__':
    print(time.localtime())
    schedule.every().day.at("10:00").do(stressCPU)
    schedule.every().day.at("12:00").do(stressCPU50)

    while True:
        schedule.run_pending()
        time.sleep(1)
