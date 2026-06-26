Page({
  data: {
    showDetail: false, // 是否显示详情
    detailStyle: '', // 动画样式
    currentActivity: null, // 当前详情数据
    relatedActivities: [], // 相关活动
    activityId: null, // 当前活动ID
    category: null, // 当前分类
    allActivities: [], // 全部活动数据
    // 分类映射（中英文）
    categoryMap: {
      online: '线上活动',
      offline: '线下活动',
      discount: '优惠活动',
      points: '积分活动',
      recycle: '回收活动'
    }
  },

  // ====================== 动画相关 ======================
  // 初始化动画
  initAnimation() {
    this.animation = wx.createAnimation({
      duration: 500,
      timingFunction: 'ease-out',
      delay: 0,
      transformOrigin: '50% 50% 0'
    });
  },

  // 详情页弹跳动画
  showBounceAnimation() {
    // 初始位置：屏幕底部外
    this.animation.translateY('100%').step();
    this.setData({
      detailStyle: this.animation.export(),
      showDetail: true
    });

    // 执行弹跳逻辑
    setTimeout(() => {
      // 1. 弹到目标位置
      this.animation.translateY(0).step({
        duration: 300,
        timingFunction: 'ease-out'
      });
      // 2. 轻微弹回（模拟弹跳）
      this.animation.translateY(-30).step({
        duration: 100,
        timingFunction: 'ease-in'
      });
      // 3. 回到最终位置
      this.animation.translateY(0).step({
        duration: 100,
        timingFunction: 'ease-out'
      });

      this.setData({
        detailStyle: this.animation.export()
      });
    }, 50);
  },

  // 关闭详情页动画
  closeAnimation(callback) {
    this.animation.translateY('100%').step({
      duration: 300
    });
    this.setData({
      detailStyle: this.animation.export()
    });
    // 动画结束后执行回调（如返回上一页）
    setTimeout(() => {
      callback && callback();
    }, 300);
  },

  // ====================== 数据相关 ======================
  // 初始化所有活动数据
  initActivitiesData() {
    const allActivities = [
      // 回收活动
      {
        id: 1,
        title: "绿色回收月活动，积分翻倍送好礼",
        image: "https://picsum.photos/600/400?random=10",
        organizer: "奇奇回收",
        time: "2024-01-15 至 2024-01-31",
        category: "recycle",
        participants: 2500,
        status: "进行中",
        content: "活动期间，用户回收废旧物品可获得双倍积分奖励，更有精美礼品等你来拿！\n\n活动详情：\n1. 回收废旧手机、电脑等电子产品，积分翻倍\n2. 回收废旧衣物、书籍等生活用品，额外获得环保积分\n3. 累计回收金额满100元，即可获得精美环保礼品一份\n4. 活动期间每日前100名用户，额外获得神秘礼品\n\n参与方式：\n1. 打开奇奇回收小程序\n2. 选择回收物品类型\n3. 预约上门回收时间\n4. 完成回收后自动获得双倍积分\n\n注意事项：\n- 活动仅限新用户和活跃用户参与\n- 积分奖励将在回收完成后24小时内到账\n- 礼品数量有限，先到先得"
      }
    ];

    this.setData({
      allActivities
    }, () => {
      // 数据初始化完成后加载详情
      this.loadActivityDetail();
    });
  },

  // 加载当前活动详情
  loadActivityDetail() {
    const {
      activityId,
      allActivities,
      category
    } = this.data;
    // 查找当前活动
    const currentActivity = allActivities.find(item => item.id === activityId);
    if (!currentActivity) {
      wx.showToast({
        title: '详情数据异常',
        icon: 'none'
      });
      this.closeDetail();
      return;
    }
    // 查找相关活动（同分类、不同ID，取前3条）
    const relatedActivities = allActivities.filter(
      item => item.category === category && item.id !== activityId
    ).slice(0, 3);
    // 更新数据并执行动画
    this.setData({
      currentActivity,
      relatedActivities
    }, () => {
      this.showBounceAnimation();
    });
  },

  // ====================== 页面跳转/关闭 ======================
  // 跳转到相关活动
  navigateToRelated(e) {
    const activityId = e.currentTarget.dataset.id;
    // 关闭当前详情动画
    this.closeAnimation(() => {
      wx.redirectTo({
        url: `/pages/activity/detail/detail?activityId=${activityId}&category=${this.data.category}`
      });
    });
  },

  // 关闭详情页
  closeDetail() {
    this.closeAnimation(() => {
      wx.navigateBack();
    });
  },

  // ====================== 页面生命周期 ======================
  onLoad(options) {
    // 获取跳转参数
    const activityId = parseInt(options.activityId);
    const category = options.category || 'all';
    this.setData({
      activityId,
      category
    });
    // 初始化动画和数据
    this.initAnimation();
    this.initActivitiesData();
  },

  // 防止页面被下拉
  onPullDownRefresh() {
    wx.stopPullDownRefresh();
  }
})
