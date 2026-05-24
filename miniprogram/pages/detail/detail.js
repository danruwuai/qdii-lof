const api = require("../../utils/api");

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

Page({
  data: {
    fund: null,
    loading: true,
    inWatchlist: false,
    price: "--",
    change_pct: "--",
    change_class: "",
    nav: "--",
    est_nav: "--",
    premium_rate: "--",
    premium_color: "#999",
    calc_method: "C",
    daily_limit_text: "无限额",
    holdings: [],
  },

  onLoad(options) {
    this.loadDetail(options.code);
  },

  loadDetail(code) {
    var that = this;
    this.setData({ loading: true });

    api.get("/api/v1/funds/" + code)
      .then(function(fund) {
        var prem = fund.premium || {};
        var pr = prem.premium_rate;

        var holdings = (fund.holdings || []).map(function(h) {
          return {
            asset_name: h.asset_name,
            asset_code: h.asset_code,
            weight: h.weight != null ? Number(h.weight).toFixed(2) : "--",
          };
        });

        // Check if in watchlist
        return api.get("/api/v1/watchlist")
          .then(function(watchlist) {
            var inWatchlist = (watchlist.items || []).some(function(f) {
              return f.code === code;
            });
            that.setData({
              fund: fund,
              inWatchlist: inWatchlist,
              price: formatPrice(fund.market_price),
              change_pct: formatPercent(fund.change_pct),
              change_class: (fund.change_pct || 0) > 0 ? "text-green" : (fund.change_pct || 0) < 0 ? "text-red" : "",
              nav: formatPrice(fund.nav),
              est_nav: formatPrice(prem.estimated_nav),
              premium_rate: formatPercent(pr),
              premium_color: premiumColor(pr),
              calc_method: prem.calc_method || "C",
              daily_limit_text: fund.daily_limit
                ? (fund.daily_limit >= 10000 ? (fund.daily_limit / 10000).toFixed(0) + "万元" : fund.daily_limit + "元")
                : "无限额",
              holdings: holdings,
            });
          });
      })
      .catch(function(e) {
        console.error("Failed to load detail:", e);
        wx.showToast({ title: "加载失败", icon: "none" });
      })
      .finally(function() {
        that.setData({ loading: false });
      });
  },

  toggleWatchlist() {
    var that = this;
    var code = this.data.fund.code;
    var inList = this.data.inWatchlist;

    var promise = inList
      ? api.delete("/api/v1/watchlist/" + code)
      : api.post("/api/v1/watchlist", { fund_code: code });

    promise
      .then(function() {
        that.setData({ inWatchlist: !inList });
        wx.showToast({ title: inList ? "已移除" : "已添加", icon: "success" });
      })
      .catch(function() {
        wx.showToast({ title: "操作失败", icon: "none" });
      });
  },
});
