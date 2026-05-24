const api = require("../../utils/api");
const wsManager = require("../../utils/websocket");

function formatPrice(num) {
  if (num === null || num === undefined) return "--";
  return Number(num).toFixed(3);
}

function formatPercent(num) {
  if (num === null || num === undefined) return "--";
  return Number(num).toFixed(2) + "%";
}

function premiumColor(rate) {
  if (rate === null || rate === undefined) return "#999";
  if (rate > 3) return "#ff4d4f";
  if (rate > 0) return "#fa8c16";
  if (rate > -3) return "#1890ff";
  return "#00b578";
}

function processItem(item) {
  var prem = item.premium || {};
  var pr = prem.premium_rate;
  return {
    code: item.code,
    name: item.name,
    price: formatPrice(item.market_price),
    premium_rate: formatPercent(pr),
    premium_color: premiumColor(pr),
  };
}

Page({
  data: {
    funds: [],
    loading: false,
  },

  onLoad() {
    this.loadWatchlist();
  },

  onShow() {
    this.loadWatchlist();
  },

  loadWatchlist() {
    var that = this;
    this.setData({ loading: true });

    api.get("/api/v1/watchlist")
      .then(function(res) {
        var items = (res.items || []).map(processItem);
        that.setData({ funds: items });
        var codes = items.map(function(f) { return f.code; });
        wsManager.subscribe(codes);
      })
      .catch(function(e) {
        console.error("Failed to load watchlist:", e);
      })
      .finally(function() {
        that.setData({ loading: false });
      });
  },

  removeWatch(e) {
    var that = this;
    var code = e.currentTarget.dataset.code;
    api.delete("/api/v1/watchlist/" + code)
      .then(function() {
        that.loadWatchlist();
      })
      .catch(function() {
        wx.showToast({ title: "移除失败", icon: "none" });
      });
  },

  onDetailTap(e) {
    var code = e.currentTarget.dataset.code;
    wx.navigateTo({ url: "/pages/detail/detail?code=" + code });
  },
});
