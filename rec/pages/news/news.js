Page({
  data: {
    allNews: [], // 全部资讯数据
    filteredNews: [], // 分类后的数据
    currentCategory: 'all', // 当前选中分类（默认全部）
    loading: false, // 加载中状态
    hasMore: true, // 是否有更多数据
    page: 1, // 当前页码
    pageSize: 5, // 每页条数
    uiMode: 'points', // UI模式（points=列表，news=卡片）
    searchValue: '', // 搜索输入值
    // 分类中英文映射
    categoryMap: {
      all: '全部',
      tech: '科技',
      finance: '财经',
      sports: '体育',
      entertainment: '娱乐',
      policy: '政策'
    }
  },

  // ====================== UI交互相关 ======================
  // 切换UI模式（列表/卡片）
  toggleUIMode() {
    this.setData({
      uiMode: this.data.uiMode === 'points' ? 'news' : 'points'
    });
    // 切换后滚动到顶部
    wx.pageScrollTo({
      scrollTop: 0,
      duration: 300
    });
  },
  // 搜索输入变化
  onSearchInput(e) {
    this.setData({ searchValue: e.detail.value.trim() });
  },
  // 执行搜索（可扩展）
  doSearch() {
    const { searchValue, allNews } = this.data;
    if (!searchValue) {
      this.setData({ filteredNews: this.filterNewsByCategory(allNews, this.data.currentCategory) });
      return;
    }
    // 关键词搜索（标题/描述匹配）
    const filtered = allNews.filter(item => 
      item.title.includes(searchValue) || item.desc.includes(searchValue)
    );
    this.setData({ filteredNews: filtered });
  },

  // ====================== 数据加载相关 ======================
  // 加载资讯数据（支持分页）
  loadNewsData(isLoadMore = false) {
    if (this.data.loading) return; // 防止重复加载
    this.setData({ loading: true });

    // 模拟API请求延迟（实际项目替换为真实接口）
    setTimeout(() => {
      // 模拟资讯数据（含政策分类）
      const newsData = [
        {
          id: 1,
          title: "人工智能技术取得重大突破，新型模型性能提升300%",
          image: "https://picsum.photos/600/400?random=1",
          source: "科技日报",
          time: "2小时前",
          category: "tech",
          views: Math.floor(Math.random() * 10000) + 1000,
          desc: "该新型AI模型在多模态任务中表现优异，图像识别、自然语言处理效率较传统模型提升3倍，将加速产业智能化落地。"
        },
        {
          id: 2,
          title: "央行发布最新金融政策，市场反应积极",
          image: "https://picsum.photos/600/400?random=2",
          source: "财经时报",
          time: "5小时前",
          category: "finance",
          views: Math.floor(Math.random() * 10000) + 1000,
          desc: "政策聚焦小微企业融资支持，下调部分贷款利率，今日A股金融板块涨幅超2%，市场信心持续回升。"
        },
        {
          id: 3,
          title: "国家篮球队公布新一期集训名单，多位新秀入选",
          image: "https://picsum.photos/600/400?random=3",
          source: "体育周报",
          time: "昨天",
          category: "sports",
          views: Math.floor(Math.random() * 10000) + 1000,
          desc: "本次集训名单包含5名00后新秀，将备战下月的国际友谊赛，教练组表示将重点培养年轻球员的大赛经验。"
        },
        {
          id: 4,
          title: "年度电影节获奖名单揭晓，多部国产影片斩获大奖",
          image: "https://picsum.photos/600/400?random=4",
          source: "娱乐前线",
          time: "3天前",
          category: "entertainment",
          views: Math.floor(Math.random() * 10000) + 1000,
          desc: "国产影片《时光里的我们》获最佳影片奖，导演张艺谋获终身成就奖，国产电影在叙事与美学上获国际认可。"
        },
        {
          id: 5,
          title: "2023年报废车回收政策解读（补充政策数据）",
          image: "https://picsum.photos/600/400?random=6",
          source: "政策法规网",
          time: "1天前",
          category: "policy",
          views: 2356,
          desc: "国家最新出台的报废车回收政策将于2024年1月正式实施，回收流程进一步规范，车主可享受更多补贴。"
        }
      ];

      let allNews = this.data.allNews;
      let newData = [];

      if (!isLoadMore) {
        // 首次加载/刷新
        allNews = newsData;
        newData = newsData;
        this.setData({ page: 1 });
      } else {
        // 加载更多（避免ID重复，叠加页码偏移）
        const moreData = JSON.parse(JSON.stringify(newsData)).map(item => {
          item.id = item.id + this.data.page * 10;
          return item;
        });
        allNews = [...allNews, ...moreData];
        newData = moreData;
      }

      // 分类过滤 + 搜索过滤
      let filteredNews = this.filterNewsByCategory(allNews, this.data.currentCategory);
      if (this.data.searchValue) {
        filteredNews = filteredNews.filter(item => 
          item.title.includes(this.data.searchValue) || item.desc.includes(this.data.searchValue)
        );
      }

      // 控制分页（模拟最多5页数据）
      const hasMore = this.data.page < 5;

      this.setData({
        allNews,
        filteredNews: isLoadMore ? [...this.data.filteredNews, ...newData] : filteredNews,
        loading: false,
        hasMore,
        page: isLoadMore ? this.data.page + 1 : 1
      });
    }, 1000); // 模拟1秒请求延迟
  },

  // 按分类过滤资讯
  filterNewsByCategory(newsList, category) {
    return category === 'all' ? newsList : newsList.filter(item => item.category === category);
  },

  // 切换分类
  switchCategory(e) {
    const category = e.currentTarget.dataset.category;
    if (this.data.currentCategory === category) return;
    // 更新分类并过滤数据
    this.setData({
      currentCategory: category,
      filteredNews: this.filterNewsByCategory(this.data.allNews, category)
    });
    // 滚动到顶部
    wx.pageScrollTo({ scrollTop: 0, duration: 300 });
  },

  // ====================== 页面跳转 ======================
  // 跳转到资讯详情页
  goToDetail(e) {
    const { id, category } = e.currentTarget.dataset;
    wx.navigateTo({
      url: `/pages/newsdetail/newsdetail?newsId=${id}&category=${category || this.data.currentCategory}`,
      fail: () => wx.showToast({ title: '跳转详情失败', icon: 'none' })
    });
  },

  // ====================== 页面生命周期 ======================
  onLoad() {
    // 首次加载数据
    this.loadNewsData(false);
  },
  // 下拉刷新
  onPullDownRefresh() {
    this.loadNewsData(false);
    wx.stopPullDownRefresh(); // 停止刷新动画
  },
  // 上拉加载更多
  onReachBottom() {
    if (this.data.hasMore && !this.data.loading) {
      this.loadNewsData(true);
    }
  },
  // 页面显示时执行搜索（如从其他页面返回）
  onShow() {
    if (this.data.searchValue) {
      this.doSearch();
    }
  }
})