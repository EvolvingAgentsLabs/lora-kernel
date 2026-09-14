"""A model stub that asks for tools and then decides. It exists to prove the loop.

IT IS NOT A MODEL AND IT IS NOT A BASELINE. Its rule is deliberately crude — it uses
three of the four signals and never opens the message — so it scores below the
majority-class bar, which is the correct thing for the harness to report about it.
What it proves is the plumbing: that `tools=[…]` arrives, that a tag comes back as
`tool_calls`, that a `role: "tool"` result lands where the model can read it, and
that the conversation terminates.
"""

import json, re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
class H(BaseHTTPRequestHandler):
    protocol_version="HTTP/1.1"
    def log_message(self,*a): pass
    def do_POST(self):
        n=int(self.headers.get("Content-Length") or 0)
        req=json.loads(self.rfile.read(n) or b"{}")
        msgs=req.get("messages") or []
        seen=" ".join(m.get("content") or "" for m in msgs)
        tid=(re.search(r"thr-\d+", seen) or [None])[0] if re.search(r"thr-\d+", seen) else None
        addr=(re.search(r"[\w.]+@[\w.-]+", seen.split("From:")[-1]) if "From:" in seen else None)
        if "i_wrote_in_thread" not in seen and tid:
            body=f"<thread_history>{tid}</thread_history>"
        elif "messages_i_sent_them" not in seen and addr:
            body=f"<sender_stats>{addr.group(0)}</sender_stats>"
        else:
            wrote = '"i_wrote_in_thread": true' in seen
            freq  = '"frequent": true' in seen
            direct= '"addressed_directly": true' in seen
            auto  = "automated message" in seen
            verdict = (not auto) and (sum([wrote,freq,direct])>=2)
            body = "IMPORTANT" if verdict else "NOT IMPORTANT"
        out={"choices":[{"message":{"role":"assistant","content":body},
                         "finish_reason":"stop"}]}
        b=json.dumps(out).encode()
        self.send_response(200); self.send_header("Content-Type","application/json")
        self.send_header("Content-Length",str(len(b))); self.end_headers(); self.wfile.write(b)
    def do_GET(self):
        b=json.dumps({"data":[{"id":"kernel"}]}).encode()
        self.send_response(200); self.send_header("Content-Type","application/json")
        self.send_header("Content-Length",str(len(b))); self.end_headers(); self.wfile.write(b)
ThreadingHTTPServer(("127.0.0.1",8099),H).serve_forever()
