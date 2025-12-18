import httpx


def httpx_client_kwargs():
    return {
        "timeout": 10.0,
    }


def aget_http_client():
    return httpx.AsyncClient(**httpx_client_kwargs())


def get_http_client():
    return httpx.Client(**httpx_client_kwargs())
