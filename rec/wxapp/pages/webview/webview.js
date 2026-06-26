Page({
  data: {
    webUrl: '',
    loading: true,
    error: false,
    errorMessage: '网页加载失败，请稍后再试'
  },

  onLoad(options) {
    // 解析传入的URL参数
    if (options.url) {
      try {
        const decodedUrl = decodeURIComponent(options.url);
        // 再次验证URL有效性（二次校验，防止恶意参数）
        if (this.isValidUrl(decodedUrl)) {
          this.setData({
            webUrl: decodedUrl
          });
        } else {
          this.setData({
            error: true,
            errorMessage: '无效的网址',
            loading: false
          });
        }
      } catch (e) {
        this.setData({
          error: true,
          errorMessage: '网址解析失败',
          loading: false
        });
        console.error('URL解码错误:', e);
      }
    } else {
      this.setData({
        error: true,
        errorMessage: '未指定网址',
        loading: false
      });
    }
  },

  // 验证URL有效性（复用逻辑）
  isValidUrl(url) {
    const urlReg = /^(https?:\/\/)?([\da-z.-]+)\.([a-z.]{2,6})([\/\w.-]*)*\/?$/i;
    return urlReg.test(url);
  },

  // 网页加载完成
  onWebLoad() {
    this.setData({
      loading: false,
      error: false
    });
  },

  // 网页加载错误
  onWebError(e) {
    this.setData({
      loading: false,
      error: true,
      errorMessage: `加载失败: ${e.detail.errMsg}`
    });
    console.error('网页加载错误:', e.detail.errMsg);
  },

  // 重新加载页面
  reloadPage() {
    this.setData({
      loading: true,
      error: false
    });
    // 重新加载当前页面（刷新webview）
    wx.redirectTo({
      url: `/pages/webview/webview?url=${encodeURIComponent(this.data.webUrl)}`
    });
  },

  // 支持返回上一页（增强导航体验）
  onNavigateBack() {
    wx.navigateBack();
  }
});