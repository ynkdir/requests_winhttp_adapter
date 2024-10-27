import argparse

import requests

from . import WinHttpAdapter


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("url")
    parser.add_argument("-X", default="GET", help="request method")
    parser.add_argument("-H", action="append", help="request header ('KEY: VALUE')")
    parser.add_argument("-d", help="post data")
    args = parser.parse_args()

    if args.H is None:
        headers = None
    else:
        headers = {}
        for header in args.H:
            k, v = header.split(":", 1)
            headers[k.strip()] = v.strip()

    with requests.Session() as session:
        session.mount("http://", WinHttpAdapter())
        session.mount("https://", WinHttpAdapter())
        response = session.request(args.X, args.url, headers=headers, data=args.d)

        response.encoding = response.apparent_encoding

        print(f"{args.X}")
        for k, v in response.request.headers.items():
            print(f"{k}: {v}")
        print("")
        if args.d is not None:
            print(args.d)

        print(response)
        for k, v in response.headers.items():
            print(f"{k}: {v}")
        print("")
        if response.text is not None:
            print(response.text)


if __name__ == "__main__":
    main()
