Component({
  properties: {
    rate: Number,
  },

  data: {
    color: "#999",
    bgColor: "#f0f0f0",
  },

  observers: {
    rate(val) {
      let color, bgColor;
      if (val == null) {
        color = "#999";
        bgColor = "#f0f0f0";
      } else if (val > 3) {
        color = "#ff4d4f";
        bgColor = "#fff1f0";
      } else if (val > 0) {
        color = "#fa8c16";
        bgColor = "#fff7e6";
      } else if (val > -3) {
        color = "#1890ff";
        bgColor = "#e6f7ff";
      } else {
        color = "#00b578";
        bgColor = "#f6ffed";
      }
      this.setData({ color, bgColor });
    },
  },
});
