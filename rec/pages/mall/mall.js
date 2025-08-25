// pages/mall/mall.js
Page({

  /**
   * 页面的初始数据
   */
  data: {
    isCategoryPage: false, // 新增状态，控制显示首页还是分类页
    inputValue: '',
    // 初始默认数据（接口成功后会覆盖）
    activeList: [{
      id: 1,
      image: '/static/img/colorful.jpg',
      title: '全新福利活动',
      desc: '积分兑换商品，赶快行动'
    }],
    goodList: [{
        imgUrl: "/static/img/lanyue.png",
        type: "热销",
        title: "蓝悦 车载空气净化器 除甲醛",
        currency: "$",
        price: 4399
      },
      {
        imgUrl: "/static/img/colorful.jpg",
        type: "新品",
        title: "车享 全包围汽车脚垫 防水耐磨",
        currency: "$",
        price: 2199
      },
      {
        imgUrl: "/static/img/kuxiaomis.jpg",
        type: "特惠",
        title: "道狗 高清行车记录仪 夜视双录",
        currency: "$",
        price: 3599
      },
      {
        imgUrl: "/static/img/carlv.jpg",
        type: "热销",
        title: "云马 车载充电器 快充双USB",
        currency: "$",
        price: 599
      }
    ],
    // 用于防止快速点击导致的闪屏
    isAddingToCart: false,
    // 从shop.js合并的分类数据
    activeCategoryName: '',
    categories: [{
        id: 1,
        name: '机油养护',
        icon: '/static/icon/oil.png'
      },
      {
        id: 2,
        name: '维修配件',
        icon: '/static/icon/tools.png'
      },
      {
        id: 3,
        name: '汽车装饰',
        icon: '/static/icon/car.png'
      },
      {
        id: 4,
        name: '车载电器',
        icon: '/static/icon/fan.png'
      },
      {
        id: 5,
        name: '清洁用品',
        icon: '/static/icon/fan.png'
      },
      {
        id: 6,
        name: '应急工具',
        icon: '/static/icon/fan.png'
      },
      {
        id: 7,
        name: '汽车香水',
        icon: '/static/icon/fan.png'
      }
    ],
    activeCategoryId: 1,
    categoryGoods: {
      1: [{
          id: 101,
          imgUrl: "/static/img/kuxiaomis.jpg",
          title: "全合成机油 5W-30 4L装",
          currency: "$",
          price: 5999,
          sales: 128
        },
        {
          id: 102,
          imgUrl: "/static/img/colorful.jpg",
          title: "机油滤清器 适配多数车型",
          currency: "$",
          price: 899,
          sales: 356
        },
        {
          id: 103,
          imgUrl: "/static/img/lanyue.png",
          title: "发动机清洗剂 强效去污",
          currency: "$",
          price: 1299,
          sales: 98
        }
      ],
      2: [{
          id: 201,
          imgUrl: "/static/img/carlv.jpg",
          title: "空气滤清器 高效过滤",
          currency: "$",
          price: 1599,
          sales: 215
        },
        {
          id: 202,
          imgUrl: "/static/img/kuxiaomis.jpg",
          title: "刹车片 前两轮套装",
          currency: "$",
          price: 4599,
          sales: 106
        },
        {
          id: 203,
          imgUrl: "/static/img/kuxiaomis.jpg",
          title: "火花塞 4支装",
          currency: "$",
          price: 2399,
          sales: 78
        }
      ],
      3: [{
          id: 301,
          imgUrl: "/static/img/kuxiaomis.jpg",
          title: "汽车座套 四季通用",
          currency: "$",
          price: 3299,
          sales: 189
        },
        {
          id: 302,
          imgUrl: "/static/img/kuxiaomis.jpg",
          title: "方向盘套 真皮质感",
          currency: "$",
          price: 1299,
          sales: 245
        },
        {
          id: 303,
          imgUrl: "/static/img/kuxiaomis.jpg",
          title: "汽车脚垫 全包围",
          currency: "$",
          price: 2799,
          sales: 156
        }
      ],
      4: [{
          id: 401,
          imgUrl: "/static/img/kuxiaomis.jpg",
          title: "车载充电器 快充",
          currency: "$",
          price: 599,
          sales: 324
        },
        {
          id: 402,
          imgUrl: "/static/img/kuxiaomis.jpg",
          title: "行车记录仪 高清夜视",
          currency: "$",
          price: 3599,
          sales: 218
        },
        {
          id: 403,
          imgUrl: "/static/img/kuxiaomis.jpg",
          title: "车载蓝牙音箱",
          currency: "$",
          price: 1899,
          sales: 97
        }
      ],
      5: [{
          id: 501,
          imgUrl: "/static/img/kuxiaomis.jpg",
          title: "汽车玻璃水 6瓶装",
          currency: "$",
          price: 899,
          sales: 412
        },
        {
          id: 502,
          imgUrl: "/static/img/kuxiaomis.jpg",
          title: "内饰清洁剂 多功能",
          currency: "$",
          price: 1099,
          sales: 178
        },
        {
          id: 503,
          imgUrl: "/static/img/kuxiaomis.jpg",
          title: "洗车工具套装",
          currency: "$",
          price: 2199,
          sales: 89
        }
      ],
      6: [{
          id: 601,
          imgUrl: "/static/img/kuxiaomis.jpg",
          title: "车载急救包 标准版",
          currency: "$",
          price: 1599,
          sales: 132
        },
        {
          id: 602,
          imgUrl: "/static/img/kuxiaomis.jpg",
          title: "胎压监测器 无线",
          currency: "$",
          price: 2399,
          sales: 205
        },
        {
          id: 603,
          imgUrl: "/static/img/kuxiaomis.jpg",
          title: "汽车搭电线 应急启动",
          currency: "$",
          price: 1899,
          sales: 67
        }
      ],
      7: [{
          id: 701,
          imgUrl: "/static/img/kuxiaomis.jpg",
          title: "车载香水 持久淡香",
          currency: "$",
          price: 999,
          sales: 256
        },
        {
          id: 702,
          imgUrl: "/static/img/kuxiaomis.jpg",
          title: "香薰精油 3瓶装",
          currency: "$",
          price: 1499,
          sales: 123
        },
        {
          id: 703,
          imgUrl: "/static/img/kuxiaomis.jpg",
          title: "固体香膏 车载专用",
          currency: "$",
          price: 799,
          sales: 189
        }
      ]
    },
    cart: []
  },

  // 加入购物车功能
  addToCart(e) {
    // 清除上一次定时器
    if (this.data.clickTimer) {
      clearTimeout(this.data.clickTimer);
    }
    // 防止快速多次点击导致的闪烁
    if (this.data.isAddingToCart) return;

    this.setData({
      isAddingToCart: true
    });

    const goodId = e.currentTarget.dataset.id;
    let goods = null;

    // 查找商品信息（优化查找逻辑）
    if (!goods) {
      // 先在当前激活分类中查找，减少遍历范围
      const categoryGoods = this.data.categoryGoods[this.data.activeCategoryId] || [];
      goods = categoryGoods.find(item => item.id === goodId);
    }

    if (!goods) {
      // 再在热门商品中查找
      goods = this.data.goodList.find(item => item.id === goodId);
    }

    if (goods) {
      // 创建新的购物车数组，避免直接修改原数组
      const newCart = [...this.data.cart];
      const existingIndex = newCart.findIndex(item => item.id === goodId);

      if (existingIndex > -1) {
        // 只更新需要变化的商品数量，减少数据更新量
        newCart[existingIndex].quantity = (newCart[existingIndex].quantity || 1) + 1;
        this.setData({
          [`cart[${existingIndex}]`]: newCart[existingIndex]
        });
      } else {
        // 添加新商品到购物车
        newCart.push({
          ...goods,
          quantity: 1
        });
        this.setData({
          cart: newCart
        });
      }

      // 显示提示（使用无闪烁的提示方式）
      wx.showToast({
        title: '已加入购物车',
        icon: 'none', // 使用文字提示避免图标闪烁
        duration: 1000
      });

      // 异步保存到本地，避免阻塞UI
      setTimeout(() => {
        wx.setStorageSync('cart', newCart);
      }, 300);
    }

    // 延迟释放点击锁，避免快速点击
    setTimeout(() => {
      this.setData({
        isAddingToCart: false
      });
    }, 500);
  },

  /**
   * 生命周期函数--监听页面加载
   */
  onLoad(options) {
    // 初始化时设置默认分类名称
    const defaultCategory = this.data.categories.find(cat => cat.id === this.data.activeCategoryId);
    this.setData({
      activeCategoryName: defaultCategory ? defaultCategory.name : ''
    });
  },

  // 切换分类时更新名称
  switchCategory(e) {
    const categoryId = e.currentTarget.dataset.id;
    const category = this.data.categories.find(cat => cat.id === categoryId);

    this.setData({
      activeCategoryId: categoryId,
      activeCategoryName: category ? category.name : ''
    });
  },

  // 输入框事件
  onInput(e) {
    this.setData({
      inputValue: e.detail.value
    });
  },

  // 清除输入
  clearInput() {
    this.setData({
      inputValue: ''
    });
  },

  // 搜索事件
  onSearch() {
    if (this.data.inputValue.trim()) {
      wx.showToast({
        title: `搜索: ${this.data.inputValue}`,
        icon: 'none'
      });
    }
  },

  // 跳转到商品详情
  goToGoodDetail(e) {
    const goodId = e.currentTarget.dataset.id;
    wx.navigateTo({
      url: `/pages/goodDetail/goodDetail?id=${goodId}`
    });
  },

  // 切换到分类页面
  goToCategoryPage(e) {
    const categoryId = e.currentTarget.dataset.id || 1;
    const category = this.data.categories.find(cat => cat.id === categoryId);

    this.setData({
      isCategoryPage: true,
      activeCategoryId: categoryId,
      activeCategoryName: category ? category.name : ''
    });
  },

  // 返回到首页
  backToHome() {
    this.setData({
      isCategoryPage: false
    });
  },

  /**
   * 生命周期函数--监听页面初次渲染完成
   */
  onReady() {

  },

  /**
   * 生命周期函数--监听页面显示
   */
  onShow() {

  },

  /**
   * 生命周期函数--监听页面隐藏
   */
  onHide() {

  },

  /**
   * 生命周期函数--监听页面卸载
   */
  onUnload() {

  },

  /**
   * 页面相关事件处理函数--监听用户下拉动作
   */
  onPullDownRefresh() {

  },

  /**
   * 页面上拉触底事件的处理函数
   */
  onReachBottom() {

  },

  /**
   * 用户点击右上角分享
   */
  onShareAppMessage() {

  }
})