Page({
  data: {
    currentTab: 0,
    indicatorLeft: 0,
    indicatorWidth: 0
  },

  onReady() {
    console.log('报废车回收页面渲染完成');
    // 延迟初始化，确保DOM完全渲染（解决首次加载active类未生效问题）
    setTimeout(() => {
      this.initIndicatorPosition();
    }, 100);
  },

  // 初始化导航指示器位置（改用索引定位）
  initIndicatorPosition() {
    const query = wx.createSelectorQuery().in(this);
    // 第一个导航项（tab=0）对应第1个子元素（CSS nth-child索引从1开始）
    query.select('.nav-items .nav-item:nth-child(1)').boundingClientRect();
    query.exec((res) => {
      if (res && res[0]) {
        this.setData({
          indicatorWidth: res[0].width,
          indicatorLeft: res[0].left - 10 // 减去左边距
        });
      } else {
        console.error('初始化时未找到导航项元素');
      }
    });
  },

  // 切换导航标签（改用索引定位）
  switchTab(e) {
    const tab = Number(e.currentTarget.dataset.tab);
    if (this.data.currentTab === tab) return;

    const query = wx.createSelectorQuery().in(this);
    // 导航项顺序与tab值一致（tab=0对应第1个，tab=1对应第2个...）
    query.select(`.nav-items .nav-item:nth-child(${tab + 1})`).boundingClientRect();
    
    query.exec((res) => {
      if (res && res[0]) {
        this.setData({
          currentTab: tab,
          indicatorLeft: res[0].left - 10,
          indicatorWidth: res[0].width
        });
      } else {
        console.error(`未找到 tab=${tab} 的导航项元素`);
        this.setData({ currentTab: tab });
      }
    });

    wx.pageScrollTo({
      scrollTop: 0,
      duration: 300
    });
  },

  // 其他方法保持不变...
  onBookNow() {
    wx.navigateTo({
      url: '/pages/recycleInfo/recycleInfo', 
      fail: (err) => {
        console.error('页面跳转失败', err);
        wx.showToast({
          title: '跳转失败，请重试',
          icon: 'none',
          duration: 2000
        });
      }
    });
  },

  onLearnMore() {
    wx.showToast({
      title: '更多信息开发中',
      icon: 'none',
      duration: 2000
    });
  },

  onGetPrice() {
    wx.navigateTo({
      url: '/pages/valuation/valuation'
    });
  },

  onCallNow() {
    wx.makePhoneCall({
      phoneNumber: '4001234567',
      success: () => console.log('拨打电话成功'),
      fail: () => console.log('拨打电话失败')
    });
  }
});