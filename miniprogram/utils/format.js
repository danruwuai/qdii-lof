function formatNumber(num, decimals = 2) {
  if (num === null || num === undefined) return "--";
  return Number(num).toFixed(decimals);
}

function formatPercent(num) {
  if (num === null || num === undefined) return "--";
  return formatNumber(num) + "%";
}

function formatPrice(num) {
  if (num === null || num === undefined) return "--";
  return formatNumber(num, 3);
}

function formatVolume(num) {
  if (num === null || num === undefined) return "--";
  if (num >= 1e8) return formatNumber(num / 1e8, 2) + "亿";
  if (num >= 1e4) return formatNumber(num / 1e4, 2) + "万";
  return formatNumber(num, 0);
}

function formatTime(dateStr) {
  if (!dateStr) return "--";
  const d = new Date(dateStr);
  const month = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  const hour = String(d.getHours()).padStart(2, "0");
  const min = String(d.getMinutes()).padStart(2, "0");
  return `${month}-${day} ${hour}:${min}`;
}

function premiumColor(rate) {
  if (rate === null || rate === undefined) return "#999";
  if (rate > 3) return "#ff4d4f";   // 高溢价 - 红色
  if (rate > 0) return "#fa8c16";   // 正溢价 - 橙色
  if (rate > -3) return "#1890ff";   // 折价 - 蓝色
  return "#00b578";                  // 深折价 - 绿色
}

module.exports = {
  formatNumber,
  formatPercent,
  formatPrice,
  formatVolume,
  formatTime,
  premiumColor,
};
