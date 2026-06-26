import api from '../../../config/settings'
Page({
  data: {
    inputValue: '', // 搜索框输入值
    searchValue: '', // 搜索输入值
    allNews: [], // 全部资讯数据
    filteredNews: [], // 分类后的数据
    currentCategory: 'all', // 当前选中分类（默认全部）
    loading: false, // 加载中状态
    hasMore: true, // 是否有更多数据
    page: 1, // 当前页码
    pageSize: 10, // 每页条数
    categories: [], // 存储分类数据
    uiMode: 'points', // UI模式（points=卡片，news=列表）
    // 分类中英文映射
    categoryMap: {
      all: '全部',
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
    this.setData({
      searchValue: e.detail.value.trim()
    });
  },

  // 执行搜索
  doSearch() {
    const {
      searchValue,
      allNews
    } = this.data;
    if (!searchValue) {
      this.setData({
        filteredNews: this.filterNewsByCategory(allNews, this.data.currentCategory)
      });
      return;
    }
    // 关键词搜索（标题/描述匹配）
    const filtered = allNews.filter(item =>
      item.title.includes(searchValue) || item.desc.includes(searchValue)
    );
    this.setData({
      filteredNews: filtered
    });
  },

  // 清空搜索
  clearSearch() {
    this.setData({
      searchValue: '',
      filteredNews: this.filterNewsByCategory(this.data.allNews, this.data.currentCategory)
    });
  },

  // 回车搜索
  onSearchConfirm(e) {
    this.doSearch();
  },

  // ====================== 数据加载相关 ======================
  // 加载分类数据
  loadCategories() {
    wx.request({
      url: api.newsCategories,
      method: 'GET',
      success: (res) => {
        if (res.statusCode === 200 && res.data) {
          const categoryMap = {
            'all': '全部'
          };
          const categories = res.data.results;

          // 构建分类映射
          categories.forEach(category => {
            categoryMap[category.EngName] = category.name;
          });

          this.setData({
            categories,
            categoryMap
          });
        }
      },
      fail: (err) => {
        console.error('获取分类失败：', err);
        wx.showToast({
          title: '获取分类失败',
          icon: 'none'
        });
      }
    });
  },

  // 加载资讯数据（支持分页）
  loadNewsData(isLoadMore = false, isSearch = false) {
    if (this.data.loading) return; // 防止重复加载

    this.setData({
      loading: true
    });

    // 构建请求参数
    let params = {
      page: this.data.page,
      page_size: this.data.pageSize
    };

    // 添加分类过滤
    if (this.data.currentCategory !== 'all') {
      params.category = this.data.currentCategory;
    }

    // 添加搜索关键词
    if (isSearch && this.data.searchValue) {
      params.search = this.data.searchValue;
    }

    wx.request({
      url: api.news,
      method: 'GET',
      data: params,
      success: (res) => {
        if (res.statusCode === 200 && res.data) {
          const newsData = res.data.results.map(item => ({
            id: item.id,
            title: item.title,
            image: item.image || item.image_url,
            source: item.category.name,
            time: item.publish_date,
            category: item.category ? item.category.EngName : null,
            views: item.view_count,
            desc: item.content.length > 100 ? item.content.substring(0, 100) + '...' : item.content
          }));

          let allNews = this.data.allNews;
          let newData = [];

          if (!isLoadMore) {
            // 首次加载/刷新
            allNews = newsData;
            newData = newsData;
            this.setData({
              page: 1
            });
          } else {
            // 加载更多
            allNews = [...allNews, ...newsData];
            newData = newsData;
          }

          // 控制分页
          const hasMore = res.data.next !== null;

          this.setData({
            allNews,
            filteredNews: isLoadMore ? [...this.data.filteredNews, ...newData] : newsData,
            loading: false,
            hasMore,
            page: isLoadMore ? this.data.page + 1 : 1
          });
        }
      },
      fail: (err) => {
        console.error('获取新闻失败:', err);
        this.setData({
          loading: false
        });
        wx.showToast({
          title: '加载失败',
          icon: 'none'
        });
      }
    });
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
      filteredNews: this.filterNewsByCategory(this.data.allNews, category),
      page: 1,
    });
    // 滚动到顶部
    wx.pageScrollTo({
      scrollTop: 0,
      duration: 300
    });
  },

  // ====================== 页面跳转 ======================
  // 跳转到资讯详情页
  goToDetail(e) {
    const {
      id,
      category
    } = e.currentTarget.dataset;
    wx.navigateTo({
      url: `/pages/news/detail/detail?newsId=${id}&category=${category || this.data.currentCategory}`,
      fail: () => wx.showToast({
        title: '跳转详情失败',
        icon: 'none'
      })
    });
  },

  // ====================== 页面生命周期 ======================
  onLoad() {
    // 首次加载数据
    this.loadCategories();
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
    // 从全局数据或本地存储获取目标分类
    const targetCategory = getApp().globalData.targetCategory || wx.getStorageSync('targetCategory');

    if (targetCategory) {
      // 清除存储，避免下次进入还生效
      getApp().globalData.targetCategory = null;
      wx.removeStorageSync('targetCategory');

      // 切换到目标分类
      if (this.data.currentCategory !== targetCategory) {
        this.setData({
          currentCategory: targetCategory,
          filteredNews: this.filterNewsByCategory(this.data.allNews, targetCategory),
          page: 1,
        });

        // 滚动到顶部
        wx.pageScrollTo({
          scrollTop: 0,
          duration: 300
        });
      }
    }

    if (this.data.searchValue) {
      this.doSearch();
    }
  }
})