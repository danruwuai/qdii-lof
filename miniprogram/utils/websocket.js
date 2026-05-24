const app = getApp();
const isDev = wx.getAccountInfoSync().miniProgram.envVersion === 'develop';

var SINGLETON = null;

function WSManager() {
  this.subscribedCodes = [];
  this.callbacks = [];
  this.openid = "";
  this.reconnectTimer = null;
  this.heartbeatTimer = null;
  this.isConnected = false;
}

WSManager.prototype.connect = function(openid) {
  var self = this;
  self.openid = openid;
  var protocol = isDev ? "ws" : "wss";
  var host = isDev ? "localhost:8000" : "your-server.com";  // 替换为你的服务器域名
  var url = protocol + "://" + host + "/ws/realtime?openid=" + openid;

  try {
    wx.closeSocket();
  } catch (e) {}

  wx.connectSocket({
    url: url,
    fail: function() {
      self.scheduleReconnect();
    },
  });

  wx.onSocketOpen(function() {
    console.log("[WS] connected");
    self.isConnected = true;
    app.globalData.wsConnected = true;
    self.startHeartbeat();
    if (self.subscribedCodes.length > 0) {
      self.subscribe(self.subscribedCodes);
    }
  });

  wx.onSocketMessage(function(res) {
    try {
      var msg = JSON.parse(res.data);
      if (msg.type === "premium_update") {
        for (var i = 0; i < self.callbacks.length; i++) {
          self.callbacks[i](msg.data);
        }
      }
      if (msg.type === "alert_triggered") {
        wx.showToast({ title: msg.data.message, icon: "none", duration: 3000 });
      }
    } catch (e) {
      console.error("[WS] parse error:", e);
    }
  });

  wx.onSocketClose(function() {
    console.log("[WS] closed");
    self.isConnected = false;
    app.globalData.wsConnected = false;
    self.clearTimers();
    self.scheduleReconnect();
  });

  wx.onSocketError(function(err) {
    console.log("[WS] error, will reconnect:", JSON.stringify(err));
    self.isConnected = false;
    app.globalData.wsConnected = false;
    self.clearTimers();
    self.scheduleReconnect();
  });
};

WSManager.prototype.subscribe = function(fundCodes) {
  var self = this;
  self.subscribedCodes = fundCodes;
  if (self.isConnected) {
    try {
      wx.sendSocketMessage({
        data: JSON.stringify({ type: "subscribe", fund_codes: fundCodes }),
      });
    } catch (e) {}
  }
};

WSManager.prototype.onPremiumUpdate = function(callback) {
  this.callbacks.push(callback);
};

WSManager.prototype.disconnect = function() {
  var self = this;
  self.clearTimers();
  self.reconnectTimer = null;
  if (self.isConnected) {
    try {
      wx.closeSocket();
    } catch (e) {}
  }
};

WSManager.prototype.scheduleReconnect = function() {
  if (this.reconnectTimer) return;
  var self = this;
  this.reconnectTimer = setTimeout(function() {
    self.reconnectTimer = null;
    self.connect(self.openid);
  }, 5000);
};

WSManager.prototype.startHeartbeat = function() {
  var self = this;
  self.heartbeatTimer = setInterval(function() {
    if (self.isConnected) {
      try {
        wx.sendSocketMessage({ data: "ping" });
      } catch (e) {}
    }
  }, 30000);
};

WSManager.prototype.clearTimers = function() {
  if (this.reconnectTimer) {
    clearTimeout(this.reconnectTimer);
    this.reconnectTimer = null;
  }
  if (this.heartbeatTimer) {
    clearInterval(this.heartbeatTimer);
    this.heartbeatTimer = null;
  }
};

SINGLETON = new WSManager();

module.exports = SINGLETON;
