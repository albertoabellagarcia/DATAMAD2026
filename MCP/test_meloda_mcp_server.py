#!/usr/bin/env python3
"""
Test suite for the Smart Data Models MCP Server
https://opendatamodels.org/smart-data-models-mcp-server/

It talks to the server with plain JSON-RPC over HTTP (the MCP protocol) and checks:

  A. Service endpoints   health, manifest, docs
  B. MCP handshake       initialize (+ server_instructions), tools/list (15 tools)
  C. Every tool          the 15 tools, with arguments based on the Madrid traffic
                         use case (TrafficFlowObserved), checking the content
  D. Behaviour           invalid payload  -> isError false, valid false
                         unknown model    -> MODEL_NOT_FOUND + suggestion
                         recovery pattern -> fuzzy_find_model + retry
  E. Operations          rate-limit headers, response time vs. SLA (2000 ms),
                         deprecated /mcp endpoint headers

It respects the server's rate limit (60 requests / 60 s) and its retry policy
for HTTP 503 (5 s -> 15 s -> 60 s).

Usage:
  python test_sdm_mcp.py               # run everything
  python test_sdm_mcp.py --verbose     # also print each response
  python test_sdm_mcp.py --url URL     # test another deployment

Output: a PASS/WARN/FAIL summary and the full report in mcp_test_report.json

Requirements: pip install requests
"""

import json
import sys
import time
from datetime import datetime, timezone

import requests

BASE_URL = "https://opendatamodels.org/mcp/v1"
LEGACY_URL = "https://opendatamodels.org/mcp"
REPORT_FILE = "mcp_test_report.json"

SLA_MS = 2000
RETRY_503 = [5, 15, 60]
TIMEOUT = 60

EXPECTED_TOOLS = {
    "search_data_models", "get_data_model", "list_domains", "list_models_by_domain",
    "validate_data", "get_related_models", "get_attributes_for_model",
    "get_attribute_details", "find_subject_by_model_name", "fuzzy_find_model",
    "get_subject_repo_url", "get_model_repo_url", "get_full_catalog",
    "export_model_attributes", "get_model_context",
}
EXPECTED_DOMAINS = {
    "SmartCities", "SmartAgrifood", "SmartWater", "SmartEnergy", "SmartEnvironment",
    "SmartRobotics", "SmartSensoring", "CrossSector", "SmartAeronautics",
    "SmartDestinations", "SmartHealth", "SmartManufacturing", "SmartLogistics",
}

MODEL = "TrafficFlowObserved"
SUBJECT = "dataModel.Transportation"

# A Madrid traffic measuring point already converted to TrafficFlowObserved
VALID_PAYLOAD = {
    "id": "urn:ngsi-ld:TrafficFlowObserved:madrid-3409",
    "type": "TrafficFlowObserved",
    "name": "SEPÚLVEDA ENTRADA CRUCE N-S",
    "dateObserved": "2026-11-05T11:15:00Z",
    "intensity": 80,
    "occupancy": 0.01,
    "congested": False,
    "location": {"type": "Point", "coordinates": [-3.7426, 40.3994]},
}
INVALID_PAYLOAD = dict(VALID_PAYLOAD, intensity="mucho")

VERBOSE = "--verbose" in sys.argv
if "--url" in sys.argv:
    BASE_URL = sys.argv[sys.argv.index("--url") + 1].rstrip("/")
    LEGACY_URL = BASE_URL[:-3] if BASE_URL.endswith("/v1") else BASE_URL


# ================================================================ HTTP client
class MCPClient:
    def __init__(self, url):
        self.url = url
        self.http = requests.Session()
        self.http.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "User-Agent": "datamad-mcp-tester/1.0",
        })
        self.next_id = 1
        self.session_id = None
        self.rate = {}        # last rate-limit headers seen
        self.timings = []     # (label, ms)

    # -- low level ---------------------------------------------------------
    def _throttle(self):
        """Wait if the rate-limit window is almost used up."""
        remaining = self.rate.get("remaining")
        reset = self.rate.get("reset")
        if remaining is not None and remaining <= 2 and reset:
            print(f"   … rate limit nearly reached, waiting {reset} s")
            time.sleep(reset + 1)

    def _remember_rate(self, headers):
        def num(name):
            try:
                return int(headers.get(name))
            except (TypeError, ValueError):
                return None
        self.rate = {"limit": num("X-RateLimit-Limit"),
                     "remaining": num("X-RateLimit-Remaining"),
                     "reset": num("X-RateLimit-Reset"),
                     "window": headers.get("X-RateLimit-Window")}

    def request(self, method, url=None, label=None, **kwargs):
        """HTTP request with rate-limit handling and the 503 retry policy."""
        url = url or self.url
        delays = list(RETRY_503)
        while True:
            self._throttle()
            start = time.perf_counter()
            r = self.http.request(method, url, timeout=TIMEOUT, **kwargs)
            ms = round((time.perf_counter() - start) * 1000)
            self._remember_rate(r.headers)
            if r.status_code == 429:
                wait = self.rate.get("reset") or 60
                print(f"   … HTTP 429, waiting {wait} s")
                time.sleep(wait + 1)
                continue
            if r.status_code == 503 and delays:
                wait = delays.pop(0)
                print(f"   … HTTP 503, retrying in {wait} s")
                time.sleep(wait)
                continue
            self.timings.append((label or url, ms))
            return r, ms

    @staticmethod
    def _parse_body(r):
        """Accept plain JSON or a Server-Sent Events stream."""
        ctype = r.headers.get("Content-Type", "")
        if "text/event-stream" in ctype:
            for line in r.text.splitlines():
                if line.startswith("data:"):
                    try:
                        return json.loads(line[5:].strip())
                    except ValueError:
                        continue
            return None
        try:
            return r.json()
        except ValueError:
            return None

    # -- JSON-RPC ----------------------------------------------------------
    def rpc(self, method, params=None, notify=False):
        body = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            body["params"] = params
        if not notify:
            body["id"] = self.next_id
            self.next_id += 1
        headers = {"Mcp-Session-Id": self.session_id} if self.session_id else {}
        r, ms = self.request("POST", json=body, headers=headers, label=method)
        sid = r.headers.get("Mcp-Session-Id")
        if sid:
            self.session_id = sid
        return r, self._parse_body(r), ms

    def call_tool(self, name, arguments):
        r, msg, ms = self.rpc("tools/call", {"name": name, "arguments": arguments})
        return r, msg, unwrap(msg), ms


def unwrap(msg):
    """
    Get the tool's own JSON answer out of an MCP response.
    MCP wraps it as result.structuredContent or result.content[].text.
    """
    if not isinstance(msg, dict):
        return None
    if "error" in msg and "result" not in msg:
        return {"isError": True, "rpc_error": msg["error"]}
    result = msg.get("result")
    if not isinstance(result, dict):
        return result
    if isinstance(result.get("structuredContent"), (dict, list)):
        data = result["structuredContent"]
    else:
        data = None
        for item in result.get("content") or []:
            if item.get("type") == "text":
                try:
                    data = json.loads(item["text"])
                except (ValueError, TypeError):
                    data = {"text": item.get("text")}
                break
        if data is None:
            data = result
    if isinstance(data, dict) and "isError" not in data and "isError" in result:
        data = dict(data, isError=result["isError"])
    return data


# ================================================================ test runner
RESULTS = []


def record(group, name, status, detail="", ms=None, response=None):
    RESULTS.append({"group": group, "test": name, "status": status,
                    "detail": detail, "ms": ms,
                    "response": truncate(response)})
    icon = {"PASS": "✔", "WARN": "!", "FAIL": "✘"}[status]
    time_txt = f" ({ms} ms)" if ms is not None else ""
    print(f"  {icon} {status:<4} {name}{time_txt}" + (f" — {detail}" if detail else ""))
    if VERBOSE and response is not None:
        print("        " + json.dumps(response, ensure_ascii=False)[:800])


def truncate(obj, limit=4000):
    if obj is None:
        return None
    text = json.dumps(obj, ensure_ascii=False, default=str)
    return obj if len(text) <= limit else text[:limit] + " …(truncated)"


def text_of(obj):
    return json.dumps(obj, ensure_ascii=False, default=str) if obj is not None else ""


def is_error(data):
    return isinstance(data, dict) and data.get("isError") is True


def find_key(obj, key):
    """First value of `key` anywhere in a nested structure."""
    if isinstance(obj, dict):
        if key in obj:
            return obj[key]
        for v in obj.values():
            found = find_key(v, key)
            if found is not None:
                return found
    elif isinstance(obj, list):
        for v in obj:
            found = find_key(v, key)
            if found is not None:
                return found
    return None


def section(title):
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


# ================================================================ A. endpoints
def test_endpoints(c):
    section("A · SERVICE ENDPOINTS")

    try:
        r, ms = c.request("GET", f"{BASE_URL}/health", label="health")
        data = r.json()
        status = data.get("status")
        ok = r.status_code == 200 and status == "healthy"
        record("A", "GET /health", "PASS" if ok else "FAIL",
               f"HTTP {r.status_code}, status={status}, version={data.get('version')}, "
               f"adapter={data.get('adapter_status')}, uptime={data.get('uptime_human')}",
               ms, data)
    except (requests.RequestException, ValueError) as e:
        record("A", "GET /health", "FAIL", str(e))

    for path in ("manifest.json", "docs"):
        try:
            r, ms = c.request("GET", f"{BASE_URL}/{path}", label=path)
            if path.endswith(".json"):
                data = r.json()
                tools = find_key(data, "tools")
                n = len(tools) if isinstance(tools, list) else "?"
                record("A", f"GET /{path}", "PASS" if r.status_code == 200 else "FAIL",
                       f"HTTP {r.status_code}, valid JSON, tools listed: {n}", ms, data)
            else:
                record("A", f"GET /{path}", "PASS" if r.status_code == 200 else "FAIL",
                       f"HTTP {r.status_code}, {len(r.content)} bytes", ms)
        except (requests.RequestException, ValueError) as e:
            record("A", f"GET /{path}", "FAIL", str(e))


# ================================================================ B. handshake
def test_handshake(c):
    section("B · MCP HANDSHAKE")

    try:
        r, msg, ms = c.rpc("initialize", {
            "protocolVersion": "2025-03-26",
            "capabilities": {},
            "clientInfo": {"name": "datamad-mcp-tester", "version": "1.0"},
        })
        result = (msg or {}).get("result") or {}
        server = result.get("serverInfo", {})
        instructions = (result.get("instructions") or result.get("server_instructions")
                        or find_key(result, "server_instructions"))
        ok = r.status_code == 200 and bool(result.get("protocolVersion"))
        record("B", "initialize", "PASS" if ok else "FAIL",
               f"protocol={result.get('protocolVersion')}, server={server.get('name')} "
               f"{server.get('version')}, session={'yes' if c.session_id else 'no'}",
               ms, msg)
        record("B", "initialize returns server_instructions",
               "PASS" if instructions else "WARN",
               f"{len(str(instructions))} characters" if instructions else "not found")
        c.rpc("notifications/initialized", notify=True)
    except requests.RequestException as e:
        record("B", "initialize", "FAIL", str(e))

    tools = []
    try:
        r, msg, ms = c.rpc("tools/list", {})
        tools = ((msg or {}).get("result") or {}).get("tools") or []
        names = {t.get("name") for t in tools}
        missing = EXPECTED_TOOLS - names
        extra = names - EXPECTED_TOOLS
        record("B", "tools/list returns the 15 documented tools",
               "PASS" if not missing else "FAIL",
               f"{len(names)} tools" + (f"; missing: {sorted(missing)}" if missing else "")
               + (f"; extra: {sorted(extra)}" if extra else ""), ms,
               sorted(names))
        no_schema = [t.get("name") for t in tools if t.get("inputSchema") is None]
        no_desc = [t.get("name") for t in tools if not t.get("description")]
        record("B", "every tool has inputSchema and description",
               "PASS" if not (no_schema or no_desc) else "WARN",
               (f"no schema: {no_schema} " if no_schema else "")
               + (f"no description: {no_desc}" if no_desc else ""))
    except requests.RequestException as e:
        record("B", "tools/list", "FAIL", str(e))
    return tools


# ================================================================ C. tools
def tool_test(c, name, args, check, describe):
    """Call one tool and apply a check(data) -> (ok, detail)."""
    try:
        r, msg, data, ms = c.call_tool(name, args)
    except requests.RequestException as e:
        record("C", name, "FAIL", str(e))
        return None
    if data is None:
        record("C", name, "FAIL", f"HTTP {r.status_code}, no parsable answer", ms, msg)
        return None
    if is_error(data):
        err = find_key(data, "error") or data.get("rpc_error")
        record("C", name, "FAIL", f"isError: {text_of(err)[:200]}", ms, data)
        return data
    try:
        ok, detail = check(data)
    except Exception as e:
        ok, detail = False, f"check failed: {e}"
    status = "PASS" if ok else "FAIL"
    if ok and ms > SLA_MS:
        status, detail = "WARN", f"{detail}; slower than SLA ({SLA_MS} ms)"
    record("C", f"{name} — {describe}", status, detail, ms, data)
    return data


def contains(data, *words):
    t = text_of(data)
    missing = [w for w in words if w not in t]
    return (not missing, "found " + ", ".join(words) if not missing
            else f"missing {missing}")


def test_tools(c):
    section(f"C · THE 15 TOOLS (use case: {MODEL})")

    tool_test(c, "search_data_models", {"query": "traffic", "limit": 10},
              lambda d: contains(d, MODEL), 'query "traffic"')

    tool_test(c, "search_data_models",
              {"query": "traffic", "domain": "SmartCities", "limit": 5},
              lambda d: (len(text_of(d)) > 20, f"{len(text_of(d))} chars"),
              "with domain filter")

    def check_domains(d):
        found = {x for x in EXPECTED_DOMAINS if x in text_of(d)}
        return len(found) == 13, f"{len(found)}/13 domains"
    tool_test(c, "list_domains", {}, check_domains, "13 domains")

    tool_test(c, "list_models_by_domain", {"domain": "SmartCities", "limit": 500},
              lambda d: contains(d, MODEL), "SmartCities contains the model")

    tool_test(c, "get_data_model", {"model_name": MODEL},
              lambda d: contains(d, "intensity", "properties"), "full JSON Schema")

    tool_test(c, "get_data_model", {"model_name": MODEL, "include_examples": True},
              lambda d: contains(d, "example"), "include_examples=true")

    tool_test(c, "get_attributes_for_model", {"model_name": MODEL},
              lambda d: contains(d, "intensity", "occupancy", "averageVehicleSpeed",
                                 "congested", "Property"), "attributes + NGSI types")

    tool_test(c, "get_attribute_details",
              {"model_name": MODEL, "attribute": "averageVehicleSpeed"},
              lambda d: contains(d, "averageVehicleSpeed"), "averageVehicleSpeed")

    tool_test(c, "find_subject_by_model_name", {"model_name": MODEL},
              lambda d: contains(d, SUBJECT), "resolves to subject")

    tool_test(c, "fuzzy_find_model",
              {"model_name": "TraficFlowObservd", "threshold": 70},
              lambda d: contains(d, MODEL), 'misspelled "TraficFlowObservd"')

    tool_test(c, "get_subject_repo_url", {"subject": SUBJECT},
              lambda d: contains(d, "github.com", "Transportation"), "GitHub URL")

    tool_test(c, "get_model_repo_url", {"model_name": MODEL},
              lambda d: contains(d, "github"), "GitHub URL(s)")

    tool_test(c, "get_full_catalog", {"domain": "SmartCities"},
              lambda d: contains(d, MODEL), "SmartCities catalogue")

    def check_export(d):
        t = text_of(d)
        ok = "intensity" in t and ("," in t)
        return ok, "delimited export with intensity" if ok else "unexpected format"
    tool_test(c, "export_model_attributes",
              {"model_name": MODEL, "separator": ",",
               "fields": ["property", "type", "typeNGSI", "units", "description"]},
              check_export, "CSV export")

    tool_test(c, "get_model_context", {"model_name": MODEL},
              lambda d: contains(d, "context"), "@context for NGSI-LD")

    tool_test(c, "get_related_models", {"model_name": MODEL},
              lambda d: (len(text_of(d)) > 20, f"{len(text_of(d))} chars"),
              "related models")

    def check_valid(d):
        v = find_key(d, "valid")
        return v is True, f"valid={v}, errors={find_key(d, 'errors')}"
    tool_test(c, "validate_data", {"model_name": MODEL, "data": VALID_PAYLOAD},
              check_valid, "Madrid point (key-values) is valid")

    normalized = {
        "@context": "https://raw.githubusercontent.com/smart-data-models/"
                    "dataModel.Transportation/master/context.jsonld",
        "id": VALID_PAYLOAD["id"], "type": MODEL,
        "dateObserved": {"type": "Property", "value": VALID_PAYLOAD["dateObserved"]},
        "intensity": {"type": "Property", "value": 80},
        "location": {"type": "GeoProperty", "value": VALID_PAYLOAD["location"]},
    }
    tool_test(c, "validate_data", {"model_name": MODEL, "data": normalized},
              check_valid, "same point in NGSI-LD normalized")


# ================================================================ D. behaviour
def test_behaviour(c):
    section("D · ERROR HANDLING AND RECOVERY")

    # Invalid payload: not a system error
    try:
        r, msg, data, ms = c.call_tool("validate_data",
                                       {"model_name": MODEL, "data": INVALID_PAYLOAD})
        valid = find_key(data, "valid")
        ok = not is_error(data) and valid is False
        record("D", 'invalid payload (intensity="mucho") -> isError false, valid false',
               "PASS" if ok else "FAIL",
               f"isError={find_key(data, 'isError')}, valid={valid}, "
               f"errors={text_of(find_key(data, 'errors'))[:150]}", ms, data)
    except requests.RequestException as e:
        record("D", "invalid payload", "FAIL", str(e))

    # Unknown model: structured MODEL_NOT_FOUND
    wrong = "TraficFlowObservd"
    try:
        r, msg, data, ms = c.call_tool("get_data_model", {"model_name": wrong})
        code = find_key(data, "code")
        suggestion = find_key(data, "suggestion")
        ok = is_error(data) and code == "MODEL_NOT_FOUND"
        record("D", f'unknown model "{wrong}" -> MODEL_NOT_FOUND',
               "PASS" if ok else "FAIL", f"isError={is_error(data)}, code={code}", ms, data)
        record("D", "error includes a suggestion", "PASS" if suggestion else "FAIL",
               str(suggestion)[:120] if suggestion else "no suggestion field")
    except requests.RequestException as e:
        record("D", "unknown model", "FAIL", str(e))

    # Documented recovery pattern: fuzzy_find_model + retry
    try:
        r, msg, data, ms = c.call_tool("fuzzy_find_model",
                                       {"model_name": wrong, "threshold": 70})
        found = MODEL in text_of(data)
        record("D", "recovery step 1: fuzzy_find_model proposes the right name",
               "PASS" if found else "FAIL", f"{MODEL} {'found' if found else 'not found'}",
               ms, data)
        if found:
            r, msg, data, ms = c.call_tool("get_data_model", {"model_name": MODEL})
            record("D", "recovery step 2: retry with corrected name succeeds",
                   "PASS" if not is_error(data) and data else "FAIL", "", ms)
    except requests.RequestException as e:
        record("D", "recovery pattern", "FAIL", str(e))

    # Bad domain value
    try:
        r, msg, data, ms = c.call_tool("list_models_by_domain", {"domain": "SmartMars"})
        record("D", 'invalid domain "SmartMars" -> structured error',
               "PASS" if is_error(data) and find_key(data, "code") else "WARN",
               f"isError={is_error(data)}, code={find_key(data, 'code')}", ms, data)
    except requests.RequestException as e:
        record("D", "invalid domain", "FAIL", str(e))

    # Unknown tool: JSON-RPC level error expected
    try:
        r, msg, data, ms = c.call_tool("does_not_exist", {})
        ok = is_error(data) or (isinstance(msg, dict) and "error" in msg)
        record("D", "unknown tool -> error", "PASS" if ok else "FAIL",
               text_of(msg)[:150], ms)
    except requests.RequestException as e:
        record("D", "unknown tool", "FAIL", str(e))


# ================================================================ E. operations
def test_operations(c):
    section("E · OPERATIONS")

    rate = c.rate
    ok = rate.get("limit") is not None and rate.get("remaining") is not None
    record("E", "rate-limit headers present", "PASS" if ok else "WARN",
           f"limit={rate.get('limit')}, remaining={rate.get('remaining')}, "
           f"reset={rate.get('reset')}, window={rate.get('window')}")

    times = [ms for _, ms in c.timings]
    if times:
        slow = [(lbl, ms) for lbl, ms in c.timings if ms > SLA_MS]
        avg = round(sum(times) / len(times))
        record("E", f"response times within SLA ({SLA_MS} ms)",
               "PASS" if not slow else "WARN",
               f"{len(times)} requests, avg {avg} ms, max {max(times)} ms"
               + (f", {len(slow)} slower than SLA" if slow else ""))

    try:
        r, ms = c.request("POST", LEGACY_URL, label="legacy /mcp",
                          json={"jsonrpc": "2.0", "id": 999, "method": "tools/list"})
        dep = r.headers.get("Deprecation")
        sunset = r.headers.get("Sunset")
        record("E", "legacy /mcp sends Deprecation + Sunset headers",
               "PASS" if dep and sunset else "WARN",
               f"HTTP {r.status_code}, Deprecation={dep}, Sunset={sunset}", ms)
    except requests.RequestException as e:
        record("E", "legacy /mcp", "WARN", str(e))


# ================================================================ main
def main():
    print(f"Testing MCP server: {BASE_URL}")
    print(f"Started: {datetime.now():%Y-%m-%d %H:%M:%S}")
    c = MCPClient(BASE_URL)

    test_endpoints(c)
    test_handshake(c)
    test_tools(c)
    test_behaviour(c)
    test_operations(c)

    section("SUMMARY")
    counts = {s: sum(1 for r in RESULTS if r["status"] == s) for s in ("PASS", "WARN", "FAIL")}
    for group, label in (("A", "Endpoints"), ("B", "Handshake"), ("C", "Tools"),
                         ("D", "Behaviour"), ("E", "Operations")):
        g = [r for r in RESULTS if r["group"] == group]
        p = sum(1 for r in g if r["status"] == "PASS")
        print(f"  {label:<11} {p}/{len(g)} passed")
    print(f"\n  PASS {counts['PASS']}   WARN {counts['WARN']}   FAIL {counts['FAIL']}"
          f"   (total {len(RESULTS)})")
    failed = [r for r in RESULTS if r["status"] == "FAIL"]
    if failed:
        print("\n  Failed tests:")
        for r in failed:
            print(f"    ✘ [{r['group']}] {r['test']}: {r['detail'][:120]}")

    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        json.dump({"server": BASE_URL,
                   "date": datetime.now(timezone.utc).isoformat(),
                   "summary": counts, "rate_limit_last": c.rate,
                   "results": RESULTS}, f, ensure_ascii=False, indent=2, default=str)
    print(f"\nFull report saved to {REPORT_FILE}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()