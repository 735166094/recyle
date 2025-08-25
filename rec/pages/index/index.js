import api from '../../config/settings'
Page({
  data: {
    inputValue: '', // 搜索框输入值
    // 轮播图数据（默认+接口覆盖）
    bannerList: [{
      id: 1,
      image: '/static/img/lanyue.png',
      title: '报废车回收服务升级',
      desc: '评估价提升15%，回收流程更便捷'
    }],
    notice: '奇奇回收新版本上线了~',
    // 车辆评估数据
    evaluateList: {
      materials: ["铝车身", "铁车身"], // 材质列表
      materialPrices: [4500, 3500], // 对应单价（元/吨）
      selectedIndex: 0, // 默认选中铝车身
      weight: '', // 整车质量（吨）
      showResult: false, // 是否显示结果
      resultPrice: 0 // 计算结果
    },
    formattedResultPrice: '0.00', // 格式化后价格
    // 政策/资讯列表数据
    noticeList: [{
      titles: "最新政策",
      cards: [{
          id: "1",
          imgUrl: "/static/img/colorful.jpg",
          title: "2023年报废车回收政策解读",
          date: "2023-07-15",
          views: "1,248",
          desc: "国家最新出台的报废车回收政策将于2024年1月正式实施，回收流程进一步规范..."
        },
        {
          id: "11",
          imgUrl: "/static/img/kuxiaomis.jpg",
          title: "报废车回收行业迎来黄金发展期",
          date: "2023-07-05",
          views: "1,429",
          desc: "随着汽车保有量持续增长，报废车回收行业迎来发展机遇..."
        }
      ]
    }]
  },

  // ====================== 搜索框相关事件 ======================
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
  // 搜索确认（可扩展搜索逻辑）
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

  // ====================== 车辆评估相关事件 ======================
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
      const fixedWeight = parseFloat(weight.toFixed(4)); // 保留4位小数
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
    const result = Math.round(materialPrice * weight * 0.7 * 100) / 100 / 1000; // 转换为万元单位
    const formattedPrice = result.toFixed(2); // 保留2位小数
    // 更新结果
    this.setData({
      'evaluateList.showResult': true,
      'evaluateList.resultPrice': result,
      formattedResultPrice: formattedPrice
    }, () => {
      console.log('计算结果：', result, '格式化价格：', formattedPrice);
    });
  },

  // ====================== 页面跳转相关事件 ======================
  // 跳转到报废车回收页
  goToRecyleCarPage() {
    wx.navigateTo({
      url: '/pages/recycle/recycle',
      fail: () => wx.showToast({
        title: '跳转失败',
        icon: 'none'
      })
    })
  },
  // 跳转到积分商城（tab页）
  goToShopPage() {
    wx.switchTab({
      url: '/pages/mall/mall',
      fail: () => wx.showToast({
        title: '商城入口异常',
        icon: 'none'
      })
    })
  },
  // 跳转到政策资讯列表（tab页）
  goToPolicyPage() {
    wx.switchTab({
      url: '/pages/news/news',
      fail: () => wx.showToast({
        title: '资讯入口异常',
        icon: 'none'
      })
    })
  },
  // 跳转到我的积分页
  goToPointPage() {
    wx.navigateTo({
      url: '/pages/points/points',
      fail: () => wx.showToast({
        title: '跳转失败',
        icon: 'none'
      })
    })
  },
  // 跳转到回收详情页
  gotoRecyleInfo() {
    wx.navigateTo({
      url: '/pages/recycleInfo/recycleInfo',
      fail: () => wx.showToast({
        title: '跳转失败',
        icon: 'none'
      })
    })
  },
  // 政策卡片点击（跳详情页）
  onCardTap(e) {
    const {
      id,
      category
    } = e.currentTarget.dataset;
    // 查找当前点击的政策卡片数据
    let targetCard = null;
    this.data.noticeList.forEach(notice => {
      const card = notice.cards.find(item => item.id === id);
      if (card) targetCard = card;
    });
    if (!targetCard) {
      wx.showToast({
        title: '数据异常',
        icon: 'none'
      });
      return;
    }
    // 跳转到资讯详情页（携带政策ID和分类）
    wx.navigateTo({
      url: `/pages/newsdetail/newsdetail?newsId=${id}&category=${category}`,
      fail: () => wx.showToast({
        title: '跳转详情失败',
        icon: 'none'
      })
    });
  },
  // 阅读全文点击（阻止冒泡，避免重复触发卡片点击）
  onReadMore(e) {
    e.stopPropagation(); // 阻止事件冒泡到卡片
    this.onCardTap(e); // 复用卡片点击逻辑
  },

  // ====================== 页面生命周期 ======================
  onLoad() {
    // 加载轮播图和公告接口数据
    wx.request({
      url: api.banner,
      method: 'GET',
      success: (res) => {
        if (res.data.code === 200) {
          // 格式化接口返回的轮播图数据
          const bannerList = res.data.banner.map(item => ({
            id: item.id,
            image: item.img,
            title: item.title,
            desc: item.desc
          }));
          const notice = res.data.notice.title;
          this.setData({
            bannerList,
            notice
          });
        }
      },
      fail: () => {
        wx.showToast({
          title: '轮播图加载失败',
          icon: 'none'
        });
      }
    })
  }
})