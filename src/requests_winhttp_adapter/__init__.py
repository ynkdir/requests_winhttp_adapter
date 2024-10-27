import gzip
import io
import zlib

import requests
from requests.structures import CaseInsensitiveDict
from win32more import (
    FAILED,
    POINTER,
    Byte,
    Int32,
    VoidPtr,
    WinError,
    cast,
    pointer,
)
from win32more.Windows.Win32.Foundation import (
    BSTR,
    VARIANT_FALSE,
    SysAllocStringLen,
    SysFreeString,
)
from win32more.Windows.Win32.Networking.WinHttp import IWinHttpRequest, WinHttpRequest
from win32more.Windows.Win32.System.Com import (
    CLSCTX_INPROC_SERVER,
    CoCreateInstance,
    CoIncrementMTAUsage,
)
from win32more.Windows.Win32.System.Ole import (
    SafeArrayAccessData,
    SafeArrayCreateVector,
    SafeArrayGetUBound,
    SafeArrayUnaccessData,
)
from win32more.Windows.Win32.System.Variant import (
    VARIANT,
    VT_ARRAY,
    VT_BOOL,
    VT_EMPTY,
    VT_UI1,
    VariantClear,
)

CoIncrementMTAUsage(VoidPtr())


class RAII:
    def __new__(cls, obj, free):
        self = super().__new__(cls)
        self._obj = obj
        self._free = free
        obj._raii = self
        return obj

    def __del__(self):
        if self._obj:
            self._free(self._obj)


def _bstr(s: str) -> BSTR:
    return RAII(BSTR(SysAllocStringLen(s, len(s), _as_intptr=True)), SysFreeString)


class WinHttpAdapter(requests.adapters.BaseAdapter):
    def send(self, request, stream=False, timeout=None, verify=True, cert=None, proxies=None):
        req = self._send_request(request)

        response = requests.Response()
        response.status_code = self._get_status_code(req)
        response.reason = self._get_status_text(req)
        response.headers = self._get_headers(req)
        response.encoding = requests.utils.get_encoding_from_headers(response.headers)
        response.raw = self._get_body(req, response.headers)
        response.request = request
        response.connection = self
        return response

    def close(self):
        pass

    def _send_request(self, request) -> IWinHttpRequest:
        req = IWinHttpRequest(own=True)

        hr = CoCreateInstance(WinHttpRequest, None, CLSCTX_INPROC_SERVER, IWinHttpRequest._iid_, req)
        if FAILED(hr):
            raise WinError(hr)

        hr = req.Open(_bstr(request.method), _bstr(request.url), VARIANT(vt=VT_BOOL, boolVal=VARIANT_FALSE))
        if FAILED(hr):
            raise WinError(hr)

        for k, v in request.headers.items():
            req.SetRequestHeader(_bstr(k), _bstr(v))

        hr = req.Send(self._create_body_variant(request.body))
        if FAILED(hr):
            raise WinError(hr)

        return req

    def _create_body_variant(self, body: str | bytes | None) -> VARIANT:
        if body is None:
            return VARIANT(vt=VT_EMPTY)

        if isinstance(body, str):
            body = body.encode("utf-8")

        v = RAII(VARIANT(vt=VT_ARRAY | VT_UI1, parray=SafeArrayCreateVector(VT_UI1, 0, len(body))), VariantClear)
        if v.parray is None:
            raise WinError()

        ptr = POINTER(Byte)()
        hr = SafeArrayAccessData(v.parray, cast(pointer(ptr), POINTER(VoidPtr)))
        if FAILED(hr):
            raise WinError(hr)

        for i, c in enumerate(body):
            ptr[i] = c

        hr = SafeArrayUnaccessData(v.parray)
        if FAILED(hr):
            raise WinError(hr)

        return v

    def _get_status_code(self, req: IWinHttpRequest) -> int:
        status = Int32()
        hr = req.get_Status(status)
        if FAILED(hr):
            raise WinError(hr)
        return status.value

    def _get_status_text(self, req: IWinHttpRequest) -> str:
        status_text = RAII(BSTR(), SysFreeString)
        hr = req.get_StatusText(status_text)
        if FAILED(hr):
            raise WinError(hr)
        return status_text.value

    def _get_headers(self, req: IWinHttpRequest) -> dict[str, str]:
        lines = RAII(BSTR(), SysFreeString)
        hr = req.GetAllResponseHeaders(lines)
        if FAILED(hr):
            raise WinError(hr)
        headers = CaseInsensitiveDict()
        for line in lines.value.split("\r\n"):
            if line == "":
                break
            k, v = line.split(":", 1)
            headers[k.strip()] = v.strip()
        return headers

    def _get_body(self, req: IWinHttpRequest, response_headers: dict[str, str]) -> io.BytesIO | None:
        body = VARIANT(vt=VT_EMPTY)

        hr = req.get_ResponseBody(body)
        if FAILED(hr):
            raise WinError(hr)

        if body.vt == VT_EMPTY:
            return None

        ubound = Int32()
        hr = SafeArrayGetUBound(body.parray, 1, ubound)
        if FAILED(hr):
            raise WinError(hr)

        ptr = POINTER(Byte)()
        hr = SafeArrayAccessData(body.parray, cast(pointer(ptr), POINTER(VoidPtr)))
        if FAILED(hr):
            raise WinError(hr)

        data = bytes(ptr[0 : ubound.value + 1])

        hr = SafeArrayUnaccessData(body.parray)
        if FAILED(hr):
            raise WinError(hr)

        hr = VariantClear(body)
        if FAILED(hr):
            raise WinError(hr)

        enc = response_headers.get("content-encoding")
        if enc == "gzip":
            data = gzip.decompress(data)
        elif enc == "deflate":
            data = zlib.decompress(data)
        elif enc is not None:
            raise ValueError(f"Not supported Content-Encoding: {enc}")

        return io.BytesIO(data)
