Page({
  data: {
    // 商品ID
    goodsId: null,
    // 商品详情数据（后续从后端获取）
    goodsDetail: null,
    // 购物车数量
    cartCount: 0,
    // 是否已收藏
    isFavorite: false
  },

  onLoad(options) {
    // 获取商品ID
    this.setData({
      goodsId: parseInt(options.id)
    });
    
    // 加载商品详情数据
    this.loadGoodsDetail();
    
    // 检查是否已收藏
    this.checkIsFavorite();
    
    // 获取购物车数量
    this.getCartCount();
  },

  onShow() {
    // 页面显示时更新购物车数量
    this.getCartCount();
  },

  // 加载商品详情（本地数据，后续替换为后端接口）
  loadGoodsDetail() {
    // 模拟从本地获取数据
    // 实际项目中应根据goodsId从后端获取
    const mockGoodsDetail = {
      id: this.data.goodsId,
      title: '',
      subtitle: '',
      price: '',
      originalPrice: '',
      currency: '¥',
      images: [],
      details: [],
      sales: 0,
      stock: 0,
      specifications: [],
      description: ''
    };

    // 根据商品ID填充模拟数据
    switch(this.data.goodsId) {
      case 101:
        mockGoodsDetail.title = '全合成机油 5W-30 4L装 汽车发动机润滑油';
        mockGoodsDetail.subtitle = '适用于多数车型，提供卓越保护';
        mockGoodsDetail.price = '199.00';
        mockGoodsDetail.originalPrice = '299.00';
        mockGoodsDetail.images = [
          'https://picsum.photos/750/750?random=10',
          'https://picsum.photos/750/750?random=11',
          'https://picsum.photos/750/750?random=12'
        ];
        mockGoodsDetail.details = [
          'https://picsum.photos/750/1200?random=13',
          'https://picsum.photos/750/1200?random=14'
        ];
        mockGoodsDetail.sales = 126;
        mockGoodsDetail.stock = 58;
        mockGoodsDetail.specifications = [
          { name: '容量', value: '4L' },
          { name: '类型', value: '全合成' },
          { name: '粘度', value: '5W-30' },
          { name: '适用车型', value: '通用型' }
        ];
        mockGoodsDetail.description = '全合成机油采用先进配方，为发动机提供卓越的润滑和保护，有效减少磨损，延长发动机寿命，提高燃油经济性。';
        break;
        
      case 102:
        mockGoodsDetail.title = '汽车空气滤清器 滤芯 适用多种车型';
        mockGoodsDetail.subtitle = '高效过滤，保护发动机';
        mockGoodsDetail.price = '89.00';
        mockGoodsDetail.originalPrice = '129.00';
        mockGoodsDetail.images = [
          'https://picsum.photos/750/750?random=20',
          'https://picsum.photos/750/750?random=21'
        ];
        mockGoodsDetail.details = [
          'https://picsum.photos/750/1200?random=22'
        ];
        mockGoodsDetail.sales = 89;
        mockGoodsDetail.stock = 120;
        mockGoodsDetail.specifications = [
          { name: '材质', value: '高效滤纸' },
          { name: '适用车型', value: '多种车型' },
          { name: '更换周期', value: '10000公里' }
        ];
        mockGoodsDetail.description = '高效空气滤清器，能有效过滤空气中的灰尘、杂质，为发动机提供洁净空气，保护发动机，提高燃烧效率。';
        break;
        
      // 其他商品ID的模拟数据...
      default:
        // 通用模拟数据
        mockGoodsDetail.title = '汽车用品通用商品';
        mockGoodsDetail.price = '159.00';
        mockGoodsDetail.originalPrice = '199.00';
        mockGoodsDetail.images = [
          'https://picsum.photos/750/750?random=99'
        ];
        mockGoodsDetail.sales = 50;
        mockGoodsDetail.stock = 80;
    }

    this.setData({
      goodsDetail: mockGoodsDetail
    });
  },

  // 从后端获取商品详情的预留方法
  fetchGoodsDetailFromBackend() {
    wx.request({
      url: `https://your-backend-url.com/api/goods/${this.data.goodsId}`,
      method: 'GET',
      success: (res) => {
        if (res.data.success) {
          this.setData({
            goodsDetail: res.data.data
          });
        }
      },
      fail: (err) => {
        console.error('获取商品详情失败', err);
      }
    });
  },

  // 购物车相关方法
  goToCart() {
    wx.navigateTo({
      url: '/pages/cart/cart'
    });
  },

  getCartCount() {
    const cartData = wx.getStorageSync('cartData') || [];
    const count = cartData.reduce((total, item) => total + item.quantity, 0);
    this.setData({
      cartCount: count
    });
  },

  addToCart() {
    if (!this.data.goodsDetail) return;

    const goods = this.data.goodsDetail;
    let cartData = wx.getStorageSync('cartData') || [];
    const existingItemIndex = cartData.findIndex(item => item.id === goods.id);
    
    if (existingItemIndex > -1) {
      cartData[existingItemIndex].quantity += 1;
    } else {
      cartData.push({
        ...goods,
        quantity: 1
      });
    }
    
    wx.setStorageSync('cartData', cartData);
    
    wx.showToast({
      title: '已加入购物车',
      icon: 'success',
      duration: 1500
    });
    
    this.getCartCount();
  },

  // 收藏相关方法
  checkIsFavorite() {
    const favorites = wx.getStorageSync('favorites') || [];
    const isFavorite = favorites.some(item => item.id === this.data.goodsId);
    this.setData({
      isFavorite: isFavorite
    });
  },

  toggleFavorite() {
    if (!this.data.goodsDetail) return;

    let favorites = wx.getStorageSync('favorites') || [];
    const goods = this.data.goodsDetail;
    const existingIndex = favorites.findIndex(item => item.id === goods.id);
    
    if (existingIndex > -1) {
      // 取消收藏
      favorites.splice(existingIndex, 1);
      this.setData({ isFavorite: false });
      wx.showToast({
        title: '已取消收藏',
        icon: 'none',
        duration: 1500
      });
    } else {
      // 添加收藏
      favorites.push({
        id: goods.id,
        title: goods.title,
        imgUrl: goods.images[0],
        price: goods.price,
        currency: goods.currency,
        sales: goods.sales
      });
      this.setData({ isFavorite: true });
      wx.showToast({
        title: '已添加到收藏',
        icon: 'success',
        duration: 1500
      });
    }
    
    wx.setStorageSync('favorites', favorites);
  },

  // 立即购买
  buyNow() {
    if (!this.data.goodsDetail) return;
    
    // 这里可以直接跳转到结算页面
    wx.showToast({
      title: '跳转到结算页面',
      icon: 'none'
    });
  }
});
