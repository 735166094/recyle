Page({
  data: {
    inputValue: '', // 搜索框输入值
    allActivities: [], // 全部活动数据
    filteredActivities: [], // 分类后的数据
    currentCategory: 'all', // 当前选中分类（默认全部）
    loading: false, // 加载中状态
    hasMore: true, // 是否有更多数据
    page: 1, // 当前页码
    pageSize: 5, // 每页条数
    uiMode: 'points', // UI模式（points=列表，activity=卡片）
    searchValue: '', // 搜索输入值
    // 分类中英文映射
    categoryMap: {
      all: '全部',
      online: '线上活动',
      offline: '线下活动',
      discount: '优惠活动',
      points: '积分活动',
      recycle: '回收活动'
    }
  },

  // ====================== UI交互相关 ======================
  // 切换UI模式（列表/卡片）
  toggleUIMode() {
    this.setData({
      uiMode: this.data.uiMode === 'points' ? 'activity' : 'points'
    });
    // 切换后滚动到顶部
    wx.pageScrollTo({
      scrollTop: 0,
      duration: 300
    });
  },
  // 搜索输入变化
  onSearchInput(e) {
    this.setData({
      searchValue: e.detail.value.trim()
    });
  },
  // 执行搜索（可扩展）
  doSearch() {
    const {
      searchValue,
      allActivities
    } = this.data;
    if (!searchValue) {
      this.setData({
        filteredActivities: this.filterActivitiesByCategory(allActivities, this.data.currentCategory)
      });
      return;
    }
    // 关键词搜索（标题/描述匹配）
    const filtered = allActivities.filter(item =>
      item.title.includes(searchValue) || item.desc.includes(searchValue)
    );
    this.setData({
      filteredActivities: filtered
    });
  },

  // ====================== 数据加载相关 ======================
  // 加载活动数据（支持分页）
  loadActivitiesData(isLoadMore = false) {
    if (this.data.loading) return; // 防止重复加载
    this.setData({
      loading: true
    });

    // 模拟API请求延迟（实际项目替换为真实接口）
    setTimeout(() => {
      // 模拟活动数据
      const activitiesData = [{
          id: 1,
          title: "绿色回收月活动，积分翻倍送好礼",
          image: "https://picsum.photos/600/400?random=10",
          organizer: "奇奇回收",
          time: "2024-01-15 至 2024-01-31",
          category: "recycle",
          participants: Math.floor(Math.random() * 5000) + 1000,
          status: "进行中",
          desc: "活动期间回收废旧物品可获得双倍积分，更有精美礼品等你来拿！"
        },
        {
          id: 2,
          title: "线上环保知识竞赛，赢取丰厚奖品",
          image: "https://picsum.photos/600/400?random=11",
          organizer: "环保协会",
          time: "2024-01-20 至 2024-01-25",
          category: "online",
          participants: Math.floor(Math.random() * 3000) + 500,
          status: "即将开始",
          desc: "参与环保知识问答，学习环保知识的同时还能获得精美奖品。"
        },
        {
          id: 3,
          title: "社区回收站开放日，现场体验回收流程",
          image: "https://picsum.photos/600/400?random=12",
          organizer: "社区服务中心",
          time: "2024-01-25 至 2024-01-25",
          category: "offline",
          participants: Math.floor(Math.random() * 200) + 50,
          status: "即将开始",
          desc: "现场参观回收站，了解回收流程，还有专业讲解员为您答疑解惑。"
        },
        {
          id: 4,
          title: "新用户专享优惠，首次回收立减10元",
          image: "https://picsum.photos/600/400?random=13",
          organizer: "奇奇回收",
          time: "2024-01-10 至 2024-02-10",
          category: "discount",
          participants: Math.floor(Math.random() * 1000) + 200,
          status: "进行中",
          desc: "新用户首次使用回收服务，立享10元优惠，让环保更实惠。"
        },
        {
          id: 5,
          title: "积分商城限时特惠，热门商品5折起",
          image: "https://picsum.photos/600/400?random=14",
          organizer: "积分商城",
          time: "2024-01-18 至 2024-01-24",
          category: "points",
          participants: Math.floor(Math.random() * 2000) + 800,
          status: "进行中",
          desc: "积分商城精选商品限时特惠，用积分兑换心仪好物，超值优惠不容错过。"
        },
        {
          id: 6,
          title: "环保达人挑战赛，展示你的环保创意",
          image: "https://picsum.photos/600/400?random=15",
          organizer: "环保基金会",
          time: "2024-02-01 至 2024-02-28",
          category: "online",
          participants: Math.floor(Math.random() * 1500) + 300,
          status: "即将开始",
          desc: "分享你的环保创意和行动，参与挑战赛，赢取环保达人称号和丰厚奖励。"
        },
        {
          id: 7,
          title: "校园回收宣传活动，环保从校园开始",
          image: "https://picsum.photos/600/400?random=16",
          organizer: "大学生环保联盟",
          time: "2024-01-22 至 2024-01-22",
          category: "offline",
          participants: Math.floor(Math.random() * 500) + 100,
          status: "即将开始",
          desc: "走进校园宣传环保理念，让更多年轻人了解回收的重要性。"
        },
        {
          id: 8,
          title: "会员专享福利，每月免费回收额度",
          image: "https://picsum.photos/600/400?random=17",
          organizer: "奇奇回收",
          time: "2024-01-01 至 2024-12-31",
          category: "discount",
          participants: Math.floor(Math.random() * 3000) + 1500,
          status: "进行中",
          desc: "会员用户每月可享受免费回收额度，让环保成为生活的一部分。"
        }
      ];

      let allActivities = this.data.allActivities;
      let newData = [];

      if (!isLoadMore) {
        // 首次加载/刷新
        allActivities = activitiesData;
        newData = activitiesData;
        this.setData({
          page: 1
        });
      } else {
        // 加载更多（避免ID重复，叠加页码偏移）
        const moreData = JSON.parse(JSON.stringify(activitiesData)).map(item => {
          item.id = item.id + this.data.page * 10;
          return item;
        });
        allActivities = [...allActivities, ...moreData];
        newData = moreData;
      }

      // 分类过滤 + 搜索过滤
      let filteredActivities = this.filterActivitiesByCategory(allActivities, this.data.currentCategory);
      if (this.data.searchValue) {
        filteredActivities = filteredActivities.filter(item =>
          item.title.includes(this.data.searchValue) || item.desc.includes(this.data.searchValue)
        );
      }

      // 控制分页（模拟最多5页数据）
      const hasMore = this.data.page < 5;

      this.setData({
        allActivities,
        filteredActivities: isLoadMore ? [...this.data.filteredActivities, ...newData] : filteredActivities,
        loading: false,
        hasMore,
        page: isLoadMore ? this.data.page + 1 : 1
      });
    }, 1000); // 模拟1秒请求延迟
  },

  // 按分类过滤活动
  filterActivitiesByCategory(activitiesList, category) {
    return category === 'all' ? activitiesList : activitiesList.filter(item => item.category === category);
  },

  // 切换分类
  switchCategory(e) {
    const category = e.currentTarget.dataset.category;
    if (this.data.currentCategory === category) return;
    // 更新分类并过滤数据
    this.setData({
      currentCategory: category,
      filteredActivities: this.filterActivitiesByCategory(this.data.allActivities, category)
    });
    // 滚动到顶部
    wx.pageScrollTo({
      scrollTop: 0,
      duration: 300
    });
  },

  // ====================== 页面跳转 ======================
  // 跳转到活动详情页
  goToDetail(e) {
    const {
      id,
      category
    } = e.currentTarget.dataset;
    wx.navigateTo({
      url: `/pages/activity/detail/detail?activityId=${id}&category=${category || this.data.currentCategory}`,
      fail: () => wx.showToast({
        title: '跳转详情失败',
        icon: 'none'
      })
    });
  },

  // ====================== 页面生命周期 ======================
  onLoad() {
    // 首次加载数据
    this.loadActivitiesData(false);
  },
  // 下拉刷新
  onPullDownRefresh() {
    this.loadActivitiesData(false);
    wx.stopPullDownRefresh(); // 停止刷新动画
  },
  // 上拉加载更多
  onReachBottom() {
    if (this.data.hasMore && !this.data.loading) {
      this.loadActivitiesData(true);
    }
  },
  // 页面显示时执行搜索（如从其他页面返回）
  onShow() {
    if (this.data.searchValue) {
      this.doSearch();
    }
  }
})
