import time
import api.report_queue  # noqa: F401


def main():
    print("[worker] starting report worker loop...", flush=True)
    try:
        while True:
            time.sleep(5)
            print("[worker] heartbeat", flush=True)
    except KeyboardInterrupt:
        print("[worker] stopping.", flush=True)


if __name__ == "__main__":
    main()
