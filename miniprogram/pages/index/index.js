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

function formatLimit(limit, canSubscribe) {
  if (!canSubscribe) return "暂停申购";
  if (!limit) return "不限额";
  if (limit >= 10000) return (limit / 10000).toFixed(0) + "万";
  return limit + "元";
}

function settlementText(fundType) {
  var ft = fundType || "";
  if (ft.indexOf("QDII") >= 0 && ft.indexOf("LOF") >= 0) return "T+2到账，转场内T+5+";
  if (ft.indexOf("QDII") >= 0) return "T+2到账";
  if (ft.indexOf("LOF") >= 0) return "T+1到账";
  if (ft.indexOf("ETF") >= 0) return "ETF申赎门槛50万+";
  return "T+1到账";
}

function formatProfit(amount) {
  if (amount == null) return "";
  if (amount >= 10000) return (amount / 10000).toFixed(2) + "万元";
  return amount.toFixed(2) + "元";
}

function formatNetProfit(pct) {
  if (pct == null) return "";
  return pct.toFixed(2) + "%";
}

function processItem(item) {
  var prem = item.premium || {};
  var pr = prem.premium_rate;
  return {
    code: item.code,
    name: item.name,
    fund_type: item.fund_type || "",
    trading_venue: item.trading_venue || "场内",
    can_subscribe: item.can_subscribe,
    subscribe_status: item.subscribe_status || (item.can_subscribe ? "可申购" : "暂停申购"),
    daily_limit: item.daily_limit,
    daily_limit_text: formatLimit(item.daily_limit, item.can_subscribe),
    settlement_text: settlementText(item.fund_type),
    market_price: formatPrice(item.market_price),
    change_pct: formatPercent(item.change_pct),
    change_class: (item.change_pct || 0) > 0 ? "text-green" : (item.change_pct || 0) < 0 ? "text-red" : "",
    premium_rate: formatPercent(pr),
    premium_color: premiumColor(pr),
    estimated_nav: formatPrice(prem.estimated_nav),
    calc_method: prem.calc_method || "C",
    nav_accuracy: item.nav_accuracy || "T-2",
    nav_date: item.nav_date || "--",
    is_watched: item.is_watched || false,
    is_high_premium: item.is_high_premium || false,
    estimated_daily_profit: item.estimated_daily_profit,
    estimated_daily_profit_text: formatProfit(item.estimated_daily_profit),
    arbitrage_type: item.arbitrage_type || "",
    net_profit: item.net_profit,
    net_profit_text: formatNetProfit(item.net_profit),
    risk_tags: item.risk_tags || [],
  };
}

Page({
  data: {
    funds: [],
    sortField: "premium_rate",
    sortDirection: "desc",
    loading: false,
    loadingMore: false,
    searchValue: "",
    lastUpdateTime: "",
    page: 1,
    pageSize: 100,
    hasMore: true,
    total: 0,
    // Tab data
    activeTab: "all",
    tabs: [
      { key: "all", label: "全部", count: 0 },
      { key: "watchlist", label: "关注", count: 0 },
      { key: "arbitrage", label: "套利", count: 0 },
      { key: "QDII-ETF", label: "QDII-ETF", count: 0 },
      { key: "QDII-LOF", label: "LOF", count: 0 },
    ],
    watchedCodes: {},
    // Filter state
    filterCanSubscribe: null,      // null=all, true=可申购, false=暂停申购
    filterPremiumLevel: null,      // null=all, high/normal/discount
    filterArbitrageType: null,     // null=all, 溢价套利/持有者卖出/折价埋伏/低溢价埋伏/溢价回落
    filterRegion: null,            // null=all, US/HK/JP/EU等
    showArbitrageOptions: false,   // 套利类型下拉选项显示状态
    activeFilters: [],             // 当前激活的筛选标签
  },

  onLoad() {
    this.loadTabCounts();
    this.loadFunds();
  },

  onShow() {
    var that = this;
    var app = getApp();
    wsManager.connect(app.globalData.openid);
    wsManager.onPremiumUpdate(function(data) {
      that.updateFundRow(data);
    });
  },

  onHide() {},

  onPullDownRefresh() {
    var that = this;
    this.setData({ page: 1, hasMore: true });
    this.loadTabCounts();
    this.loadFunds().then(function() {
      wx.stopPullDownRefresh();
    });
  },

  onReachBottom() {
    if (!this.data.hasMore || this.data.loadingMore || this.data.loading) return;
    this.setData({ page: this.data.page + 1 });
    this.loadMoreFunds();
  },

  loadTabCounts() {
    var that = this;
    api.get("/api/v1/funds/tab-counts")
      .then(function(res) {
        var tabs = that.data.tabs.slice();
        for (var i = 0; i < tabs.length; i++) {
          var count = 0;
          if (tabs[i].key === "all") count = res.all || 0;
          else if (tabs[i].key === "watchlist") count = res.watchlist || 0;
          else if (tabs[i].key === "arbitrage") count = res.arbitrage || 0;
          else count = res[tabs[i].key] || 0;
          tabs[i].count = count;
        }
        that.setData({ tabs: tabs });
      })
      .catch(function(e) {
        console.error("Failed to load tab counts:", e);
      });
  },

  loadFunds() {
    var that = this;
    this.setData({ loading: true });

    var params = {
      sort: this.data.sortField,
      sort_dir: this.data.sortDirection,
      page: 1,
      page_size: this.data.pageSize,
    };
    // 添加筛选参数
    if (this.data.filterCanSubscribe !== null) {
      params.can_subscribe = this.data.filterCanSubscribe;
    }
    if (this.data.filterPremiumLevel) {
      params.premium_level = this.data.filterPremiumLevel;
    }
    if (this.data.filterArbitrageType) {
      params.arbitrage_type = this.data.filterArbitrageType;
    }
    if (this.data.filterRegion) {
      params.region = this.data.filterRegion;
    }
    if (this.data.activeTab && this.data.activeTab !== "all") {
      params.tab = this.data.activeTab;
    }
    if (this.data.searchValue) params.search = this.data.searchValue;

    return api.get("/api/v1/funds", params)
      .then(function(res) {
        var items = (res.items || []).map(processItem);
        var total = res.total || 0;
        var watchedCodes = {};
        for (var i = 0; i < items.length; i++) {
          if (items[i].is_watched) {
            watchedCodes[items[i].code] = true;
          }
        }
        that.setData({
          funds: items,
          lastUpdateTime: new Date().toLocaleTimeString(),
          total: total,
          hasMore: items.length < total,
          page: 1,
          watchedCodes: Object.assign({}, that.data.watchedCodes, watchedCodes),
        });

        var codes = items.map(function(f) { return f.code; });
        wsManager.subscribe(codes);
      })
      .catch(function(e) {
        console.error("Failed to load funds:", e);
        wx.showToast({ title: "加载失败", icon: "none" });
      })
      .finally(function() {
        that.setData({ loading: false });
      });
  },

  loadMoreFunds() {
    var that = this;
    this.setData({ loadingMore: true });

    var params = {
      sort: this.data.sortField,
      sort_dir: this.data.sortDirection,
      page: this.data.page,
      page_size: this.data.pageSize,
    };
    // 添加筛选参数
    if (that.data.filterCanSubscribe !== null) {
      params.can_subscribe = that.data.filterCanSubscribe;
    }
    if (that.data.filterPremiumLevel) {
      params.premium_level = that.data.filterPremiumLevel;
    }
    if (that.data.filterArbitrageType) {
      params.arbitrage_type = that.data.filterArbitrageType;
    }
    if (that.data.filterRegion) {
      params.region = that.data.filterRegion;
    }
    if (this.data.activeTab && this.data.activeTab !== "all") {
      params.tab = this.data.activeTab;
    }
    if (this.data.searchValue) params.search = this.data.searchValue;

    return api.get("/api/v1/funds", params)
      .then(function(res) {
        var items = (res.items || []).map(processItem);
        var existingFunds = that.data.funds.concat(items);
        var watchedCodes = {};
        for (var i = 0; i < items.length; i++) {
          if (items[i].is_watched) {
            watchedCodes[items[i].code] = true;
          }
        }
        that.setData({
          funds: existingFunds,
          hasMore: existingFunds.length < (res.total || 0),
          watchedCodes: Object.assign({}, that.data.watchedCodes, watchedCodes),
        });
      })
      .catch(function(e) {
        console.error("Failed to load more funds:", e);
      })
      .finally(function() {
        that.setData({ loadingMore: false });
      });
  },

  onTabChange(e) {
    var tab = e.currentTarget.dataset.tab;
    this.setData({ activeTab: tab, page: 1, hasMore: true, funds: [] });
    this.loadFunds();
  },

  updateFundRow(data) {
    var idx = -1;
    var funds = this.data.funds;
    for (var i = 0; i < funds.length; i++) {
      if (funds[i].code === data.code) {
        idx = i;
        break;
      }
    }
    if (idx >= 0) {
      var pr = data.premium_rate;
      var updates = {
        ["funds[" + idx + "].market_price"]: formatPrice(data.market_price),
        ["funds[" + idx + "].premium_rate"]: formatPercent(pr),
        ["funds[" + idx + "].premium_color"]: premiumColor(pr),
        ["funds[" + idx + "].estimated_nav"]: formatPrice(data.estimated_nav),
        ["funds[" + idx + "].calc_method"]: data.calc_method || "C",
      };
      this.setData(updates);
    }
  },

  toggleWatchlist(e) {
    var code = e.currentTarget.dataset.code;
    var isWatched = this.data.watchedCodes[code];
    var that = this;

    var promise = isWatched
      ? api.delete("/api/v1/watchlist/" + code)
      : api.post("/api/v1/watchlist", { fund_code: code });

    promise.then(function() {
      var watchedCodes = Object.assign({}, that.data.watchedCodes);
      if (isWatched) {
        delete watchedCodes[code];
        if (that.data.activeTab === "watchlist") {
          var funds = that.data.funds.filter(function(f) { return f.code !== code; });
          that.setData({ funds: funds, watchedCodes: watchedCodes });
        } else {
          that.setData({ watchedCodes: watchedCodes, ["funds[" + that.data.funds.findIndex(function(f) { return f.code === code; }) + "].is_watched"]: false });
        }
        wx.showToast({ title: "已取消关注", icon: "success" });
      } else {
        watchedCodes[code] = true;
        that.setData({ watchedCodes: watchedCodes, ["funds[" + that.data.funds.findIndex(function(f) { return f.code === code; }) + "].is_watched"]: true });
        wx.showToast({ title: "已关注", icon: "success" });
      }
    }).catch(function() {
      wx.showToast({ title: "操作失败", icon: "none" });
    });
  },

  onSearchInput(e) {
    this.setData({ searchValue: e.detail.value });
  },

  onSearchConfirm() {
    this.setData({ page: 1, hasMore: true });
    this.loadFunds();
  },

  onSortChange(e) {
    var field = e.currentTarget.dataset.field;
    var dir = this.data.sortField === field
      ? (this.data.sortDirection === "asc" ? "desc" : "asc")
      : "desc";
    this.setData({ sortField: field, sortDirection: dir, page: 1, hasMore: true });
    this.loadFunds();
  },

  // 筛选函数
  onFilterCanSubscribeChange(e) {
    var value = e.currentTarget.dataset.value;
    // 如果点击已选中的，则取消选择
    if (this.data.filterCanSubscribe === value) {
      value = null;
    }
    this.setData({ filterCanSubscribe: value, page: 1, hasMore: true });
    this.updateActiveFilters();
    this.loadFunds();
  },

  onFilterPremiumLevelChange(e) {
    var value = e.currentTarget.dataset.value;
    if (this.data.filterPremiumLevel === value) {
      value = null;
    }
    this.setData({ filterPremiumLevel: value, page: 1, hasMore: true });
    this.updateActiveFilters();
    this.loadFunds();
  },

  onFilterArbitrageTypeChange(e) {
    // 点击按钮时切换下拉菜单显示状态
    this.setData({ showArbitrageOptions: !this.data.showArbitrageOptions });
  },

  onFilterArbitrageTypeSelect(e) {
    var value = e.currentTarget.dataset.value;
    // 如果点击已选中的，则取消选择
    if (this.data.filterArbitrageType === value) {
      value = null;
    }
    this.setData({
      filterArbitrageType: value,
      showArbitrageOptions: false,
      page: 1,
      hasMore: true
    });
    this.updateActiveFilters();
    this.loadFunds();
  },

  onFilterRegionChange(e) {
    var value = e.currentTarget.dataset.value;
    if (this.data.filterRegion === value) {
      value = null;
    }
    this.setData({ filterRegion: value, page: 1, hasMore: true });
    this.updateActiveFilters();
    this.loadFunds();
  },

  clearFilters() {
    this.setData({
      filterCanSubscribe: null,
      filterPremiumLevel: null,
      filterArbitrageType: null,
      filterRegion: null,
      page: 1,
      hasMore: true,
    });
    this.updateActiveFilters();
    this.loadFunds();
  },

  updateActiveFilters() {
    var activeFilters = [];
    if (this.data.filterCanSubscribe !== null) {
      activeFilters.push({ key: 'can_subscribe', label: this.data.filterCanSubscribe ? '可申购' : '暂停申购', type: 'can_subscribe' });
    }
    if (this.data.filterPremiumLevel) {
      var levelLabels = { high: '高溢价', normal: '正常', discount: '折价' };
      activeFilters.push({ key: 'premium_level', label: levelLabels[this.data.filterPremiumLevel], type: 'premium_level' });
    }
    if (this.data.filterArbitrageType) {
      activeFilters.push({ key: 'arbitrage_type', label: this.data.filterArbitrageType, type: 'arbitrage_type' });
    }
    if (this.data.filterRegion) {
      activeFilters.push({ key: 'region', label: this.data.filterRegion, type: 'region' });
    }
    this.setData({ activeFilters: activeFilters });
  },

  onDetailTap(e) {
    var code = e.currentTarget.dataset.code;
    wx.navigateTo({ url: "/pages/detail/detail?code=" + code });
  },
});
