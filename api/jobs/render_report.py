import time

def main():
    print("[worker] starting dummy worker loop...", flush=True)
    print("[worker] (real project: consume SQS and render PDFs)", flush=True)
    try:
        while True:
            time.sleep(5)
            print("[worker] heartbeat", flush=True)
    except KeyboardInterrupt:
        print("[worker] stopping.", flush=True)

if __name__ == "__main__":
    main()
