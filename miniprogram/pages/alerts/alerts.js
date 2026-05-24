const api = require("../../utils/api");

Page({
  data: {
    alerts: [],
    loading: false,
    showForm: false,
    formCode: "",
    formAbove: "",
    formBelow: "",
  },

  onLoad() {
    this.loadAlerts();
  },

  loadAlerts() {
    var that = this;
    this.setData({ loading: true });

    api.get("/api/v1/alerts")
      .then(function(res) {
        that.setData({ alerts: res.items || [] });
      })
      .catch(function(e) {
        console.error("Failed to load alerts:", e);
      })
      .finally(function() {
        that.setData({ loading: false });
      });
  },

  toggleForm() {
    this.setData({ showForm: !this.data.showForm });
  },

  onCodeInput(e) {
    this.setData({ formCode: e.detail.value });
  },

  onAboveInput(e) {
    this.setData({ formAbove: e.detail.value });
  },

  onBelowInput(e) {
    this.setData({ formBelow: e.detail.value });
  },

  submitAlert() {
    var that = this;
    var formCode = this.data.formCode;
    var formAbove = this.data.formAbove;
    var formBelow = this.data.formBelow;

    if (!formCode) {
      wx.showToast({ title: "请输入基金代码", icon: "none" });
      return;
    }

    var data = { fund_code: formCode };
    if (formAbove) data.threshold_above = parseFloat(formAbove);
    if (formBelow) data.threshold_below = parseFloat(formBelow);

    api.post("/api/v1/alerts", data)
      .then(function() {
        that.setData({ showForm: false, formCode: "", formAbove: "", formBelow: "" });
        that.loadAlerts();
        wx.showToast({ title: "添加成功", icon: "success" });
      })
      .catch(function() {
        wx.showToast({ title: "添加失败", icon: "none" });
      });
  },

  toggleActive(e) {
    var id = e.currentTarget.dataset.id;
    var alerts = this.data.alerts;
    var alert = null;
    for (var i = 0; i < alerts.length; i++) {
      if (alerts[i].id === id) {
        alert = alerts[i];
        break;
      }
    }
    if (alert) {
      var that = this;
      api.put("/api/v1/alerts/" + id, { is_active: !alert.is_active })
        .then(function() {
          that.loadAlerts();
        });
    }
  },

  deleteAlert(e) {
    var that = this;
    var id = e.currentTarget.dataset.id;
    api.delete("/api/v1/alerts/" + id)
      .then(function() {
        that.loadAlerts();
      })
      .catch(function() {
        wx.showToast({ title: "删除失败", icon: "none" });
      });
  },
});
