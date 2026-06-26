// pages/ocr/settings/agreement/agreement.js
Page({
  data: {
    type: 'agreement',
    pageTitle: '用户协议'
  },

  onLoad(options) {
    const { type = 'agreement' } = options;
    let pageTitle = '用户协议';
    
    if (type === 'privacy') {
      pageTitle = '隐私政策';
    }

    this.setData({
      type,
      pageTitle
    });

    // 设置导航栏标题
    wx.setNavigationBarTitle({
      title: pageTitle
    });
  },

  navBack() {
    wx.navigateBack();
  }
});