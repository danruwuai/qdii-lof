const api = require("../../utils/api");

Page({
  data: {
    baseUrl: "",
    marketStatus: null,
  },

  onLoad() {
    this.setData({ baseUrl: getApp().globalData.baseUrl });
    this.loadMarketStatus();
  },

  loadMarketStatus() {
    var that = this;
    api.get("/api/v1/market-status")
      .then(function(status) {
        that.setData({ marketStatus: status });
      })
      .catch(function(e) {
        console.error("Failed to load market status:", e);
      });
  },

  onBaseUrlChange(e) {
    getApp().globalData.baseUrl = e.detail.value;
    this.setData({ baseUrl: e.detail.value });
  },
});
