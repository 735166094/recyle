import api from '../../config/settings'
Page({
  data: {
    inputValue: '',
    bannerList: [],
    evaluateList: {
      materials: ["铝车身", "铁车身"],
      materialPrices: [4500, 3500],
      selectedIndex: 0,
      weight: '',
      showResult: false,
      resultPrice: 0
    },
    formattedResultPrice: '0.00',
    newsdata: [{
      types: "最新政策",
      category: "policy",
      cards: []
    }],
    currentNewsPage: 1,
    hasMoreNews: true,
    loadingNews: false,
    showInHomeCategoryId: null,  

  },

  onLoad() {
    // 页面加载时的生命周期函数
    this.getBanners();
    this.getHomeNewsCategory();

  },

  // 输入框内容变化
  onInput(e) {
    this.setData({
      inputValue: e.detail.value.trim()
    });
  },
  // 清空输入框
  clearInput() {
    this.setData({
      inputValue: ''
    });
  },
  // 搜索确认
  onSearch() {
    const {
      inputValue
    } = this.data;
    if (!inputValue) {
      wx.showToast({
        title: '请输入搜索内容',
        icon: 'none',
        duration: 1500
      });
      return;
    }
    // 此处可添加搜索接口请求逻辑（如搜索车辆品牌/商品）
    wx.showToast({
      title: `搜索关键词：${inputValue}`,
      icon: 'none',
      duration: 1500
    });
  },


  // 切换车辆材质
  onMaterialChange(e) {
    this.setData({
      'evaluateList.selectedIndex': e.detail.value
    });
  },

  // 输入整车质量（限制4位小数+数字校验）
  onWeightInput(e) {
    const inputValue = e.detail.value.trim();
    if (inputValue === '') {
      this.setData({
        'evaluateList.weight': ''
      });
      return;
    }
    const weight = parseFloat(inputValue);
    if (!isNaN(weight)) {
      const fixedWeight = parseFloat(weight.toFixed(4)); // 保留位数
      this.setData({
        'evaluateList.weight': fixedWeight
      });
    } else {
      wx.showToast({
        title: "请输入有效的数字",
        icon: "none",
        duration: 1500
      });
      this.setData({
        'evaluateList.weight': ''
      });
    }
  },

  // 计算评估价格（核心逻辑）
  calculatePrice() {
    const {
      materialPrices,
      selectedIndex,
      weight
    } = this.data.evaluateList;
    // 校验重量为空
    if (weight === '' || weight === null || weight === undefined) {
      wx.showToast({
        title: "请输入整车质量",
        icon: "none",
        duration: 2000
      });
      this.setData({
        'evaluateList.showResult': false
      });
      return;
    }
    // 校验重量有效性（必须>0）
    if (typeof weight !== 'number' || weight <= 0) {
      wx.showToast({
        title: "请输入大于0的质量值",
        icon: "none",
        duration: 2000
      });
      this.setData({
        'evaluateList.showResult': false
      });
      return;
    }
    // 校验材质数据
    if (!materialPrices || !materialPrices.length || selectedIndex < 0 || selectedIndex >= materialPrices.length) {
      wx.showToast({
        title: "材质数据异常",
        icon: "none",
        duration: 2000
      });
      this.setData({
        'evaluateList.showResult': false
      });
      return;
    }
    // 核心计算（单价 * 重量 * 0.7（系数） → 格式化）
    const materialPrice = materialPrices[selectedIndex];
    const result = Math.round(materialPrice * weight * 0.56 * 100) / 100 / 1000; // 转换为万元单位
    const formattedPrice = result.toFixed(2); // 保留2位小数
    // 更新结果
    this.setData({
      'evaluateList.showResult': true,
      'evaluateList.resultPrice': result,
      formattedResultPrice: formattedPrice
    }, () => {
      // console.log('计算结果：', result, '格式化价格：', formattedPrice);
    });
  },


  // 跳转到报废车回收
  goToRecyleCarPage() {
    wx.navigateTo({
      url: '/pages/recycle/recycle/recycle',
      fail: () => wx.showToast({
        title: '跳转失败',
        icon: 'none'
      })
    })
  },
  // 跳转到积分商城
  goToShopPage() {
    wx.switchTab({
      url: '/pages/mall/index/index',
      fail: () => wx.showToast({
        title: '商城入口异常',
        icon: 'none'
      })
    })
  },
  // 跳转到政策资讯
  goToPolicyPage(e) {
    const category = e.currentTarget.dataset.category;

    // 存储分类信息到全局数据或本地存储
    getApp().globalData.targetCategory = category;
    // 或者使用本地存储
    wx.setStorageSync('targetCategory', category);

    wx.switchTab({
      url: '/pages/news/index/index',
      fail: (error) => {
        wx.showToast({
          title: '资讯入口异常',
          icon: 'none'
        })
        console.error('跳转失败:', error);
      }
    })
  },

  // 跳转到我的积分
  goToPointPage() {
    wx.navigateTo({
      url: '/pages/points/index/index',
      fail: () => wx.showToast({
        title: '积分中心页面开发中',
        icon: 'error'
      })
    })
  },

  // 跳转到回收详情
  gotoRecyleInfo() {
    wx.navigateTo({
      url: '/pages/recycle/submitinfo/submitinfo',
      fail: () => wx.showToast({
        title: '跳转失败',
        icon: 'none'
      })
    })
  },
  // 跳转到新闻详情
  goToDetail() {
    wx.navigateTo({
      url: '/pages/news/detail/detail',
      fail: () => wx.showToast({
        title: '跳转失败',
        icon: 'none'
      })
    })
  },
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

  // 获取轮播图
  getBanners() {
    // 开启加载状态
    this.setData({
      loading: true
    });

    wx.request({
      url: api.banner,
      method: 'GET',
      header: {
        'content-type': 'application/json'
      },
      // 用箭头函数避免this指向问题（无需再定义const that = this）
      success: (res) => {
        // 双重校验：1. HTTP状态码200 2. 后端业务状态码200（确保业务逻辑成功）
        if (res.statusCode === 200 && res.data?.code === 200) {
          // 后端轮播图数组在 res.data.data 中（关键路径修正）
          const backendBannerList = res.data.data || [];

          // 字段映射：严格对应后端返回的字段名（image、link等）
          const bannerList = backendBannerList.map(item => ({
            id: item.id,
            image: item.image,
            title: item.title,
            desc: item.desc,
            link: item.link || ''
          }));

          // 更新前端轮播图数据
          this.setData({
            bannerList
          });
          // console.log('轮播图数据加载成功', bannerList);

        } else {
          // 数据异常处理（如后端返回业务错误、数据为空）
          wx.showToast({
            title: '轮播图数据异常',
            icon: 'none',
            duration: 2000
          });
          console.error('轮播图数据异常：', res.data || '后端无返回数据');
        }
      },
      fail: (err) => {
        // 网络请求失败处理（如断网、接口不可达）
        wx.showToast({
          title: '网络请求失败',
          icon: 'none',
          duration: 2000
        });
        console.error('轮播图请求失败：', err);
      },
      complete: () => {
        // 无论成功/失败，都关闭加载状态
        this.setData({
          loading: false
        });
      }
    });
  },

  // 轮播图点击事件
  onBannerTap(e) {
    const linkUrl = e.currentTarget.dataset.link;
    // 只有link不为空时才跳转（避免无效跳转）
    if (linkUrl && linkUrl.trim()) {
      wx.navigateTo({
        url: `/pages/webview/webview?url=${encodeURIComponent(linkUrl)}`
      });
    }
  },

  // 下拉刷新事件
  onPullDownRefresh() {
    // 重置页码和加载状态
    this.setData({
      currentNewsPage: 1,
      hasMoreNews: true
    });

    // 重新获取新闻数据
    this.getNews(true).then(() => {
      wx.stopPullDownRefresh(); // 停止下拉刷新动画
    });
  },

  // 上拉加载更多事件
  onReachBottom() {
    // 如果正在加载或没有更多数据，则不再请求
    if (this.data.loadingNews || !this.data.hasMoreNews) {
      return;
    }

    // 加载更多新闻
    this.getNews(false);
  },

// 获取首页要显示的新闻分类
getHomeNewsCategory() {
  wx.request({
    url: api.newsCategories, // 假设新闻分类接口
    method: 'GET',
    success: (res) => {
      if (res.statusCode === 200 && res.data) {
        // 查找 show_in_home 为 true 的分类
        const homeCategory = res.data.results?.find(cat => cat.show_in_home === true) || 
                             res.data.find(cat => cat.show_in_home === true);
        
        if (homeCategory) {
          // 设置首页分类ID
          this.setData({
            showInHomeCategoryId: homeCategory.id
          });
          
          // 初始化newsdata数据结构
          const newsdata = [{
            types: homeCategory.name,
            category: homeCategory.EngName,
            cards: []
          }];
          
          this.setData({ newsdata }, () => {
            // 获取该分类的新闻
            this.getNews(true);
          });
        } else {
          // 没有设置首页显示的分类
          this.setData({
            newsdata: []
          });
        }
      }
    },
    fail: (err) => {
      console.error('获取新闻分类失败:', err);
    }
  });
},

// 获取新闻数据 
getNews(isRefresh) {
  // 如果没有获取到首页分类ID，直接返回
  if (!this.data.showInHomeCategoryId) {
    return Promise.resolve();
  }
  
  if (this.data.loadingNews) {
    return Promise.resolve();
  }

  this.setData({
    loadingNews: true
  });

  return new Promise((resolve, reject) => {
    wx.request({
      url: api.news,
      method: 'GET',
      data: {
        category: this.data.showInHomeCategoryId, // 使用动态获取的分类ID
        is_active: true,
        page: this.data.currentNewsPage,
        page_size: 10
      },
      header: {
        'content-type': 'application/json'
      },
      success: (res) => {
        if (res.statusCode === 200 && res.data) {
          const newsData = res.data;

          const newsList = newsData.results.map(item => ({
            id: item.id,
            title: item.title,
            image: item.image || item.image_url,
            source: item.source || "未知来源",
            time: item.publish_date || item.created_at.substring(0, 10),
            category: item.category?.EngName || "policy",
            views: item.view_count || 0,
            desc: item.content ? (item.content.length > 50 ? item.content.substring(0, 50) + '...' : item.content) : "暂无简介"
          }));

          // 更新新闻
          if (isRefresh) {
            // 刷新时替换数据
            this.setData({
              'newsdata[0].cards': newsList,
              currentNewsPage: 1,
              hasMoreNews: !!newsData.next
            });
          } else {
            // 加载更多时追加数据
            this.setData({
              'newsdata[0].cards': this.data.newsdata[0].cards.concat(newsList),
              currentNewsPage: this.data.currentNewsPage + 1,
              hasMoreNews: !!newsData.next
            });
          }

        } else {
          wx.showToast({
            title: '新闻数据加载失败',
            icon: 'none',
            duration: 2000
          });
          console.error('新闻数据异常：', res.data);
        }
        resolve();
      },
      fail: (err) => {
        wx.showToast({
          title: '新闻请求失败',
          icon: 'none',
          duration: 2000
        });
        console.error('新闻请求失败：', err);
        reject(err);
      },
      complete: () => {
        this.setData({
          loadingNews: false
        });
      }
    });
  });
},

});