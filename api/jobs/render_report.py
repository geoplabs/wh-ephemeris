from api.report_queue import worker_loop


def main() -> None:
    worker_loop()


if __name__ == "__main__":
    main()
