const app = getApp();

function request(method, url, data) {
  var fullUrl = app.globalData.baseUrl + url;
  console.log("[API] " + method + " " + fullUrl);
  return new Promise(function(resolve, reject) {
    wx.request({
      url: fullUrl,
      method: method,
      data: data || {},
      header: {
        "Content-Type": "application/json",
      },
      timeout: 10000,
      success(res) {
        console.log("[API] " + method + " " + url + " -> " + res.statusCode);
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data);
        } else {
          reject(new Error("HTTP " + res.statusCode));
        }
      },
      fail(err) {
        var errMsg = err && err.errMsg ? err.errMsg : "unknown";
        if (errMsg.indexOf("timeout") !== -1) {
          console.log("[API] timeout " + method + " " + url);
        } else {
          console.error("[API] FAIL " + method + " " + url + ": " + errMsg);
        }
        reject(err);
      },
    });
  });
}

module.exports = {
  get: function(url, data) { return request("GET", url, data); },
  post: function(url, data) { return request("POST", url, data); },
  put: function(url, data) { return request("PUT", url, data); },
  delete: function(url, data) { return request("DELETE", url, data); },
};
