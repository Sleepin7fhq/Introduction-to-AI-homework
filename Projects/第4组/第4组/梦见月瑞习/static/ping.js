/* 课堂模式心跳：让「在线人数」是真实的 */
(function () {
  try {
    var sid = sessionStorage.getItem("dsh_sid");
    if (!sid) {
      sid = Math.random().toString(36).slice(2, 12);
      sessionStorage.setItem("dsh_sid", sid);
    }
    var ping = function () {
      fetch("/api/ping", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ sid: sid })
      }).catch(function () {});
    };
    ping();
    setInterval(ping, 10000);
  } catch (e) { /* 隐私模式下 sessionStorage 可能不可用，忽略 */ }
})();
