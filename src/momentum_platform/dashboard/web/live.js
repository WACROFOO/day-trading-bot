// DeskLive: one EventSource for the whole page, typed handlers, automatic
// resume. The browser re-sends Last-Event-ID on reconnect; the server replays
// what was missed or sends `resync`, in which case the page reloads its state
// through the normal session endpoint instead of drawing a gap.
//
// Usage:
//   DeskLive.on("bar10s", b => chart10s.update(b))
//           .on("health", h => badge(h.state))
//           .connect("/api/v1/stream");
(function () {
  const TYPES = ["quote", "bar5s", "bar10s", "bar1m", "health", "screener",
                 "symbol-added", "alert", "session", "resync"];
  const DeskLive = {
    state: "idle",            // idle | connecting | open | reconnecting | closed | unsupported
    lastEventId: null,
    counts: {},
    _handlers: {},
    _es: null,
    _url: null,

    on(type, fn) {
      (this._handlers[type] = this._handlers[type] || []).push(fn);
      return this;
    },
    off(type, fn) {
      this._handlers[type] = (this._handlers[type] || []).filter(f => f !== fn);
      return this;
    },
    _emit(type, payload, raw) {
      this.counts[type] = (this.counts[type] || 0) + 1;
      for (const fn of (this._handlers[type] || [])) {
        try { fn(payload, raw); } catch (e) { console.error("DeskLive handler", type, e); }
      }
      // "*" hears every DATA event (never the socket's own status): the page
      // uses it as the feed's heartbeat.
      if (type !== "status") {
        for (const fn of (this._handlers["*"] || [])) {
          try { fn(payload, type); } catch (e) { console.error("DeskLive handler *", type, e); }
        }
      }
    },
    _setState(s) {
      if (this.state === s) return;
      this.state = s;
      this._emit("status", { state: s, lastEventId: this.lastEventId });
    },
    // Exposed so tests can feed frames without a socket.
    _dispatch(type, ev) {
      let data = null;
      try { data = ev.data == null ? null : JSON.parse(ev.data); }
      catch (e) { console.error("DeskLive bad frame", type, ev.data); return; }
      if (ev.lastEventId) this.lastEventId = ev.lastEventId;
      this._emit(type, data, ev);
    },
    connect(url) {
      this._url = url || this._url || "/api/v1/stream";
      if (typeof EventSource === "undefined") { this._setState("unsupported"); return this; }
      if (this._es) this._es.close();
      this._setState("connecting");
      const es = new EventSource(this._url);
      this._es = es;
      es.onopen = () => this._setState("open");
      es.onerror = () => {
        // EventSource retries by itself and sends Last-Event-ID; we only
        // report it so the health badge can say "reconnecting" honestly.
        this._setState(es.readyState === 2 ? "closed" : "reconnecting");
      };
      for (const t of TYPES) es.addEventListener(t, ev => this._dispatch(t, ev));
      return this;
    },
    close() {
      if (this._es) { this._es.close(); this._es = null; }
      this._setState("closed");
      return this;
    },
    types: TYPES.slice(),
  };
  if (typeof window !== "undefined") window.DeskLive = DeskLive;
  if (typeof module !== "undefined" && module.exports) module.exports = DeskLive;
})();
