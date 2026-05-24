Component({
  properties: {
    fund: Object,
  },

  data: {
    price: "--",
    change: "--",
    changeClass: "",
    premium: "--",
    premiumColor: "#999",
    venue: "",
  },

  observers: {
    fund(val) {
      if (!val) return;
      const price = val.market_price ? val.market_price.toFixed(3) : "--";
      const change = val.change_pct != null ? val.change_pct.toFixed(2) + "%" : "--";
      const changeClass = val.change_pct > 0 ? "text-green" : val.change_pct < 0 ? "text-red" : "";
      const prem = val.premium || {};
      const premium = prem.premium_rate != null ? prem.premium_rate.toFixed(2) + "%" : "--";
      let premiumColor = "#999";
      const pr = prem.premium_rate;
      if (pr > 3) premiumColor = "#ff4d4f";
      else if (pr > 0) premiumColor = "#fa8c16";
      else if (pr > -3) premiumColor = "#1890ff";
      else premiumColor = "#00b578";

      this.setData({ price, change, changeClass, premium, premiumColor, venue: val.trading_venue || "" });
    },
  },

  methods: {
    onTap() {
      const code = this.data.fund ? this.data.fund.code : "";
      this.triggerEvent("tap", { code: code });
    },
  },
});
