// 环境配置：开发/生产环境自动切换
const isDev = wx.getAccountInfoSync().miniProgram.envVersion === 'develop';

// 开发环境（开发者工具）使用 localhost，扫码预览和生产环境使用 Cloudflare Tunnel
const BASE_URL = isDev
  ? 'http://localhost:8000'
  : 'https://qdii-api.14f124fc-0853-4536-9c61-b4a14dc005b5.trycloudflare.com';

App({
  globalData: {
    baseUrl: BASE_URL,
    openid: "default_user",
    wsConnected: false,
  },

  onLaunch() {
    // 初始化 openid（实际应通过微信登录获取）
    const openid = wx.getStorageSync("openid");
    if (openid) {
      this.globalData.openid = openid;
    } else {
      const newOpenid = "user_" + Date.now();
      wx.setStorageSync("openid", newOpenid);
      this.globalData.openid = newOpenid;
    }
    
    console.log(`[App] BASE_URL: ${BASE_URL}`);
    console.log(`[App] Environment: ${isDev ? 'develop' : 'release'}`);
  },
});
