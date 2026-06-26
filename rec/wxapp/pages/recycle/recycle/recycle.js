Page({
  data: {
    currentTab: 0,
    indicatorLeft: 0,
    indicatorWidth: 0,
    defaultIndicatorWidth: 100,
    navItems: [],
    // 新增导航项数量配置（与实际WXML中的数量保持一致）
    navItemCount: 5 // 假设实际有5个导航项（0-4索引）
  },

  onReady() {
    // 先检查导航容器是否存在，再执行查询
    this.checkNavContainerExists(() => {
      this.queryNavItems(this.initIndicatorPosition);
    });
  },

  // 检查导航容器是否存在
  checkNavContainerExists(callback) {
    const query = wx.createSelectorQuery().in(this);
    query.select('.nav-items').boundingClientRect();
    query.exec((res) => {
      if (res && res[0]) {
        // 容器存在，继续查询子项
        callback();
      } else {
        console.error('导航容器.nav-items不存在，请检查WXML结构');
        // 直接使用默认配置初始化
        this.initWithDefaultConfig();
      }
    });
  },

  // 封装导航项查询逻辑，增强重试机制
  queryNavItems(callback) {
    const query = wx.createSelectorQuery().in(this);
    // 选择器兼容处理：先尝试直接子元素，再尝试后代元素
    query.selectAll('.nav-items > .nav-item, .nav-items .nav-item').boundingClientRect();
    query.exec((res) => {
      if (res && res[0] && res[0].length > 0) {
        this.setData({
          navItems: res[0]
        });
        callback && callback();
      } else {
        console.warn(`导航项查询失败（当前尝试${this.queryRetryCount || 0}/8次），150ms后重试`);
        // 增加重试次数到8次，延长间隔到150ms
        if (this.queryRetryCount === undefined) this.queryRetryCount = 0;
        if (this.queryRetryCount < 8) {
          this.queryRetryCount++;
          setTimeout(() => this.queryNavItems(callback), 150);
        } else {
          console.error('超过最大重试次数，使用预设配置');
          // 手动生成模拟的导航项数据（根据实际数量）
          this.generateMockNavItems();
          callback && callback();
        }
      }
    });
  },

  // 生成模拟的导航项数据（当查询完全失败时）
  generateMockNavItems() {
    const mockItems = [];
    const {
      navItemCount,
      defaultIndicatorWidth
    } = this.data;
    // 平均分配宽度，模拟实际布局
    for (let i = 0; i < navItemCount; i++) {
      mockItems.push({
        left: 10 + i * (defaultIndicatorWidth + 30), // 模拟左边距
        width: defaultIndicatorWidth // 使用默认宽度
      });
    }
    this.setData({
      navItems: mockItems
    });
  },

  // 初始化默认配置
  initWithDefaultConfig() {
    this.generateMockNavItems();
    this.initIndicatorPosition();
  },

  // 初始化导航指示器位置
  initIndicatorPosition() {
    const {
      navItems
    } = this.data;
    if (navItems.length > 0) {
      this.setData({
        indicatorWidth: navItems[0].width,
        indicatorLeft: navItems[0].left - 10
      });
    } else {
      console.warn('使用最终默认值初始化');
      this.setData({
        indicatorWidth: this.data.defaultIndicatorWidth,
        indicatorLeft: 10
      });
    }
  },

  // 切换导航标签
  switchTab(e) {
    const tab = Number(e.currentTarget.dataset.tab);
    if (this.data.currentTab === tab) return;

    const {
      navItems,
      navItemCount
    } = this.data;

    // 先检查tab是否在有效范围内
    if (tab < 0 || tab >= navItemCount) {
      console.error(`tab=${tab}超出有效范围（0-${navItemCount-1}）`);
      return;
    }

    if (navItems.length > tab) {
      const targetItem = navItems[tab];
      this.setData({
        currentTab: tab,
        indicatorLeft: targetItem.left - 10,
        indicatorWidth: targetItem.width
      });
    } else {
      // 基于预设数量计算更精准的默认位置
      console.warn(`未找到tab=${tab}的导航项，使用预设位置`);
      const {
        defaultIndicatorWidth
      } = this.data;
      this.setData({
        currentTab: tab,
        indicatorWidth: defaultIndicatorWidth,
        indicatorLeft: 10 + tab * (defaultIndicatorWidth + 30) // 更精准的计算
      });
    }

    wx.pageScrollTo({
      scrollTop: 0,
      duration: 300
    });
  },

  onBookNow() {
    wx.navigateTo({
      url: '/pages/recycle/submitinfo/submitinfo',
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

  onCallNow() {
    wx.makePhoneCall({
      phoneNumber: '18656208787',
      success: () => console.log('拨打电话成功'),
      fail: () => console.log('拨打电话失败')
    });
  },
  onCallNow2() {
    wx.makePhoneCall({
      phoneNumber: '13665530519',
      success: () => console.log('拨打电话成功'),
      fail: () => console.log('拨打电话失败')
    });
  },
  onCallNow3() {
    wx.makePhoneCall({
      phoneNumber: '13695675280',
      success: () => console.log('拨打电话成功'),
      fail: () => console.log('拨打电话失败')
    });
  }
});